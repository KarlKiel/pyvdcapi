# pyvdcapi API Reference

**Version:** 1.0.0  
**Protocol:** digitalSTROM vDC API v2.0

This document provides a comprehensive reference for using the pyvdcapi library to create vDC hosts, virtual device connectors, and virtual devices compliant with the digitalSTROM vDC API specification.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Architecture](#core-architecture)
3. [Entity Classes](#entity-classes)
   - [VdcHost](#vdchost)
   - [Vdc](#vdc)
   - [VdSD](#vdsd)
4. [Component Classes](#component-classes)
   - [Output & OutputChannel](#output--outputchannel)
   - [Button](#button)
   - [BinaryInput](#binaryinput)
   - [Sensor](#sensor)
5. [Action & State Management](#action--state-management)
6. [Event Handling & Callbacks](#event-handling--callbacks)
7. [Persistence](#persistence)
8. [Constants & Enums](#constants--enums)
9. [Complete Examples](#complete-examples)

---

## Quick Start

```python
import asyncio
from pyvdcapi import VdcHost
from pyvdcapi.core.constants import DSGroup, DSChannelType

async def main():
    # 1. Create vDC host
    host = VdcHost(
        port=8444,
        mac_address="00:11:22:33:44:55",
        vendor_id="MyCompany",
        name="Home Automation Hub",
        model="HomeHub v1.0",
        persistence_file="config.yaml"
    )
    
    # 2. Create vDC (device connector)
    vdc = host.create_vdc(
        name="Living Room Controller",
        model="LightController v1.0"
    )
    
    # 3. Create device
    device = vdc.create_vdsd(
        name="Ceiling Light",
        model="DimmableLED",
        primary_group=DSGroup.LIGHT
    )
    
    # 4. Add output channel
    brightness = device.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0
    )
    
    # 5. Register hardware callback
    def apply_brightness(value):
        print(f"Set hardware brightness to {value}%")
        # your_hardware.set_brightness(value)
    
    brightness.subscribe(apply_brightness)
    
    # 6. Start the host
    await host.start()
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await host.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Core Architecture

### Entity Hierarchy

```
VdcHost (port 8444)
├── Vdc (Light Controller)
│   ├── VdSD (Living Room Light)
│   │   ├── Output with Channel (Brightness)
│   │   ├── Button (Wall Switch)
│   │   └── Sensor (Motion)
│   └── VdSD (Kitchen Light)
│       └── Output with Channels (Brightness, ColorTemp)
└── Vdc (Heating Controller)
    └── VdSD (Thermostat)
        ├── Output (Heating Power)
        └── Sensor (Temperature)
```

### Data Flow

#### Property Read (vdSM → Device)
```
vdSM → TCP → VdcHost → Vdc → VdSD → Component → get_property() → Response
```

#### Property Write (vdSM → Device → Hardware)
```
vdSM → TCP → VdcHost → Vdc → VdSD → Component.set_value()
                                           ↓
                                    Observable.notify()
                                           ↓
                                    Hardware Callback
```

#### State Update (Hardware → vdSM)
```
Hardware → Application → Component.update_value()
                                ↓
                         Observable.notify()
                                ↓
                         VdcHost.push_notification() → vdSM
```

---

## Entity Classes

### VdcHost

The top-level container managing TCP server, sessions, and all vDCs.

#### Constructor

```python
VdcHost(
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
)
```

**Parameters:**
- `name`: User-specified name for the host (required)
- `port`: TCP port for vdSM connections (default: 8444)
- `mac_address`: MAC address for dSUID generation (format: "aa:bb:cc:dd:ee:ff")  
  If empty, uses system's default MAC address
- `vendor_id`: Vendor identifier for dSUID namespace
- `model`: Human-readable model name (default: "vDC Host")
- `model_uid`: Unique model identifier (default: "vdc-host")
- `model_version`: Model version string (optional, provide empty string to omit)
- `persistence_file`: Path to YAML configuration file
- `auto_save`: Automatically save configuration on changes
- `enable_backup`: Create shadow .bak file during saves
- `announce_service`: Enable mDNS/DNS-SD service announcement for auto-discovery (default: False)
- `use_avahi`: Use Avahi daemon instead of zeroconf library (Linux only, default: False)
- `**properties`: Additional properties (see optional properties below)

**Returns:** VdcHost instance

**Optional Properties (via \*\*properties):**

All optional common properties from the vDC API specification can be provided:

- `displayId` (str, optional): Human-readable identification printed on physical device (if available)
- `hardwareVersion` (str, optional): Hardware version string
- `hardwareGuid` (str): Hardware's globally unique identifier (format: `schema:id`)
  - Examples: `"macaddress:00:11:22:33:44:55"`, `"uuid:2f402f80-ea50-11e1-9b23-001778216465"`
- `hardwareModelGuid` (str): Hardware model's globally unique identifier
- `vendorName` (str): Manufacturer or vendor name (default: "KarlKiel")
- `vendorGuid` (str): Globally unique vendor identifier
  - Examples: `"gs1:(412)7640161170001"`, `"vendorname:ACME Corp"`
- `oemGuid` (str): OEM product identifier
- `oemModelGuid` (str): OEM product model identifier (often GTIN)
- `configURL` (str): Full URL to web configuration interface
- `deviceIcon16` (bytes): 16x16 pixel PNG image
- `deviceIconName` (str): Filename-safe icon name for caching
- `deviceClass` (str): digitalSTROM device class profile name
- `deviceClassVersion` (str): Device class profile revision number
- `active` (bool): Operational state (default: True)

**Example:**
```python
host = VdcHost(
    name="ACME Home Hub",
    port=8444,
    mac_address="aa:bb:cc:dd:ee:ff",
    vendor_id="acme.com",
    model="HomeHub Pro",
    model_uid="homehub-pro",
    model_version="2.1.0",
    vendorName="ACME Corporation",
    hardwareVersion="HW-2.1",
    hardwareGuid="macaddress:aa:bb:cc:dd:ee:ff",
    configURL="http://192.168.1.100:8080",
    persistence_file="/etc/vdc/config.yaml"
)
```

**Service Announcement (Optional):**

The vDC host can optionally announce itself on the local network using mDNS/DNS-SD according to the vDC API specification (Section 3: Discovery). This allows vdSMs to automatically discover available vDC hosts without manual configuration.

```python
# Enable service announcement with zeroconf (cross-platform)
host = VdcHost(
    name="My vDC Host",
    port=8444,
    announce_service=True  # Requires: pip install zeroconf
)

# Use Avahi daemon on Linux (requires Avahi running, needs root privileges)
host = VdcHost(
    name="My vDC Host",
    port=8444,
    announce_service=True,
    use_avahi=True  # Linux only, no additional dependencies
)
```

**Service Details:**
- Service type: `_ds-vdc._tcp.local.`
- Service name: `{name}._ds-vdc._tcp.local.`
- TXT records: Contains host model and version information
- Port: Configured TCP port (default: 8444)

For complete documentation on service announcement, see [SERVICE_ANNOUNCEMENT.md](SERVICE_ANNOUNCEMENT.md).

#### Methods

##### `async start() -> None`

Start the vDC host and begin accepting vdSM connections.

**Behavior:**
1. Creates TCP server on configured port
2. Begins listening for vdSM connections
3. Loads persisted vDCs from configuration
4. Starts service announcement if enabled
5. Transitions to running state

**Raises:**
- `OSError`: If port is already in use
- `RuntimeError`: If host is already running

**Example:**
```python
await host.start()
logger.info("Host is running")
```

##### `async stop() -> None`

Stop the vDC host and close all connections.

**Behavior:**
1. Closes vdSM session if connected
2. Stops TCP server
3. Stops service announcement if running
4. Saves final configuration state
5. Transitions to stopped state

**Example:**
```python
await host.stop()
logger.info("Host stopped gracefully")
```

##### `create_vdc(name: str, model: str, model_uid: Optional[str] = None, model_version: str = "1.0", vendor_id: Optional[str] = None, mac_address: Optional[str] = None, **properties) -> Vdc`

Create a new virtual device connector (vDC).

**Parameters:**
- `name`: vDC name (e.g., "Hue Bridge", "Z-Wave Controller")
- `model`: vDC model identifier (human-readable)
- `model_uid`: Unique model identifier for vdSM (auto-generated from model if not provided)  
  **Important:** This is **mandatory for vdSM announcement**. If not provided, will be auto-generated  
  by converting model to lowercase and replacing spaces/dots with hyphens.
- `model_version`: Model version string (optional - omit or use empty string if not applicable)
- `vendor_id`: Vendor ID (defaults to host's vendor ID)
- `mac_address`: MAC for dSUID generation (defaults to host's MAC)
- `**properties`: Additional vDC properties

**Returns:** Newly created Vdc instance

**Auto-generation of modelUID:**
- If `model_uid` is not provided, it's generated from `model`
- Example: `"Hue vDC v2.0"` → `"hue-vdc-v2-0"`
- For production: Always provide explicit `model_uid` for consistency

**Optional Properties (via \*\*properties):**

All optional common properties plus vDC-specific properties:

**Common Properties:**
- `displayId` (str, optional): Human-readable identification (if available)
- `hardwareVersion` (str, optional): Hardware version
- `hardwareGuid` (str): Hardware GUID (e.g., `"uuid:..."`, `"macaddress:..."`)
- `hardwareModelGuid` (str): Hardware model GUID
- `vendorName` (str): Vendor name
- `vendorGuid` (str): Vendor GUID
- `oemGuid` (str): OEM product GUID
- `oemModelGuid` (str): OEM model GUID
- `configURL` (str): Web configuration URL
- `deviceIcon16` (bytes): 16x16 PNG icon
- `deviceIconName` (str): Icon name for caching
- `active` (bool): Operational state

**vDC-Specific Properties:**
- `implementationId` (str): vDC implementation identifier (default: "x-KarlKiel-generic vDC")
  - Non-digitalSTROM vDCs must use "x-company-" prefix
- `zoneID` (int): Default zone ID for this vDC
- `capabilities` (dict): vDC capabilities
  - `metering` (bool): Provides metering data
  - `identification` (bool): Can identify itself (e.g., blink LED)
  - `dynamicDefinitions` (bool): Supports dynamic definitions (default: True)

**Example:**
```python
# Explicit modelUID and version (recommended)
light_vdc = host.create_vdc(
    name="Philips Hue Bridge",
    model="Hue vDC",
    model_uid="philips-hue-vdc",
    model_version="2.0",
    vendorName="Philips",
    implementationId="x-philips-hue-vdc",
    hardwareGuid="uuid:2f402f80-ea50-11e1-9b23-001778216465",
    configURL="http://192.168.1.50",
    capabilities={
        "metering": True,
        "identification": True,
        "dynamicDefinitions": True
    }
)

# Auto-generated modelUID (for quick prototyping)
light_vdc = host.create_vdc(
    name="Test Light",
    model="Test vDC v1.0"  # modelUID will be "test-vdc-v1-0"
)
```

##### `get_vdc(dsuid: str) -> Optional[Vdc]`

Retrieve a vDC by its dSUID.

**Parameters:**
- `dsuid`: dSUID of the vDC to retrieve

**Returns:** Vdc instance or None if not found

**Example:**
```python
vdc = host.get_vdc("AA112233445566778899AABBCCDDEEFF00")
if vdc:
    print(f"Found vDC: {vdc.get_name()}")
```

##### `get_all_vdcs() -> List[Vdc]`

Get all vDCs managed by this host.

**Returns:** List of Vdc instances

**Example:**
```python
for vdc in host.get_all_vdcs():
    print(f"vDC: {vdc.get_name()}, Devices: {len(vdc.get_all_vdsds())}")
```

##### `is_running() -> bool`

Check if host is running.

**Returns:** True if host is running, False otherwise

##### `is_connected() -> bool`

Check if vdSM is currently connected.

**Returns:** True if vdSM is connected, False otherwise

**Example:**
```python
if host.is_connected():
    await host.push_notification("0x01234567", {"brightness": {"value": 75}})
```

---

### Vdc

Virtual Device Connector - manages a collection of related devices.

#### Constructor

```python
# Note: Don't create directly - use VdcHost.create_vdc()
Vdc(
    host: VdcHost,
    mac_address: str,
    vendor_id: str,
    persistence: YAMLPersistence,
    model: str,
    model_uid: str,
    model_version: str = "1.0",
    **properties
)
```

**Internal use only.** Always create vDCs via `VdcHost.create_vdc()`.

**Parameters:**
- `host`: Parent VdcHost instance
- `mac_address`: MAC address for dSUID generation
- `vendor_id`: Vendor identifier
- `persistence`: YAML persistence manager
- `model`: Human-readable model name (required)
- `model_uid`: Unique model identifier (required)
- `model_version`: Model version string (default: "1.0")
- `**properties`: Additional vDC properties

#### Methods

##### `create_vdsd(name: str, model: str, primary_group: int, model_uid: Optional[str] = None, model_version: str = "1.0", **properties) -> VdSD`

Create a new virtual device (vdSD).

**Parameters:**
- `name`: Device name (human-readable, e.g., "Living Room Light")
- `model`: Device model identifier (human-readable)
- `primary_group`: Device functional group (DSGroup enum, e.g., DSGroup.LIGHT)
- `model_uid`: Unique model identifier for vdSM (auto-generated from model if not provided)  
  **Important:** This is **mandatory for vdSM announcement**. If not provided, will be auto-generated  
  by converting model to lowercase and replacing spaces/dots with hyphens.
- `model_version`: Model version string (optional - omit or pass empty string if not applicable)
- `**properties`: Additional device properties

**Returns:** Newly created VdSD instance

**Auto-generation of modelUID:**
- If `model_uid` is not provided, it's generated from `model`
- Example: `"ZWave Dimmer v1"` → `"zwave-dimmer-v1"`
- For production: Always provide explicit `model_uid` for consistency

**Optional Properties (via \*\*properties):**

All optional common properties plus vdSD-specific properties:

**Common Properties:**
- `displayId` (str, optional): Human-readable identification printed on device (if available)
- `hardwareVersion` (str, optional): Hardware version string
- `hardwareGuid` (str): Hardware GUID
  - Examples: `"enoceanaddress:A4BC23D2"`, `"hueuid:00:17:88:01:00:bd:ef:d1-0b"`
- `hardwareModelGuid` (str): Hardware model GUID
  - Examples: `"enoceaneep:A50904"`, `"gs1:(01)4050300870342"`
- `vendorName` (str): Manufacturer name
- `vendorGuid` (str): Vendor GUID
  - Examples: `"enoceanvendor:002:Themokon"`, `"gs1:(412)7640161170001"`
- `oemGuid` (str): OEM product GUID
- `oemModelGuid` (str): OEM model GUID (GTIN format)
- `configURL` (str): Device web configuration URL
- `deviceIcon16` (bytes): 16x16 PNG icon
- `deviceIconName` (str): Icon filename for caching
- `deviceClass` (str): Device class profile name
- `deviceClassVersion` (str): Device class profile version
- `active` (bool): Device operational state

**vdSD-Specific Properties:**
- `zoneID` (int): Zone the device is assigned to
- `progMode` (bool): Enable local programming mode
- `currentConfigId` (str): Currently active configuration/profile ID
- `configurations` (list): List of supported configuration IDs
- `modelFeatures` (dict): Device model features (visibility matrix)
  - See [Model Features](#valid-model-features) for complete list
  - Example: `{"blink": True, "outmode": True, "outputchannels": True}`

**Output/Functionality Properties:**
- `output_function` (int): Output function type (DSOutputFunction enum)
- `output_mode` (int): Output mode (DSOutputMode enum)
- `output_usage` (int): Output usage hint (DSOutputUsage enum)

**Hardware Identification:**
- `serial` (str): Device serial number
- `vendor` (str): Vendor/manufacturer name (shorthand for vendorName)

**Example:**
```python
# Explicit modelUID and version (recommended)
device = vdc.create_vdsd(
    name="Bedroom Dimmer",
    model="ZWave Dimmer",
    model_uid="zwave-dimmer",
    model_version="1.0",
    primary_group=DSGroup.LIGHT,
    vendorName="Fibaro",
    vendorGuid="vendorname:Fibaro",
    hardwareGuid="enoceanaddress:A4BC23D2",
    hardwareModelGuid="gs1:(01)4050300870342",
    serial="FGD212-12345",
    output_function=DSOutputFunction.DIMMER,
    modelFeatures={
        "blink": True,
        "outmode": True,
        "outputchannels": True,
        "highlevel": True
    },
    zoneID=1,
    active=True
)

# Auto-generated modelUID (for quick prototyping)
device = vdc.create_vdsd(
    name="Test Light",
    model="Dimmer 1CH",  # modelUID will be "dimmer-1ch"
    primary_group=DSGroup.LIGHT
)
```

##### `remove_vdsd(dsuid: str) -> bool`

Remove a device from this vDC.

**Parameters:**
- `dsuid`: dSUID of device to remove

**Returns:** True if removed, False if not found

**Behavior:**
- Removes device from vDC
- Sends Vanish notification to vdSM
- Deletes device from persistent storage

**Example:**
```python
if vdc.remove_vdsd("11223344556677889900AABBCCDDEEFF02"):
    print("Device removed and vanished")
```

##### `get_vdsd(dsuid: str) -> Optional[VdSD]`

Retrieve a device by its dSUID.

**Parameters:**
- `dsuid`: dSUID of device

**Returns:** VdSD instance or None if not found

**Example:**
```python
device = vdc.get_vdsd("11223344556677889900AABBCCDDEEFF02")
if device:
    brightness = device.get_output_channel(DSChannelType.BRIGHTNESS)
```

##### `get_all_vdsds() -> List[VdSD]`

Get all devices in this vDC.

**Returns:** List of VdSD instances

**Example:**
```python
for device in vdc.get_all_vdsds():
    print(f"Device: {device.get_name()}, Group: {device.get_primary_group()}")
```

##### `get_properties(query: Dict[str, Any]) -> Dict[str, Any]`

Get vDC properties (dSUID, name, model, etc.).

**Parameters:**
- `query`: Property query from vdSM

**Returns:** Property tree dictionary

**Example:**
```python
props = vdc.get_properties({})
print(f"vDC Name: {props.get('name')}")
print(f"vDC dSUID: {props.get('dSUID')}")
```

---

### VdSD

Virtual Smart Device - represents an individual device with inputs, outputs, and scenes.

#### Constructor

```python
# Note: Don't create directly - use Vdc.create_vdsd()
VdSD(
    vdc: Vdc,
    name: str,
    model: str,
    primary_group: int,
    mac_address: str,
    vendor_id: str,
    enumeration: int = 0,
    model_uid: Optional[str] = None,
    model_version: str = "1.0",
    **properties
)
```

**Internal use only.** Always create devices via `Vdc.create_vdsd()`.

**Parameters:**
- `vdc`: Parent Vdc instance
- `name`: Human-readable device name (required)
- `model`: Device model identifier (required)
- `primary_group`: digitalSTROM group/color (required)
- `mac_address`: MAC address for dSUID generation
- `vendor_id`: Vendor identifier
- `enumeration`: Device enumeration number (default: 0)
- `model_uid`: Unique model identifier (auto-generated if None)
- `model_version`: Model version string (default: "1.0")
- `**properties`: Additional device properties

#### Methods

##### `add_output_channel(channel_type: int, min_value: float = 0.0, max_value: float = 100.0, resolution: float = 0.1, initial_value: Optional[float] = None, **properties) -> OutputChannel`

Add an output channel to the device.

**Parameters:**
- `channel_type`: Channel type (DSChannelType enum, e.g., DSChannelType.BRIGHTNESS)
- `min_value`: Minimum channel value (default: 0.0)
- `max_value`: Maximum channel value (default: 100.0)
- `resolution`: Smallest increment (default: 0.1)
- `initial_value`: Initial value (defaults to min_value)
- `**properties`: Additional channel properties

**Returns:** OutputChannel instance

**Example:**
```python
# Simple brightness channel
brightness = device.add_output_channel(
    channel_type=DSChannelType.BRIGHTNESS,
    min_value=0.0,
    max_value=100.0,
    resolution=1.0
)

# Color temperature channel
color_temp = device.add_output_channel(
    channel_type=DSChannelType.COLOR_TEMP,
    min_value=2700,  # Warm white
    max_value=6500,  # Cool white
    resolution=100,
    initial_value=4000
)

# Shade position
position = device.add_output_channel(
    channel_type=DSChannelType.SHADE_POSITION_OUTSIDE,
    min_value=0,    # Fully open
    max_value=100,  # Fully closed
    resolution=1
)
```

##### `add_button(name: str, button_type: int, on_press: Optional[Callable] = None, **properties) -> Button`

Add a button input to the device.

**Parameters:**
- `name`: Button name (e.g., "Wall Switch", "Remote Button 1")
- `button_type`: Button type (DSButtonType enum)
- `on_press`: Optional callback function(click_type) called when button is pressed
- `**properties`: Additional button properties

**Returns:** Button instance

**Example:**
```python
def handle_button(click_type):
    if click_type == DSButtonClickType.CLICK_1X:
        print("Single click - toggle light")
    elif click_type == DSButtonClickType.CLICK_2X:
        print("Double click - scene preset")
    elif click_type == DSButtonClickType.HOLD_START:
        print("Long press - start dimming")

wall_switch = device.add_button(
    name="Wall Switch",
    button_type=DSButtonType.SINGLE_PUSHBUTTON,
    on_press=handle_button,
    group=DSGroup.LIGHT
)
```

##### `add_binary_input(name: str, sensor_function: int, on_change: Optional[Callable] = None, **properties) -> BinaryInput`

Add a binary input to the device.

**Parameters:**
- `name`: Input name (e.g., "Window Contact", "Motion Sensor")
- `sensor_function`: Sensor function (DSBinaryInputFunction enum)
- `on_change`: Optional callback function(state) called on state change
- `**properties`: Additional input properties

**Returns:** BinaryInput instance

**Example:**
```python
def handle_motion(state):
    if state:
        print("Motion detected!")
    else:
        print("Motion cleared")

motion = device.add_binary_input(
    name="PIR Sensor",
    sensor_function=DSBinaryInputFunction.MOTION,
    on_change=handle_motion,
    inputUsage=DSBinaryInputUsage.ROOM_CLIMATE
)
```

##### `add_sensor(name: str, sensor_type: int, on_update: Optional[Callable] = None, **properties) -> Sensor`

Add a sensor to the device.

**Parameters:**
- `name`: Sensor name (e.g., "Temperature", "Humidity")
- `sensor_type`: Sensor type (DSSensorType enum)
- `on_update`: Optional callback function(value) called on value update
- `**properties`: Additional sensor properties

**Returns:** Sensor instance

**Example:**
```python
def handle_temperature(value):
    print(f"Temperature: {value}°C")
    if value > 25:
        print("Warning: High temperature!")

temperature = device.add_sensor(
    name="Room Temperature",
    sensor_type=DSSensorType.TEMPERATURE,
    min_value=-20.0,
    max_value=60.0,
    resolution=0.1,
    on_update=handle_temperature,
    sensorUsage=DSSensorUsage.ROOM
)
```

##### `async call_scene(scene_no: int, force: bool = False) -> bool`

Call a scene on this device.

**Parameters:**
- `scene_no`: Scene number (DSScene enum)
- `force`: Force scene even if don't care flag is set

**Returns:** True if successful

**Example:**
```python
# Turn device to preset scene
await device.call_scene(DSScene.PRESENT)

# Emergency off
await device.call_scene(DSScene.DEEP_OFF, force=True)
```

##### `async save_scene(scene_no: int) -> bool`

Save current device state to a scene.

**Parameters:**
- `scene_no`: Scene number to save to

**Returns:** True if successful

**Example:**
```python
# Save current brightness as "Present" scene
await device.save_scene(DSScene.PRESENT)
```

##### `async identify(duration: float = 3.0) -> bool`

Make device identify itself (blink, beep, etc.).

**Parameters:**
- `duration`: Identification duration in seconds

**Returns:** True if successful

**Example:**
```python
# Blink light for 5 seconds
await device.identify(duration=5.0)
```

##### `get_output_channel(channel_type: int) -> Optional[OutputChannel]`

Get output channel by type.

**Parameters:**
- `channel_type`: Channel type to find

**Returns:** OutputChannel instance or None

**Example:**
```python
brightness = device.get_output_channel(DSChannelType.BRIGHTNESS)
if brightness:
    current_value = brightness.get_value()
```

##### `get_properties(query: Dict[str, Any]) -> Dict[str, Any]`

Get device properties.

**Parameters:**
- `query`: Property query from vdSM

**Returns:** Property tree dictionary

---

## Component Classes

### Output & OutputChannel

#### Output

Container for output channels. Automatically created when adding channels.

**Properties:**
- `function`: Output function type (DSOutputFunction enum)
- `mode`: Output mode (DSOutputMode enum)

#### OutputChannel

Represents a controllable output parameter.

##### Constructor

```python
# Note: Don't create directly - use VdSD.add_output_channel()
OutputChannel(
    vdsd: VdSD,
    channel_type: int,
    min_value: float = 0.0,
    max_value: float = 100.0,
    resolution: float = 0.1,
    initial_value: Optional[float] = None,
    ds_index: int = 0,
    name: Optional[str] = None
)
```

##### Methods

###### `set_value(value: float, transition_time: Optional[float] = None) -> bool`

Set channel value (called by vdSM).

**Parameters:**
- `value`: New value (will be clamped to min/max)
- `transition_time`: Transition duration in seconds (optional)

**Returns:** True if successful

**Behavior:**
1. Validates and clamps value to min/max range
2. Triggers Observable callbacks (hardware application)
3. Updates internal state
4. Returns success/failure

**Example:**
```python
# Called by vdSM via protocol - don't call directly
# Instead, register a callback:
brightness.subscribe(apply_to_hardware)
```

###### `update_value(value: float) -> None`

Update channel value from hardware (called by application).

**Parameters:**
- `value`: New value from hardware

**Behavior:**
1. Updates internal state
2. Sends push notification to vdSM
3. Updates age timestamp

**Example:**
```python
# After hardware confirms state change
hardware.on_brightness_changed = lambda val: brightness.update_value(val)
```

###### `subscribe(callback: Callable[[float], None]) -> None`

Register callback for value changes.

**Parameters:**
- `callback`: Function(value) called when vdSM sets value

**Example:**
```python
def apply_brightness(value):
    # Send to hardware
    hardware_driver.set_pwm(int(value * 2.55))  # 0-100 to 0-255
    print(f"Applied: {value}%")

brightness.subscribe(apply_brightness)
```

###### `get_value() -> float`

Get current channel value.

**Returns:** Current value

**Example:**
```python
current = brightness.get_value()
print(f"Current brightness: {current}%")
```

###### `start_dimming(direction: int) -> None`

Start continuous dimming.

**Parameters:**
- `direction`: 1 for up, -1 for down

**Example:**
```python
# Start dimming up
brightness.start_dimming(1)
```

###### `stop_dimming() -> None`

Stop continuous dimming.

**Example:**
```python
brightness.stop_dimming()
```

---

### Button

Represents a button or pushbutton input.

#### Constructor

```python
# Don't create directly - use VdSD.add_button()
Button(
    vdsd: VdSD,
    name: str,
    button_type: int,
    button_id: int = 0,
    **properties
)
```

#### Methods

##### `press(click_type: int = DSButtonClickType.CLICK_1X) -> None`

Simulate button press (called by hardware).

**Parameters:**
- `click_type`: Type of click (DSButtonClickType enum)

**Behavior:**
1. Updates button state
2. Triggers registered callbacks
3. Sends push notification to vdSM

**Example:**
```python
# Hardware detected single click
button.press(DSButtonClickType.CLICK_1X)

# Hardware detected long press start
button.press(DSButtonClickType.HOLD_START)

# Hardware detected double click
button.press(DSButtonClickType.CLICK_2X)
```

##### `subscribe(callback: Callable[[int], None]) -> None`

Register callback for button events.

**Parameters:**
- `callback`: Function(click_type) called on button press

**Example:**
```python
def on_button_event(click_type):
    if click_type == DSButtonClickType.CLICK_1X:
        toggle_light()
    elif click_type == DSButtonClickType.CLICK_2X:
        activate_scene()
    elif click_type == DSButtonClickType.HOLD_START:
        start_dimming()
    elif click_type == DSButtonClickType.HOLD_END:
        stop_dimming()

button.subscribe(on_button_event)
```

---

### BinaryInput

Represents a binary (on/off) input like a contact sensor.

#### Constructor

```python
# Don't create directly - use VdSD.add_binary_input()
BinaryInput(
    vdsd: VdSD,
    name: str,
    sensor_function: int,
    input_id: int = 0,
    **properties
)
```

#### Methods

##### `set_state(state: bool) -> None`

Update binary input state (called by hardware).

**Parameters:**
- `state`: True for active/closed, False for inactive/open

**Behavior:**
1. Updates state if changed
2. Triggers registered callbacks
3. Sends push notification to vdSM

**Example:**
```python
# Window opened
window_contact.set_state(False)

# Window closed
window_contact.set_state(True)

# Motion detected
motion_sensor.set_state(True)

# Motion cleared (after timeout)
motion_sensor.set_state(False)
```

##### `get_state() -> bool`

Get current state.

**Returns:** True if active, False if inactive

**Example:**
```python
if window_contact.get_state():
    print("Window is closed")
else:
    print("Window is open")
```

##### `subscribe(callback: Callable[[bool], None]) -> None`

Register callback for state changes.

**Parameters:**
- `callback`: Function(state) called on state change

**Example:**
```python
def on_window_change(state):
    if state:
        print("Window closed - security OK")
    else:
        print("Warning: Window opened!")

window_contact.subscribe(on_window_change)
```

---

### Sensor

Represents an analog sensor (temperature, humidity, etc.).

#### Constructor

```python
# Don't create directly - use VdSD.add_sensor()
Sensor(
    vdsd: VdSD,
    name: str,
    sensor_type: int,
    sensor_id: int = 0,
    min_value: float = 0.0,
    max_value: float = 100.0,
    **properties
)
```

#### Methods

##### `update_value(value: float) -> None`

Update sensor value (called by hardware).

**Parameters:**
- `value`: New sensor reading

**Behavior:**
1. Validates value against min/max
2. Checks if change exceeds threshold
3. Triggers registered callbacks
4. Sends push notification to vdSM (respecting minPushInterval)

**Example:**
```python
# Temperature reading from hardware
temperature.update_value(22.5)

# Humidity reading
humidity.update_value(65.0)

# Power consumption reading
power.update_value(1250.5)  # Watts
```

##### `get_value() -> Optional[float]`

Get current sensor value.

**Returns:** Current value or None if no reading available

**Example:**
```python
temp = temperature.get_value()
if temp is not None:
    print(f"Current temperature: {temp}°C")
```

##### `subscribe(callback: Callable[[float], None]) -> None`

Register callback for value updates.

**Parameters:**
- `callback`: Function(value) called on value update

**Example:**
```python
def on_temperature_change(value):
    print(f"New temperature: {value}°C")
    if value > 25:
        activate_cooling()

temperature.subscribe(on_temperature_change)
```

---

## Action & State Management

### ActionManager

Manages device actions (identify, reset, calibrate, etc.).

#### Accessing ActionManager

```python
# Access via VdSD
device.actions  # ActionManager instance
```

#### Methods

##### `add_standard_action(name: str, description: str = "", params: Optional[Dict[str, ActionParameter]] = None, handler: Optional[Callable] = None) -> None`

Add a standard (built-in) action.

**Parameters:**
- `name`: Action name (will be prefixed with "std.")
- `description`: Human-readable description
- `params`: Parameter definitions (ActionParameter instances)
- `handler`: Callback function(**params) to execute action

**Example:**
```python
from pyvdcapi.components.actions import ActionParameter

def identify_handler(duration=3.0):
    # Blink LED for specified duration
    hardware.blink_led(duration)
    return {"success": True}

device.actions.add_standard_action(
    name="identify",
    description="Identify device by blinking LED",
    params={
        "duration": ActionParameter(
            param_type="numeric",
            min_value=1.0,
            max_value=10.0,
            default=3.0,
            siunit="s"
        )
    },
    handler=identify_handler
)
```

##### `async call_action(action_name: str, **params) -> Dict[str, Any]`

Execute an action.

**Parameters:**
- `action_name`: Full action name (e.g., "std.identify")
- `**params`: Action parameters

**Returns:** Action result dictionary

**Example:**
```python
result = await device.actions.call_action("std.identify", duration=5.0)
if result.get("success"):
    print("Device identified")
```

---

### StateManager

Manages device states (operational, reachable, service, error).

#### Accessing StateManager

```python
# Access via VdSD
device.states  # StateManager instance
```

#### Methods

##### `add_state_description(name: str, options: Dict[int, str], description: str = "") -> None`

Define a state with its possible values.

**Parameters:**
- `name`: State name (e.g., "operational")
- `options`: Map of option_id → option_name
- `description`: Human-readable description

**Example:**
```python
device.states.add_state_description(
    name="operational",
    options={
        0: "off",
        1: "initializing",
        2: "running",
        3: "error"
    },
    description="Device operational state"
)

device.states.add_state_description(
    name="connection",
    options={
        0: "disconnected",
        1: "connecting",
        2: "connected"
    },
    description="Hardware connection state"
)
```

##### `set_state(name: str, value: Any) -> None`

Set state value.

**Parameters:**
- `name`: State name
- `value`: New value (must be in defined options)

**Behavior:**
1. Validates value against options
2. Triggers registered callbacks
3. Sends push notification to vdSM

**Example:**
```python
# Device starting up
device.states.set_state("operational", "initializing")

# Device ready
device.states.set_state("operational", "running")

# Error occurred
device.states.set_state("operational", "error")
```

##### `get_state(name: str) -> Optional[Any]`

Get current state value.

**Parameters:**
- `name`: State name

**Returns:** Current state value or None

**Example:**
```python
state = device.states.get_state("operational")
if state == "error":
    print("Device is in error state!")
```

##### `on_change(callback: Callable[[str, Any], None]) -> None`

Register callback for state changes.

**Parameters:**
- `callback`: Function(state_name, new_value)

**Example:**
```python
def on_state_change(name, value):
    print(f"State '{name}' changed to '{value}'")
    if name == "operational" and value == "error":
        send_alert("Device error!")

device.states.on_change(on_state_change)
```

---

## Event Handling & Callbacks

### Observable Pattern

All components use the Observable pattern for event notification.

#### Subscribing to Events

```python
# Output channel value changes
def on_brightness_change(value):
    hardware.set_brightness(value)

brightness.subscribe(on_brightness_change)

# Button presses
def on_button_press(click_type):
    if click_type == DSButtonClickType.CLICK_1X:
        toggle_device()

button.subscribe(on_button_press)

# Binary input state changes
def on_motion(state):
    if state:
        activate_light()

motion.subscribe(on_motion)

# Sensor value updates
def on_temperature(value):
    update_display(value)

temperature.subscribe(on_temperature)

# State changes
def on_state_change(name, value):
    log_state_change(name, value)

device.states.on_change(on_state_change)
```

#### Unsubscribing

```python
# Observable supports unsubscribe (if you keep callback reference)
brightness.unsubscribe(on_brightness_change)
```

### Hardware Integration Pattern

#### Bidirectional Sync

```python
# 1. vdSM → Hardware (control)
def apply_to_hardware(value):
    hardware.set_brightness(value)
    # DO NOT call brightness.update_value() here!

brightness.subscribe(apply_to_hardware)

# 2. Hardware → vdSM (feedback)
def hardware_changed_callback(value):
    brightness.update_value(value)  # Sends push to vdSM

hardware.on_brightness_feedback = hardware_changed_callback

# 3. Manual control
def on_manual_control_detected(value):
    brightness.update_value(value)  # Updates vdSM

hardware.on_manual_override = on_manual_control_detected
```

---

## Persistence

### Automatic Saving

Configuration is automatically saved when:
- Properties change
- Devices are added/removed
- Scenes are saved
- Settings are modified

**Control:**
```python
host = VdcHost(
    persistence_file="config.yaml",
    auto_save=True,  # Enable auto-save
    enable_backup=True  # Create .bak shadow file
)
```

### Manual Saving

```python
# Force save current state
await host._persistence.save()
```

### Configuration Structure

```yaml
vdc_host:
  dSUID: "AA112233445566778899AABBCCDDEEFF00"
  type: "vDChost"
  name: "Home Hub"
  model: "HomeHub v1.0"

vdcs:
  "BB112233445566778899AABBCCDDEEFF01":
    dSUID: "BB112233445566778899AABBCCDDEEFF01"
    type: "vDC"
    name: "Light Controller"
    model: "LightVDC v1.0"
    
    vdsds:
      "CC112233445566778899AABBCCDDEEFF02":
        dSUID: "CC112233445566778899AABBCCDDEEFF02"
        type: "vdSD"
        name: "Living Room Light"
        primaryGroup: 1
        outputs:
          - channelType: 1  # Brightness
            min: 0.0
            max: 100.0
            value: 50.0
        scenes:
          8:  # PRESENT scene
            channels:
              1: 75.0  # Brightness at 75%
            effect: 1  # SMOOTH
```

---

## Constants & Enums

All constants are available from `pyvdcapi.core.constants`:

```python
from pyvdcapi.core.constants import (
    # Scenes
    DSScene,
    
    # Groups
    DSGroup,
    
    # Channel types
    DSChannelType,
    
    # Effects
    DSSceneEffect,
    
    # Output properties
    DSOutputFunction,
    DSOutputMode,
    DSOutputUsage,
    
    # Heating
    DSHeatingSystemCapability,
    DSHeatingSystemType,
    
    # Button properties
    DSButtonType,
    DSButtonClickType,
    DSButtonActionMode,
    
    # Sensor properties
    DSSensorType,
    DSSensorUsage,
    
    # Binary input
    DSBinaryInputUsage,
    DSBinaryInputFunction,
    
    # Error states
    DSErrorState
)
```

### Common Constants

```python
# Scene numbers
DSScene.DEEP_OFF       # 5 - Deep off
DSScene.PRESENT        # 8 - Present/working
DSScene.ALARM          # 11 - Alarm

# Groups (colors)
DSGroup.LIGHT          # 1 - Yellow (Light)
DSGroup.BLINDS         # 2 - Gray (Blinds)
DSGroup.HEATING        # 3 - Blue (Heating)

# Channel types
DSChannelType.BRIGHTNESS              # 1
DSChannelType.HUE                     # 2
DSChannelType.SATURATION              # 3
DSChannelType.COLOR_TEMP              # 4
DSChannelType.SHADE_POSITION_OUTSIDE  # 11
DSChannelType.HEATING_POWER           # 21

# Button click types
DSButtonClickType.CLICK_1X      # Single click
DSButtonClickType.CLICK_2X      # Double click
DSButtonClickType.HOLD_START    # Long press start
DSButtonClickType.HOLD_END      # Long press end

# Sensor types
DSSensorType.TEMPERATURE        # 1 - °C
DSSensorType.HUMIDITY           # 2 - %
DSSensorType.ILLUMINATION       # 3 - lux
DSSensorType.CO2_CONCENTRATION  # 22 - ppm

# Error states
DSErrorState.OK                 # 0 - No error
DSErrorState.OPEN_CIRCUIT       # 1 - Open circuit
DSErrorState.SHORT_CIRCUIT      # 2 - Short circuit
DSErrorState.BUS_CONNECTION_PROBLEM  # 4 - Bus problem
```

See [CONSTANTS_README.md](CONSTANTS_README.md) for complete reference.

---

## Complete Examples

### Example 1: Simple Dimmable Light

```python
import asyncio
from pyvdcapi import VdcHost
from pyvdcapi.core.constants import DSGroup, DSChannelType

class HardwareInterface:
    def __init__(self):
        self.brightness = 0
    
    def set_brightness(self, value):
        self.brightness = value
        print(f"Hardware: Brightness set to {value}%")

async def main():
    # Hardware
    hardware = HardwareInterface()
    
    # Create host
    host = VdcHost(
        port=8444,
        mac_address="aa:bb:cc:dd:ee:ff",
        vendor_id="example.com",
        name="Light Controller"
    )
    
    # Create vDC
    vdc = host.create_vdc(
        name="LED Controller",
        model="LED-CTL-v1"
    )
    
    # Create device
    light = vdc.create_vdsd(
        name="Ceiling Light",
        model="LED Dimmer",
        primary_group=DSGroup.LIGHT
    )
    
    # Add brightness channel
    brightness = light.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0
    )
    
    # Connect to hardware
    brightness.subscribe(lambda v: hardware.set_brightness(v))
    
    # Start host
    await host.start()
    print("Light controller running...")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await host.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### Example 2: RGB Light with Color Temperature

```python
import asyncio
from pyvdcapi import VdcHost
from pyvdcapi.core.constants import DSGroup, DSChannelType, DSOutputFunction

class RGBHardware:
    def __init__(self):
        self.brightness = 0
        self.hue = 0
        self.saturation = 0
        self.color_temp = 4000
    
    def set_brightness(self, value):
        self.brightness = value
        self.apply_color()
    
    def set_hue(self, value):
        self.hue = value
        self.apply_color()
    
    def set_saturation(self, value):
        self.saturation = value
        self.apply_color()
    
    def set_color_temp(self, value):
        self.color_temp = value
        self.apply_color()
    
    def apply_color(self):
        print(f"RGB: B={self.brightness}%, H={self.hue}°, "
              f"S={self.saturation}%, CT={self.color_temp}K")

async def main():
    hardware = RGBHardware()
    
    host = VdcHost(
        port=8444,
        mac_address="aa:bb:cc:dd:ee:ff",
        vendor_id="rgb.example.com",
        name="RGB Light Hub"
    )
    
    vdc = host.create_vdc(
        name="RGB Controller",
        model="RGB-CTL-v1"
    )
    
    light = vdc.create_vdsd(
        name="Living Room RGB",
        model="RGB Strip",
        primary_group=DSGroup.LIGHT
    )
    
    # Set output function
    light._outputs[0].set_function(DSOutputFunction.FULL_COLOR)
    
    # Add channels
    brightness = light.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        max_value=100.0
    )
    
    hue = light.add_output_channel(
        channel_type=DSChannelType.HUE,
        max_value=360.0
    )
    
    saturation = light.add_output_channel(
        channel_type=DSChannelType.SATURATION,
        max_value=100.0
    )
    
    color_temp = light.add_output_channel(
        channel_type=DSChannelType.COLOR_TEMP,
        min_value=2700,
        max_value=6500
    )
    
    # Connect to hardware
    brightness.subscribe(hardware.set_brightness)
    hue.subscribe(hardware.set_hue)
    saturation.subscribe(hardware.set_saturation)
    color_temp.subscribe(hardware.set_color_temp)
    
    await host.start()
    print("RGB Light running...")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await host.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### Example 3: Motion-Activated Light

```python
import asyncio
from pyvdcapi import VdcHost
from pyvdcapi.core.constants import (
    DSGroup, DSChannelType,
    DSBinaryInputFunction, DSBinaryInputUsage
)

class MotionLightHardware:
    def __init__(self):
        self.light_on = False
        self.motion_timer = None
    
    def set_light(self, brightness):
        self.light_on = brightness > 0
        print(f"Light: {'ON' if self.light_on else 'OFF'} ({brightness}%)")
    
    async def simulate_motion(self, motion_input):
        """Simulate motion detection"""
        await asyncio.sleep(5)
        print("Motion detected!")
        motion_input.set_state(True)
        
        await asyncio.sleep(2)
        print("Motion cleared")
        motion_input.set_state(False)

async def main():
    hardware = MotionLightHardware()
    
    host = VdcHost(
        port=8444,
        mac_address="aa:bb:cc:dd:ee:ff",
        vendor_id="motion.example.com",
        name="Motion Light System"
    )
    
    vdc = host.create_vdc(
        name="Motion Light Controller",
        model="ML-CTL-v1"
    )
    
    device = vdc.create_vdsd(
        name="Hallway Light",
        model="Motion Light",
        primary_group=DSGroup.LIGHT
    )
    
    # Add brightness output
    brightness = device.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        max_value=100.0
    )
    brightness.subscribe(hardware.set_light)
    
    # Add motion sensor
    motion_timeout = None
    
    async def on_motion_change(state):
        nonlocal motion_timeout
        
        if state:
            # Motion detected - turn on light
            print("Motion → Light ON")
            brightness.update_value(100.0)
            
            # Cancel existing timeout
            if motion_timeout:
                motion_timeout.cancel()
        else:
            # Motion cleared - start timeout
            print("Motion cleared → Starting timeout")
            
            async def turn_off():
                await asyncio.sleep(30)  # 30 second delay
                print("Timeout → Light OFF")
                brightness.update_value(0.0)
            
            motion_timeout = asyncio.create_task(turn_off())
    
    motion = device.add_binary_input(
        name="PIR Motion Sensor",
        sensor_function=DSBinaryInputFunction.MOTION,
        inputUsage=DSBinaryInputUsage.ROOM_CLIMATE
    )
    
    # Use async callback
    motion.subscribe(lambda state: asyncio.create_task(on_motion_change(state)))
    
    await host.start()
    print("Motion light system running...")
    
    # Simulate motion for demo
    asyncio.create_task(hardware.simulate_motion(motion))
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await host.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### Example 4: Climate Control with Temperature Sensor

```python
import asyncio
from pyvdcapi import VdcHost
from pyvdcapi.core.constants import (
    DSGroup, DSChannelType,
    DSSensorType, DSSensorUsage
)

class ThermostatHardware:
    def __init__(self):
        self.heating_power = 0
        self.current_temp = 20.0
        self.target_temp = 21.0
    
    def set_heating_power(self, value):
        self.heating_power = value
        print(f"Heating power: {value}%")
    
    async def simulate_temperature(self, sensor):
        """Simulate temperature changes"""
        while True:
            # Simple heating simulation
            if self.heating_power > 0:
                self.current_temp += 0.1
            else:
                self.current_temp -= 0.05
            
            # Clamp temperature
            self.current_temp = max(15.0, min(30.0, self.current_temp))
            
            # Update sensor
            sensor.update_value(self.current_temp)
            
            await asyncio.sleep(5)

async def main():
    hardware = ThermostatHardware()
    
    host = VdcHost(
        port=8444,
        mac_address="aa:bb:cc:dd:ee:ff",
        vendor_id="climate.example.com",
        name="Climate Controller"
    )
    
    vdc = host.create_vdc(
        name="Thermostat Controller",
        model="THERM-CTL-v1"
    )
    
    thermostat = vdc.create_vdsd(
        name="Living Room Thermostat",
        model="Smart Thermostat",
        primary_group=DSGroup.HEATING
    )
    
    # Add heating power output
    heating = thermostat.add_output_channel(
        channel_type=DSChannelType.HEATING_POWER,
        max_value=100.0
    )
    heating.subscribe(hardware.set_heating_power)
    
    # Add temperature sensor
    def on_temperature_update(value):
        print(f"Temperature: {value:.1f}°C")
        
        # Simple control logic
        if value < hardware.target_temp - 0.5:
            # Too cold - increase heating
            heating.update_value(100.0)
        elif value > hardware.target_temp + 0.5:
            # Too warm - turn off
            heating.update_value(0.0)
    
    temperature = thermostat.add_sensor(
        name="Room Temperature",
        sensor_type=DSSensorType.TEMPERATURE,
        min_value=-20.0,
        max_value=60.0,
        resolution=0.1,
        sensorUsage=DSSensorUsage.ROOM
    )
    temperature.subscribe(on_temperature_update)
    
    await host.start()
    print("Climate control running...")
    
    # Start temperature simulation
    asyncio.create_task(hardware.simulate_temperature(temperature))
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await host.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Best Practices

### 1. Device Initialization

Always initialize in this order:
1. Create VdcHost
2. Create Vdc(s)
3. Create VdSD(s)
4. Add components (outputs, inputs, sensors)
5. Register callbacks
6. Start host

### 2. Callback Registration

Register callbacks **before** starting the host to ensure no events are missed.

### 3. Bidirectional Sync

- **vdSM → Hardware**: Use `subscribe()` callbacks
- **Hardware → vdSM**: Use `update_value()` methods
- **Never** call `update_value()` inside a `subscribe()` callback (creates loop)

### 4. Error Handling

```python
try:
    await host.start()
except OSError as e:
    logger.error(f"Failed to start host: {e}")
    # Port already in use?
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

### 5. Resource Cleanup

Always stop the host gracefully:

```python
try:
    await asyncio.Event().wait()
except KeyboardInterrupt:
    logger.info("Shutting down...")
finally:
    await host.stop()
    logger.info("Stopped")
```

### 6. Persistence

- Use meaningful persistence file paths
- Enable backup for production systems
- Test configuration loading on startup

### 7. Testing

Test devices without vdSM:

```python
# Simulate vdSM commands
brightness.set_value(75.0)  # Simulates vdSM set

# Simulate hardware events
brightness.update_value(80.0)  # Simulates hardware feedback
button.press(DSButtonClickType.CLICK_2X)
sensor.update_value(23.5)
```

---

## Troubleshooting

### Host won't start

**Error:** `OSError: [Errno 48] Address already in use`

**Solution:** Port 8444 is already in use. Either:
- Stop other vDC host
- Use different port: `VdcHost(port=8445)`

### Device not appearing in vdSM

**Checklist:**
1. Host started? `await host.start()`
2. vdSM connected? `host.is_connected()`
3. Device created before connection? Device should be created before vdSM connects
4. Check logs for errors

### Callbacks not firing

**Checklist:**
1. Callback registered? `component.subscribe(callback)`
2. Callback registered before `host.start()`?
3. Check callback function signature matches expected parameters

### Configuration not persisting

**Checklist:**
1. Auto-save enabled? `VdcHost(auto_save=True)`
2. Write permissions on persistence file?
3. File path correct?

---

## Further Reading

- [Architecture Document](ARCHITECTURE.md) - System design and component interactions
- [Constants Reference](CONSTANTS_README.md) - Complete enum and constant documentation
- [vDC API Properties](Documentation/vdc-API-properties/) - Official property specifications
- [Examples Directory](examples/) - Additional working examples

---

**Version:** 1.0.0  
**Last Updated:** January 10, 2026  
**Maintainer:** KarlKiel
