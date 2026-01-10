## 4.2 Button Input

### 4.2.1 Button Input Description

- Description (invariable properties) of a button. The properties described here are contained in the elements of the device-level 4.1.2 buttonInputDescriptions property.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| name | r | string | human readable name/number for the input (e.g. matching labels for hardware connectors) |
| dsIndex | r | integer | 0..N-1, where N=number of buttons in this device. |
| supportsLocalKeyMode | r | boolean | can be local button |
| buttonID | r | optional integer 0..n | ID of physical button. No ID means no fixed assignment to a button. All elements of a multi-function hardware button must have the same buttonID. |
| buttonType | r | integer enum | Type of physical button<br>0: undefined<br>1: single pushbutton<br>2: 2-way pushbutton<br>3: 4-way navigation button<br>4: 4-way navigation with center button<br>5: 8-way navigation with center button<br>6: on-off switch |
| buttonElementID | r | integer | Element of multi-contact button<br>0: center<br>1: down<br>2: up<br>3: left<br>4: right<br>5: upper left<br>6: lower left<br>7: upper right<br>8: lower right<br><br>Note: For undefined buttonType, buttonElement just enumerates the elements (0..numElements-1) |

### 4.2.2 Button Input Settings

- Settings (properties that can be changed and are stored persistently in the vDC) for a button. The properties described here are contained in the elements of the device-level 4.1.2 buttonInputSettings property.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| group | r/w | integer | dS group number |
| function | r/w | integer 0..15 | see LTNUM descriptions<br>(0: device, 5: room, ...)<br>255: inactive |
| mode | r/w | integer | 0: standard<br>2: presence<br>5..8 : button1..4 down<br>9..12 : button1..4 up |
| channel | r/w | integer enum | channel this button should control<br>0: (default) button controls the default channel<br>1..191: reserved for digitalSTROM standard channel types<br>192..239: device specific channel types |
| setsLocalPriority | r/w | boolean | button should set local priority |
| callsPresent | r/w | boolean | button should call present (if system state is absent) |

### 4.2.3 Button Input State

- State (current state, changing during operation of the device, but not persistently stored in the vDC) of a button. The properties described here are contained in the elements of the device-level 4.1.2 buttonInputStates property.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| value | r | boolean or NULL | false=inactive<br>true=active<br>NULL=unknown state |
| clickType | r | integer enum | Most recent click state of the button:<br>0: tip_1x<br>1: tip_2x<br>2: tip_3x<br>3: tip_4x<br>4: hold_start<br>5: hold_repeat<br>6: hold_end<br>7: click_1x<br>8: click_2x<br>9: click_3x<br>10: short_long<br>11: local_off<br>12: local_on<br>13: short_short_long<br>14: local_stop<br>255: idle (no recent click) |
| age | r | double or NULL | age of the state shown in the value and clickType fields in seconds. If no recent state is known, returns NULL. |
| error | r | integer enum | 0: ok<br>1: open circuit<br>2: short circuit<br>4: bus connection problem<br>5: low battery in device<br>6: other device error |

Alternatively, buttons can emit direct scene calls instead of button clicks. So the buttonInputState can contain the actionId and actionMode properties instead of value and clickType when the most current button action was not a regular click event, but a direct scene call:

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| actionId | r | integer | scene id |
| actionMode | r | integer enum | 0: normal<br>1: force<br>2: undo |
