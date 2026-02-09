# Age Property Implementation

## Overview

The `age` property is a common read-only property across multiple vDC API components that indicates **how long ago (in seconds)** a value or state was last updated. This provides freshness information to the digitalSTROM system (vdSM).

## API Specification

Per vDC API specification, the `age` property:

- **Type**: `double` (or `NULL` if no recent state known)
- **Access**: `r` (read-only)
- **Unit**: **Seconds** (not milliseconds!)
- **Calculation**: `current_time - last_update_timestamp`

## Components with Age Property

### 1. Button Input (Section 4.2.3)

**Location**: `buttonInputStates[].age`

**Description**: Age of the state shown in the `value` and `clickType` fields in seconds.

**Implementation**: [pyvdcapi/components/button_input.py](pyvdcapi/components/button_input.py#L343-L366)

```python
def get_state(self) -> Dict[str, Any]:
    """Get current button state for property queries."""
    # Update age since last state change
    self._age = time.time() - self._last_update_time
    
    return {
        "value": self._value,
        "clickType": self._click_type,
        "age": self._age,  # In seconds
        "error": self._error
    }
```

**Timestamp Tracking**: `self._last_update_time` updated on each button event

### 2. Binary Input (Section 4.3.3)

**Location**: `binaryInputStates[].age`

**Description**: Age of the state shown in the `value` field in seconds.

**Implementation**: [pyvdcapi/components/binary_input.py](pyvdcapi/components/binary_input.py#L272-L284)

```python
def get_age(self) -> float:
    """
    Get age of current state in seconds.
    
    Returns:
        Seconds since last state change
    """
    return time.time() - self._last_change_time
```

**Timestamp Tracking**: `self._last_change_time` updated in:
- `set_state()` - When state is explicitly set
- `update_state()` - When state changes from hardware

**Usage in Property Tree**:
```python
{
    "state": {
        "value": self._state,
        "age": self.get_age()  # In seconds
    }
}
```

### 3. Sensor Input (Section 4.4.3)

**Location**: `sensorStates[].age`

**Description**: Age of the state shown in the `value` field in seconds.

**Implementation**: [pyvdcapi/components/sensor.py](pyvdcapi/components/sensor.py#L378-L391)

```python
def get_age(self) -> Optional[float]:
    """
    Get age of current reading in seconds.
    
    Returns:
        Seconds since last update, or None if no reading
    """
    if self._last_update_time is None:
        return None
    return time.time() - self._last_update_time
```

**Timestamp Tracking**: `self._last_update_time` updated in:
- `update_value()` - When sensor value is updated
- Can be `None` initially (returns `NULL` to API)

**Usage in Property Tree**:
```python
{
    "value": self._value,
    "age": self.get_age()  # In seconds or None
}
```

### 4. Output Channel (Section 4.9.2)

**Location**: `channels[].age`

**Description**: Age of the state shown in the `value` field in seconds. Indicates when value was last applied to actual device hardware, or when an actual output status was last received from the device. Age is `NULL` when a new value was set but not yet applied to the device.

**Implementation**: [pyvdcapi/components/output_channel.py](pyvdcapi/components/output_channel.py#L354-L366)

```python
def get_age(self) -> float:
    """
    Get age of current value in seconds.
    
    Returns:
        Seconds since last update
    """
    return time.time() - self._last_update
```

**Timestamp Tracking**: `self._last_update` updated in:
- `set_value()` - When channel value is set
- `apply_scene()` - When scene is applied
- Always updated even if value unchanged

**Usage in Property Tree**:
```python
{
    "value": self._value,
    "age": self.get_age()  # In seconds
}
```

## Bug Fix History

### Issue Found (2026-02-09)

All `get_age()` methods were incorrectly returning age in **milliseconds** instead of **seconds**:

```python
# ❌ INCORRECT (before fix)
def get_age(self) -> float:
    return (time.time() - self._last_change_time) * 1000.0
```

This violated the vDC API specification which explicitly states age should be in seconds.

### Fix Applied

Removed the `* 1000.0` multiplication from all `get_age()` methods:

```python
# ✅ CORRECT (after fix)
def get_age(self) -> float:
    return time.time() - self._last_change_time
```

**Files Modified**:
1. [pyvdcapi/components/binary_input.py](pyvdcapi/components/binary_input.py#L272-L284)
2. [pyvdcapi/components/sensor.py](pyvdcapi/components/sensor.py#L378-L391)
3. [pyvdcapi/components/output_channel.py](pyvdcapi/components/output_channel.py#L354-L366)

**Note**: `button_input.py` was already correct as it calculated age inline in `get_state()` without the multiplication.

## Timestamp Management

Each component maintains its own timestamp tracking:

| Component | Timestamp Field | Updated When |
|-----------|----------------|--------------|
| ButtonInput | `_last_update_time` | Button event occurs (`set_click_type()`) |
| BinaryInput | `_last_change_time` | State changes (`set_state()`, `update_state()`) |
| Sensor | `_last_update_time` | Value updated (`update_value()`) |
| OutputChannel | `_last_update` | Value set (`set_value()`, `apply_scene()`) |

All timestamps use `time.time()` which returns Unix epoch time in seconds (float).

## API Compliance

✅ **All age properties now comply with vDC API specification**:

1. ✅ Return type: `double` (float in Python)
2. ✅ Unit: Seconds (not milliseconds)
3. ✅ Access: Read-only
4. ✅ Can return `None` (mapped to `NULL` in API) when no recent state
5. ✅ Accurately reflects time since last update
6. ✅ Updated on every state/value change

## Testing

Age calculation correctness can be verified with:

```bash
python3 -c "
import sys
import time
sys.path.insert(0, '.')

from pyvdcapi.components import binary_input, sensor, output_channel
import inspect

# Verify no multiplication by 1000 in get_age() methods
for module, class_name in [
    (binary_input, 'BinaryInput'),
    (sensor, 'Sensor'),
    (output_channel, 'OutputChannel')
]:
    cls = getattr(module, class_name)
    source = inspect.getsource(cls.get_age)
    if '* 1000' in source or '*1000' in source:
        print(f'❌ {class_name}.get_age() still uses milliseconds')
    else:
        print(f'✅ {class_name}.get_age() returns seconds')
"
```

## Examples

### Example 1: Binary Input State Age

```python
from pyvdcapi.components.binary_input import BinaryInput

# Create binary input (e.g., door contact sensor)
door_sensor = BinaryInput(vdsd=device, name="Front Door", input_id=0)

# Sensor detects door opened
door_sensor.set_state(True)

# Wait 2.5 seconds
import time
time.sleep(2.5)

# Get age (should be approximately 2.5 seconds)
age = door_sensor.get_age()
print(f"Door state age: {age:.2f} seconds")  # ~2.50 seconds

# Query state (includes age)
state = door_sensor.to_dict()["state"]
print(f"State: {state}")
# {'value': True, 'age': 2.50}
```

### Example 2: Sensor Value Age

```python
from pyvdcapi.components.sensor import Sensor
from pyvdcapi.core.constants import DSSensorType

# Create temperature sensor
temp_sensor = Sensor(
    sensor_id=0, 
    name="Room Temperature",
    sensor_type=DSSensorType.TEMPERATURE
)

# Update temperature reading
temp_sensor.update_value(23.5)

# Wait 5 seconds
time.sleep(5.0)

# Get age
age = temp_sensor.get_age()
print(f"Temperature reading age: {age:.2f} seconds")  # ~5.00 seconds

# If no reading yet
new_sensor = Sensor(sensor_id=1, name="New Sensor", sensor_type=DSSensorType.TEMPERATURE)
age = new_sensor.get_age()
print(f"New sensor age: {age}")  # None
```

### Example 3: Output Channel Age

```python
from pyvdcapi.components.output_channel import OutputChannel
from pyvdcapi.core.constants import DSChannelType

# Create brightness channel
brightness = OutputChannel(channel_type=DSChannelType.BRIGHTNESS)

# Set brightness to 75%
brightness.set_value(75.0)

# Wait 1.5 seconds
time.sleep(1.5)

# Get age
age = brightness.get_age()
print(f"Brightness value age: {age:.2f} seconds")  # ~1.50 seconds

# Get state dict (used by property tree)
state = brightness.to_dict()
print(f"Channel state: {state}")
# {'value': 75.0, 'age': 1.50}
```

## Integration with Property Tree

Age values are automatically included when components serialize to property trees for vdSM queries:

```python
# Example: vdSM queries binaryInputStates
{
    "binaryInputStates": [
        {
            "value": True,
            "age": 12.34,  # Seconds since last change
            "error": 0
        }
    ]
}

# Example: vdSM queries sensorStates
{
    "sensorStates": [
        {
            "value": 23.5,
            "age": 5.67,   # Seconds since last update
            "error": 0
        }
    ]
}
```

## See Also

- [vDC API Documentation - Button Input](Documentation/vdc-API-properties/05-Button-Input.md)
- [vDC API Documentation - Binary Input](Documentation/vdc-API-properties/06-Binary-Input.md)
- [vDC API Documentation - Sensor Input](Documentation/vdc-API-properties/07-Sensor-Input.md)
- [vDC API Documentation - Output Channel](Documentation/vdc-API-properties/12-Output-Channel.md)
- [Property Compliance Verification](verify_property_compliance.py)
