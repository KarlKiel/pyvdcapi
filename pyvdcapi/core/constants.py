"""
digitalSTROM constants for scenes, channels, and groups.

Based on digitalSTROM specification and vDC API documentation.
"""

from enum import IntEnum
from typing import Dict, Any


class DSScene(IntEnum):
    """
    Standard digitalSTROM scene numbers.

    Based on digitalSTROM specification:
    - 0-4: Area scenes (1-4)
    - 5-12: Named scenes
    - 13-31: Reserved/special scenes
    - 32-63: User-defined presets
    - 64-126: Reserved
    - 127: Stop/LocalOff
    """

    # Area scenes (Area 1-4, plus Global Off)
    AREA_1_OFF = 0
    AREA_2_OFF = 1
    AREA_3_OFF = 2
    AREA_4_OFF = 3
    GLOBAL_OFF = 4  # Also known as Area Global Off

    # Standard named scenes
    DEEP_OFF = 5  # Deep off (power saving mode)
    STANDBY = 6  # Standby
    WAKE_UP = 7  # Wake up / morning
    PRESENT = 8  # Present / working
    ABSENT = 9  # Absent / night
    SLEEPING = 10  # Sleeping
    ALARM = 11  # Alarm
    FIRE = 12  # Fire alarm / panic

    # Special control scenes
    STOP = 13  # Stop dimming/movement
    MIN = 14  # Minimum value
    MAX = 15  # Maximum value
    INC = 16  # Increment
    DEC = 17  # Decrement

    AREA_1_ON = 18  # Area 1 stepping on
    AREA_2_ON = 19  # Area 2 stepping on
    AREA_3_ON = 20  # Area 3 stepping on
    AREA_4_ON = 21  # Area 4 stepping on

    AREA_1_INC = 22  # Area 1 increment
    AREA_2_INC = 23  # Area 2 increment
    AREA_3_INC = 24  # Area 3 increment
    AREA_4_INC = 25  # Area 4 increment

    AREA_1_DEC = 26  # Area 1 decrement
    AREA_2_DEC = 27  # Area 2 decrement
    AREA_3_DEC = 28  # Area 3 decrement
    AREA_4_DEC = 29  # Area 4 decrement

    AUTO_STANDBY = 30  # Auto standby
    SUN_PROTECTION = 31  # Sun protection

    # User-defined presets (32-63)
    PRESET_0 = 32
    PRESET_1 = 33
    PRESET_2 = 34
    PRESET_3 = 35
    PRESET_4 = 36
    PRESET_5 = 37
    PRESET_6 = 38
    PRESET_7 = 39
    PRESET_8 = 40
    PRESET_9 = 41
    PRESET_10 = 42
    PRESET_11 = 43
    PRESET_12 = 44
    PRESET_13 = 45
    PRESET_14 = 46
    PRESET_15 = 47
    PRESET_16 = 48
    PRESET_17 = 49
    PRESET_18 = 50
    PRESET_19 = 51
    PRESET_20 = 52
    PRESET_21 = 53
    PRESET_22 = 54
    PRESET_23 = 55
    PRESET_24 = 56
    PRESET_25 = 57
    PRESET_26 = 58
    PRESET_27 = 59
    PRESET_28 = 60
    PRESET_29 = 61
    PRESET_30 = 62
    PRESET_31 = 63

    # Special scenes
    LOCAL_OFF = 127  # Local off / stop


class DSGroup(IntEnum):
    """
    Standard digitalSTROM group (color) numbers.

    Groups represent functional classes of devices.
    """

    YELLOW = 1  # Light
    GRAY = 2  # Blinds/Shades
    BLUE = 3  # Heating
    CYAN = 4  # Audio
    MAGENTA = 5  # Video
    RED = 6  # Security
    GREEN = 7  # Access
    BLACK = 8  # Joker (multi-purpose)
    WHITE = 9  # Cooling
    UNDEFINED = 0  # Undefined/not assigned


