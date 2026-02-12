# Property-Driven Binding Implementation

## Overview

The binding layer connects native device hardware to vDC API components by mapping native variables to vDC properties. The binding behavior is **automatically determined by the vDC API properties** that are already part of the device configuration (and saved in templates).

**No separate "binding" configuration is needed** - the vDC API properties already tell us everything!

## Binding Behavior by Component Type

### 1. Buttons - Always Event-Driven

**Properties**: `clickType/value` OR `actionId/actionMode` (never both)

**Binding**: ALWAYS event-driven (no polling option)

**Reason**: Buttons report EITHER click patterns (clickType 0-14,255) OR direct scene calls (actionId/actionMode). Both are discrete events, not continuous values. Polling makes no sense for discrete button events.

**Two Button Modes**:
- **Standard mode** (default): Reports `clickType` (0-14, 255) and `value` (active/inactive)
- **Action mode**: Reports `actionId` (scene id) and `actionMode` (0=normal, 1=force, 2=undo)

**Usage**:
```python
# Buttons ALWAYS require event registration
device.bind_inputs_auto({
    "buttons": [
        {"register": hardware.on_button_event},  # Required
    ]
})
```

**vDC API Reference**: Button Input State (section 4.2.3)
- clickType values: 0-14, 255
- These are discrete events that occur at specific moments
- No continuous value to poll

---

### 2. Binary Inputs - Property-Driven

**Properties**: `value` (boolean) or `extendedValue` (integer), `inputType`

**Binding**: Event-driven OR polling (based on hardware capability)

**Reason**: The `inputType` property defines the sensor type (motion, contact, etc.) which guides whether push or pull is more appropriate. However, the actual binding choice depends on hardware capabilities.

**Usage**:
```python
device.bind_inputs_auto({
    "binary_inputs": [
        # Event-driven (if hardware supports callbacks)
        {"register": hardware.on_motion_change},
        
        # OR Polling (if hardware doesn't support events)
        {"getter": hardware.get_door_state, "poll_interval": 0.2},
    ]
})
```

**vDC API Reference**: Binary Input Descriptions (section 4.3.1)
- `inputType`: Defines sensor type
- `updateInterval`: How often the value updates
- The vDC can push updates or respond to polls from dSS

---

### 3. Sensors - Throttled Push

**Properties**: `value`, `min_push_interval`, `changes_only_interval`, `update_interval`

**Binding**: Polling, events, or both

**Reason**: 
- `update_interval`: Normal update frequency of the native device variable
- `min_push_interval`: Minimum time between pushes to dSS (throttling)
- `changes_only_interval`: Max time between pushes if value unchanged
- These properties control push throttling behavior

**Usage**:
```python
device.bind_inputs_auto({
    "sensors": [
        # Polling (uses sensor.min_push_interval as default poll rate)
        {"getter": hardware.get_temperature},
        
        # OR Event-driven
        {"register": hardware.on_temp_change},
        
        # OR Both (for reliability)
        {
            "getter": hardware.get_temperature,
            "register": hardware.on_temp_change,
        },
    ]
})
```

**vDC API Reference**: Sensor Settings (section 4.4.2)
- `minPushInterval`: Minimum seconds between push notifications
- `changesOnlyInterval`: Interval for pushes when value doesn't change
- Hardware can update faster, but pushes are throttled per these settings

---

### 4. Output Channels - Always Bidirectional

**Properties**: `value`, `push_changes` (in output settings)

**Binding**: Always bidirectional (getter AND setter required)

**Reason**: The output's `push_changes` setting is ALWAYS True (enforced by library). This means:
- vdSM→hardware: Changes from dSS must update native variable (setter)
- hardware→vdSM: Changes from hardware must be pushed back (getter)

**Usage**:
```python
# Output channels - ALWAYS bidirectional
device.bind_output_channel(
    channel_type=1,  # Brightness
    getter=hardware.get_brightness,  # hardware→vdSM
    setter=hardware.set_brightness,  # vdSM→hardware
    poll_interval=0.1,  # Check for hardware changes
)
```

