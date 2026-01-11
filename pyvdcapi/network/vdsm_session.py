"""
vdSM session management for vDC API protocol.

A vdSM (virtualDeviceConnector Smart Manager) session represents the
connection lifecycle between a vDC host and the digitalSTROM manager.

Session Lifecycle:
1. vdSM connects to vDC host TCP server
2. vdSM sends Hello message
3. vDC host responds with Hello (includes dSUID)
4. Session is established - normal message exchange
5. vdSM sends Bye or connection closes
6. Session ends

Session State Machine:
┌─────────────┐
│ DISCONNECTED│
└──────┬──────┘
       │ TCP connect
       ▼
┌─────────────┐
│  CONNECTED  │
└──────┬──────┘
       │ Hello received
       ▼
┌─────────────┐
│ HELLO_RCVD  │◄──┐
└──────┬──────┘   │
       │ Hello sent│ Ping/Pong
       ▼           │
┌─────────────┐   │
│  ACTIVE     │───┘
└──────┬──────┘
       │ Bye/disconnect
       ▼
┌─────────────┐
│ DISCONNECTED│
└─────────────┘

The session manager:
- Tracks session state
- Handles Hello/Bye protocol
- Manages ping/pong keepalive
- Enforces protocol requirements
- Provides session info for routing
"""

import asyncio
import time
import logging
from enum import Enum
from typing import Optional, Callable, Awaitable
from proto.genericVDC_pb2 import Message, VDC_RESPONSE_HELLO, VDC_SEND_PONG, VDC_SEND_PONG

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """
    vdSM session states.
    
    DISCONNECTED: No TCP connection active
    CONNECTED: TCP connection established, waiting for Hello
    HELLO_RECEIVED: Received Hello from vdSM, not yet responded
    ACTIVE: Full handshake complete, normal operation
    CLOSING: Bye received or sent, connection terminating
    """
    DISCONNECTED = 0
    CONNECTED = 1
    HELLO_RECEIVED = 2
    ACTIVE = 3
    CLOSING = 4


