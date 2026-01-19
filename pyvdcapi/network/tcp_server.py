"""
TCP server implementation for vDC API protocol.

The vDC API uses a simple framing protocol over TCP:
- Each message is prefixed with a 2-byte length field (uint16, network byte order)
- The length indicates the size of the following protobuf message
- Multiple messages can be sent over a single connection
- Connection is persistent (not request/response like HTTP)

Message Format:
┌──────────────┬─────────────────────────────────┐
│ Length (2B)  │ Protobuf Message (variable)     │
│ uint16 BE    │ genericVDC.Message              │
└──────────────┴─────────────────────────────────┘

The server:
- Listens on a configurable port (default 8444)
- Accepts connections from vdSM (digitalSTROM manager)
- Enforces single connection policy (only one vdSM at a time)
- Handles message framing/deframing automatically
- Delegates message processing to a callback handler

Threading Model:
- Uses asyncio for asynchronous I/O
- Each connection runs in the event loop
- Message handlers can be async or sync
- Thread-safe for integration with sync code
"""

import asyncio
import struct
import logging
from datetime import datetime
from typing import Optional, Callable, Awaitable
from pyvdcapi.network.genericVDC_pb2 import Message

logger = logging.getLogger(__name__)

# Protocol constants
MESSAGE_LENGTH_SIZE = 2  # 2 bytes for uint16 length prefix
MESSAGE_LENGTH_FORMAT = "!H"  # Network byte order (big-endian) unsigned short
MAX_MESSAGE_SIZE = 65535  # Maximum size for a single message (uint16 max)
DEFAULT_PORT = 8444  # Standard vDC API port


