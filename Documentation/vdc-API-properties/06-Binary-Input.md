## 4.3 Binary Input

### 4.3.1 Binary Input Description

- Description (invariable properties) of a binary input. The properties described here are contained in the elements of the device-level 4.1.2 binaryInputDescriptions property.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| name | r | string | human readable name/number for the input (e.g. matching labels for hardware connectors) |
| dsIndex | r | integer | 0..N-1, where N=number of binary inputs in this device. |
| inputType | r | integer (inputs with binary functions supported only) | 0: poll only<br>1: detects changes |
| inputUsage | r | integer enum | Describes the usage field for the input (beyond device color)<br>0: undefined (generic usage or unknown)<br>1: room climate<br>2: outdoor climate<br>3: climate setting (from user) |
| sensorFunction | r | integer enum | hardwired function of this input if it is not freely configurable. See sensorFunction in binaryInputSettings[] below for all possible values.<br><br>Specifically, hardwired functions in use are:<br>0 means generic input with no hardware-defined functionality.<br>12 Battery low status (set when battery is low) |
| updateInterval | r | double | how fast the physical value is tracked, in seconds |

### 4.3.2 Binary Input Settings

- Settings (properties that can be changed and are stored persistently in the vDC) for a button. The properties described here are contained in the elements of the device-level 4.1.2 binaryInputSettings property.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| group | r/w | integer | dS group number |
| sensorFunction | r/w | integer enum | 0 App Mode (no system function)<br>1 Presence<br>2 Light – not yet in use<br>3 Presence in darkness – not yet in use<br>4 Twilight<br>5 Motion detector<br>6 Motion in darkness– not yet in use<br>7 Smoke detector<br>8 Wind monitor<br>9 Rain monitor<br>10 Sun radiation<br>11 Thermostat<br>12 Battery low status (set when battery is low)<br>13 Window contact (set when window is open)<br>14 Door contact (set when door is open)<br>15 Window handle, status is close, open, or tilted<br>16 Garage door contact (set when garage door is open)<br>17 Sun protection<br>18 Frost detection<br>19 Heating system enabled<br>20 Heating change-over, switch between heating and cooling mode<br>21 Initialization status (set during startup or powerup of devices)<br>22 Malfunction: Connected device is broken and requires maintenance. Operation may have seized.<br>23 Service: Connected device requires maintenance. Normal operation still possible. |

### 4.3.3 Binary Input State

- State (current state, changing during operation of the device, but not persistently stored in the vDC) of a button. The properties described here are contained in the elements of the device-level 4.1.2 binaryInputStates property.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| value | r | boolean or NULL | false=inactive<br>true=active<br>NULL=unknown state |
| extendedValue | r | integer or NULL | The property 'extendedValue' replaces the property 'value'. If the property extendedValue is present, the property value is not needed. The data from property 'value' is overwritten. |
| age | r | double or NULL | age of the state shown in the value and clickType fields in seconds. If no recent state is known, returns NULL. |
| error | r | integer enum | 0: ok<br>1: open circuit<br>2: short circuit<br>4: bus connection problem<br>5: low battery in device<br>6: other device error |
