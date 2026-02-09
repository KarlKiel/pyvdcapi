# pyvdcapi Architecture & Design Document

## 1. Overview

This document outlines the complete architecture for the Python vDC API implementation. The system enables creating vDC hosts that manage virtual devices (vdSDs) through virtual device connectors (vDCs), communicating with digitalSTROM vdSM over TCP using protocol buffers.

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         VdcHost                                  │
│  ┌──────────────┐  ┌─────────────┐  ┌──────────────────────┐  │
│  │ TCP Server   │  │ Persistence │  │  Common Properties   │  │
│  │ (Port 8444)  │  │ (YAML)      │  │  (dSUID, model, etc) │  │
│  └──────────────┘  └─────────────┘  └──────────────────────┘  │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              VdSM Session Manager                          │ │
│  │  - Hello/Bye handling                                      │ │
│  │  - Single connection enforcement                           │ │
│  │  - Ping/Pong keepalive                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              Message Router                                │ │
│  │  - Protobuf encode/decode                                  │ │
│  │  - Route to correct handler                                │ │
│  │  - Property get/set processing                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                     │
│  │  Vdc 1   │  │  Vdc 2   │  │  Vdc N   │                     │
│  └──────────┘  └──────────┘  └──────────┘                     │
└─────────────────────────────────────────────────────────────────┘
         │                │                │
         ▼                ▼                ▼
    ┌────────┐       ┌────────┐       ┌────────┐
    │ VdSD 1 │       │ VdSD 3 │       │ VdSD N │
    ├────────┤       ├────────┤       ├────────┤
    │ VdSD 2 │       │ VdSD 4 │       │  ...   │
    └────────┘       └────────┘       └────────┘
         │                │
         ▼                ▼
   ┌──────────────────────────┐
   │   Device Components      │
   ├──────────────────────────┤
   │ - Buttons                │
   │ - BinaryInputs           │
   │ - Sensors                │
   │ - OutputChannels         │
   │ - Scenes                 │
   └──────────────────────────┘
```

## 3. Component Responsibilities

### 3.1 VdcHost (Main Container)

**File:** `pyvdcapi/core/vdc_host.py`

**Responsibilities:**
- TCP server management (listen on configured port)
- VdSM session management (accept one connection at a time)
- VdC lifecycle management (create/delete vDCs)
- Global message routing
- YAML persistence coordination
- Common properties (type="vDChost")

**Key Methods:**
```python
class VdcHost:
    def __init__(self, port: int, mac_address: str, persistence_file: str, **properties)
    async def start(self) -> None  # Start TCP server
    async def stop(self) -> None   # Stop TCP server
    def create_vdc(
        self,
        name: str,
        model: str,
        model_uid: Optional[str] = None,
        model_version: str = "1.0",
        **properties
    ) -> Vdc
    def get_vdc(self, dsuid: str) -> Optional[Vdc]
    def get_all_vdcs(self) -> List[Vdc]
    def delete_vdc(self, dsuid: str) -> bool
    
    # Internal message handlers (called by MessageRouter)
    # All handlers accept Message objects and return Optional[Message]
    async def _handle_hello(self, message: Message) -> Optional[Message]
    async def _handle_bye(self, message: Message) -> Optional[Message]
    async def _handle_ping(self, message: Message) -> Optional[Message]
    async def _handle_get_property(self, message: Message) -> Optional[Message]
    async def _handle_set_property(self, message: Message) -> Optional[Message]
    async def _handle_generic_request(self, message: Message, session: VdSMSession) -> Message
```

**State:**
- `_tcp_server: TCPServer` - Server instance
- `_session: Optional[VdSMSession]` - Current vdSM connection
- `_vdcs: Dict[str, Vdc]` - Managed vDCs
- `_persistence: YAMLPersistence` - Persistence layer
- `_common_props: CommonProperties` - Host properties
- `_message_router: MessageRouter` - Route incoming messages

### 3.2 TCPServer (Network Layer)

**File:** `pyvdcapi/network/tcp_server.py`

**Responsibilities:**
- Listen on TCP port
- Accept connections (reject if already connected)
- Read messages with 2-byte length header (network byte order)
- Write messages with 2-byte length header
- Handle connection errors and reconnection

**Key Methods:**
```python
class TCPServer:
    def __init__(
        self,
        port: int = 8444,
        message_handler: Optional[Callable[[Message, asyncio.StreamWriter], Awaitable[None]]] = None,
        host: str = "0.0.0.0"
    )
    async def start(self) -> None
    async def stop(self) -> None
    
    # Static method for sending messages
    @staticmethod
    async def send_message(writer: asyncio.StreamWriter, message: Message) -> None
    
    # Internal
    async def _handle_connection(self, reader, writer) -> None
    async def _read_message(self, reader) -> Message
    async def _write_message(self, writer, message: Message) -> None