class DSChannelType(IntEnum):
    """
    Standard digitalSTROM channel types.

    Based on vDC API specification and digitalSTROM standards.
    Channel types 0-191 are reserved for digitalSTROM standards.
    """

    # Default channel
    DEFAULT = 0  # Default channel (usually brightness for lights)

    # Standard light channels (1-10)
    BRIGHTNESS = 1  # Brightness (0-100%)
    HUE = 2  # Hue (0-360°)
    SATURATION = 3  # Saturation (0-100%)
    COLOR_TEMP = 4  # Color temperature (in mired, 100-1000)
    CIE_X = 5  # CIE x coordinate (0-10000, scaled to 0.0-1.0)
    CIE_Y = 6  # CIE y coordinate (0-10000, scaled to 0.0-1.0)

    # Blind/shade channels (11-20)
    SHADE_POSITION_OUTSIDE = 11  # Shade position outside/blinds (0-100%)
    SHADE_POSITION_INDOOR = 12  # Shade position indoor/curtains (0-100%)
    SHADE_OPENING_ANGLE_OUTSIDE = 13  # Shade opening angle outside/blinds (0-100%)
    SHADE_OPENING_ANGLE_INDOOR = 14  # Shade opening angle indoor/curtains (0-100%)
    TRANSPARENCY = 15  # Transparency, e.g. smart glass (0-100%)

    # HVAC/Climate channels (21-40)
    HEATING_POWER = 21  # Heating power (0-100%)
    HEATING_VALUE = 22  # Heating valve position (0-100%)
    COOLING_CAPACITY = 23  # Cooling capacity (0-100%)
    COOLING_VALUE = 24  # Cooling valve position (0-100%)
    AIR_FLOW_INTENSITY = 25  # Air flow intensity (0-100%)
    AIR_FLOW_DIRECTION = 26  # Air flow direction (0=bothUndefined, 1=supplyIn, 2=exhaustOut)
    AIR_FLAP_POSITION = 27  # Air flap opening angle (0-100%)
    AIR_LOUVER_POSITION = 28  # Ventilation louver position (0-100%)
    AIR_LOUVER_AUTO = 29  # Ventilation swing mode (0=notActive, 1=active)
    AIR_FLOW_AUTO = 30  # Ventilation auto intensity (0=notActive, 1=active)

    # Audio channels (41-50)
    AUDIO_VOLUME = 41  # Audio volume/loudness (0-100%)
    AUDIO_BASS = 42  # Bass level
    AUDIO_TREBLE = 43  # Treble level
    AUDIO_BALANCE = 44  # Balance (L-R)

    # Extended channels (51-100)
    WATER_TEMPERATURE = 51  # Water temperature (0-150°C)
    WATER_FLOW = 52  # Water flow
    POWER_STATE = 53  # Power state (0=powerOff, 1=powerOn, 2=forcedOff, 3=standby)
    WIND_SPEED_RATE = 54  # Wind speed rate (0-100%)
    POWER_LEVEL = 55  # Power level (0-100%)

    # Device-specific channels start at 192


class DSSceneEffect(IntEnum):
    """Scene effect types when calling a scene."""

    NONE = 0  # No effect, immediate transition
    SMOOTH = 1  # Smooth normal transition
    SLOW = 2  # Slow transition
    VERY_SLOW = 3  # Very slow transition
    ALERT = 4  # Blink/alerting effect


class DSOutputFunction(IntEnum):
    """Output function types."""

    SWITCH = 0  # On/off only
    DIMMER = 1  # Dimmer (brightness)
    POSITIONAL = 2  # Positional (valves, blinds)
    DIMMER_WITH_CT = 3  # Dimmer with color temperature
    FULL_COLOR = 4  # Full color dimmer (RGB/HSV)
    BIPOLAR = 5  # Bipolar (heating/cooling)
    INTERNALLY_CONTROLLED = 6  # Device has internal control


class DSOutputUsage(IntEnum):
    """Output usage types (beyond device color)."""

    UNDEFINED = 0  # Generic usage or unknown
    ROOM = 1  # Room usage
    OUTDOORS = 2  # Outdoor usage
    USER = 3  # User display/indicator


class DSOutputMode(IntEnum):
    """Output mode settings."""

    DISABLED = 0  # Disabled, inactive
    BINARY = 1  # Binary (on/off)
    GRADUAL = 2  # Gradual (dimming/positioning)
    DEFAULT = 127  # Default (generically enabled using device's default mode)


