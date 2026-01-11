"""
Message routing and dispatch for vDC API protocol.

The vDC API uses protobuf Messages with a type field to distinguish
different message kinds. The MessageRouter:

1. Receives incoming protobuf Messages
2. Determines message type
3. Routes to appropriate handler
4. Handles message ID correlation (request/response)
5. Manages errors and unknown message types

Message Type Categories:
- vdSM → vDC requests (vdsm_Request*): Require responses
- vdSM → vDC notifications (vdsm_Send*): No response expected
- vDC → vdSM responses (vdc_Response*): Correlate with requests
- vDC → vdSM notifications (vdc_Send*): Autonomous notifications

Message Flow Examples:

Request/Response:
┌──────┐                                    ┌──────┐
│ vdSM │                                    │ vDC  │
└───┬──┘                                    └───┬──┘
    │                                           │
    │ vdsm_RequestGetProperty (msgId=123)      │
    │──────────────────────────────────────────>│
    │                                           │
    │                         (lookup property) │
    │                                           │
    │      vdc_ResponseGetProperty (msgId=123)  │
    │<──────────────────────────────────────────│
    │                                           │

Notification (No Response):
┌──────┐                                    ┌──────┐
│ vdSM │                                    │ vDC  │
└───┬──┘                                    └───┬──┘
    │                                           │
    │ vdsm_SendPing                             │
    │──────────────────────────────────────────>│
    │                                           │
    │      vdc_SendPong                         │
    │<──────────────────────────────────────────│
    │                                           │

The router maps message types to handler functions and ensures
proper response correlation using message IDs.
"""

import asyncio
import logging
from typing import Dict, Callable, Awaitable, Optional, Any
from proto.genericVDC_pb2 import (
    Message,
    VDSM_REQUEST_HELLO,
    VDSM_REQUEST_GET_PROPERTY,
    VDSM_REQUEST_SET_PROPERTY
)

logger = logging.getLogger(__name__)