```

**Message Format:**
```
[2 bytes: length (uint16, network byte order)][N bytes: protobuf Message]
```

### 3.3 VdSMSession (Session Management)

**File:** `pyvdcapi/network/vdsm_session.py`

**Responsibilities:**
- Track vdSM connection state
- Store vdSM dSUID
- Ping/pong keepalive
- Session initialization state machine

**Key Methods:**
```python
class VdSMSession:
    def __init__(self, vdsm_dsuid: str, connection_info: Any)
    def is_initialized(self) -> bool
    def mark_initialized(self) -> None
    def get_vdsm_dsuid(self) -> str
    def update_last_activity(self) -> None
    def get_idle_time(self) -> float
```

### 3.4 MessageRouter (Message Dispatch)

**File:** `pyvdcapi/network/message_router.py`

**Responsibilities:**
- Parse incoming protobuf messages
- Route to appropriate entity (host/vdc/vdsd)
- Handle errors and generate GenericResponse
- Convert between PropertyElement and Python dicts

**Key Methods:**
```python
class MessageRouter:
    def __init__(self, vdc_host: VdcHost)
    async def route_message(self, message: pb.Message) -> Optional[pb.Message]
    
    # Route by message type
    async def _route_hello(self, msg: pb.Message) -> pb.Message
    async def _route_get_property(self, msg: pb.Message) -> pb.Message
    async def _route_set_property(self, msg: pb.Message) -> pb.Message
    async def _route_ping(self, msg: pb.Message) -> pb.Message
    async def _route_notification(self, msg: pb.Message) -> Optional[pb.Message]
    
    # Helper to find entity by dSUID
    def _get_entity(self, dsuid: str) -> Optional[Union[VdcHost, Vdc, VdSD]]
```

### 3.5 Vdc (Virtual Device Connector)

**File:** `pyvdcapi/core/vdc.py`

**Responsibilities:**
- Manage multiple vdSDs
- Announce vDC to vdSM
- Handle vdSD lifecycle
- VdC-specific properties (implementationId, zoneID, capabilities)
- Common properties (type="vDC")

**Key Methods:**
```python
class Vdc:
    def __init__(self, vdc_host: VdcHost, vdc_index: int, **properties)
    
    # Device management
    def create_device(self, hardware_guid: str, primary_group: int, **properties) -> VdSD
    def delete_device(self, dsuid: str) -> bool
    def get_device(self, dsuid: str) -> Optional[VdSD]
    def get_all_devices(self) -> List[VdSD]
    
    # Announcements
    async def announce_to_vdsm(self) -> None
    async def announce_device(self, device: VdSD) -> None
    async def send_vanish(self, dsuid: str) -> None
    
    # Properties
    def get_properties(self, query: Dict[str, Any]) -> Dict[str, Any]
    def set_properties(self, properties: Dict[str, Any]) -> bool
    
    # Persistence
    def save_to_persistence(self) -> None
    def load_from_persistence(self, config: Dict[str, Any]) -> None
```

**State:**
- `_vdc_host: VdcHost` - Parent host
- `_devices: Dict[str, VdSD]` - Managed devices
- `_common_props: CommonProperties` - Common properties
- `_vdc_props: VdcProperties` - VdC-specific properties
- `_dsuid: str` - This vDC's dSUID

### 3.6 VdSD (Virtual Device)

**File:** `pyvdcapi/core/vdsd.py`

**Responsibilities:**
- Device-level properties (primaryGroup, zoneID, modelFeatures)
- Common properties (type="vdSD")
- Manage device components (inputs, outputs, scenes)
- Handle notifications (callScene, dimChannel, etc.)
- Bidirectional value synchronization

**Key Methods:**
```python
class VdSD:
    def __init__(self, vdc: Vdc, hardware_guid: str, primary_group: int, subdevice_index: int = 0, **properties)
    
    # Component management
    def add_button(self, button_id: int, **properties) -> Button
    def add_binary_input(self, input_id: int, **properties) -> BinaryInput
    def add_sensor(self, sensor_id: int, sensor_type: str, **properties) -> Sensor
    def add_output_channel(self, channel_id: int, channel_type: str, **properties) -> OutputChannel
    
    # Scene management
    def set_scene_value(self, scene_number: int, **values) -> None
    def get_scene_value(self, scene_number: int) -> Dict[str, Any]
    def call_scene(self, scene_number: int, force: bool = False) -> None
    def save_scene(self, scene_number: int) -> None
    def undo_scene(self, scene_number: int) -> None
    
    # Actions
    async def handle_call_scene(self, scene: int, force: bool, group: int, zone_id: int) -> None
    async def handle_dim_channel(self, channel: int, mode: int, area: int) -> None
    async def handle_set_output_channel_value(self, channel: int, value: float, apply_now: bool) -> None
    async def handle_identify(self) -> None
    
    # Properties
    def get_properties(self, query: Dict[str, Any]) -> Dict[str, Any]
    def set_properties(self, properties: Dict[str, Any]) -> bool
    
    # Announcements
    async def announce_to_vdsm(self) -> None
    
    # Persistence
    def save_to_persistence(self) -> None
    def load_from_persistence(self, config: Dict[str, Any]) -> None