class DSHeatingSystemCapability(IntEnum):
    """Climate control heating system capability."""

    HEATING_ONLY = 1  # Heating only (heatingLevel 0..100 -> output 0..100)
    COOLING_ONLY = 2  # Cooling only (heatingLevel 0..-100 -> output 0..100)
    HEATING_AND_COOLING = 3  # Heating and cooling (heatingLevel -100..0..100)


class DSHeatingSystemType(IntEnum):
    """Climate control heating system type."""

    UNDEFINED = 0  # Undefined
    FLOOR_HEATING = 1  # Floor heating (valve)
    RADIATOR = 2  # Radiator (valve)
    WALL_HEATING = 3  # Wall heating (valve)
    CONVECTOR_PASSIVE = 4  # Convector passive
    CONVECTOR_ACTIVE = 5  # Convector active
    FLOOR_HEATING_LOW_ENERGY = 6  # Floor heating low energy (valve)


class DSInputType(IntEnum):
    """Input types for buttons and binary inputs."""

    BUTTON_SINGLE = 0  # Single press button
    BUTTON_DOUBLE = 1  # Double press capable
    BUTTON_LONG = 2  # Long press capable
    BINARY_INPUT = 10  # Binary input (on/off)
    CONTACT = 11  # Contact sensor
    MOTION = 12  # Motion sensor


class DSButtonType(IntEnum):
    """Physical button types."""

    UNDEFINED = 0  # Undefined
    SINGLE_PUSHBUTTON = 1  # Single pushbutton
    TWO_WAY_PUSHBUTTON = 2  # 2-way pushbutton
    FOUR_WAY_NAVIGATION = 3  # 4-way navigation button
    FOUR_WAY_NAV_WITH_CENTER = 4  # 4-way navigation with center button
    EIGHT_WAY_NAV_WITH_CENTER = 5  # 8-way navigation with center button
    ON_OFF_SWITCH = 6  # On-off switch


class DSButtonClickType(IntEnum):
    """Button click types."""

    TIP_1X = 0  # Single tip
    TIP_2X = 1  # Double tip
    TIP_3X = 2  # Triple tip
    TIP_4X = 3  # Quadruple tip
    HOLD_START = 4  # Hold start
    HOLD_REPEAT = 5  # Hold repeat
    HOLD_END = 6  # Hold end
    CLICK_1X = 7  # Single click
    CLICK_2X = 8  # Double click
    CLICK_3X = 9  # Triple click
    SHORT_LONG = 10  # Short-long combination
    LOCAL_OFF = 11  # Local off
    LOCAL_ON = 12  # Local on
    SHORT_SHORT_LONG = 13  # Short-short-long combination
    LOCAL_STOP = 14  # Local stop
    IDLE = 255  # Idle (no recent click)


class DSButtonActionMode(IntEnum):
    """Button action modes."""

    NORMAL = 0  # Normal action
    FORCE = 1  # Force action
    UNDO = 2  # Undo action


class DSSensorType(IntEnum):
    """Sensor physical unit types."""

    NONE = 0  # None
    TEMPERATURE = 1  # Temperature in °C
    HUMIDITY = 2  # Relative humidity in %
    ILLUMINATION = 3  # Illumination in lux
    SUPPLY_VOLTAGE = 4  # Supply voltage level in V
    CO_CONCENTRATION = 5  # CO concentration in ppm
    RADON_ACTIVITY = 6  # Radon activity in Bq/m3
    GAS_TYPE = 7  # Gas type sensor
    PARTICLES_10 = 8  # Particles <10µm in μg/m3
    PARTICLES_2_5 = 9  # Particles <2.5µm in μg/m3
    PARTICLES_1 = 10  # Particles <1µm in μg/m3
    ROOM_OP_PANEL_SET_POINT = 11  # Room operating panel set point, 0..100%
    FAN_SPEED = 12  # Fan speed, 0..1 (0=off, <0=auto)
    WIND_SPEED = 13  # Wind speed in m/s (average)
    ACTIVE_POWER = 14  # Active Power in W
    ELECTRIC_CURRENT = 15  # Electric current in A
    ENERGY_METER = 16  # Energy Meter in kWh
    APPARENT_POWER = 17  # Apparent Power in VA
    AIR_PRESSURE = 18  # Air pressure in hPa
    WIND_DIRECTION = 19  # Wind direction in degrees
    SOUND_PRESSURE_LEVEL = 20  # Sound pressure level in dB
    PRECIPITATION = 21  # Precipitation intensity in mm/m2 (sum of last hour)
    CO2_CONCENTRATION = 22  # CO2 concentration in ppm
    WIND_GUST_SPEED = 23  # Wind gust speed in m/s
    WIND_GUST_DIRECTION = 24  # Wind gust direction in degrees
    GENERATED_ACTIVE_POWER = 25  # Generated Active Power in W
    GENERATED_ENERGY = 26  # Generated Energy in kWh
    WATER_QUANTITY = 27  # Water Quantity in l
    WATER_FLOW_RATE = 28  # Water Flow Rate in l/s


