## 4.8 Output

- Note: devices with no output functionality return a NULL response when queried for outputDescription, outputSettings or outputState

### 4.8.1 Output Description

- Description (invariable properties) of the device's output. The properties described here are contained in the device-level 4.1.3 outputDescription property.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| defaultGroup | r | integer | dS Application Id of the device |
| name | r | string | human readable name/number for the output (e.g. matching labels for hardware connectors) |
| function | r | integer enum | 0: on/off only (with channel 1, "brightness", switched on when "brightness">"onThreshold")<br>1: dimmer (with channel 1, "brightness")<br>2: positional (e.g. valves, blinds)<br>3: dimmer with color temperature (with channels 1 and 4, "brightness", "ct")<br>4: full color dimmer (with channels 1-6, "brightness", "hue", "saturation", "ct", "cieX", "cieY"<br>5: bipolar, with negative and positive values (e.g. combined heating/cooling valve, in/out fan control)<br>6: internally controlled (e.g. device has temperature control algorithm integrated) |
| outputUsage | r | integer enum | Describes the usage field for the output (beyond device color)<br>0: undefined (generic usage or unknown)<br>1: room<br>2: outdoors<br>3: user (display/indicator) |
| variableRamp | r | boolean | supports variable ramps |
| maxPower | r | optional double | max output power in Watts. If absent, power capability is undefined |
| activeCoolingMode | r | optional boolean | Set to true if the device can activly cool (e.g. air-condition and FCU devices) |

### 4.8.2 Output Settings

- Settings (properties that can be changed and are stored persistently in the vDC) for the device's output. The properties described here are contained in the device-level 4.1.3 outputSettings property.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| activeGroup | r/w | integer | dS Application Id of the device |
| groups | r/w | list of boolean property elements | contains a list of property elements with a boolean value, representing this device's output's membership in one or multiple groups.<br>• The name of the subproperty represents the dS group number ("1" to "63").<br>• For efficiency reasons, only "true" values are returned, so the result of requesting the entire subproperty list with a wildcard query is a list of groups the output is member of (thus usually consisting of a few elements only)<br>• When querying a single group by ID, a NULL value is returned if the output is not a member of the queried group.<br>• For writing, value can be true or false to add or remove a group membership. |
| mode | r/w | integer enum | 0: disabled, inactive<br>1: binary<br>2: gradual<br>127: default (generically enabled using device's default mode) |
| pushChanges | r/w | boolean | if set, locally generated changes in the output value will be pushed |
| onThreshold | r/w | optional double | Light outputs: minimum brightness level (0..100%) that will switch on non-dimmable lamps. Defaults to 50%. |
| minBrightness | r/w | optional double | minmum brightness (0..100%) that hardware supports (for dimming outputs). This value is used for callSceneMin and dimming. Devices pre-set this value according to the dimmer capabilities, but the value can be changed to adjust depending on connected light |
| dimTimeUp | r/w | optional integer | Light outputs: dim up time in digitalSTROM 8-bit dim time format:<br>4msbits = exp, 4lsbits = lin, time = 100ms/32 ∗ 2^exp ∗ (17 + lin) |
| dimTimeDown | r/w | optional integer | Light outputs: dim down time in digitalSTROM 8-bit dim time format |
| dimTimeUpAlt1 | r/w | optional integer | Light outputs: alternate 1 dim up time in digitalSTROM 8-bit dim time format |
| dimTimeDownAlt1 | r/w | optional integer | Light outputs: alternate 1 dim down time in digitalSTROM 8-bit dim time format |
| dimTimeUpAlt2 | r/w | optional integer | Light outputs: alternate 2 dim up time in digitalSTROM 8-bit dim time format |
| dimTimeDownAlt2 | r/w | optional integer | Light outputs: alternate 2 dim down time in digitalSTROM 8-bit dim time format |
| heatingSystemCapability | r/w | optional integer enum | Climate control: specifies how "heatingLevel" controlValue is applied:<br>1: heating only (heatingLevel 0..100 -> output 0..100)<br>2: cooling only (heatingLevel 0..-100 -> output 0..100)<br>3: heating and cooling (heatingLevel -100..0..100 is directly applied in case of bipolar output, and absolute value (0..100) is applied to unipolar outputs) |
| heatingSystemType | r/w | optional integer enum | Climate control: specifies which kind of valve type or actuator is attached:<br>0: undefined<br>1: floor heating (valve)<br>2: radiator (valve)<br>3: wall heating (valve)<br>4: convector passive<br>5: convector active<br>6: floor heating low energy (valve) |

### 4.8.3 Output State

- State (current state, changing during operation of the device, but not persistently stored in the vDC) of the device's output. The properties described here are contained in the device-level 4.1.3 outputState property.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| localPriority | r/w | boolean | enables local priority of the device's output. In local priority mode, device ignores scene calls unless the scene has the ignoreLocalPriority flag set, or the callScene call has the force parameter set to true |
| error | r | integer enum | 0: ok<br>1: open circuit / lamp broken<br>2: short circuit<br>3: overload<br>4: bus connection problem<br>5: low battery in device<br>6: other device error |