```

**State:**
- `_vdc: Vdc` - Parent vDC
- `_common_props: CommonProperties`
- `_vdsd_props: VdSDProperties`
- `_dsuid: str`
- `_buttons: Dict[int, Button]`
- `_binary_inputs: Dict[int, BinaryInput]`
- `_sensors: Dict[int, Sensor]`
- `_output_channels: Dict[int, OutputChannel]`
- `_scenes: Dict[int, SceneConfig]`

### 3.7 Device Components (Inputs/Outputs)

#### Button

**File:** `pyvdcapi/devices/button.py`

```python
class Button:
    def __init__(self, button_id: int, **properties)
    
    # State
    def get_value(self) -> Observable  # Observable button state
    def set_value(self, value: Any) -> None  # Update and notify
    
    # Properties
    def to_dict(self) -> Dict[str, Any]
```

#### BinaryInput

**File:** `pyvdcapi/devices/binary_input.py`

```python
class BinaryInput:
    def __init__(self, input_id: int, **properties)
    
    # State
    def get_value(self) -> Observable
    def set_value(self, value: bool) -> None
    
    # Properties
    def to_dict(self) -> Dict[str, Any]
```

#### Sensor

**File:** `pyvdcapi/devices/sensor.py`

```python
class Sensor:
    def __init__(self, sensor_id: int, sensor_type: str, **properties)
    
    # State
    def get_value(self) -> Observable
    def set_value(self, value: float) -> None
    
    # Properties
    def to_dict(self) -> Dict[str, Any]
    def get_sensor_type(self) -> str
```

#### OutputChannel

**File:** `pyvdcapi/devices/output_channel.py`

```python
class OutputChannel:
    def __init__(self, channel_id: int, channel_type: str, **properties)
    
    # State - bidirectional sync
    def get_value(self) -> Observable  # For external monitoring
    def set_value(self, value: float, notify_vdsm: bool = True) -> None
    
    # External hardware interface
    def on_hardware_change(self, callback: Callable[[float], None]) -> None  # Register callback for value changes
    def set_hardware_value(self, value: float) -> None  # Called when hardware changes
    
    # Actions
    def dim(self, direction: int) -> None  # 1=up, -1=down, 0=stop
    
    # Properties
    def to_dict(self) -> Dict[str, Any]
```

### 3.8 Scene Management

**File:** `pyvdcapi/devices/scene.py`

```python
class SceneConfig:
    def __init__(self, scene_number: int)
    
    def set_channel_value(self, channel_id: int, value: float) -> None
    def get_channel_value(self, channel_id: int) -> Optional[float]
    def apply_to_device(self, device: VdSD) -> None
    def save_from_device(self, device: VdSD) -> None
    def to_dict(self) -> Dict[str, Any]
    def from_dict(self, data: Dict[str, Any]) -> None

class SceneManager:
    def __init__(self, device: VdSD)
    
    def set_scene(self, scene_number: int, config: SceneConfig) -> None
    def get_scene(self, scene_number: int) -> Optional[SceneConfig]
    def call_scene(self, scene_number: int, force: bool = False) -> None
    def save_scene(self, scene_number: int) -> None
    def undo_scene(self, scene_number: int) -> None
    def to_dict(self) -> Dict[str, Any]
```

### 3.9 Discovery Module

**File:** `pyvdcapi/discovery/base.py`

```python
class DiscoveryProvider(ABC):
    @abstractmethod
    def announce_service(self, port: int, **kwargs) -> None
    
    @abstractmethod
    def withdraw_service(self) -> None