class DSSensorUsage(IntEnum):
    """Sensor usage field types."""

    UNDEFINED = 0  # Undefined (generic usage or unknown)
    ROOM = 1  # Room
    OUTDOOR = 2  # Outdoor
    USER_INTERACTION = 3  # User interaction (setting, dial)
    DEVICE_LEVEL_MEASUREMENT = 4  # Device level measurement (total, sum)
    DEVICE_LEVEL_LAST_RUN = 5  # Device level last run
    DEVICE_LEVEL_AVERAGE = 6  # Device level average


class DSBinaryInputUsage(IntEnum):
    """Binary input usage field types."""

    UNDEFINED = 0  # Undefined (generic usage or unknown)
    ROOM_CLIMATE = 1  # Room climate
    OUTDOOR_CLIMATE = 2  # Outdoor climate
    CLIMATE_SETTING = 3  # Climate setting (from user)


class DSBinaryInputFunction(IntEnum):
    """Binary input sensor functions."""

    APP_MODE = 0  # App Mode (no system function)
    PRESENCE = 1  # Presence
    LIGHT = 2  # Light (not yet in use)
    PRESENCE_IN_DARKNESS = 3  # Presence in darkness (not yet in use)
    TWILIGHT = 4  # Twilight
    MOTION = 5  # Motion detector
    MOTION_IN_DARKNESS = 6  # Motion in darkness (not yet in use)
    SMOKE = 7  # Smoke detector
    WIND_MONITOR = 8  # Wind monitor
    RAIN_MONITOR = 9  # Rain monitor
    SUN_RADIATION = 10  # Sun radiation
    THERMOSTAT = 11  # Thermostat
    BATTERY_LOW = 12  # Battery low status
    WINDOW_CONTACT = 13  # Window contact (set when open)
    DOOR_CONTACT = 14  # Door contact (set when open)
    WINDOW_HANDLE = 15  # Window handle (close/open/tilted)
    GARAGE_DOOR = 16  # Garage door (set when open)
    SUN_PROTECTION = 17  # Sun protection
    FROST = 18  # Frost
    HEATING_MODE_SWITCH = 19  # Heating mode switch
    HEATING_SYSTEM_ENABLED = 20  # Heating system enabled


class DSErrorState(IntEnum):
    """Device/sensor/output error states."""

    OK = 0  # OK
    OPEN_CIRCUIT = 1  # Open circuit / lamp broken
    SHORT_CIRCUIT = 2  # Short circuit
    OVERLOAD = 3  # Overload (output only)
    BUS_CONNECTION_PROBLEM = 4  # Bus connection problem
    LOW_BATTERY = 5  # Low battery in device
    OTHER_ERROR = 6  # Other device error


class ButtonEvent(IntEnum):
    """Button event types."""

    SINGLE_PRESS = 0  # Single press
    DOUBLE_PRESS = 1  # Double press
    LONG_PRESS = 2  # Long press start
    LONG_RELEASE = 3  # Long press release
    RELEASE = 4  # Button released


