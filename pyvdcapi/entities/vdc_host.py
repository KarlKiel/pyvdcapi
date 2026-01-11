"""
VdcHost - Top-level vDC API container.

The VdcHost is the main entry point for the vDC API. It:
- Runs a TCP server to accept vdSM connections
- Manages one or more virtual device connectors (Vdcs)
- Handles the vDC API protocol (Hello/Bye, properties, etc.)
- Persists configuration to YAML
- Coordinates message routing between vdSM and devices

Responsibilities Overview:
┌────────────────────────────────────────────────────────────┐
│ VdcHost                                                    │
├────────────────────────────────────────────────────────────┤
│ 1. Network Layer:                                          │
│    - TCP server on port 8444                               │
│    - vdSM session management                               │
│    - Message framing/deframing                             │
│                                                            │
│ 2. Protocol Layer:                                         │
│    - Hello/Bye handshake                                   │
│    - Ping/Pong keepalive                                   │
│    - Property get/set routing                              │
│    - vDC/vdSD announcement                                 │
│                                                            │
│ 3. Data Layer:                                             │
│    - vDC lifecycle management                              │
│    - YAML configuration persistence                        │
│    - Property tree management                              │
│                                                            │
│ 4. Device Layer:                                           │
│    - Route device notifications to vdSM                    │
│    - Route vdSM commands to devices                        │
└────────────────────────────────────────────────────────────┘

Message Flow:
1. vdSM connects → TCP server accepts → Create session
2. vdSM sends Hello → Respond with Hello (host dSUID)
3. vdSM requests property → Route to vDC/vdSD → Return value
4. Device state changes → Generate notification → Send to vdSM
5. vdSM sends Bye → Close session → Clean up

Usage Example:
```python
from pyvdcapi.entities import VdcHost
from pyvdcapi.core.constants import DSGroup

# Create vDC host
host = VdcHost(
    port=8444,
    mac_address="aa:bb:cc:dd:ee:ff",
    vendor_id="KarlKiel",
    persistence_file="config.yaml",
    name="My Home Automation"
)

# Create a vDC for lighting devices
light_vdc = host.create_vdc(
    name="Light Controller",
    model="Generic vDC v1.0"
)

# Add devices to the vDC
dimmer = light_vdc.create_vdsd(
    name="Living Room Dimmer",
    model="Dimmer 1ch",
    primary_group=DSGroup.YELLOW,
    output_type=DSOutputFunction.DIMMER
)

# Start the host
await host.start()

# Host now accepts vdSM connections and serves devices
# ...

# Graceful shutdown
await host.stop()
```

Threading Model:
- Runs in asyncio event loop
- All I/O is asynchronous
- Device callbacks can be sync or async
- Persistence is thread-safe
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable
from proto.genericVDC_pb2 import (
    Message,
    VDSM_REQUEST_HELLO,
    VDSM_SEND_BYE,
    VDSM_SEND_PING,
    VDC_SEND_PONG,
    VDSM_REQUEST_GET_PROPERTY,
    VDSM_REQUEST_SET_PROPERTY,
    VDSM_REQUEST_GENERIC_REQUEST,
    VDSM_SEND_REMOVE,
    VDSM_NOTIFICATION_CALL_SCENE,
    VDSM_NOTIFICATION_SAVE_SCENE,
    VDSM_NOTIFICATION_UNDO_SCENE,
    VDSM_NOTIFICATION_SET_LOCAL_PRIO,
    VDSM_NOTIFICATION_CALL_MIN_SCENE,
    VDSM_NOTIFICATION_IDENTIFY,
    VDSM_NOTIFICATION_SET_OUTPUT_CHANNEL_VALUE,
    VDSM_NOTIFICATION_DIM_CHANNEL,
    VDSM_NOTIFICATION_SET_CONTROL_VALUE,
)

from ..core.dsuid import DSUIDGenerator, DSUIDNamespace
from ..network.tcp_server import TCPServer
from ..network.vdsm_session import VdSMSession
from ..network.message_router import MessageRouter
from ..network.service_announcement import ServiceAnnouncer
from ..persistence.yaml_store import YAMLPersistence
from ..properties.common import CommonProperties
from ..properties.property_tree import PropertyTree

# Import Vdc class (placed after to avoid circular import)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .vdc import Vdc

logger = logging.getLogger(__name__)


class VdcHost:
    """
    Top-level container for vDC API implementation.
    
    The VdcHost represents the root of the vDC hierarchy. It owns:
    - TCP server for vdSM communication
    - Session manager for connection lifecycle
    - Message router for protocol handling
    - Persistence layer for configuration
    - Collection of vDCs (virtual device connectors)
    
    Protocol Implementation:
    - Responds to Hello with host dSUID and API version
    - Handles property get/set for host properties
    - Routes vDC/vdSD queries to appropriate entities
    - Manages vDC announcements when vdSM requests device discovery
    - Forwards device notifications to vdSM
    
    Configuration Persistence:
    - Saves host properties to YAML
    - Delegates vDC/vdSD persistence to child entities
    - Auto-saves on property changes (configurable)
    - Shadow backup for safe writes
    
    Attributes:
        port: TCP port for vdSM connections (default 8444)
        dsuid: digitalSTROM unique ID for this host
        session: Current vdSM session (None if disconnected)
        vdcs: Dictionary of vDCs managed by this host
    """
    
    # vDC API version implemented
    API_VERSION = "2.0"
    
    def __init__(
        self,
        name: str,
        port: int = 8444,
        mac_address: str = "",
        vendor_id: str = "KarlKiel",
        model: str = "vDC Host",
        model_uid: str = "vdc-host",
        model_version: str = "1.0",
        persistence_file: str = "vdc_config.yaml",
        auto_save: bool = True,
        enable_backup: bool = True,
        announce_service: bool = False,
        use_avahi: bool = False,
        **properties
    ):
        """
        Initialize vDC host.
        
        Args:
            name: User-specified name for the host (required)
            port: TCP port to listen on (default 8444)
            mac_address: MAC address for dSUID generation (format: "aa:bb:cc:dd:ee:ff")
                        If empty, uses system's default MAC
            vendor_id: Vendor identifier for dSUID namespace
            model: Human-readable model name (default: "vDC Host")
            model_uid: Unique model identifier (default: "vdc-host")
            model_version: Model version string (default: "1.0")
            persistence_file: Path to YAML configuration file
            auto_save: Automatically save on property changes
            enable_backup: Enable shadow backup (.bak) file
            announce_service: Enable mDNS/DNS-SD service announcement for auto-discovery (default: False)
            use_avahi: Use Avahi daemon instead of zeroconf library (requires Linux + root, default: False)
            **properties: Additional host properties
        
        Example:
            host = VdcHost(
                name="Home Automation Hub",
                port=8444,
                mac_address="00:11:22:33:44:55",
                vendor_id="MyCompany",
                model="HomeHub",
                model_uid="home-hub",
                model_version="2.0"
            )
        """
        # Store for later use in creating vDCs
        self._mac_address = mac_address
        self._vendor_id = vendor_id
        
        # Generate host dSUID
        # Note: dSUID must be deterministic (same MAC = same dSUID)
        # This allows vdSM to recognize the host across restarts
        dsuid_gen = DSUIDGenerator(mac_address, vendor_id)
        self.dsuid = dsuid_gen.generate(DSUIDNamespace.VDCHOST)
        
        logger.info(f"Initializing vDC host with dSUID: {self.dsuid}")
        
        # Network components
        self.port = port
        self._tcp_server: Optional[TCPServer] = None
        self._session: Optional[VdSMSession] = None
        
        # Message routing
        self._message_router = MessageRouter()
        self._setup_message_handlers()
        
        # Persistence
        self._persistence = YAMLPersistence(
            file_path=persistence_file,
            auto_save=auto_save,
            enable_backup=enable_backup
        )
        
        # Load or initialize host configuration
        host_config = self._persistence.get_vdc_host()
        if not host_config:
            # First time setup - save initial config
            host_config = {
                'dSUID': self.dsuid,
                'type': 'vDChost',
                'name': name,
                'model': model,
                'model_uid': model_uid,
                'model_version': model_version,
                'vendor_id': vendor_id,
                'api_version': self.API_VERSION,
                **properties
            }
            self._persistence.set_vdc_host(host_config)
        
        # Common properties (dSUID, name, model, etc.)
        # Use constructor parameters as defaults if not in persisted config
        # Extract explicitly handled properties from host_config to avoid duplicates
        extra_props = {k: v for k, v in host_config.items() 
                      if k not in ['name', 'model', 'model_uid', 'model_version', 'vendor_id', 'api_version']}
        
        self._common_props = CommonProperties(
            dsuid=self.dsuid,
            entity_type='vDChost',
            name=host_config.get('name', name),
            model=host_config.get('model', model),
            model_uid=host_config.get('model_uid', model_uid),
            model_version=host_config.get('model_version', model_version) or "",
            **extra_props
        )
        
        # vDC management
        # Key: vDC dSUID, Value: Vdc instance
        self._vdcs: Dict[str, 'Vdc'] = {}
        
        # Service announcement (optional)
        self._announce_service = announce_service
        self._service_announcer: Optional[ServiceAnnouncer] = None
        if announce_service:
            self._service_announcer = ServiceAnnouncer(
                port=self.port,
                dsuid=self.dsuid,
                use_avahi=use_avahi
            )
            logger.info(
                f"Service announcement enabled using {'Avahi' if use_avahi else 'zeroconf'}"
            )
        
        # State tracking
        self._running = False
        
        logger.info(
            f"vDC host initialized: name='{self._common_props.get_name()}', "
            f"model='{self._common_props.get_property('model')}'"
        )
    
    async def start(self) -> None:
        """
        Start the vDC host and begin accepting vdSM connections.
        
        This:
        1. Creates and starts the TCP server
        2. Begins listening for vdSM connections
        3. Loads any persisted vDCs from configuration
        4. Transitions to running state
        
        After calling start(), the host will:
        - Accept exactly one vdSM connection at a time
        - Respond to protocol messages (Hello, property queries, etc.)
        - Forward device notifications to vdSM
        
        Raises:
            OSError: If port is already in use
            RuntimeError: If host is already running
        """
        if self._running:
            raise RuntimeError("vDC host already running")
        
        logger.info(f"Starting vDC host on port {self.port}...")
        
        # Create TCP server with our message handler
        self._tcp_server = TCPServer(
            port=self.port,
            message_handler=self._handle_message,
            host='0.0.0.0'  # Listen on all interfaces
        )
        
        # Start listening
        await self._tcp_server.start()
        
        # Start service announcement if enabled
        if self._service_announcer:
            success = await self._service_announcer.start()
            if success:
                logger.info(f"Service announcement started: _ds-vdc._tcp on port {self.port}")
            else:
                logger.warning(
                    "Failed to start service announcement. "
                    "vDC host will still work but won't be auto-discoverable. "
                    "Install 'zeroconf' package: pip install zeroconf"
                )
        
        # Load persisted vDCs (implementation depends on Vdc class)
        # await self._load_vdcs()
        
        self._running = True
        
        logger.info(
            f"vDC host started successfully - "
            f"listening for vdSM connections on port {self.port}"
        )
    
    async def stop(self) -> None:
        """
        Stop the vDC host and close all connections.
        
        This:
        1. Closes active vdSM session (sends Bye if connected)
        2. Stops the TCP server
        3. Saves current configuration
        4. Transitions to stopped state
        
        This is a graceful shutdown - all pending operations complete
        before the host fully stops.
        """
        if not self._running:
            logger.warning("vDC host not running")
            return
        
        logger.info("Stopping vDC host...")
        
        # Close active session if any
        if self._session and self._session.is_connected():
            # Send Bye to vdSM
            bye_message = Message()
            bye_message.type = Message.VDC_SEND_BYE
            
            if self._session.writer:
                try:
                    await TCPServer.send_message(self._session.writer, bye_message)
                except Exception as e:
                    logger.error(f"Error sending Bye: {e}")
            
            await self._session.on_disconnected()
        
        # Stop service announcement
        if self._service_announcer:
            await self._service_announcer.stop()
            logger.info("Service announcement stopped")
        
        # Stop TCP server
        if self._tcp_server:
            await self._tcp_server.stop()
            self._tcp_server = None
        
        # Final save of configuration
        try:
            self._persistence.save()
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
        
        self._running = False
        
        logger.info("vDC host stopped")
    
    def save_config(self) -> None:
        """
        Save the complete vDC host configuration to persistence layer.
        
        This saves:
        - Host common properties (name, model, etc.)
        - All vDC configurations
        - All vdSD configurations (via their respective vDCs)
        
        The save is typically automatic (when auto_save=True), but this
        method can be called manually to force a save at any time.
        
        Example:
            # Make changes to host
            host._common_props.set('name', 'Updated Host Name')
            
            # Manually save all configurations
            host.save_config()
        """
        # Save host configuration
        host_config = {
            'dSUID': self.dsuid,
            'type': 'vDChost',
            **self._common_props.to_dict()
        }
        self._persistence.set_vdc_host(host_config)
        
        # Force save to file
        self._persistence.save()
        
        logger.info(f"Saved configuration for vDC host {self.dsuid}")
    
    def _setup_message_handlers(self) -> None:
        """
        Register message handlers with the router.
        
        This maps each vDC API message type to the appropriate handler method.
        Handlers are called when messages of that type are received from vdSM.
        
        Message Handler Responsibilities:
        - Validate message content
        - Process the request/command
        - Generate appropriate response
        - Update state as needed
        
        The router automatically handles:
        - Message ID correlation (request/response matching)
        - Error responses for exceptions
        - Unknown message type handling
        """
        # Register handlers for each message type
        # Note: Using lambda to bind self to handler methods
        handlers = {
            # Session management
            VDSM_REQUEST_HELLO: self._handle_hello,
            VDSM_SEND_BYE: self._handle_bye,
            VDSM_SEND_PING: self._handle_ping,
            VDC_SEND_PONG: self._handle_pong,
            
            # Property access
            VDSM_REQUEST_GET_PROPERTY: self._handle_get_property,
            VDSM_REQUEST_SET_PROPERTY: self._handle_set_property,
            
            # Generic requests
            VDSM_REQUEST_GENERIC_REQUEST: self._handle_generic_request,
            
            # Device management
            VDSM_SEND_REMOVE: self._handle_remove,
            
            # Scene operations (notifications - no response expected)
            VDSM_NOTIFICATION_CALL_SCENE: self._handle_call_scene,
            VDSM_NOTIFICATION_SAVE_SCENE: self._handle_save_scene,
            VDSM_NOTIFICATION_UNDO_SCENE: self._handle_undo_scene,
            VDSM_NOTIFICATION_SET_LOCAL_PRIO: self._handle_set_local_prio,
            VDSM_NOTIFICATION_CALL_MIN_SCENE: self._handle_call_min_scene,
            
            # Device identification
            VDSM_NOTIFICATION_IDENTIFY: self._handle_identify,
            
            # Output control
            VDSM_NOTIFICATION_SET_OUTPUT_CHANNEL_VALUE: self._handle_set_output_channel_value,
            VDSM_NOTIFICATION_DIM_CHANNEL: self._handle_dim_channel,
            VDSM_NOTIFICATION_SET_CONTROL_VALUE: self._handle_set_control_value,
        }
        
        self._message_router.register_handlers(handlers)
        
        logger.debug(f"Registered {len(handlers)} message handlers")
    
    async def _handle_message(
        self,
        message: Message,
        writer: asyncio.StreamWriter
    ) -> None:
        """
        Handle incoming message from vdSM.
        
        This is the callback registered with TCPServer. It:
        1. Routes message through the message router
        2. Gets response from handler
        3. Sends response back to vdSM (if any)
        
        The actual message processing is delegated to specific handler
        methods registered with the message router.
        
        Args:
            message: Protobuf message received from vdSM
            writer: Stream writer to send response to
        """
        try:
            # Route message to appropriate handler
            response = await self._message_router.route(message)
            
            # Send response if handler returned one
            if response:
                await TCPServer.send_message(writer, response)
        
        except Exception as e:
            # This should rarely happen as router catches handler exceptions
            logger.error(f"Unexpected error handling message: {e}", exc_info=True)
    
    async def _handle_hello(self, message: Message) -> Optional[Message]:
        """
        Handle Hello request from vdSM.
        
        The Hello message is the first message vdSM sends after connecting.
        It initiates the session and provides vdSM version information.
        
        Response includes:
        - vDC host dSUID (identifies this host uniquely)
        - API version (protocol version we support)
        - Optional host name/model
        
        Args:
            message: vdsm_RequestHello message
        
        Returns:
            vdc_ResponseHello message with host identification
        """
        logger.info("Received Hello from vdSM")
        
        # Create or update session
        if not self._session:
            self._session = VdSMSession(
                vdc_host_dsuid=self.dsuid,
                on_disconnected_callback=self._on_session_disconnected
            )
        
        # Notify session of Hello
        await self._session.on_hello_received(message)
        
        # Create Hello response with message_id from request
        response = self._session.create_hello_response(message)
        
        # Add additional host info to response if available
        # (Depends on your protobuf structure)
        
        # Mark session as active
        await self._session.on_hello_sent()
        
        logger.info("Sent Hello response to vdSM - session now ACTIVE")
        
        return response
    
    async def _handle_bye(self, message: Message) -> Optional[Message]:
        """
        Handle Bye notification from vdSM.
        
        Bye signals that vdSM is disconnecting. We should:
        1. Acknowledge the Bye
        2. Clean up session
        3. Close connection
        
        Args:
            message: vdsm_SendBye message
        
        Returns:
            Generic acknowledgment response (optional)
        """
        logger.info("Received Bye from vdSM")
        
        if self._session:
            await self._session.on_bye_received(message)
        
        # Note: Connection cleanup happens in TCP server
        
        return None  # No response needed for Bye
    
    async def _handle_ping(self, message: Message) -> Optional[Message]:
        """
        Handle Ping from vdSM.
        
        Ping/Pong is used for keepalive and connectivity testing.
        We must respond with Pong.
        
        Args:
            message: vdsm_SendPing message
        
        Returns:
            vdc_SendPong message
        """
        logger.debug("Received Ping from vdSM, sending Pong")
        
        if self._session:
            return await self._session.on_ping_received(message)
        
        # If no session, still respond with Pong
        response = Message()
        response.type = VDC_SEND_PONG
        response.message_id = message.message_id
        return response
    
    def _handle_pong(self, message: Message) -> None:
        """
        Handle Pong from vdSM.
        
        Pong is a response to our Ping. This confirms connectivity.
        
        Args:
            message: vdc_SendPong message
        """
        logger.debug("Received Pong from vdSM")
        
        if self._session:
            self._session.on_pong_received()
    
    async def _handle_get_property(self, message: Message) -> Optional[Message]:
        """
        Handle property get request from vdSM.
        
        Property queries can target:
        - vDC host properties (this entity)
        - vDC properties (specific vDC)
        - vdSD properties (specific device)
        
        The request includes:
        - dSUID: Which entity to query
        - query: Property path to retrieve (PropertyElement tree)
        
        Process:
        1. Extract dSUID from request
        2. Determine if it's host/vDC/vdSD
        3. Route to appropriate entity
        4. Build property tree response
        5. Return properties
        
        Args:
            message: vdsm_RequestGetProperty message
        
        Returns:
            vdc_ResponseGetProperty with property tree
        """
        get_prop = message.vdsm_request_get_property
        
        # Extract target dSUID and query
        target_dsuid = get_prop.dSUID if get_prop.HasField('dSUID') else self.dsuid
        query = get_prop.query  # PropertyElement tree specifying what to get
        
        logger.debug(f"Property get request for dSUID {target_dsuid}")
        
        # Determine target entity
        if target_dsuid == self.dsuid:
            # Query is for vDC host properties
            properties = self._get_host_properties(query)
        elif target_dsuid in self._vdcs:
            # Query is for a specific vDC
            properties = self._vdcs[target_dsuid].get_properties(query)
        else:
            # Query might be for a vdSD - search in all vDCs
            properties = self._get_vdsd_properties(target_dsuid, query)
        
        # Build response
        response = Message()
        response.type = Message.VDC_RESPONSE_GET_PROPERTY
        response.message_id = message.message_id
        
        resp_get_prop = response.vdc_response_get_property
        resp_get_prop.properties.CopyFrom(properties)
        
        logger.debug(f"Returning properties for {target_dsuid}")
        
        return response
    
    async def _handle_set_property(self, message: Message) -> Optional[Message]:
        """
        Handle property set request from vdSM.
        
        Allows vdSM to modify writable properties of entities.
        
        The request includes:
        - dSUID: Which entity to modify
        - properties: PropertyElement tree with new values
        
        Process:
        1. Extract dSUID and properties
        2. Validate properties are writable
        3. Route to appropriate entity
        4. Apply changes
        5. Persist if needed
        6. Return success/error
        
        Args:
            message: vdsm_RequestSetProperty message
        
        Returns:
            Generic response with success/error code
        """
        set_prop = message.vdsm_request_set_property
        
        # Extract target dSUID and properties to set
        target_dsuid = set_prop.dSUID if set_prop.HasField('dSUID') else self.dsuid
        properties = set_prop.properties  # PropertyElement tree
        
        logger.debug(f"Property set request for dSUID {target_dsuid}")
        
        try:
            # Determine target and apply changes
            if target_dsuid == self.dsuid:
                # Set vDC host properties
                self._set_host_properties(properties)
            elif target_dsuid in self._vdcs:
                # Set vDC properties
                self._vdcs[target_dsuid].set_properties(properties)
            else:
                # Set vdSD properties
                self._set_vdsd_properties(target_dsuid, properties)
            
            # Build success response
            response = Message()
            response.type = Message.GENERIC_RESPONSE
            response.message_id = message.message_id
            
            generic_resp = response.generic_response
            generic_resp.code = 0  # Success
            generic_resp.description = "OK"
            
            logger.debug(f"Properties set successfully for {target_dsuid}")
            
            return response
        
        except Exception as e:
            # Build error response
            logger.error(f"Error setting properties for {target_dsuid}: {e}")
            
            response = Message()
            response.type = Message.GENERIC_RESPONSE
            response.message_id = message.message_id
            
            generic_resp = response.generic_response
            generic_resp.code = 500  # Error
            generic_resp.description = str(e)
            
            return response
    
    def _get_host_properties(self, query) -> Any:
        """
        Get vDC host properties based on query.
        
        Args:
            query: PropertyElement tree specifying what to retrieve
        
        Returns:
            PropertyElement tree with requested properties
        """
        # Convert common properties to protobuf PropertyElement
        host_dict = self._common_props.to_dict()
        
        # Add host-specific properties
        host_dict['api_version'] = self.API_VERSION
        host_dict['vdc_count'] = len(self._vdcs)
        host_dict['connected'] = self._session.is_connected() if self._session else False
        
        # Convert to PropertyElement tree
        return PropertyTree.to_protobuf(host_dict)
    
    def _set_host_properties(self, properties) -> None:
        """
        Set vDC host properties from PropertyElement tree.
        
        Args:
            properties: PropertyElement tree with new values
        """
        # Convert PropertyElement to dict
        prop_dict = PropertyTree.from_protobuf(properties)
        
        # Update common properties
        self._common_props.update(prop_dict)
        
        # Persist changes
        host_config = self._common_props.to_dict()
        self._persistence.set_vdc_host(host_config)
    
    def _get_vdsd_properties(self, dsuid: str, query) -> Any:
        """
        Get vdSD properties by searching all vDCs.
        
        Args:
            dsuid: vdSD dSUID to find
            query: Property query
        
        Returns:
            PropertyElement tree with properties
        
        Raises:
            ValueError: If vdSD not found
        """
        # Search all vDCs for this vdSD
        for vdc in self._vdcs.values():
            if vdc.has_vdsd(dsuid):
                return vdc.get_vdsd_properties(dsuid, query)
        
        raise ValueError(f"vdSD with dSUID {dsuid} not found")
    
    def _set_vdsd_properties(self, dsuid: str, properties) -> None:
        """
        Set vdSD properties by finding the owning vDC.
        
        Args:
            dsuid: vdSD dSUID
            properties: PropertyElement tree
        
        Raises:
            ValueError: If vdSD not found
        """
        # Search all vDCs for this vdSD
        for vdc in self._vdcs.values():
            if vdc.has_vdsd(dsuid):
                vdc.set_vdsd_properties(dsuid, properties)
                return
        
        raise ValueError(f"vdSD with dSUID {dsuid} not found")
    
    async def _on_session_disconnected(self) -> None:
        """
        Callback when vdSM session ends.
        
        Called when the TCP connection closes or Bye is received.
        Cleans up session state.
        """
        logger.info("vdSM session disconnected")
        self._session = None
    
    def create_vdc(
        self,
        name: str,
        model: str,
        model_uid: Optional[str] = None,
        model_version: str = "1.0",
        vendor_id: Optional[str] = None,
        mac_address: Optional[str] = None,
        **properties
    ) -> 'Vdc':
        """
        Create a new virtual device connector (vDC).
        
        A vDC represents a collection of related devices, typically
        from the same technology or manufacturer. Examples:
        - Light controller vDC for Philips Hue lights
        - Heating vDC for thermostats
        - Audio vDC for speakers
        
        Args:
            name: vDC name (e.g., "Hue Bridge")
            model: vDC model identifier (human-readable)
            model_uid: Unique model identifier for vdSM (auto-generated from model if not provided)
            model_version: Model version string (default: "1.0")
            vendor_id: Vendor ID (defaults to host's vendor)
            mac_address: MAC for dSUID (defaults to host's MAC)
            **properties: Additional vDC properties
        
        Returns:
            Newly created Vdc instance
        
        Example:
            light_vdc = host.create_vdc(
                name="Hue Bridge",
                model="Philips Hue vDC",
                model_uid="philips-hue-vdc",
                model_version="2.0",
                vendor="Philips"
            )
        """
        # Import here to avoid circular dependency
        from .vdc import Vdc
        
        # Use host's MAC/vendor if not specified
        if mac_address is None:
            # Extract from host's generator (stored during init)
            mac_address = self._mac_address
        if vendor_id is None:
            vendor_id = self._vendor_id
        
        # Generate modelUID if not provided
        # modelUID must be unique identifier for this functional model
        if model_uid is None:
            # Auto-generate from model name: "MyVDC v1.0" -> "myvdc-v1-0"
            model_uid = model.lower().replace(' ', '-').replace('.', '-')
        
        # Calculate enumeration (number of existing vDCs)
        enumeration = len(self._vdcs)
        
        # Create vDC instance
        vdc = Vdc(
            host=self,
            mac_address=mac_address,
            vendor_id=vendor_id,
            persistence=self._persistence,
            name=name,
            model=model,
            model_uid=model_uid,
            model_version=model_version,
            enumeration=enumeration,
            **properties
        )
        
        # Add to collection
        self._vdcs[vdc.dsuid] = vdc
        
        logger.info(f"Created vDC: {vdc}")
        
        return vdc
    
    def is_running(self) -> bool:
        """Check if host is running."""
        return self._running
    
    def is_connected(self) -> bool:
        """Check if vdSM is connected."""
        return self._session is not None and self._session.is_active()
    
    def get_vdc(self, dsuid: str) -> Optional['Vdc']:
        """
        Get vDC by dSUID.
        
        Args:
            dsuid: vDC dSUID
        
        Returns:
            Vdc instance or None if not found
        """
        return self._vdcs.get(dsuid)
    
    def get_all_vdcs(self) -> List['Vdc']:
        """
        Get all vDCs managed by this host.
        
        Returns:
            List of Vdc instances
        """
        return list(self._vdcs.values())
    
    # ===================================================================
    # Additional Message Handlers (Scene, Output, Device Management)
    # ===================================================================
    
    async def _handle_call_scene(self, message: Message, session: 'VdsmSession') -> Optional[Message]:
        """
        Handle VDSM_NOTIFICATION_CALL_SCENE message.
        
        This is a notification (no response required) to activate a scene on a device.
        Scenes represent predefined configurations (e.g., "Deep Off", "Preset 1").
        
        Args:
            message: Incoming VDSM_NOTIFICATION_CALL_SCENE protobuf
            session: Active vdSM session
        
        Returns:
            None (notifications don't send responses)
        
        Message Flow:
            vdSM → vDC: Call scene on device/group
            vDC: Execute scene internally
            vDC → vdSM: Push property notification if values changed
        
        Property Access:
            message.vdsm_notification_call_scene.dSUID - Device dSUID
            message.vdsm_notification_call_scene.scene - Scene number (0-127)
            message.vdsm_notification_call_scene.force - Force execution even if already active
            message.vdsm_notification_call_scene.group - Group filter (optional)
            message.vdsm_notification_call_scene.zone_id - Zone filter (optional)
        """
        try:
            notification = message.vdsm_notification_call_scene
            dsuid = notification.dSUID
            scene = notification.scene
            force = notification.force if notification.HasField('force') else False
            
            logger.info(f"Call scene {scene} on device {dsuid} (force={force})")
            
            # Find the device across all vDCs
            device = None
            for vdc in self._vdcs.values():
                if vdc.has_vdsd(dsuid):
                    device = vdc.get_vdsd(dsuid)
                    break
            
            if device is None:
                logger.warning(f"Device {dsuid} not found for CallScene")
                return None
            
            # Execute scene on device
            # This will apply output values, trigger callbacks, etc.
            await device.call_scene(scene, force=force)
            
            # Device's internal callbacks should trigger push notifications
            # if output values changed
            
        except Exception as e:
            logger.error(f"Error handling CallScene: {e}", exc_info=True)
        
        # Notifications don't send responses
        return None
    
    async def _handle_save_scene(self, message: Message, session: 'VdsmSession') -> Optional[Message]:
        """
        Handle VDSM_NOTIFICATION_SAVE_SCENE message.
        
        Save current device output values to a scene number.
        This captures the "snapshot" of current state for later recall.
        
        Args:
            message: Incoming VDSM_NOTIFICATION_SAVE_SCENE protobuf
            session: Active vdSM session
        
        Returns:
            None (notifications don't send responses)
        
        Message Flow:
            vdSM → vDC: Save current state to scene
            vDC: Capture current output values
            vDC: Persist scene configuration
            vDC → vdSM: Push property notification (scenes updated)
        
        Property Access:
            message.vdsm_notification_save_scene.dSUID - Device dSUID
            message.vdsm_notification_save_scene.scene - Scene number to save to
            message.vdsm_notification_save_scene.group - Group filter (optional)
            message.vdsm_notification_save_scene.zone_id - Zone filter (optional)
        """
        try:
            notification = message.vdsm_notification_save_scene
            dsuid = notification.dSUID
            scene = notification.scene
            
            logger.info(f"Save scene {scene} for device {dsuid}")
            
            # Find device
            device = None
            for vdc in self._vdcs.values():
                if vdc.has_vdsd(dsuid):
                    device = vdc.get_vdsd(dsuid)
                    break
            
            if device is None:
                logger.warning(f"Device {dsuid} not found for SaveScene")
                return None
            
            # Save current state as scene
            await device.save_scene(scene)
            
            # Persistence is automatically triggered in device.save_scene()
            # Push notification should be sent by device callbacks
            
        except Exception as e:
            logger.error(f"Error handling SaveScene: {e}", exc_info=True)
        
        return None
    
    async def _handle_undo_scene(self, message: Message, session: 'VdsmSession') -> Optional[Message]:
        """
        Handle VDSM_NOTIFICATION_UNDO_SCENE message.
        
        Undo the last scene call and restore previous state.
        Useful for "oops, didn't mean to do that" situations.
        
        Args:
            message: Incoming VDSM_NOTIFICATION_UNDO_SCENE protobuf
            session: Active vdSM session
        
        Returns:
            None (notifications don't send responses)
        
        Message Flow:
            vdSM → vDC: Undo last scene
            vDC: Restore previous output values from undo stack
            vDC → vdSM: Push property notification (values changed)
        
        Property Access:
            message.vdsm_notification_undo_scene.dSUID - Device dSUID
            message.vdsm_notification_undo_scene.group - Group filter (optional)
            message.vdsm_notification_undo_scene.zone_id - Zone filter (optional)
        """
        try:
            notification = message.vdsm_notification_undo_scene
            dsuid = notification.dSUID
            
            logger.info(f"Undo scene for device {dsuid}")
            
            # Find device
            device = None
            for vdc in self._vdcs.values():
                if vdc.has_vdsd(dsuid):
                    device = vdc.get_vdsd(dsuid)
                    break
            
            if device is None:
                logger.warning(f"Device {dsuid} not found for UndoScene")
                return None
            
            # Undo last scene
            await device.undo_scene()
            
            # Device callbacks will send push notifications
            
        except Exception as e:
            logger.error(f"Error handling UndoScene: {e}", exc_info=True)
        
        return None
    
    async def _handle_set_output_channel_value(
        self, 
        message: Message, 
        session: 'VdsmSession'
    ) -> Optional[Message]:
        """
        Handle VDSM_NOTIFICATION_SET_OUTPUT_CHANNEL_VALUE message.
        
        Set a specific output channel value (brightness, hue, etc.).
        This is for direct control outside of scenes.
        
        Args:
            message: Incoming VDSM_NOTIFICATION_SET_OUTPUT_CHANNEL_VALUE protobuf
            session: Active vdSM session
        
        Returns:
            None (notifications don't send responses)
        
        Message Flow:
            vdSM → vDC: Set channel X to value Y
            vDC: Update channel value (with transitions if specified)
            vDC → vdSM: Push property notification (channel value changed)
        
        Property Access:
            message.vdsm_notification_set_output_channel_value.dSUID - Device dSUID
            message.vdsm_notification_set_output_channel_value.channel - Channel type (0=brightness, etc.)
            message.vdsm_notification_set_output_channel_value.channelId - Channel ID (API v3+)
            message.vdsm_notification_set_output_channel_value.value - New value (0-100)
            message.vdsm_notification_set_output_channel_value.apply_now - Apply immediately (optional)
            message.vdsm_notification_set_output_channel_value.transition_time - Transition time in ms (optional)
        """
        try:
            notification = message.vdsm_notification_set_output_channel_value
            dsuid = notification.dSUID
            
            # Support both old 'channel' and new 'channelId'
            if notification.HasField('channelId'):
                channel_id = notification.channelId
            else:
                channel_id = notification.channel
            
            value = notification.value
            apply_now = notification.apply_now if notification.HasField('apply_now') else True
            transition_time = notification.transition_time if notification.HasField('transition_time') else 0
            
            logger.info(f"Set channel {channel_id} to {value} on device {dsuid} "
                       f"(apply={apply_now}, transition={transition_time}ms)")
            
            # Find device
            device = None
            for vdc in self._vdcs.values():
                if vdc.has_vdsd(dsuid):
                    device = vdc.get_vdsd(dsuid)
                    break
            
            if device is None:
                logger.warning(f"Device {dsuid} not found for SetOutputChannelValue")
                return None
            
            # Get output container
            output = device.get_output()
            if output is None:
                logger.warning(f"Device {dsuid} has no output channels")
                return None
            
            # Set channel value
            output.set_channel_value(
                channel_id, 
                value,
                apply_now=apply_now,
                transition_time_ms=transition_time
            )
            
            # Output callbacks will trigger push notifications
            
        except Exception as e:
            logger.error(f"Error handling SetOutputChannelValue: {e}", exc_info=True)
        
        return None
    
    async def _handle_dim_channel(self, message: Message, session: 'VdsmSession') -> Optional[Message]:
        """
        Handle VDSM_NOTIFICATION_DIM_CHANNEL message.
        
        Start/stop continuous dimming (up/down) of a channel.
        Typically triggered by holding a button.
        
        Args:
            message: Incoming VDSM_NOTIFICATION_DIM_CHANNEL protobuf
            session: Active vdSM session
        
        Returns:
            None (notifications don't send responses)
        
        Message Flow:
            vdSM → vDC: Start dimming channel up/down
            vDC: Begin continuous value adjustment
            vDC → vdSM: Push property notifications as value changes
            
            vdSM → vDC: Stop dimming (mode=stop)
            vDC: Halt dimming, maintain current value
        
        Property Access:
            message.vdsm_notification_dim_channel.dSUID - Device dSUID
            message.vdsm_notification_dim_channel.channel - Channel to dim
            message.vdsm_notification_dim_channel.channelId - Channel ID (API v3+)
            message.vdsm_notification_dim_channel.mode - Dimming mode:
                0 = stop
                1 = start dimming down
                2 = start dimming up
        """
        try:
            notification = message.vdsm_notification_dim_channel
            dsuid = notification.dSUID
            
            # Support both old and new channel identifiers
            if notification.HasField('channelId'):
                channel_id = notification.channelId
            else:
                channel_id = notification.channel
            
            mode = notification.mode  # 0=stop, 1=down, 2=up
            
            logger.info(f"Dim channel {channel_id} mode {mode} on device {dsuid}")
            
            # Find device
            device = None
            for vdc in self._vdcs.values():
                if vdc.has_vdsd(dsuid):
                    device = vdc.get_vdsd(dsuid)
                    break
            
            if device is None:
                logger.warning(f"Device {dsuid} not found for DimChannel")
                return None
            
            # Get output container
            output = device.get_output()
            if output is None:
                logger.warning(f"Device {dsuid} has no output channels")
                return None
            
            # Execute dimming operation
            if mode == 0:  # Stop dimming
                output.stop_dimming(channel_id)
            elif mode == 1:  # Dim down
                output.start_dimming(channel_id, direction='down')
            elif mode == 2:  # Dim up
                output.start_dimming(channel_id, direction='up')
            else:
                logger.warning(f"Unknown dim mode: {mode}")
            
        except Exception as e:
            logger.error(f"Error handling DimChannel: {e}", exc_info=True)
        
        return None
    
    async def _handle_identify(self, message: Message, session: 'VdsmSession') -> Optional[Message]:
        """
        Handle VDSM_NOTIFICATION_IDENTIFY message.
        
        Request device to identify itself (blink, beep, etc.).
        Useful for finding physical devices during commissioning.
        
        Args:
            message: Incoming VDSM_NOTIFICATION_IDENTIFY protobuf
            session: Active vdSM session
        
        Returns:
            None (notifications don't send responses)
        
        Message Flow:
            vdSM → vDC: Identify device
            vDC: Trigger identification (blink LED, beep, etc.)
            vDC: Execute for specified duration
        
        Property Access:
            message.vdsm_notification_identify.dSUID - Device dSUID
            message.vdsm_notification_identify.duration - Identification duration in seconds (optional)
        """
        try:
            notification = message.vdsm_notification_identify
            dsuid = notification.dSUID
            duration = notification.duration if notification.HasField('duration') else 3.0
            
            logger.info(f"Identify device {dsuid} for {duration}s")
            
            # Find device
            device = None
            for vdc in self._vdcs.values():
                if vdc.has_vdsd(dsuid):
                    device = vdc.get_vdsd(dsuid)
                    break
            
            if device is None:
                logger.warning(f"Device {dsuid} not found for Identify")
                return None
            
            # Trigger identification
            # Device implementation should handle the actual identification
            # (blink LED, flash output, play sound, etc.)
            await device.identify(duration=duration)
            
        except Exception as e:
            logger.error(f"Error handling Identify: {e}", exc_info=True)
        
        return None
    
    async def _handle_remove(self, message: Message, session: 'VdsmSession') -> Optional[Message]:
        """
        Handle VDSM_SEND_REMOVE message.
        
        Request to remove a device from the system.
        vDC should disconnect/unpair the device and send Vanish notification.
        
        Args:
            message: Incoming VDSM_SEND_REMOVE protobuf
            session: Active vdSM session
        
        Returns:
            Message with VDC_SEND_REMOVE_RESULT (success/error)
        
        Message Flow:
            vdSM → vDC: Remove device
            vDC: Attempt to disconnect/unpair device
            vDC → vdSM: RemoveResult (success/failure)
            vDC → vdSM: VanishNotification (if successful)
        
        Property Access:
            message.vdsm_send_remove.dSUID - Device dSUID to remove
        """
        try:
            request = message.vdsm_send_remove
            dsuid = request.dSUID
            
            logger.info(f"Remove device {dsuid}")
            
            # Find device and owning vDC
            device = None
            owning_vdc = None
            for vdc in self._vdcs.values():
                if vdc.has_vdsd(dsuid):
                    device = vdc.get_vdsd(dsuid)
                    owning_vdc = vdc
                    break
            
            if device is None or owning_vdc is None:
                # Device not found - send error
                response = Message()
                response.message_id = message.message_id
                response.vdc_send_remove_result.SetInParent()
                response.vdc_send_remove_result.code = genericVDC_pb2.ERROR_NOT_FOUND
                response.vdc_send_remove_result.description = f"Device {dsuid} not found"
                return response
            
            # Remove device from vDC
            owning_vdc.remove_vdsd(dsuid)
            
            # Send success response
            response = Message()
            response.message_id = message.message_id
            response.vdc_send_remove_result.SetInParent()
            response.vdc_send_remove_result.code = genericVDC_pb2.ERROR_OK
            
            # Send vanish notification (device no longer exists)
            await self._send_vanish_notification(dsuid)
            
            logger.info(f"Device {dsuid} removed successfully")
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling Remove: {e}", exc_info=True)
            
            # Send error response
            response = Message()
            response.message_id = message.message_id
            response.vdc_send_remove_result.SetInParent()
            response.vdc_send_remove_result.code = genericVDC_pb2.ERROR_INTERNAL
            response.vdc_send_remove_result.description = str(e)
            return response
    
    async def _handle_generic_request(self, message: Message, session: 'VdsmSession') -> Message:
        """
        Handle VDSM_REQUEST_GENERIC_REQUEST message.
        
        Generic requests allow calling custom actions or methods on devices.
        This is the primary way to invoke actions defined via the action system.
        
        Args:
            message: Incoming VDSM_REQUEST_GENERIC_REQUEST protobuf
            session: Active vdSM session
        
        Returns:
            Message with VDC_RESPONSE_GENERIC_RESPONSE (result or error)
        
        Message Flow:
            vdSM → vDC: GenericRequest(dSUID, method, params)
            vDC: Find device and action
            vDC: Execute action with params
            vDC → vdSM: GenericResponse(result or error)
        
        Property Access:
            message.vdsm_request_generic_request.dSUID - Device dSUID (optional, host if empty)
            message.vdsm_request_generic_request.method_name - Method/action name
            message.vdsm_request_generic_request.params - PropertyElement tree with parameters
        
        Standard Actions:
            - Custom actions defined via ActionManager
            - Standard operations like reset, factory_reset, etc.
        """
        try:
            request = message.vdsm_request_generic_request
            dsuid = request.dSUID if request.HasField('dSUID') else None
            method_name = request.method_name
            params = PropertyTree.from_protobuf(request.params) if request.HasField('params') else {}
            
            logger.info(f"Generic request: {method_name} on {dsuid or 'host'} with params {params}")
            
            result = None
            
            # If dSUID is specified, find device
            if dsuid:
                device = None
                for vdc in self._vdcs.values():
                    if vdc.has_vdsd(dsuid):
                        device = vdc.get_vdsd(dsuid)
                        break
                
                if device is None:
                    # Device not found
                    response = Message()
                    response.message_id = message.message_id
                    response.vdc_response_generic_response.SetInParent()
                    response.vdc_response_generic_response.code = genericVDC_pb2.ERROR_NOT_FOUND
                    response.vdc_response_generic_response.description = f"Device {dsuid} not found"
                    return response
                
                # Try to call action on device
                action_manager = device.get_action_manager()
                if action_manager and action_manager.has_action(method_name):
                    result = await action_manager.call_action(method_name, **params)
                else:
                    # Action not found
                    response = Message()
                    response.message_id = message.message_id
                    response.vdc_response_generic_response.SetInParent()
                    response.vdc_response_generic_response.code = genericVDC_pb2.ERROR_NOT_IMPLEMENTED
                    response.vdc_response_generic_response.description = f"Action '{method_name}' not found on device"
                    return response
            
            else:
                # Host-level generic request
                # Could implement host-level actions here
                response = Message()
                response.message_id = message.message_id
                response.vdc_response_generic_response.SetInParent()
                response.vdc_response_generic_response.code = genericVDC_pb2.ERROR_NOT_IMPLEMENTED
                response.vdc_response_generic_response.description = "Host-level actions not implemented"
                return response
            
            # Send successful response with result
            response = Message()
            response.message_id = message.message_id
            response.vdc_response_generic_response.SetInParent()
            response.vdc_response_generic_response.code = genericVDC_pb2.ERROR_OK
            
            # Convert result to PropertyElement if present
            if result is not None:
                response.vdc_response_generic_response.result.CopyFrom(
                    PropertyTree.to_protobuf({'result': result})
                )
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling GenericRequest: {e}", exc_info=True)
            
            # Send error response
            response = Message()
            response.message_id = message.message_id
            response.vdc_response_generic_response.SetInParent()
            response.vdc_response_generic_response.code = genericVDC_pb2.ERROR_INTERNAL
            response.vdc_response_generic_response.description = str(e)
            return response
    
    async def _handle_set_local_prio(self, message: Message, session: 'VdsmSession') -> Optional[Message]:
        """
        Handle VDSM_NOTIFICATION_SET_LOCAL_PRIO message.
        
        Set local priority for a device/group/zone.
        Local priority determines which device takes precedence
        when multiple devices control the same resource.
        
        Args:
            message: Incoming VDSM_NOTIFICATION_SET_LOCAL_PRIO protobuf
            session: Active vdSM session
        
        Returns:
            None (notifications don't send responses)
        """
        try:
            notification = message.vdsm_notification_set_local_prio
            dsuid = notification.dSUID
            scene = notification.scene if notification.HasField('scene') else None
            
            logger.info(f"Set local priority on device {dsuid} for scene {scene}")
            
            # Find device
            device = None
            for vdc in self._vdcs.values():
                if vdc.has_vdsd(dsuid):
                    device = vdc.get_vdsd(dsuid)
                    break
            
            if device is None:
                logger.warning(f"Device {dsuid} not found for SetLocalPrio")
                return None
            
            # Set local priority
            # This affects which device's scene takes precedence
            device.set_local_priority(scene)
            
        except Exception as e:
            logger.error(f"Error handling SetLocalPrio: {e}", exc_info=True)
        
        return None
    
    async def _handle_call_min_scene(self, message: Message, session: 'VdsmSession') -> Optional[Message]:
        """
        Handle VDSM_NOTIFICATION_CALL_MIN_SCENE message.
        
        Call a "minimum scene" - activates scene only if current
        values are below the scene's values. Useful for ensuring
        minimum light levels without overriding higher values.
        
        Args:
            message: Incoming VDSM_NOTIFICATION_CALL_MIN_SCENE protobuf
            session: Active vdSM session
        
        Returns:
            None (notifications don't send responses)
        
        Message Flow:
            vdSM → vDC: Call min scene on device
            vDC: Compare current values with scene values
            vDC: Apply only if scene values are higher
            vDC → vdSM: Push notification if values changed
        """
        try:
            notification = message.vdsm_notification_call_min_scene
            dsuid = notification.dSUID
            scene = notification.scene
            
            logger.info(f"Call min scene {scene} on device {dsuid}")
            
            # Find device
            device = None
            for vdc in self._vdcs.values():
                if vdc.has_vdsd(dsuid):
                    device = vdc.get_vdsd(dsuid)
                    break
            
            if device is None:
                logger.warning(f"Device {dsuid} not found for CallMinScene")
                return None
            
            # Call scene with min mode
            await device.call_scene(scene, mode='min')
            
        except Exception as e:
            logger.error(f"Error handling CallMinScene: {e}", exc_info=True)
        
        return None
    
    async def _handle_set_control_value(self, message: Message, session: 'VdsmSession') -> Optional[Message]:
        """
        Handle VDSM_NOTIFICATION_SET_CONTROL_VALUE message.
        
        Set a control value (e.g., valve position, motor position).
        Control values are distinct from output channels - they
        represent actuator positions rather than light/color values.
        
        Args:
            message: Incoming VDSM_NOTIFICATION_SET_CONTROL_VALUE protobuf
            session: Active vdSM session
        
        Returns:
            None (notifications don't send responses)
        
        Property Access:
            message.vdsm_notification_set_control_value.dSUID - Device dSUID
            message.vdsm_notification_set_control_value.name - Control name
            message.vdsm_notification_set_control_value.value - Control value
        """
        try:
            notification = message.vdsm_notification_set_control_value
            dsuid = notification.dSUID
            control_name = notification.name
            value = notification.value
            
            logger.info(f"Set control '{control_name}' to {value} on device {dsuid}")
            
            # Find device
            device = None
            for vdc in self._vdcs.values():
                if vdc.has_vdsd(dsuid):
                    device = vdc.get_vdsd(dsuid)
                    break
            
            if device is None:
                logger.warning(f"Device {dsuid} not found for SetControlValue")
                return None
            
            # Set control value
            # Device should handle this via its control system
            device.set_control_value(control_name, value)
            
        except Exception as e:
            logger.error(f"Error handling SetControlValue: {e}", exc_info=True)
        
        return None
    
    # ===================================================================
    # Push Notification Helpers
    # ===================================================================
    
    async def _send_vanish_notification(self, dsuid: str) -> None:
        """
        Send VDC_NOTIFICATION_VANISH to vdSM.
        
        Notifies vdSM that a device has been removed and is no longer available.
        
        Args:
            dsuid: dSUID of vanished device
        """
        if not self._session or not self._session.is_active():
            return
        
        notification = Message()
        notification.message_id = self._next_message_id()
        notification.vdc_notification_vanish.SetInParent()
        notification.vdc_notification_vanish.dSUID = dsuid
        
        await self._session.send_message(notification)
        logger.debug(f"Sent vanish notification for device {dsuid}")
    
    async def send_push_notification(
        self, 
        dsuid: str, 
        properties: Optional[dict] = None
    ) -> None:
        """
        Send VDC_SEND_PUSH_PROPERTY to vdSM.
        
        Notifies vdSM that device properties have changed.
        This is the primary mechanism for pushing state updates to vdSM.
        
        Args:
            dsuid: Device dSUID that changed
            properties: Optional property tree (if None, vdSM will query)
        
        Message Flow:
            vDC → vdSM: PushProperty(dSUID, properties)
            vdSM: Update internal state
            vdSM: May send GetProperty for full refresh
        
        Usage:
            # Push specific properties
            await host.send_push_notification(
                device.dsuid,
                {'channelValues': [{'channelId': 0, 'value': 75}]}
            )
            
            # Push notification without properties (vdSM will query)
            await host.send_push_notification(device.dsuid)
        """
        if not self._session or not self._session.is_active():
            return
        
        notification = Message()
        notification.message_id = self._next_message_id()
        notification.vdc_send_push_property.SetInParent()
        notification.vdc_send_push_property.dSUID = dsuid
        
        # Include properties if provided
        if properties:
            notification.vdc_send_push_property.properties.CopyFrom(
                PropertyTree.to_protobuf(properties)
            )
        
        await self._session.send_message(notification)
        logger.debug(f"Sent push notification for device {dsuid}")