class TCPServer:
    """
    Asyncio-based TCP server for vDC API protocol.

    Implements the vDC API message framing protocol:
    - 2-byte length prefix (uint16, big-endian)
    - Followed by protobuf-encoded Message

    The server enforces single-connection semantics: only one vdSM
    can be connected at a time. If a second connection attempt is made,
    it will be rejected (closed immediately).

    Usage:
        async def message_handler(message: Message, writer: StreamWriter):
            # Process message and optionally send response
            response = Message()
            response.type = Message.Type.GENERIC_RESPONSE
            # ... configure response ...
            await server.send_message(writer, response)

        server = TCPServer(port=8444, message_handler=message_handler)
        await server.start()
        # ... server runs ...
        await server.stop()

    Attributes:
        port: TCP port to listen on
        message_handler: Async callback for processing received messages
        host: Interface to bind to ('0.0.0.0' for all interfaces)
    """

    def __init__(
        self,
        port: int = DEFAULT_PORT,
        message_handler: Optional[Callable[[Message, asyncio.StreamWriter], Awaitable[None]]] = None,
        host: str = "0.0.0.0",
    ):
        """
        Initialize TCP server.

        Args:
            port: TCP port to listen on (default 8444)
            message_handler: Async callback that receives (message, writer) for each message.
                           The handler should process the message and send responses using
                           send_message(). If None, messages are logged but not processed.
            host: Network interface to bind to (default '0.0.0.0' for all interfaces)
        """
        self.port = port
        self.host = host
        self.message_handler = message_handler

        # Server state
        self._server: Optional[asyncio.Server] = None
        self._current_connection: Optional[asyncio.StreamWriter] = None
        self._connection_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info(f"TCP server initialized for {host}:{port}")

    async def start(self) -> None:
        """
        Start the TCP server.

        Begins listening for incoming connections on the configured port.
        This method returns immediately after starting; the server runs
        in the background event loop.

        Raises:
            OSError: If the port is already in use or cannot be bound
        """
        if self._running:
            logger.warning("Server already running")
            return

        # Create the server socket
        # Note: start_server automatically creates a socket, binds, and listens
        self._server = await asyncio.start_server(
            self._handle_client_connection,
            self.host,
            self.port,
            # Reuse address to avoid "Address already in use" after restart
            reuse_address=True,
        )

        self._running = True

        # Get the actual addresses the server is listening on
        addrs = ", ".join(str(sock.getsockname()) for sock in self._server.sockets)
        logger.info(f"vDC API server listening on {addrs}")

    async def stop(self) -> None:
        """
        Stop the TCP server.

        Closes all active connections and stops accepting new connections.
        Waits for ongoing message processing to complete.
        """
        if not self._running:
            logger.warning("Server not running")
            return

        logger.info("Stopping vDC API server...")
        self._running = False

        # Close current connection if any
        if self._current_connection:
            try:
                self._current_connection.close()
                await self._current_connection.wait_closed()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                self._current_connection = None

        # Cancel connection task if running
        if self._connection_task and not self._connection_task.done():
            self._connection_task.cancel()
            try:
                await self._connection_task
            except asyncio.CancelledError:
                pass

        # Close the server socket
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        logger.info("vDC API server stopped")

    async def _handle_client_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """
        Handle a new client connection.

        This is called automatically by asyncio.start_server for each
        incoming connection. It enforces the single-connection policy
        and processes messages from the client.

        Args:
            reader: Stream reader for receiving data from client
            writer: Stream writer for sending data to client
        """
        # Get client address for logging
        peername = writer.get_extra_info("peername")
        sockname = writer.get_extra_info("sockname")
        logger.info(f"New connection from {peername} -> local socket {sockname}")

        # Enforce single connection policy
        # If there's already a connection, reject this one
        if self._current_connection is not None:
            logger.warning(f"Rejecting connection from {peername} - " f"already connected to another vdSM")
            writer.close()
            await writer.wait_closed()
            return

        # Accept this connection
        self._current_connection = writer

        try:
            # Process messages from this connection until it closes
            await self._handle_messages(reader, writer)
        except Exception as e:
            logger.error(f"Error handling connection from {peername}: {e}", exc_info=True)
        finally:
            # Clean up connection
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

            # Mark as no longer connected
            if self._current_connection == writer:
                self._current_connection = None

            logger.info(f"Connection from {peername} closed")

    async def _handle_messages(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """
        Read and process messages from a client connection.

        This method runs in a loop, reading framed messages and
        dispatching them to the message handler. It continues until
        the connection is closed or an error occurs.

        Message Reading Process:
        1. Read 2-byte length prefix
        2. Read exactly that many bytes of protobuf data
        3. Decode protobuf Message
        4. Dispatch to message handler
        5. Repeat

        Args:
            reader: Stream reader for receiving data
            writer: Stream writer for sending responses
        """
        while self._running:
            try:
                peername = writer.get_extra_info("peername")
                logger.debug("%s Awaiting length prefix from %s", datetime.now().isoformat(), peername)
                # Step 1: Read the 2-byte length prefix
                # readexactly() raises IncompleteReadError if connection closes
                length_bytes = await reader.readexactly(MESSAGE_LENGTH_SIZE)

                # Step 2: Decode length as big-endian uint16
                message_length = struct.unpack(MESSAGE_LENGTH_FORMAT, length_bytes)[0]
                logger.debug("%s Read length %d from %s", datetime.now().isoformat(), message_length, peername)
                try:
                    logger.debug("Raw length bytes from %s: %s", peername, length_bytes.hex())
                except Exception:
                    pass

                # Sanity check: ensure length is reasonable
                if message_length == 0:
                    logger.warning("Received message with length 0, skipping")
                    continue

                if message_length > MAX_MESSAGE_SIZE:
                    logger.error(
                        f"Received message with invalid length {message_length}, " f"max is {MAX_MESSAGE_SIZE}"
                    )
                    # This is a protocol violation, close connection
                    break

                # Step 3: Read the protobuf message payload
                message_bytes = await reader.readexactly(message_length)
                try:
                    logger.debug("Raw message bytes from %s (first 128 bytes): %s", peername, message_bytes[:128].hex())
                except Exception:
                    pass

                # Step 4: Decode protobuf
                message = Message()
                try:
                    message.ParseFromString(message_bytes)
                except Exception as e:
                    try:
                        logger.error(
                            "Failed to parse protobuf message from %s: %s; raw bytes: %s",
                            peername,
                            e,
                            message_bytes.hex(),
                        )
                    except Exception:
                        logger.error(f"Failed to parse protobuf message: {e}")
                    # Continue trying to read more messages
                    continue

                # Print decoded message to console for debugging
                try:
                    print("RECV:", message, flush=True)
                except Exception:
                    logger.debug("Failed to print received message")

                logger.debug(
                    "%s Received message from %s: type=%s, messageId=%s, size=%d bytes",
                    datetime.now().isoformat(),
                    peername,
                    message.type,
                    message.message_id,
                    message_length,
                )

                # Step 5: Dispatch to handler
                if self.message_handler:
                    try:
                        await self.message_handler(message, writer)
                    except Exception as e:
                        logger.error(f"Error in message handler for message type {message.type}: {e}", exc_info=True)
                else:
                    logger.warning(f"No message handler configured, message type {message.type} not processed")

            except asyncio.IncompleteReadError:
                # Connection closed by client (clean shutdown)
                peer = writer.get_extra_info("peername")
                logger.info("Client closed connection from %s", peer)
                break

            except asyncio.CancelledError:
                # Task was cancelled (server stopping)
                logger.info("Message handling cancelled")
                break

            except Exception as e:
                # Unexpected error
                logger.error(f"Unexpected error reading message: {e}", exc_info=True)
                break

    @staticmethod
    async def send_message(writer: asyncio.StreamWriter, message: Message) -> None:
        """
        Send a protobuf message to a client.

        Handles framing: serializes the message and prepends the 2-byte length.

        Message Sending Process:
        1. Serialize message to bytes
        2. Calculate length
        3. Create 2-byte length prefix
        4. Write length + message to stream
        5. Flush to ensure immediate sending

        Args:
            writer: Stream writer to send the message to
            message: Protobuf Message to send

        Raises:
            Exception: If serialization or sending fails
        """
        try:
            # Prepare a copy of the message for serialization so we can
            # remove the envelope `message_id` when it is unset/zero.
            try:
                out_msg = Message()
                out_msg.CopyFrom(message)
                # In proto2, optional fields may be present; ensure we do
                # not serialize an explicit zero `message_id`.
                if out_msg.HasField("message_id") and out_msg.message_id == 0:
                    out_msg.ClearField("message_id")
            except Exception:
                out_msg = message

            # Print outgoing message that will actually be sent
            try:
                print("SEND:", out_msg, flush=True)
            except Exception:
                logger.debug("Failed to print outgoing message")

            # Step 1: Serialize protobuf to bytes
            message_bytes = out_msg.SerializeToString()
            message_length = len(message_bytes)

            # Step 2: Validate length fits in uint16
            if message_length > MAX_MESSAGE_SIZE:
                raise ValueError(f"Message too large: {message_length} bytes, " f"max is {MAX_MESSAGE_SIZE}")

            # Step 3: Create length prefix (2 bytes, big-endian)
            length_bytes = struct.pack(MESSAGE_LENGTH_FORMAT, message_length)

            # Step 4: Write length + message
            writer.write(length_bytes + message_bytes)

            # Step 5: Flush to send immediately
            # Note: drain() waits for the data to be sent, not just buffered
            await writer.drain()

            logger.debug(
                f"Sent message: type={message.type}, "
                f"messageId={message.message_id}, "
                f"size={message_length} bytes"
            )

        except Exception as e:
            logger.error(f"Failed to send message: {e}", exc_info=True)
            raise

    def is_connected(self) -> bool:
        """
        Check if a vdSM client is currently connected.

        Returns:
            True if a client is connected, False otherwise
        """
        return self._current_connection is not None and not self._current_connection.is_closing()

    def get_client_address(self) -> Optional[tuple]:
        """
        Get the address of the currently connected client.

        Returns:
            Tuple of (host, port) if connected, None otherwise
        """
        if self._current_connection:
            return self._current_connection.get_extra_info("peername")
        return None
