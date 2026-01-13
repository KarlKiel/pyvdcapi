# pyvdcapi

Python implementation of the digitalSTROM vDC API - A comprehensive library for building virtual device connectors (vDCs) and virtual devices (vdSDs).

## Features

✅ **Complete Protocol Implementation** - All 19 message handlers from genericVDC.proto  
✅ **Bidirectional Sync** - Automatic push notifications to vdSM on value changes  
✅ **Auto-Discovery** - mDNS/DNS-SD service announcement (Avahi/Bonjour)  
✅ **Scene Management** - Save, recall, undo, and min-scene operations  
✅ **Output Control** - Channel values, dimming, and control values  
✅ **Device Components** - Buttons, sensors, binary inputs, outputs  
✅ **Actions & States** - Generic request handling with custom actions  
✅ **Persistence** - Automatic YAML persistence with shadow backup  
✅ **Property Trees** - Bidirectional conversion between Python dicts and protobuf  

## Installation

```bash
# Clone repository
git clone https://github.com/KarlKiel/pyvdcapi.git
cd pyvdcapi

# Install dependencies
pip install protobuf pyyaml

# Optional: For service announcement (auto-discovery)
pip install zeroconf
```

## Quick Start

```python
import asyncio
from pyvdcapi.entities.vdc_host import VdcHost
from pyvdcapi.core.constants import DSGroup, DSChannelType

async def main():
    # Create vDC host with service announcement
    host = VdcHost(
        persistence_path="config.yaml",
        mac_address="00:11:22:33:44:55",
        vendor_id="example.com",
        name="My vDC Host",
        announce_service=True  # Enable auto-discovery via mDNS
    )
    
    # Create vDC (device container)
    vdc = host.create_vdc(
        name="Light Controller",
        model="v1.0"
    )
    
    # Create device
    device = vdc.create_vdsd(
        name="Living Room Light",
        model="Dimmer",
        primary_group=DSGroup.YELLOW  # Light group
    )
    
    # Add brightness channel
    channel = device.add_output_channel(
        output_id=0,
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0,
        initial_value=0.0
    )
    
    # Set value (triggers automatic push notification to vdSM)
    device.get_output().set_channel_value(DSChannelType.BRIGHTNESS, 75.0)
    
    # Save scene
    await device.save_scene(17)  # Automatically persisted
    
    # Start vDC host server
    await host.start(port=8440)

asyncio.run(main())
```

## Project Structure

```
pyvdcapi/
├── proto/                 # Protocol buffer definitions
│   └── genericVDC.proto   # vDC API protocol definition
├── pyvdcapi/              # Main package
│   ├── network/           # Protocol communication
│   │   └── genericVDC_pb2.py  # Generated Python protobuf code (packaged)
├── pyvdcapi/              # Main package
│   ├── core/              # Core domain logic
│   │   ├── constants.py   # digitalSTROM constants (scenes, channels, groups)
│   │   └── dsuid.py       # dSUID generation
│   ├── entities/          # Main entities
│   │   ├── vdc_host.py    # vDC host (top-level container)
│   │   ├── vdc.py         # vDC (device collection)
│   │   └── vdsd.py        # vdSD (individual device)
│   ├── components/        # Device components
│   │   ├── actions.py     # ActionManager, StateManager, DevicePropertyManager
│   │   ├── output.py      # Output container
│   │   ├── output_channel.py  # Individual output channels
│   │   ├── button.py      # Button inputs
│   │   ├── binary_input.py    # Binary inputs (motion, contact)
│   │   └── sensor.py      # Sensor inputs (temperature, etc.)
│   ├── network/           # Protocol communication
│   │   ├── tcp_server.py  # TCP server with 2-byte framing
│   │   ├── vdsm_session.py    # vdSM session state machine
│   │   ├── message_router.py  # Message routing and handlers
│   │   └── service_announcement.py  # mDNS/Avahi service discovery
│   ├── properties/        # Property system
│   │   ├── property_tree.py   # Protobuf ↔ dict conversion
│   │   ├── common.py      # Common properties
│   │   ├── vdc_props.py   # vDC properties
│   │   └── vdsd_props.py  # vdSD properties
│   ├── persistence/       # Data persistence
│   │   └── yaml_store.py  # YAML storage with shadow backup
│   └── utils/             # Utilities
│       ├── callbacks.py   # Observable pattern
│       └── validators.py  # Property validation
├── examples/              # Example implementations
│   ├── complete_protocol_demo.py  # Full feature demonstration
│   ├── motion_light_device.py     # Motion-activated light
│   ├── device_configuration.py    # Configuration examples
│   ├── service_announcement_demo.py  # Auto-discovery demo
│   ├── vdsm_simulator.py         # vdSM protocol simulator
│   └── demo_with_simulator.py    # Combined demo
├── tests/                 # Test suite
│   ├── test_simple.py     # Basic functionality tests
│   ├── test_service_announcement.py  # Service announcement tests
│   └── test_vdc_host_announcement.py  # Integration tests
└── Documentation/         # API specification
    ├── proto/             # Original proto definition
    ├── vdc-API/          # API documentation
    └── vdc-API-properties/  # Property specifications
```

