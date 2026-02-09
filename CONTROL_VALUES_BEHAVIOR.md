# Control Values: Bidirectional Access Pattern

## Overview

Control Values in the vDC API have a **bidirectional access pattern** that differs from regular properties:

- **From DSS perspective**: Write-only (`acc="w"`)
- **From Device perspective**: Read-only (can read but should not write)

This pattern ensures proper separation of concerns and data flow direction.

## Use Case Example: Heating Control

### Scenario
A room temperature is controlled via a digitalSTROM native device:
1. User adjusts target temperature on a digitalSTROM controller
2. DSS sends `heatingLevel` control value to the vDC (write operation)
3. vDC stores the control value
4. Radiator device reads the control value (read operation)
5. Radiator adjusts its heating cycles based on the value

## API Specification (Section 4.11)

From the vDC API documentation:

```
Control Values are not regular properties, but like properties, they are 
identified by their name and represent persistent values. They can also 
support group and zone differentiation. However, control values cannot 
be read but only written.
```

**Important**: "cannot be read" refers to the DSS perspective (API access="w"), NOT the device implementation!

### heatingLevel Property

- **Name**: `heatingLevel`
- **Type**: `double`
- **Range**: -100 to +100
  - Positive values: Heating intensity (0 to 100)
  - Negative values: Cooling intensity (-100 to 0)
  - Zero: Neutral (no heating/cooling)
- **Access**: `acc="w"` (write-only from DSS)
- **Description**: "control value for heating (+) or cooling (-) power in %"

## Implementation Details

### 1. Data Structure

```python
# pyvdcapi/properties/control_value.py

@dataclass
class ControlValue:
    name: str
    value: float
    group: Optional[int] = None
    zone_id: Optional[int] = None
    last_updated: float = 0.0

class ControlValues:
    def get(self, name: str) -> Optional[ControlValue]
    def set(self, name: str, value: float, ...) -> ControlValue
    def to_persistence(self) -> Dict[str, Any]
    def to_simple_dict(self) -> Dict[str, float]
```

### 2. DSS → Device Flow (Write Path)

When DSS sends a control value update:

```python
# pyvdcapi/entities/vdc_host.py - handles SetControlValue notification

# 1. DSS sends SetControlValue notification
notification = {
    "dSUID": "device_dsuid",
    "name": "heatingLevel",
    "value": 75.0
}

# 2. VdcHost routes to device
device.set_control_value("heatingLevel", 75.0)

# 3. VdSD updates control value and triggers callback
self.controlValues.set(control_name, value)
self._hardware_callbacks["on_control_change"](control_name, value)

# 4. Persist to storage
self._persistence.update_vdsd_property(
    self.dsuid, 
    "controlValues", 
    self.controlValues.to_persistence()
)

# 5. Send push notification to vdSM
await host.send_push_notification(
    self.dsuid, 
    {"controlValues": {control_name: value}}
)
```

### 3. Device Reading (Read Path)

Device hardware can read control values at any time:

```python
# Device reads control value
control_value = device.controlValues.get('heatingLevel')

if control_value:
    heating_level = control_value.value
    group = control_value.group
    zone = control_value.zone_id
    
    # Use value to control hardware
    adjust_radiator_valve(heating_level)
```

### 4. Hardware Callback Pattern

Devices register callbacks to react to control value changes:

```python
class HeatingRadiator:
    def __init__(self, device: VdSD):
        # Register callback
        device._hardware_callbacks['on_control_change'] = self.on_control_change
    
    def on_control_change(self, control_name: str, value: float):
        """Called when DSS updates a control value."""
        if control_name == 'heatingLevel':
            # Read the full control value
            cv = self.device.controlValues.get('heatingLevel')
            
            # React to the new value
            self.adjust_heating(cv.value)
```

## Access Control Summary

| Perspective | Operation | Method | Purpose |
|------------|-----------|--------|---------|
| **DSS** | Write | `SetControlValue` notification | Send control updates to device |
| **DSS** | Read | ❌ Not allowed | DSS never reads control values |
| **Device** | Read | `controlValues.get(name)` | Device reads value to control hardware |
| **Device** | Write | ❌ Should not write | Only DSS can write control values |

## Key Behavioral Rules

### ✅ Correct Behavior

1. **DSS writes control values** via `SetControlValue` notification
2. **Device reads control values** via `controlValues.get()` method
3. **Control values are persisted** across restarts
4. **Hardware callbacks trigger** when control values change
5. **Push notifications sent** to vdSM after updates

### ❌ Incorrect Behavior

1. Device arbitrarily writing control values (bypassing DSS)
2. DSS attempting to read control values (API doesn't support this)
3. Not persisting control values
4. Not triggering hardware callbacks on changes

## Testing

See [examples/control_values_heating_demo.py](examples/control_values_heating_demo.py) for a complete demonstration of:

- DSS writing control values
- Device reading control values
- Hardware callback integration
- Realistic heating radiator simulation

## Persistence

Control values are automatically persisted:

```python
# Persistence format
{
    "controlValues": {
        "heatingLevel": {
            "name": "heatingLevel",
            "value": 75.0,
            "group": 1,
            "zone_id": 0,
            "last_updated": 1770667350.740511
        }
    }
}
```

After restart, devices can immediately access persisted control values:

```python
# Device restores from persistence
device = VdSD.from_persistence(config)

# Control values automatically restored
heating = device.controlValues.get('heatingLevel')
# heating.value == 75.0 (restored from persistence)
```

## Compliance Verification

The implementation is **fully compliant** with vDC API section 4.11:

- ✅ Control values identified by name
- ✅ Persistent storage supported
- ✅ Group and zone differentiation supported
- ✅ Write-only from DSS perspective (acc="w")
- ✅ Read-only from device perspective
- ✅ Hardware callback integration
- ✅ Push notification support
- ✅ Timestamp tracking

## See Also

- [Documentation/vdc-API-properties/14-Control-Values.md](Documentation/vdc-API-properties/14-Control-Values.md) - API specification
- [pyvdcapi/properties/control_value.py](pyvdcapi/properties/control_value.py) - Implementation
- [pyvdcapi/entities/vdsd.py](pyvdcapi/entities/vdsd.py) - VdSD integration
- [examples/control_values_heating_demo.py](examples/control_values_heating_demo.py) - Working example