class MessageRouter:
    """
    Routes incoming vDC API messages to registered handlers.
    
    The router acts as a dispatch table, mapping message types to
    handler functions. Each handler is responsible for:
    - Processing the message content
    - Returning a response Message (for requests)
    - Returning None (for notifications)
    
    Handler Signature:
        async def handler(message: Message) -> Optional[Message]:
            # Process message
            if message.type == Message.VDSM_REQUEST_HELLO:
                response = Message()
                response.type = Message.VDC_RESPONSE_HELLO
                # ... configure response ...
                return response
            return None  # For notifications
    
    Message ID Correlation:
    - Request messages have a message_id field
    - Responses must echo the same message_id
    - This allows matching responses to requests
    - The router automatically copies message_id to responses
    
    Usage:
        router = MessageRouter()
        
        # Register handlers for specific message types
        router.register(Message.VDSM_REQUEST_HELLO, handle_hello)
        router.register(Message.VDSM_REQUEST_GET_PROPERTY, handle_get_property)
        router.register(Message.VDSM_SEND_PING, handle_ping)
        
        # Route incoming message
        response = await router.route(incoming_message)
        if response:
            await send_message(writer, response)
    
    Attributes:
        handlers: Dictionary mapping message type to handler function
    """
    
    def __init__(self):
        """Initialize message router with empty handler registry."""
        # Message type -> handler function mapping
        # Key: Message.Type enum value (int)
        # Value: Async function taking Message and returning Optional[Message]
        self._handlers: Dict[int, Callable[[Message], Awaitable[Optional[Message]]]] = {}
        
        logger.debug("Message router initialized")
    
    def register(
        self,
        message_type: int,
        handler: Callable[[Message], Awaitable[Optional[Message]]]
    ) -> None:
        """
        Register a handler for a specific message type.
        
        Args:
            message_type: The Message.Type value to handle (e.g., Message.VDSM_REQUEST_HELLO)
            handler: Async function that processes the message and optionally returns a response
        
        Example:
            async def handle_hello(msg: Message) -> Optional[Message]:
                response = Message()
                response.type = Message.VDC_RESPONSE_HELLO
                response.message_id = msg.message_id
                response.vdc_response_hello.dSUID = "00000000..."
                return response
            
            router.register(Message.VDSM_REQUEST_HELLO, handle_hello)
        """
        if message_type in self._handlers:
            logger.warning(
                f"Replacing existing handler for message type {message_type}"
            )
        
        self._handlers[message_type] = handler
        logger.debug(f"Registered handler for message type {message_type}")
    
    def unregister(self, message_type: int) -> bool:
        """
        Unregister a handler for a message type.
        
        Args:
            message_type: The message type to unregister
        
        Returns:
            True if handler was removed, False if not registered
        """
        if message_type in self._handlers:
            del self._handlers[message_type]
            logger.debug(f"Unregistered handler for message type {message_type}")
            return True
        return False
    
    async def route(self, message: Message) -> Optional[Message]:
        """
        Route a message to its registered handler.
        
        Process:
        1. Extract message type from message
        2. Look up handler for that type
        3. Call handler with message
        4. If handler returns response, copy message_id
        5. Return response (or None)
        
        If no handler is registered for the message type, logs a warning
        and returns a generic error response.
        
        Args:
            message: The protobuf Message to route
        
        Returns:
            Response Message if handler returns one, None otherwise
        
        Raises:
            Exception: If handler raises an exception, it's logged and
                      a generic error response is returned
        """
        message_type = message.type
        message_id = message.message_id if message.HasField('message_id') else 0
        
        logger.debug(
            f"Routing message: type={message_type}, message_id={message_id}"
        )
        
        # Look up handler
        handler = self._handlers.get(message_type)
        
        if handler is None:
            # No handler registered for this message type
            logger.warning(
                f"No handler registered for message type {message_type}, "
                f"message_id={message_id}"
            )
            
            # For requests (which expect responses), return error
            if self._is_request_type(message_type):
                return self._create_error_response(
                    message_id,
                    f"Unsupported message type {message_type}"
                )
            
            # For notifications, just ignore
            return None
        
        # Call handler
        try:
            response = await handler(message)
            
            # If handler returned a response, ensure message_id is set
            if response:
                # Copy message_id from request to response for correlation
                # Note: Only set if request had a message_id
                if message.HasField('message_id'):
                    response.message_id = message.message_id
                
                logger.debug(
                    f"Handler returned response: type={response.type}, "
                    f"message_id={response.message_id if response.HasField('message_id') else 'none'}"
                )
            else:
                logger.debug("Handler returned no response (notification)")
            
            return response
        
        except Exception as e:
            # Handler raised an exception
            logger.error(
                f"Error in handler for message type {message_type}: {e}",
                exc_info=True
            )
            
            # Return error response if this was a request
            if self._is_request_type(message_type):
                return self._create_error_response(
                    message_id,
                    f"Internal error: {str(e)}"
                )
            
            return None
    
    def _is_request_type(self, message_type: int) -> bool:
        """
        Determine if a message type is a request (expects response).
        
        By vDC API convention:
        - vdsm_Request* types expect vdc_Response*
        - vdsm_Send* types are notifications (no response)
        
        Args:
            message_type: Message type value
        
        Returns:
            True if message type is a request requiring response
        """
        # Note: This mapping depends on your specific protobuf enum values
        # Adjust based on actual Message.Type enum in genericVDC_pb2.py
        
        # Common request types in vDC API:
        request_types = {
            VDSM_REQUEST_HELLO,
            VDSM_REQUEST_GET_PROPERTY,
            VDSM_REQUEST_SET_PROPERTY,
            # Add other request types as needed
        }
        
        return message_type in request_types
    
    def _create_error_response(
        self,
        message_id: int,
        error_message: str,
        error_code: int = 500  # Generic error code
    ) -> Message:
        """
        Create a generic error response message.
        
        Used when:
        - No handler is registered for a request
        - Handler raises an exception
        - Protocol error occurs
        
        Args:
            message_id: Message ID to echo in response
            error_message: Human-readable error description
            error_code: Numeric error code (vDC API result code)
        
        Returns:
            Generic error response Message
        """
        response = Message()
        response.type = Message.GENERIC_RESPONSE
        response.message_id = message_id
        
        # Set error in response
        # Note: Field structure depends on your protobuf definition
        generic_response = response.generic_response
        generic_response.code = error_code
        generic_response.description = error_message
        
        logger.debug(f"Created error response: code={error_code}, msg='{error_message}'")
        
        return response
    
    def register_handlers(
        self,
        handlers: Dict[int, Callable[[Message], Awaitable[Optional[Message]]]]
    ) -> None:
        """
        Register multiple handlers at once.
        
        Convenience method for bulk registration.
        
        Args:
            handlers: Dictionary mapping message type to handler function
        
        Example:
            router.register_handlers({
                Message.VDSM_REQUEST_HELLO: handle_hello,
                Message.VDSM_REQUEST_GET_PROPERTY: handle_get_property,
                Message.VDSM_SEND_PING: handle_ping,
            })
        """
        for message_type, handler in handlers.items():
            self.register(message_type, handler)
        
        logger.info(f"Registered {len(handlers)} message handlers")
    
    def get_registered_types(self) -> list[int]:
        """
        Get list of message types with registered handlers.
        
        Returns:
            List of message type values that have handlers
        """
        return list(self._handlers.keys())
    
    def has_handler(self, message_type: int) -> bool:
        """
        Check if a handler is registered for a message type.
        
        Args:
            message_type: Message type to check
        
        Returns:
            True if handler is registered, False otherwise
        """
        return message_type in self._handlers