```

**File:** `pyvdcapi/discovery/avahi.py`

```python
class AvahiDiscovery(DiscoveryProvider):
    def __init__(self)
    
    def announce_service(self, port: int, **kwargs) -> None:
        # Create /etc/avahi/services/ds-vdc.service
        # Or use python-zeroconf for cross-platform
    
    def withdraw_service(self) -> None
```

## 4. Message Flow Examples

### 4.1 Session Initialization

```
vdSM -> VdcHost: VDSM_REQUEST_HELLO (dSUID, api_version)
VdcHost checks: no existing session
VdcHost -> vdSM: VDC_RESPONSE_HELLO (host dSUID)
VdcHost creates: VdSMSession

VdcHost -> vdSM: VDC_SEND_ANNOUNCE_VDC (vdc1 dSUID)
VdcHost -> vdSM: VDC_SEND_ANNOUNCE_VDC (vdc2 dSUID)

VdcHost -> vdSM: VDC_SEND_ANNOUNCE_DEVICE (device1 dSUID, vdc1 dSUID)
VdcHost -> vdSM: VDC_SEND_ANNOUNCE_DEVICE (device2 dSUID, vdc1 dSUID)
VdcHost -> vdSM: VDC_SEND_ANNOUNCE_DEVICE (device3 dSUID, vdc2 dSUID)
```

### 4.2 Property Query

```
vdSM -> VdcHost: VDSM_REQUEST_GET_PROPERTY (device1 dSUID, query: "outputs")
MessageRouter routes to device1
device1 builds property tree from OutputChannels
VdcHost -> vdSM: VDC_RESPONSE_GET_PROPERTY (properties: {outputs: [...]} )
```

### 4.3 Scene Call

```
vdSM -> VdcHost: VDSM_NOTIFICATION_CALL_SCENE (device1 dSUID, scene=5)
MessageRouter routes to device1
device1.call_scene(5):
  - Load scene config from _scenes[5]
  - Apply to output channels
  - OutputChannel.set_value() triggers Observable
  - Callbacks notify external hardware
  - Persist updated state
```

### 4.4 Hardware Change (Output)

```
External Hardware -> dimmer_value = 75%
Application calls: output_channel.set_hardware_value(0.75)
OutputChannel.set_value(0.75, notify_vdsm=True)
  - Update Observable (triggers local callbacks)
  - Trigger pushProperty to vdSM
VdcHost -> vdSM: VDC_SEND_PUSH_PROPERTY (device dSUID, properties: {outputs.0.value: 0.75})
Persist to YAML
```

## 5. Data Flow Patterns

### 5.1 Value Synchronization (Bidirectional)

```
┌───────────────┐                ┌──────────────┐
│ External HW   │◄──subscribe────│ Observable   │
│ (Light Dimmer)│                │  (channel)   │
└───────────────┘                └──────────────┘
       │                                 ▲
       │ value changed                   │ set_value()
       ▼                                 │
┌───────────────┐                ┌──────────────┐
│ Application   │────────────────►│ VdSD         │
│ Callback      │  update         │ OutputChannel│
└───────────────┘                └──────────────┘
                                        │
                                        │ pushProperty
                                        ▼
                                 ┌──────────────┐
                                 │ vdSM         │
                                 └──────────────┘
```

### 5.2 Persistence Flow

```
State Change (property update, scene call, etc.)
       │
       ▼
Entity.save_to_persistence()
       │
       ▼
Build property tree dict
       │
       ▼
YAMLPersistence.set_vdsd(dsuid, config)
       │
       ▼
YAML file updated (if auto_save=True)
```

## 6. Threading & Concurrency

**Approach:** asyncio for network I/O, threading.Lock for shared state

- TCP server uses asyncio
- Message handlers are async
- Observable uses threading.Lock for callbacks
- YAMLPersistence uses threading.Lock for file I/O

## 7. Error Handling

All errors return GenericResponse with appropriate ResultCode:
- `ERR_NOT_FOUND`: Entity dSUID not found
- `ERR_INVALID_VALUE_TYPE`: Property type mismatch
- `ERR_FORBIDDEN`: Read-only property or unauthorized action
- `ERR_SERVICE_NOT_AVAILABLE`: Already connected to another vdSM
- `ERR_INCOMPATIBLE_API`: API version mismatch

## 8. Configuration Example

```yaml
vdc_host:
  dSUID: "00000000ABCDEF1234567890ABCDEF1200"
  type: "vDChost"
  model: "genericVDC Host"
  modelVersion: "1.0"
  modelUID: "KarlKielgenVDCH"
  vendorName: "KarlKiel"
  name: "My VDC Host"
  active: true

