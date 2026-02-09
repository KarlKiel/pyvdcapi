# digitalSTROM Constants Reference

This document describes the standard digitalSTROM constants implemented in `pyvdcapi/core/constants.py`.

**See Also:** 
- [API_REFERENCE.md](API_REFERENCE.md) - Complete API documentation
- [README.md](README.md) - Feature overview
- [TESTING.md](TESTING.md) - Test examples using constants

## Scene Numbers

Standard scene numbers based on digitalSTROM specification:

### Area Scenes (0-4)
| Number | Name | Description |
|--------|------|-------------|
| 0 | AREA_1_OFF | Turn off area 1 devices |
| 1 | AREA_2_OFF | Turn off area 2 devices |
| 2 | AREA_3_OFF | Turn off area 3 devices |
| 3 | AREA_4_OFF | Turn off area 4 devices |
| 4 | GLOBAL_OFF | Turn off all devices |

### Named Scenes (5-12)
| Number | Name | Description | Default Effect |
|--------|------|-------------|----------------|
| 5 | DEEP_OFF | Deep off / power saving | Smooth |
| 6 | STANDBY | Standby mode (very dim) | Slow |
| 7 | WAKE_UP | Morning / wake up (50%) | Very Slow |
| 8 | PRESENT | Present / working (75%) | Smooth |
| 9 | ABSENT | Absent / night (10%) | Smooth |
| 10 | SLEEPING | Sleeping (off) | Very Slow |
| 11 | ALARM | Alarm (full brightness) | Alert/Blink |
| 12 | FIRE | Fire alarm / panic | None (immediate) |

### Control Scenes (13-31)
| Number | Name | Description |
|--------|------|-------------|
| 13 | STOP | Stop dimming/movement |
| 14 | MIN | Set to minimum value (0%) |
| 15 | MAX | Set to maximum value (100%) |
| 16 | INC | Increment value |
| 17 | DEC | Decrement value |
| 18-21 | AREA_1-4_ON | Area stepping on (100%) |
| 22-25 | AREA_1-4_INC | Area increment |
| 26-29 | AREA_1-4_DEC | Area decrement |
| 30 | AUTO_STANDBY | Automatic standby |
| 31 | SUN_PROTECTION | Sun protection (shades down) |

### User Presets (32-63)
| Number Range | Name |
|--------------|------|
| 32-63 | PRESET_0 through PRESET_31 |

### Special Scenes
| Number | Name | Description |
|--------|------|-------------|
| 127 | LOCAL_OFF | Local off / stop |

## Channel Types

Standard channel types for device outputs:

### Light Channels (0-6)
| Type | Name | Description | Unit |
|------|------|-------------|------|
| 0 | DEFAULT | Default channel (usually brightness) | - |
| 1 | BRIGHTNESS | Brightness | 0-100% |
| 2 | HUE | Hue | 0-360° |
| 3 | SATURATION | Saturation | 0-100% |
| 4 | COLOR_TEMP | Color temperature | Kelvin or mired |
| 5 | CIE_X | CIE x coordinate | 0-1 |
| 6 | CIE_Y | CIE y coordinate | 0-1 |

### Shade/Blind Channels (11-15)
| Type | Name | Description |
|------|------|-------------|
| 11 | SHADE_POSITION_OUTSIDE | Shade position outside |
| 12 | SHADE_POSITION_INDOOR | Shade position indoor |
| 13 | SHADE_ANGLE_OUTSIDE | Shade angle/slat outside |
| 14 | SHADE_ANGLE_INDOOR | Shade angle/slat indoor |
| 15 | SHADE_OPENING_ANGLE | Opening angle |

### HVAC/Climate Channels (21-26)
| Type | Name | Description |
|------|------|-------------|
| 21 | HEATING_POWER | Heating power |
| 22 | HEATING_VALUE | Heating valve position |
| 23 | COOLING_POWER | Cooling power |
| 24 | COOLING_VALUE | Cooling valve position |
| 25 | FAN_SPEED | Fan speed |
| 26 | AIR_FLAP_POSITION | Air flap position |

### Audio Channels (41-44)
| Type | Name | Description |
|------|------|-------------|
| 41 | AUDIO_VOLUME | Audio volume |
| 42 | AUDIO_BASS | Bass level |
| 43 | AUDIO_TREBLE | Treble level |
| 44 | AUDIO_BALANCE | Balance (L-R) |

