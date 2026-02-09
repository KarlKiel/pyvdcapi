# vDC API Property Reference - Quick Guide

## Property Categories

All vDC components follow a three-tier property structure:

### 📘 Description Properties (`acc="r"`)
**Characteristics:**
- ✓ Read-only (cannot be changed by DSS)
- ✓ Invariable hardware capabilities
- ✓ Set during component initialization
- ✗ Not persisted (recreated on restart)

**Examples:** name, dsIndex, channelType, buttonType, min, max, sensorType, function

### 🔧 Settings Properties (`acc="r/w"`)
**Characteristics:**
- ✓ Read-write (can be changed by DSS/vdSM)
- ✓ Persistent configuration
- ✓ Saved to YAML files
- ✓ Restored on device restart

**Examples:** group, mode, function, pushChanges, minPushInterval

### 📊 State Properties (`acc="r"`)
**Characteristics:**
- ✓ Read-only (cannot be changed by DSS)
- ✓ Dynamic runtime values
- ✓ Change during device operation
- ✗ Not persisted (transient only)

**Examples:** value, age, error, clickType

## Component Property Summary

### ButtonInput

**Description** (read-only):
- `name` - Human-readable button name
- `dsIndex` - Button index (0..N-1)
- `supportsLocalKeyMode` - Can be local button
- `buttonID` - Physical button ID
- `buttonType` - Type of physical button (0-4)
- `buttonElementID` - Element of multi-contact button

**Settings** (read-write, persistent):
- `group` - dS group number (1-63)
- `function` - Function type (0=device, 5=room, etc.)
- `mode` - Button mode (0=standard, 2=presence, etc.)
- `channel` - Channel to control (0=default)
- `setsLocalPriority` - Should set local priority
- `callsPresent` - Should call present

**State** (read-only, dynamic):
- `value` - Button active/inactive (boolean)
- `age` - Time since last update (seconds)
- `clickType` - Click type (0-14, 255=idle)
- `error` - Error state (optional)

### BinaryInput

**Description** (read-only):
- `name` - Human-readable input name
- `dsIndex` - Input index (0..N-1)
- `inputType` - Type of input (contact, motion, etc.)
- `inputUsage` - Usage field (0=undefined, 1=room, 2=outdoors, 3=user)
- `sensorFunction` - Sensor function enum

**Settings** (read-write, persistent):
- `group` - dS group number
- `sensorFunction` - Sensor function type

**State** (read-only, dynamic):
- `value` - Input state (boolean)
- `age` - Time since last change (seconds)
- `extendedValue` - Extended value (optional)
- `error` - Error state (optional)

### Sensor

**Description** (read-only):
- `name` - Human-readable sensor name
- `dsIndex` - Sensor index (0..N-1)
- `sensorType` - Type of sensor (temperature, humidity, etc.)
- `sensorUsage` - Usage field (0=undefined, 1=room, 2=outdoors, 3=user)
- `min` - Minimum valid value
- `max` - Maximum valid value
- `resolution` - Measurement precision
- `updateInterval` - Update interval (optional)
- `aliveSignInterval` - Alive signal interval (optional)

**Settings** (read-write, persistent):
- `group` - dS group number
- `minPushInterval` - Minimum push interval (optional)
- `changesOnlyInterval` - Changes-only interval (optional)

**State** (read-only, dynamic):
- `value` - Current sensor reading
- `age` - Time since last update (seconds)
- `contextId` - Context ID (optional)
- `contextMsg` - Context message (optional)
- `error` - Error state (optional)

### Output

**Description** (read-only):
- `defaultGroup` - Default dS Application ID
- `name` - Human-readable output name
- `function` - Output function (0=on/off, 1=dimmer, 2=positional, etc.)
- `outputUsage` - Usage field (0=undefined, 1=room, 2=outdoors, 3=user)
- `variableRamp` - Supports variable ramps (boolean)
- `maxPower` - Max output power in Watts (optional)
- `activeCoolingMode` - Active cooling capability (optional)

**Settings** (read-write, persistent):
- `activeGroup` - Active dS Application ID
- `groups` - Group memberships (list of boolean)
- `mode` - Output mode (0=disabled, 1=binary, 2=gradual, 127=default)
- `pushChanges` - Push value changes immediately
- `onThreshold` - Minimum brightness for on (optional)
- `minBrightness` - Minimum hardware brightness (optional)
- `dimTimeUp/Down` - Dimming times (optional)
- `heatingSystemCapability` - Heating system type (optional)
- `heatingSystemType` - Heating valve type (optional)

**State** (read-only, dynamic):
- `localPriority` - Local priority enabled (boolean) *Exception: r/w*
- `error` - Error state (0=ok, 1=open circuit, etc.)

### OutputChannel

**Description** (read-only):
- `name` - Human-readable channel name
- `channelType` - Channel type ID (1=brightness, 2=hue, etc.)
- `dsIndex` - Channel index (0=default channel)
- `min` - Minimum channel value
- `max` - Maximum channel value
- `resolution` - Channel resolution

**Settings** (read-write, persistent):
- Currently no per-channel settings defined in API

**State** (read-only, dynamic):
- `value` - Current channel value
- `age` - Time since last update (seconds)

## Implementation Pattern

### Creating a New Component

```python
class MyComponent:
    def __init__(self, vdsd, name, ...):
        # Description properties (read-only)
        self.name = name
        self.ds_index = 0
        self.usage = 0
        
        # Settings properties (read-write, persistent)
        self.group = 1
        self.mode = 0
        
        # State properties (read-only, dynamic)
        self._value = None
        self._last_update = time.time()
    
    def to_dict(self):
        """Export all properties"""
        return {
            # Description
            "name": self.name,
            "dsIndex": self.ds_index,
            "usage": self.usage,
            # Settings
            "group": self.group,
            "mode": self.mode,
            # State
            "value": self._value,
            "age": time.time() - self._last_update,
        }
    
    def update_settings(self, settings):
        """Update Settings properties only"""
        if "group" in settings:
            self.group = settings["group"]
        if "mode" in settings:
            self.mode = settings["mode"]
        # Description and State properties are NOT updated here!
```

## Common Enums

### Output Function
- 0: on/off only
- 1: dimmer
- 2: positional (blinds, valves)
- 3: dimmer with color temperature
- 4: full color dimmer (RGB/HSV)
- 5: bipolar (heating/cooling)
- 6: internally controlled

### Output Mode
- 0: disabled
- 1: binary
- 2: gradual
- 127: default

### Channel Types
- 0: default
- 1: brightness
- 2: hue
- 3: saturation
- 4: color temperature
- 11: shade position (outdoor)
- 21: heating power
- 41: audio volume
- [See API docs for complete list]

## Property Access Rules

### DSS Can Modify
✓ Settings properties only (`acc="r/w"`)

### DSS Cannot Modify
✗ Description properties (`acc="r"`)
✗ State properties (`acc="r"`)

### Must Be Persisted
✓ Settings properties only

### Not Persisted
✗ Description properties (recreated on init)
✗ State properties (transient values)

## Verification

Run compliance checker:
```bash
python verify_property_compliance.py
```

Expected: 41/41 checks passed ✅