vdcs:
  "00000001FEDCBA0987654321FEDCBA0100":
    dSUID: "00000001FEDCBA0987654321FEDCBA0100"
    type: "vDC"
    model: "Light Controller"
    modelUID: "KarlKiel-Light-v1"
    vendorName: "KarlKiel"
    implementationId: "x-KarlKiel-generic vDC"
    zoneID: 1
    capabilities:
      metering: false
      identification: false
      dynamicDefinitions: true

vdsds:
  "00000002AABBCCDD11223344AABBCC0000":
    dSUID: "00000002AABBCCDD11223344AABBCC0000"
    type: "vdSD"
    vdc_dSUID: "00000001FEDCBA0987654321FEDCBA0100"
    model: "Dimmable Light"
    modelUID: "KarlKiel-DimLight-v1"
    vendorName: "KarlKiel"
    primaryGroup: 1  # Light/Yellow
    zoneID: 1
    modelFeatures:
      dimmable: true
      identification: true
    outputs:
      - channelId: 0
        channelType: "brightness"
        value: 0.0
        min: 0.0
        max: 1.0
        resolution: 0.01
    scenes:
      5:  # Deep Off
        outputs:
          0: 0.0
      14:  # Preset 1
        outputs:
          0: 0.5
      15:  # Preset 2
        outputs:
          0: 1.0
```

## 9. Usage Example

```python
from pyvdcapi import VdcHost

# Create VdC host
host = VdcHost(
    port=8444,
    mac_address="AA:BB:CC:DD:EE:FF",
    persistence_file="vdc_config.yaml",
    model="genericVDC Host",
    modelVersion="1.0",
    modelUID="KarlKielgenVDCH",
    vendorName="KarlKiel"
)

# Create a vDC
vdc = host.create_vdc(
    model="Light Controller",
    modelUID="KarlKiel-Light-v1"
)

# Create a device
device = vdc.create_device(
    hardware_guid="light:001",
    primary_group=1,  # Light group
    model="Dimmable Light",
    modelUID="KarlKiel-DimLight-v1"
)

# Add output channel
channel = device.add_output_channel(
    channel_id=0,
    channel_type="brightness"
)

# Register hardware callback
def on_brightness_change(value):
    print(f"Set hardware brightness to {value*100}%")
    # Control actual hardware here

channel.on_hardware_change(on_brightness_change)

# Configure scenes
device.set_scene_value(5, outputs={0: 0.0})    # Deep Off
device.set_scene_value(14, outputs={0: 0.5})   # Preset 1
device.set_scene_value(15, outputs={0: 1.0})   # Preset 2

# Start host (with optional discovery)
from pyvdcapi.discovery import AvahiDiscovery
host.set_discovery_provider(AvahiDiscovery())
host.start()

# When hardware changes
channel.set_hardware_value(0.75)  # Automatically notifies vdSM
```

## 10. Implementation Checklist

- [x] Package structure
- [x] dSUID generation
- [x] Property tree conversion
- [x] Validators
- [x] Observable callbacks
- [x] Common properties
- [x] VdC properties
- [x] VdSD properties
- [x] YAML persistence
- [ ] TCP server with framing
- [ ] VdSM session management
- [ ] Message router
- [ ] VdcHost class
- [ ] Vdc class
- [ ] VdSD class
- [ ] Button component
- [ ] BinaryInput component
- [ ] Sensor component
- [ ] OutputChannel component
- [ ] Scene management
- [ ] Discovery interface
- [ ] Avahi discovery
- [ ] Integration tests
- [ ] Examples
- [ ] Documentation

## 11. Questions & Decisions Needed

1. **Asyncio vs Threading**: Should we use asyncio throughout or mix with threading? (Proposed: asyncio for network, locks for shared state)

2. **Scene Standard Values**: Which standard dS scenes should be pre-configured? (Proposed: 0-4=Area scenes, 5=Deep Off, 13=Stop, 14-18=Presets)

3. **Property Validation Level**: How strict for custom properties? (Decided: No custom properties per user requirement)

4. **Channel Types**: Full list of supported channel types? (Proposed: brightness, hue, saturation, colortemp, audio_volume)

5. **Error Recovery**: How to handle persistence file corruption? (Proposed: Create backup, load defaults)

---

**Ready for Review**: Please review this architecture and provide feedback before I implement the remaining components.