# Default scene values for standard scenes
DEFAULT_SCENE_VALUES: Dict[int, Dict[str, Any]] = {
    DSScene.AREA_1_OFF: {
        "name": "Area 1 Off",
        "channels": {DSChannelType.DEFAULT: 0.0},
        "effect": DSSceneEffect.SMOOTH,
        "dontCare": False,
    },
    DSScene.AREA_2_OFF: {
        "name": "Area 2 Off",
        "channels": {DSChannelType.DEFAULT: 0.0},
        "effect": DSSceneEffect.SMOOTH,
        "dontCare": False,
    },
    DSScene.AREA_3_OFF: {
        "name": "Area 3 Off",
        "channels": {DSChannelType.DEFAULT: 0.0},
        "effect": DSSceneEffect.SMOOTH,
        "dontCare": False,
    },
    DSScene.AREA_4_OFF: {
        "name": "Area 4 Off",
        "channels": {DSChannelType.DEFAULT: 0.0},
        "effect": DSSceneEffect.SMOOTH,
        "dontCare": False,
    },
    DSScene.GLOBAL_OFF: {
        "name": "Global Off",
        "channels": {DSChannelType.DEFAULT: 0.0},
        "effect": DSSceneEffect.SMOOTH,
        "dontCare": False,
    },
    DSScene.DEEP_OFF: {
        "name": "Deep Off",
        "channels": {DSChannelType.DEFAULT: 0.0},
        "effect": DSSceneEffect.SMOOTH,
        "dontCare": False,
    },
    DSScene.STANDBY: {
        "name": "Standby",
        "channels": {DSChannelType.DEFAULT: 0.01},  # Very dim
        "effect": DSSceneEffect.SLOW,
        "dontCare": False,
    },
    DSScene.WAKE_UP: {
        "name": "Wake Up",
        "channels": {DSChannelType.DEFAULT: 0.50},
        "effect": DSSceneEffect.VERY_SLOW,
        "dontCare": False,
    },
    DSScene.PRESENT: {
        "name": "Present",
        "channels": {DSChannelType.DEFAULT: 0.75},
        "effect": DSSceneEffect.SMOOTH,
        "dontCare": False,
    },
    DSScene.ABSENT: {
        "name": "Absent",
        "channels": {DSChannelType.DEFAULT: 0.10},
        "effect": DSSceneEffect.SMOOTH,
        "dontCare": False,
    },
    DSScene.SLEEPING: {
        "name": "Sleeping",
        "channels": {DSChannelType.DEFAULT: 0.0},
        "effect": DSSceneEffect.VERY_SLOW,
        "dontCare": False,
    },
    DSScene.ALARM: {
        "name": "Alarm",
        "channels": {DSChannelType.DEFAULT: 1.0},
        "effect": DSSceneEffect.ALERT,
        "dontCare": False,
    },
    DSScene.FIRE: {
        "name": "Fire/Panic",
        "channels": {DSChannelType.DEFAULT: 1.0},
        "effect": DSSceneEffect.NONE,
        "dontCare": False,
    },
    DSScene.STOP: {
        "name": "Stop",
        "channels": {},
        "effect": DSSceneEffect.NONE,
        "dontCare": True,  # Don't change values, just stop
    },
    DSScene.MIN: {
        "name": "Minimum",
        "channels": {DSChannelType.DEFAULT: 0.0},
        "effect": DSSceneEffect.NONE,
        "dontCare": False,
    },
    DSScene.MAX: {
        "name": "Maximum",
        "channels": {DSChannelType.DEFAULT: 1.0},
        "effect": DSSceneEffect.NONE,
        "dontCare": False,
    },
    DSScene.AREA_1_ON: {
        "name": "Area 1 On",
        "channels": {DSChannelType.DEFAULT: 1.0},
        "effect": DSSceneEffect.SMOOTH,
        "dontCare": False,
    },
    DSScene.AREA_2_ON: {
        "name": "Area 2 On",
        "channels": {DSChannelType.DEFAULT: 1.0},
        "effect": DSSceneEffect.SMOOTH,
        "dontCare": False,
    },
    DSScene.AREA_3_ON: {
        "name": "Area 3 On",
        "channels": {DSChannelType.DEFAULT: 1.0},
        "effect": DSSceneEffect.SMOOTH,
        "dontCare": False,
    },
    DSScene.AREA_4_ON: {
        "name": "Area 4 On",
        "channels": {DSChannelType.DEFAULT: 1.0},
        "effect": DSSceneEffect.SMOOTH,
        "dontCare": False,
    },
    DSScene.AUTO_STANDBY: {
        "name": "Auto Standby",
        "channels": {DSChannelType.DEFAULT: 0.05},
        "effect": DSSceneEffect.SLOW,
        "dontCare": False,
    },
    DSScene.SUN_PROTECTION: {
        "name": "Sun Protection",
        "channels": {DSChannelType.SHADE_POSITION_OUTSIDE: 0.0},  # Shades down
        "effect": DSSceneEffect.SMOOTH,
        "dontCare": False,
    },
    DSScene.LOCAL_OFF: {
        "name": "Local Off",
        "channels": {DSChannelType.DEFAULT: 0.0},
        "effect": DSSceneEffect.NONE,
        "dontCare": False,
    },
}