## Message Handlers

All 19 protobuf message types are fully implemented:

### Session Management
- `VDSM_REQUEST_HELLO` - Session initialization
- `VDSM_SEND_BYE` - Session termination
- `VDSM_SEND_PING` / `VDC_SEND_PONG` - Keep-alive

### Property Access
- `VDSM_REQUEST_GET_PROPERTY` - Get device properties
- `VDSM_REQUEST_SET_PROPERTY` - Set device properties

### Scene Operations
- `VDSM_NOTIFICATION_CALL_SCENE` - Activate scene
- `VDSM_NOTIFICATION_SAVE_SCENE` - Save current state as scene
- `VDSM_NOTIFICATION_UNDO_SCENE` - Restore previous state
- `VDSM_NOTIFICATION_CALL_MIN_SCENE` - Conditional scene activation
- `VDSM_NOTIFICATION_SET_LOCAL_PRIO` - Set priority

### Output Control
- `VDSM_NOTIFICATION_SET_OUTPUT_CHANNEL_VALUE` - Set channel value
- `VDSM_NOTIFICATION_DIM_CHANNEL` - Continuous dimming
- `VDSM_NOTIFICATION_SET_CONTROL_VALUE` - Set control value

### Device Management
- `VDSM_NOTIFICATION_IDENTIFY` - Device identification
- `VDSM_SEND_REMOVE` - Remove device

### Actions
- `VDSM_REQUEST_GENERIC_REQUEST` - Call actions

### Push Notifications
- `VDC_SEND_PUSH_PROPERTY` - Notify property changes
- `VDC_NOTIFICATION_VANISH` - Device removed

## Examples

See the `examples/` directory:

- **`complete_protocol_demo.py`** - Demonstrates all features
- **`motion_light_device.py`** - Motion-activated light
- **`device_configuration.py`** - Configuration and cloning
- **`service_announcement_demo.py`** - Auto-discovery with mDNS
- **`vdsm_simulator.py`** - vdSM protocol simulator for testing

## Documentation

- **[SERVICE_ANNOUNCEMENT.md](SERVICE_ANNOUNCEMENT.md)** - Auto-discovery setup and usage
- **[VALIDATION_COMPLETE.md](VALIDATION_COMPLETE.md)** - Complete protocol validation report
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture
- **[CONSTANTS_README.md](CONSTANTS_README.md)** - digitalSTROM constants guide
- **[RE-VALIDATION_COMPLETE.md](RE-VALIDATION_COMPLETE.md)** - Latest validation summary

## Testing

```bash
# Run test suite
python tests/test_simple.py
python tests/test_service_announcement.py
python tests/test_vdc_host_announcement.py

# Run examples
python examples/complete_protocol_demo.py
python examples/motion_light_device.py
python examples/device_configuration.py
python examples/service_announcement_demo.py
```

## Production Ready

✅ Fully validated against vDC API specification  
✅ All critical message handlers implemented  
✅ Bidirectional sync with automatic push notifications  
✅ Automatic persistence with shadow backup  
✅ Complete scene management (save/recall/undo)  
✅ Device identification and removal  
✅ Action and state management  
✅ Hardware callback integration  

## License

See [LICENSE](LICENSE) file.

## Author

KarlKiel

## Contributing

Contributions welcome! Please ensure:
- All message handlers are tested
- Property trees serialize correctly
- Persistence works with shadow backup
- Callbacks trigger appropriately
