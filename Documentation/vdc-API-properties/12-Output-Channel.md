## 4.9 Output Channel

### 4.9.1 Output Channel Description

Description (invariable properties) of the device's channels. The properties described here are contained in the device-level 4.1.3 channelDescriptions property.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| name | r | string | human readable name/number for the channel (e.g. matching labels for hardware connectors) |
| channelType | r | integer | Numerical Type Id of the channel. For definitions of output channel types please refer to the document ds-basics.pdf, section "Output Channels", or see section 4.9.4 below for a complete list of supported channel types. |
| dsIndex | r | integer | 0..N-1, where N=number of channels in this device. The index is used for dS-OS and DSMAPI addressing. Index "0" is by definition the default output channel. |
| min | r | double | min value |
| max | r | double | max value |
| resolution | r | double | resolution |

The following attributes shall no longer be used (Version 1.0.2):

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| channelIndex | r | integer | 0..N-1, where N=number of channels in this device. The index is device specific and no assumption on any particular order of indexes vs. channel types must be made. |

### 4.9.2 Output Channel Settings

Settings (properties that can be changed and are stored persistently in the vDC) for the device's channels. The properties described here are contained in the device-level 4.1.3 channelSettings property.

**Notice** Currently there are no per-channel settings defined

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| - | - | - | - |

### 4.9.3 Output Channel State

Current state of the device's channels. The properties described here are contained in the device-level 4.1.3 channelStates property.

**Notice** Channel State must not be written to. Instead, the notification setOutputChannelValue must be used.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| value | r | double | current channel value (brightness, blind position, power on/off) |
| age | r | double | age of the state shown in the value field in seconds. This indicates when the value was last applied to the actual device hardware, or when an actual output status was last received from the device. age is NULL when a new value was set, but not yet applied to the device |

### 4.9.4 Supported Channel Types

The following table lists all supported channel types with their ID, name, range, and unit:

| ID | Description | Channel Name | Min | Max | Unit | Notes |
|---|---|---|---|---|---|---|
| 0 | Default Channel | default | - | - | - | Usually brightness for lights |
| 1 | Light Brightness | brightness | 0 | 100 | percent | |
| 2 | Colored Light Hue | hue | 0 | 360 | degrees | |
| 3 | Colored Light Saturation | saturation | 0 | 100 | percent | |
| 4 | Color Temperature | colortemp | 100 | 1000 | mired | |
| 5 | Light CIE Color Model x | x | 0 | 10000 | scaled to 0.0 to 1.0 | |
| 6 | Light CIE Color Model y | y | 0 | 10000 | scaled to 0.0 to 1.0 | |
| 11 | Shade Position Outside [blinds] | shadePositionOutside | 0 | 100 | percent | |
| 12 | Shade Position Indoor [curtains] | shadePositionIndoor | 0 | 100 | percent | |
| 13 | Shade Opening Angle Outside [blinds] | shadeOpeningAngleOutside | 0 | 100 | percent | |
| 14 | Shade Opening Angle Indoor [curtains] | shadeOpeningAngleIndoor | 0 | 100 | percent | |
| 15 | Transparency (e.g. smart glass) | transparency | 0 | 100 | percent | |
| 21 | Heating Power | heatingPower | 0 | 100 | percent | |
| 22 | Heating Valve Position | heatingValue | 0 | 100 | percent | |
| 23 | Cooling Capacity | coolingCapacity | 0 | 100 | percent | |
| 24 | Cooling Valve Position | coolingValue | 0 | 100 | percent | |
| 25 | Air Flow Intensity | airFlowIntensity | 0 | 100 | percent | |
| 26 | Air Flow Direction | airFlowDirection | 0 | 2 | specific | 0=bothUndefined, 1=supplyIn, 2=exhaustOut |
| 27 | Flap Opening Angle | airFlapPosition | 0 | 100 | percent | |
| 28 | Ventilation Louver Position | airLouverPosition | 0 | 100 | percent | |
| 29 | Ventilation Swing Mode | airLouverAuto | 0 | 1 | specific | 0=notActive, 1=active |
| 30 | Ventilation Auto Intensity | airFlowAuto | 0 | 1 | specific | 0=notActive, 1=active |
| 41 | Audio Volume [loudness] | audioVolume | 0 | 100 | percent | |
| 42 | Audio Bass Level | audioBass | 0 | 100 | percent | |
| 43 | Audio Treble Level | audioTreble | 0 | 100 | percent | |
| 44 | Audio Balance | audioBalance | 0 | 100 | percent | |
| 51 | Water Temperature | waterTemperature | 0 | 150 | celsius | |
| 52 | Water Flow | waterFlow | 0 | 100 | percent | |
| 53 | Power State | powerState | 0 | 3 | specific | 0=powerOff, 1=powerOn, 2=forcedOff, 3=standby |
| 54 | Wind Speed Rate | windSpeedRate | 0 | 100 | percent | |
| 55 | Power Level | powerLevel | 0 | 100 | percent | |
| 192+ | Device-specific channels | - | - | - | - | Reserved for custom implementations |