# Channel type names for human-readable output
CHANNEL_TYPE_NAMES: Dict[int, str] = {
    DSChannelType.DEFAULT: "default",
    DSChannelType.BRIGHTNESS: "brightness",
    DSChannelType.HUE: "hue",
    DSChannelType.SATURATION: "saturation",
    DSChannelType.COLOR_TEMP: "colortemp",
    DSChannelType.CIE_X: "x",
    DSChannelType.CIE_Y: "y",
    DSChannelType.SHADE_POSITION_OUTSIDE: "shadePositionOutside",
    DSChannelType.SHADE_POSITION_INDOOR: "shadePositionIndoor",
    DSChannelType.SHADE_OPENING_ANGLE_OUTSIDE: "shadeOpeningAngleOutside",
    DSChannelType.SHADE_OPENING_ANGLE_INDOOR: "shadeOpeningAngleIndoor",
    DSChannelType.TRANSPARENCY: "transparency",
    DSChannelType.HEATING_POWER: "heatingPower",
    DSChannelType.HEATING_VALUE: "heatingValue",
    DSChannelType.COOLING_CAPACITY: "coolingCapacity",
    DSChannelType.COOLING_VALUE: "coolingValue",
    DSChannelType.AIR_FLOW_INTENSITY: "airFlowIntensity",
    DSChannelType.AIR_FLOW_DIRECTION: "airFlowDirection",
    DSChannelType.AIR_FLAP_POSITION: "airFlapPosition",
    DSChannelType.AIR_LOUVER_POSITION: "airLouverPosition",
    DSChannelType.AIR_LOUVER_AUTO: "airLouverAuto",
    DSChannelType.AIR_FLOW_AUTO: "airFlowAuto",
    DSChannelType.AUDIO_VOLUME: "audioVolume",
    DSChannelType.AUDIO_BASS: "audioBass",
    DSChannelType.AUDIO_TREBLE: "audioTreble",
    DSChannelType.AUDIO_BALANCE: "audioBalance",
    DSChannelType.WATER_TEMPERATURE: "waterTemperature",
    DSChannelType.WATER_FLOW: "waterFlow",
    DSChannelType.POWER_STATE: "powerState",
    DSChannelType.WIND_SPEED_RATE: "windSpeedRate",
    DSChannelType.POWER_LEVEL: "powerLevel",
}


# Group names
GROUP_NAMES: Dict[int, str] = {
    DSGroup.YELLOW: "Light",
    DSGroup.GRAY: "Blinds",
    DSGroup.BLUE: "Heating",
    DSGroup.CYAN: "Audio",
    DSGroup.MAGENTA: "Video",
    DSGroup.RED: "Security",
    DSGroup.GREEN: "Access",
    DSGroup.BLACK: "Joker",
    DSGroup.WHITE: "Cooling",
    DSGroup.UNDEFINED: "Undefined",
}


def get_channel_name(channel_type: int) -> str:
    """Get human-readable name for a channel type."""
    return CHANNEL_TYPE_NAMES.get(channel_type, f"channel_{channel_type}")


def get_group_name(group: int) -> str:
    """Get human-readable name for a group."""
    return GROUP_NAMES.get(group, "Unknown")


def get_default_scene_config(scene_number: int) -> Dict[str, Any]:
    """
    Get default configuration for a standard scene.

    Args:
        scene_number: Scene number

    Returns:
        Dictionary with default scene configuration, or empty dict if not a standard scene
    """
    return DEFAULT_SCENE_VALUES.get(scene_number, {}).copy()