### Extended Channels (51-53)
| Type | Name | Description |
|------|------|-------------|
| 51 | WATER_TEMPERATURE | Water temperature |
| 52 | WATER_FLOW | Water flow |
| 53 | POWER_STATE | Power state (on/off) |

**Note:** Channel types 192+ are available for device-specific custom channels. See the full channel types table in [Documentation/vdc-API-properties/12-Output-Channel.md](Documentation/vdc-API-properties/12-Output-Channel.md#L48) for complete details.

## Groups (Functional Classes)

digitalSTROM groups represent functional device classes, identified by color:

| Group | Color | Name | Description |
|-------|-------|------|-------------|
| 0 | - | UNDEFINED | Not assigned |
| 1 | Yellow | LIGHT | Light/Illumination devices |
| 2 | Gray | BLINDS | Blinds/Shades/Jalousies |
| 3 | Blue | HEATING | Heating devices |
| 4 | Cyan | AUDIO | Audio devices |
| 5 | Magenta | VIDEO | Video devices |
| 6 | Red | SECURITY | Security/Access control |
| 7 | Green | ACCESS | Access control |
| 8 | Black | JOKER | Multi-purpose/Joker |
| 9 | White | COOLING | Cooling devices |

## Scene Effects

Effects applied when calling a scene:

| Effect | Name | Description |
|--------|------|-------------|
| 0 | NONE | Immediate transition |
| 1 | SMOOTH | Normal smooth transition |
| 2 | SLOW | Slow transition |
| 3 | VERY_SLOW | Very slow transition |
| 4 | ALERT | Blink/alerting effect |

## Output Functions

Output device function types:

| Function | Name | Description | Channels |
|----------|------|-------------|----------|
| 0 | SWITCH | On/off only | 1 (switch) |
| 1 | DIMMER | Dimmer | 1 (brightness) |
| 2 | POSITIONAL | Positional (valves, blinds) | 1-2 (position, angle) |
| 3 | DIMMER_WITH_CT | Dimmer with color temperature | 2 (brightness, ct) |
| 4 | FULL_COLOR | Full color dimmer | 1-6 (brightness, hue, sat, ct, cieX, cieY) |
| 5 | BIPOLAR | Bipolar (heating/cooling) | 1 (bipolar) |
| 6 | INTERNALLY_CONTROLLED | Device has internal control | - |

## Output Properties

### Output Usage
| Value | Name | Description |
|-------|------|-------------|
| 0 | UNDEFINED | Generic usage or unknown |
| 1 | ROOM | Room usage |
| 2 | OUTDOORS | Outdoor usage |
| 3 | USER | User display/indicator |

### Output Mode
| Value | Name | Description |
|-------|------|-------------|
| 0 | DISABLED | Disabled, inactive |
| 1 | BINARY | Binary (on/off) |
| 2 | GRADUAL | Gradual (dimming/positioning) |
| 127 | DEFAULT | Default (device's default mode) |

### Heating System Capability
| Value | Name | Description |
|-------|------|-------------|
| 1 | HEATING_ONLY | Heating only (0..100) |
| 2 | COOLING_ONLY | Cooling only (0..-100) |
| 3 | HEATING_AND_COOLING | Both heating and cooling (-100..100) |

### Heating System Type
| Value | Name | Description |
|-------|------|-------------|
| 0 | UNDEFINED | Undefined |
| 1 | FLOOR_HEATING | Floor heating (valve) |
| 2 | RADIATOR | Radiator (valve) |
| 3 | WALL_HEATING | Wall heating (valve) |
| 4 | CONVECTOR_PASSIVE | Convector passive |
| 5 | CONVECTOR_ACTIVE | Convector active |
| 6 | FLOOR_HEATING_LOW_ENERGY | Floor heating low energy (valve) |

## Button Properties

### Button Types
| Value | Name | Description |
|-------|------|-------------|
| 0 | UNDEFINED | Undefined |
| 1 | SINGLE_PUSHBUTTON | Single pushbutton |
| 2 | TWO_WAY_PUSHBUTTON | 2-way pushbutton |
| 3 | FOUR_WAY_NAVIGATION | 4-way navigation button |
| 4 | FOUR_WAY_NAV_WITH_CENTER | 4-way navigation with center |
| 5 | EIGHT_WAY_NAV_WITH_CENTER | 8-way navigation with center |
| 6 | ON_OFF_SWITCH | On-off switch |

### Button Click Types
| Value | Name | Description |
|-------|------|-------------|
| 0 | TIP_1X | Single tip |
| 1 | TIP_2X | Double tip |
| 2 | TIP_3X | Triple tip |
| 3 | TIP_4X | Quadruple tip |
| 4 | HOLD_START | Hold start |
| 5 | HOLD_REPEAT | Hold repeat |
| 6 | HOLD_END | Hold end |
| 7 | CLICK_1X | Single click |
| 8 | CLICK_2X | Double click |
| 9 | CLICK_3X | Triple click |
| 10 | SHORT_LONG | Short-long combination |
| 11 | LOCAL_OFF | Local off |
| 12 | LOCAL_ON | Local on |
| 13 | SHORT_SHORT_LONG | Short-short-long combination |
| 14 | LOCAL_STOP | Local stop |
| 255 | IDLE | Idle (no recent click) |

### Button Action Modes
| Value | Name | Description |
|-------|------|-------------|
| 0 | NORMAL | Normal action |
| 1 | FORCE | Force action |
| 2 | UNDO | Undo action |

## Sensor Properties

### Sensor Types
| Value | Name | Unit | Description |
|-------|------|------|-------------|
| 0 | NONE | - | None |
| 1 | TEMPERATURE | °C | Temperature |
| 2 | HUMIDITY | % | Relative humidity |
| 3 | ILLUMINATION | lux | Illumination |
| 4 | SUPPLY_VOLTAGE | V | Supply voltage level |
| 5 | CO_CONCENTRATION | ppm | CO concentration |
| 6 | RADON_ACTIVITY | Bq/m³ | Radon activity |
| 7 | GAS_TYPE | - | Gas type sensor |
| 8 | PARTICLES_10 | μg/m³ | Particles <10µm |
| 9 | PARTICLES_2_5 | μg/m³ | Particles <2.5µm |
| 10 | PARTICLES_1 | μg/m³ | Particles <1µm |
| 11 | ROOM_OP_PANEL_SET_POINT | % | Room operating panel set point |
| 12 | FAN_SPEED | 0..1 | Fan speed (0=off, <0=auto) |
| 13 | WIND_SPEED | m/s | Wind speed (average) |
| 14 | ACTIVE_POWER | W | Active Power |
| 15 | ELECTRIC_CURRENT | A | Electric current |
| 16 | ENERGY_METER | kWh | Energy Meter |
| 17 | APPARENT_POWER | VA | Apparent Power |
| 18 | AIR_PRESSURE | hPa | Air pressure |
| 19 | WIND_DIRECTION | degrees | Wind direction |
| 20 | SOUND_PRESSURE_LEVEL | dB | Sound pressure level |
| 21 | PRECIPITATION | mm/m² | Precipitation (last hour sum) |
| 22 | CO2_CONCENTRATION | ppm | CO2 concentration |
| 23 | WIND_GUST_SPEED | m/s | Wind gust speed |
| 24 | WIND_GUST_DIRECTION | degrees | Wind gust direction |
| 25 | GENERATED_ACTIVE_POWER | W | Generated Active Power |
| 26 | GENERATED_ENERGY | kWh | Generated Energy |
| 27 | WATER_QUANTITY | l | Water Quantity |
| 28 | WATER_FLOW_RATE | l/s | Water Flow Rate |

### Sensor Usage
| Value | Name | Description |
|-------|------|-------------|
| 0 | UNDEFINED | Generic usage or unknown |
| 1 | ROOM | Room |
| 2 | OUTDOOR | Outdoor |
| 3 | USER_INTERACTION | User interaction (setting, dial) |
| 4 | DEVICE_LEVEL_MEASUREMENT | Device level measurement (total, sum) |
| 5 | DEVICE_LEVEL_LAST_RUN | Device level last run |
| 6 | DEVICE_LEVEL_AVERAGE | Device level average |

## Binary Input Properties

### Binary Input Usage
| Value | Name | Description |
|-------|------|-------------|
| 0 | UNDEFINED | Generic usage or unknown |
| 1 | ROOM_CLIMATE | Room climate |
| 2 | OUTDOOR_CLIMATE | Outdoor climate |
| 3 | CLIMATE_SETTING | Climate setting (from user) |

### Binary Input Functions
| Value | Name | Description |
|-------|------|-------------|
| 0 | APP_MODE | App Mode (no system function) |
| 1 | PRESENCE | Presence |
| 2 | LIGHT | Light (not yet in use) |
| 3 | PRESENCE_IN_DARKNESS | Presence in darkness (not yet in use) |
| 4 | TWILIGHT | Twilight |
| 5 | MOTION | Motion detector |
| 6 | MOTION_IN_DARKNESS | Motion in darkness (not yet in use) |
| 7 | SMOKE | Smoke detector |
| 8 | WIND_MONITOR | Wind monitor |
| 9 | RAIN_MONITOR | Rain monitor |
| 10 | SUN_RADIATION | Sun radiation |
| 11 | THERMOSTAT | Thermostat |
| 12 | BATTERY_LOW | Battery low status |
| 13 | WINDOW_CONTACT | Window contact (open) |
| 14 | DOOR_CONTACT | Door contact (open) |
| 15 | WINDOW_HANDLE | Window handle (close/open/tilted) |
| 16 | GARAGE_DOOR | Garage door (open) |
| 17 | SUN_PROTECTION | Sun protection |
| 18 | FROST | Frost |
| 19 | HEATING_MODE_SWITCH | Heating mode switch |
| 20 | HEATING_SYSTEM_ENABLED | Heating system enabled |

## Error States

Error states for devices, sensors, and outputs:

| Value | Name | Description | Applies To |
|-------|------|-------------|------------|
| 0 | OK | No error | All |
| 1 | OPEN_CIRCUIT | Open circuit / lamp broken | All |
| 2 | SHORT_CIRCUIT | Short circuit | All |
| 3 | OVERLOAD | Overload | Outputs only |
| 4 | BUS_CONNECTION_PROBLEM | Bus connection problem | All |
| 5 | LOW_BATTERY | Low battery in device | All |
| 6 | OTHER_ERROR | Other device error | All |

## Usage Examples

```python
from pyvdcapi.core.constants import (
    DSScene, DSChannelType, DSGroup, DSSceneEffect,
    DSSensorType, DSButtonClickType, DSErrorState,
    DSOutputFunction, DSOutputMode,
    get_channel_name, get_group_name, get_default_scene_config
)

# Check scene number
if scene_number == DSScene.DEEP_OFF:
    print("Deep off scene called")

# Get default configuration for a scene
config = get_default_scene_config(DSScene.WAKE_UP)
# Returns: {
#     "name": "Wake Up",
#     "channels": {DSChannelType.DEFAULT: 0.50},
#     "effect": DSSceneEffect.VERY_SLOW,
#     "dontCare": False
# }

# Channel type names
channel_name = get_channel_name(DSChannelType.BRIGHTNESS)  # "brightness"
group_name = get_group_name(DSGroup.YELLOW)  # "Light"

# Sensor type usage
sensor = {
    "sensorType": DSSensorType.TEMPERATURE,
    "min": -20.0,
    "max": 60.0,
    "unit": "°C"
}

# Button click handling
if click_type == DSButtonClickType.CLICK_2X:
    print("Double click detected")
elif click_type == DSButtonClickType.HOLD_START:
    print("Long press started")

# Error checking
if error_state != DSErrorState.OK:
    if error_state == DSErrorState.LOW_BATTERY:
        print("Warning: Device battery low")
    elif error_state == DSErrorState.BUS_CONNECTION_PROBLEM:
        print("Error: Cannot connect to device")

# Output configuration
output = {
    "function": DSOutputFunction.DIMMER,
    "mode": DSOutputMode.GRADUAL
}

# Iterate over all standard scenes
for scene in DSScene:
    config = get_default_scene_config(scene.value)
    if config:
        print(f"Scene {scene.name}: {config['name']}")
```

## Default Scene Values

The `DEFAULT_SCENE_VALUES` dictionary provides default configurations for all standard scenes, including:
- Scene name
- Default channel values
- Recommended effect
- Don't care flag

User presets (32-63) do not have predefined default values and should be configured by the user/application.

## Integration with vDC API

These constants integrate seamlessly with the vDC API:

```python
from pyvdcapi.core.constants import DSScene, DSSceneEffect, DSChannelType

# Creating a scene call
scene_request = {
    "sceneNo": DSScene.PRESENT,
    "force": False,
    "effect": DSSceneEffect.SMOOTH
}

# Defining output channels
output_channels = [
    {
        "channelType": DSChannelType.BRIGHTNESS,
        "min": 0.0,
        "max": 100.0,
        "resolution": 0.1
    },
    {
        "channelType": DSChannelType.COLOR_TEMP,
        "min": 2700,
        "max": 6500,
        "resolution": 1
    }
]
```

## References

- digitalSTROM System Specification
- vDC API Documentation
- ds-basics specification (scene and channel type definitions)