class VdSMSession:
    """
    Manages a single vdSM client session.
    
    Responsibilities:
    - Track session state (disconnected -> active -> closing)
    - Handle Hello/Bye handshake protocol
    - Manage ping/pong keepalive mechanism
    - Enforce protocol timing requirements
    - Provide session metadata
    
    The vDC API requires:
    - vdSM must send Hello as first message
    - vDC host must respond with Hello containing its dSUID
    - Ping messages should be answered with Pong
    - Sessions should timeout if no activity for extended period
    
    Usage:
        session = VdSMSession(vdc_host_dsuid="00000000...")
        
        # When TCP connection established
        await session.on_connected(writer)
        
        # When Hello received
        await session.on_hello_received(hello_message)
        hello_response = session.create_hello_response()
        
        # Normal operation
        assert session.is_active()
        
        # When Bye received or connection closes
        await session.on_disconnected()
    
    Attributes:
        vdc_host_dsuid: dSUID of the vDC host
        state: Current session state
        vdsm_version: Version string from vdSM Hello message
        connected_at: Timestamp when connection was established
    """
    
    # Protocol timing constants
    PING_INTERVAL = 60.0  # Send ping every 60 seconds if no activity
    PONG_TIMEOUT = 10.0   # Expect pong within 10 seconds
    HELLO_TIMEOUT = 30.0  # vdSM must send Hello within 30 seconds
    
    def __init__(
        self,
        vdc_host_dsuid: str,
        on_disconnected_callback: Optional[Callable[[], Awaitable[None]]] = None
    ):
        """
        Initialize vdSM session manager.
        
        Args:
            vdc_host_dsuid: dSUID of the vDC host (sent in Hello response)
            on_disconnected_callback: Optional async callback when session ends
        """
        self.vdc_host_dsuid = vdc_host_dsuid
        self.on_disconnected_callback = on_disconnected_callback
        
        # Session state
        self.state = SessionState.DISCONNECTED
        self.writer: Optional[asyncio.StreamWriter] = None
        
        # Session metadata
        self.vdsm_version: Optional[str] = None
        self.connected_at: Optional[float] = None
        self.last_activity: Optional[float] = None
        self.client_address: Optional[tuple] = None
        
        # Keepalive management
        self._ping_task: Optional[asyncio.Task] = None
        self._pong_received = asyncio.Event()
        self._hello_timer: Optional[asyncio.Task] = None
    
    async def on_connected(self, writer: asyncio.StreamWriter) -> None:
        """
        Handle new TCP connection established.
        
        Called when a vdSM client connects to the TCP server.
        Transitions state to CONNECTED and starts Hello timeout.
        
        Args:
            writer: Stream writer for sending messages to client
        """
        if self.state != SessionState.DISCONNECTED:
            logger.warning(f"Connection in unexpected state: {self.state}")
        
        self.state = SessionState.CONNECTED
        self.writer = writer
        self.connected_at = time.time()
        self.last_activity = self.connected_at
        
        # Get client address for logging
        self.client_address = writer.get_extra_info('peername')
        logger.info(f"vdSM session connected from {self.client_address}")
        
        # Start Hello timeout
        # vdSM must send Hello within HELLO_TIMEOUT seconds
        self._hello_timer = asyncio.create_task(self._hello_timeout())
    
    async def on_hello_received(self, hello_message: Message) -> None:
        """
        Handle Hello message from vdSM.
        
        The Hello message is the first message a vdSM must send.
        It contains the vdSM version and signals readiness for communication.
        
        After receiving Hello:
        1. Cancel Hello timeout
        2. Extract vdSM version info
        3. Transition to HELLO_RECEIVED state
        4. Application should send Hello response
        
        Args:
            hello_message: The vdsm_RequestHello message received
        """
        if self.state != SessionState.CONNECTED:
            logger.warning(
                f"Received Hello in unexpected state {self.state}, "
                f"expected CONNECTED"
            )
        
        # Cancel Hello timeout
        if self._hello_timer:
            self._hello_timer.cancel()
            self._hello_timer = None
        
        # Extract vdSM info
        # Note: The actual field depends on protobuf structure
        # Assuming vdsm_RequestHello has a version or similar field
        if hello_message.HasField('vdsm_request_hello'):
            hello_req = hello_message.vdsm_request_hello
            # Extract version if available in your protobuf definition
            # self.vdsm_version = hello_req.version if hasattr(hello_req, 'version') else "unknown"
            self.vdsm_version = "vdSM"  # Update based on actual protobuf fields
        
        self.state = SessionState.HELLO_RECEIVED
        self.last_activity = time.time()
        
        logger.info(f"Received Hello from vdSM version {self.vdsm_version}")
    
    def create_hello_response(self) -> Message:
        """
        Create Hello response message to send to vdSM.
        
        The vDC host must respond to Hello with its own Hello message
        containing the vDC host dSUID. This completes the handshake.
        
        Returns:
            Message with vdc_ResponseHello containing host dSUID
        """
        message = Message()
        message.type = VDC_RESPONSE_HELLO
        
        # Set up response with vDC host dSUID
        # Note: Actual field structure depends on your protobuf definition
        hello_response = message.vdc_response_hello
        hello_response.dSUID = self.vdc_host_dsuid
        
        logger.debug(f"Created Hello response with dSUID {self.vdc_host_dsuid}")
        
        return message
    
    async def on_hello_sent(self) -> None:
        """
        Handle successful sending of Hello response.
        
        After the vDC host sends Hello response:
        1. Session is now fully active
        2. Start ping/pong keepalive mechanism
        3. Normal message processing can begin
        """
        if self.state != SessionState.HELLO_RECEIVED:
            logger.warning(
                f"Sent Hello in unexpected state {self.state}, "
                f"expected HELLO_RECEIVED"
            )
        
        self.state = SessionState.ACTIVE
        self.last_activity = time.time()
        
        # Start keepalive ping mechanism
        self._ping_task = asyncio.create_task(self._keepalive_loop())
        
        logger.info("vdSM session now ACTIVE")
    
    async def on_ping_received(self) -> Message:
        """
        Handle Ping message from vdSM.
        
        The vDC API uses Ping/Pong for keepalive and connectivity testing.
        When a Ping is received, we must respond with Pong.
        
        Returns:
            Pong message to send back
        """
        self.last_activity = time.time()
        logger.debug("Received Ping, sending Pong")
        
        # Create Pong response
        message = Message()
        message.type = VDC_SEND_PONG
        
        return message
    
    def on_pong_received(self) -> None:
        """
        Handle Pong message from vdSM.
        
        Pong is a response to our Ping. This confirms the connection
        is still alive and responsive.
        """
        self.last_activity = time.time()
        self._pong_received.set()  # Signal that pong was received
        logger.debug("Received Pong")
    
    async def on_bye_received(self, bye_message: Message) -> None:
        """
        Handle Bye message from vdSM.
        
        Bye signals that vdSM is gracefully terminating the session.
        We should:
        1. Acknowledge the Bye
        2. Close the connection
        3. Clean up session state
        
        Args:
            bye_message: The vdsm_SendBye message received
        """
        logger.info("Received Bye from vdSM, terminating session")
        self.state = SessionState.CLOSING
        
        # Cleanup will happen in on_disconnected
    
    async def on_disconnected(self) -> None:
        """
        Handle connection closed (graceful or ungraceful).
        
        Called when the TCP connection closes for any reason:
        - Normal Bye from vdSM
        - Network error
        - Timeout
        - Server shutdown
        
        Cleans up all session resources and state.
        """
        logger.info(
            f"vdSM session disconnected from {self.client_address}, "
            f"state was {self.state}"
        )
        
        # Cancel background tasks
        if self._ping_task:
            self._ping_task.cancel()
            try:
                await self._ping_task
            except asyncio.CancelledError:
                pass
            self._ping_task = None
        
        if self._hello_timer:
            self._hello_timer.cancel()
            try:
                await self._hello_timer
            except asyncio.CancelledError:
                pass
            self._hello_timer = None
        
        # Reset session state
        self.state = SessionState.DISCONNECTED
        self.writer = None
        self.vdsm_version = None
        self.connected_at = None
        self.last_activity = None
        self.client_address = None
        
        # Notify callback if registered
        if self.on_disconnected_callback:
            try:
                await self.on_disconnected_callback()
            except Exception as e:
                logger.error(f"Error in disconnected callback: {e}", exc_info=True)
    
    def is_active(self) -> bool:
        """
        Check if session is in active state.
        
        Returns:
            True if session is fully active and ready for message exchange
        """
        return self.state == SessionState.ACTIVE
    
    def is_connected(self) -> bool:
        """
        Check if there's an active TCP connection.
        
        Returns:
            True if connected (any state except DISCONNECTED)
        """
        return self.state != SessionState.DISCONNECTED
    
    async def _hello_timeout(self) -> None:
        """
        Background task: Enforce Hello timeout.
        
        If vdSM doesn't send Hello within HELLO_TIMEOUT seconds
        after connecting, close the connection.
        
        This prevents resource exhaustion from clients that connect
        but never send the required Hello message.
        """
        try:
            await asyncio.sleep(self.HELLO_TIMEOUT)
            
            # If we're still in CONNECTED state, Hello wasn't received
            if self.state == SessionState.CONNECTED:
                logger.warning(
                    f"Hello timeout - no Hello received from {self.client_address} "
                    f"within {self.HELLO_TIMEOUT} seconds, closing connection"
                )
                
                # Close the connection
                if self.writer:
                    self.writer.close()
                    await self.writer.wait_closed()
                
                await self.on_disconnected()
        
        except asyncio.CancelledError:
            # Normal cancellation when Hello is received
            pass
    
    async def _keepalive_loop(self) -> None:
        """
        Background task: Send periodic Ping messages.
        
        Sends Ping every PING_INTERVAL seconds if no other activity.
        If Pong isn't received within PONG_TIMEOUT, considers connection dead.
        
        This ensures:
        - Detection of dead connections (network failures)
        - Prevention of idle connection timeouts by firewalls/proxies
        """
        try:
            while self.state == SessionState.ACTIVE:
                # Wait for ping interval
                await asyncio.sleep(self.PING_INTERVAL)
                
                # Check if we've had recent activity
                # If so, skip ping (no need to ping if actively communicating)
                if self.last_activity and (time.time() - self.last_activity) < self.PING_INTERVAL:
                    continue
                
                # Send Ping
                logger.debug("Sending Ping to vdSM")
                ping_message = Message()
                ping_message.type = Message.VDC_SEND_PING
                
                if self.writer:
                    from .tcp_server import TCPServer
                    await TCPServer.send_message(self.writer, ping_message)
                    
                    # Wait for Pong with timeout
                    self._pong_received.clear()
                    try:
                        await asyncio.wait_for(
                            self._pong_received.wait(),
                            timeout=self.PONG_TIMEOUT
                        )
                    except asyncio.TimeoutError:
                        logger.error(
                            f"Pong timeout - no response from vdSM within "
                            f"{self.PONG_TIMEOUT} seconds, closing connection"
                        )
                        
                        # Connection is dead
                        self.writer.close()
                        await self.writer.wait_closed()
                        await self.on_disconnected()
                        break
        
        except asyncio.CancelledError:
            # Normal cancellation on disconnect
            pass
        except Exception as e:
            logger.error(f"Error in keepalive loop: {e}", exc_info=True)