**vDC API Reference**: Output Settings (section 5.2.2)
- `pushChanges`: If True, output pushes value changes to vdSM
- This library forces `pushChanges=True` always (per vDC spec)
- Bi-directional binding is mandatory

---

## Implementation Changes

### What Was Removed

❌ **Removed**: Custom `_binding` attribute on components
❌ **Removed**: Binding config in templates (YAML)
❌ **Removed**: Template extraction/restoration of binding config
❌ **Removed**: Mode selection logic ("poll", "event", "mixed")

### What Remains

✅ **Kept**: All single-step binding methods
- `bind_sensor()`, `bind_sensor_events()`
- `bind_binary_input()`, `bind_binary_input_events()`
- `bind_button_input()`, `bind_button_input_events()`
- `bind_output_channel()`, `bind_output_channel_events()`

✅ **Simplified**: `bind_inputs_auto()`
- No longer reads `_binding` attribute
- Uses vDC API properties to guide behavior
- Buttons: Always calls `bind_button_input_events()`
- Binary inputs: Uses `register` if provided, else `getter`
- Sensors: Uses `register` and/or `getter` based on what's provided
- Uses `sensor.min_push_interval` as default poll interval

### Modified Files

1. **`pyvdcapi/entities/vdsd.py`**
   - Simplified `bind_inputs_auto()` method
   - Buttons: Force event-driven binding
   - Sensors: Use `min_push_interval` as default poll rate
   - Binary inputs: Flexible based on hardware capability

2. **`pyvdcapi/templates/template_manager.py`**
   - Removed `_binding` extraction from `_extract_*_config()`
   - Removed `_binding` restoration from `_apply_*_configs()`
   - Template saves/loads only vDC API properties (as it should)

3. **`pyvdcapi/templates/README.md`**
   - Replaced "binding config" section with property-driven explanation
   - Shows how vDC API properties define behavior
   - Simplified examples

4. **`examples/07_automatic_binding.py`**
   - Completely rewritten to show property-driven approach
   - Four focused examples (button, binary, sensor, output)
   - Emphasizes that vDC properties define behavior

5. **`examples/README.md`**
   - Updated description to reflect property-driven approach

## Key Insight

The vDC API specification already defines everything we need:

- **Buttons**: `clickType` is an event → always push
- **Binary Inputs**: `inputType` property guides behavior → flexible
- **Sensors**: `min_push_interval`, `changes_only_interval` → throttled push
- **Outputs**: `pushChanges` always True → bidirectional

We don't need a separate "binding" configuration because **the vDC API properties ARE the configuration**!

## Usage Pattern

```python
# 1. Create device from template
#    (vDC API properties restored from template automatically)
device = vdc.create_vdsd_from_template(
    template_name="multi_sensor",
    template_type="deviceType",
    instance_name="Sensor_1",
)

# 2. Bind to native hardware
#    (binding behavior determined by vDC API properties)
device.bind_inputs_auto({
    "buttons": [{"register": hw.on_button}],  # Always event-driven
    "binary_inputs": [{"register": hw.on_motion}],  # Event if available
    "sensors": [{"getter": hw.get_temp}],  # Uses sensor.min_push_interval
})
```

## Testing Status

✅ All files compile successfully
✅ No syntax errors
✅ Template manager simplified (no binding config)
✅ VdSD simplified (uses vDC properties)
✅ Example demonstrates property-driven approach
✅ Documentation updated

## Benefits of This Approach

1. **Simpler**: No separate binding configuration to maintain
2. **Correct**: Uses actual vDC API properties (specification-compliant)
3. **Automatic**: Template save/load already handles vDC properties
4. **Intuitive**: The vDC API properties directly map to binding behavior
5. **Maintainable**: Less code, fewer edge cases
