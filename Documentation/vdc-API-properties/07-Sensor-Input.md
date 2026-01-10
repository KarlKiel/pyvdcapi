## 4.4 Sensor Input

### 4.4.1 Sensor Input Description

- Description (invariable properties) of a sensor input. The properties described here are contained in the elements of the device-level 4.1.2 sensorDescriptions property.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| name | r | string | human readable name/number for the sensor |
| dsIndex | r | integer | 0..N-1, where N=number of sensors in this device. |
| sensorType | r | integer enum | Describes the type of physical unit the sensor measures<br>0 : none<br>1 : Temperature in °C<br>2 : Relative humitity in %<br>3 : Illumination in lux<br>4 : supply voltage level in V<br>5 : CO concentration in ppm<br>6 : Radon activity in Bq/m3<br>7 : gas type sensor<br>8 : particles <10µm in μg/m3<br>9 : particles <2.5µm in μg/m3<br>10 : particles <1µm in μg/m3<br>11 : room operating panel set point, 0..100%<br>12 : fan speed, 0..1 (0=off, <0=auto)<br>13 : Wind speed in m/s (average)<br>14 : Active Power in W<br>15 : Electric current in A<br>16 : Energy Meter in kWh<br>17 : Apparent Power in VA<br>18 : Air pressure in hPa<br>19 : Wind direction in degrees<br>20 : Sound pressure level in dB<br>21 : Precipitation intensity in mm/m2 (sum of last hour)<br>22 : CO2 concentration in ppm<br>23 : Wind gust speed in m/s<br>24 : Wind gust direction in degrees<br>25 : Generated Active Power in W<br>26 : Generated Energy in kWh<br>27 : Water Quantity in l<br>28 : Water Flow Rate in l/s |
| sensorUsage | r | integer enum | Describes the usage field for the sensor<br>0: undefined (generic usage or unknown)<br>1: room<br>2: outdoor<br>3: user interaction (setting, dial)<br>4: device level measurement (total, sum)<br>5: device level last run<br>6: device level average |
| min | r | double | min value |
| max | r | double | max value |
| resolution | r | double | resolution (size of LSB of actual HW sensor) |
| updateInterval | r | double | how fast the physical value is tracked, in seconds, approximately. The purpose of this is to give information about the time resolution that can be expected from that sensor. |
| aliveSignInterval | r | double | how fast the sensor minimally sends an update. If sensor does not push a value for longer than that, it can be considered out-of-order |

### 4.4.2 Sensor Input Settings

- Settings (properties that can be changed and are stored persistently in the vDC) for a sensor. The properties described here are contained in the elements of the device-level 4.1.2 sensorSettings property.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| group | r/w | integer | dS group number |
| minPushInterval | r/w | double | minimum interval between pushes of changed state in seconds<br>default = 2 |
| changesOnlyInterval | r/w | double | minimum interval between pushes with same value (in case sensor hardware sends update, but with same value as before - only age will differ).<br>default = 0 = all updates from hardware trigger a push |

### 4.4.3 Sensor Input State

- State (current state, changing during operation of the device, but not persistently stored in the vDC) of a sensor. The properties described here are contained in the elements of the device-level 4.1.2 sensorStates property.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| value | r | double or NULL | current sensor value in the unit according to sensorType. If no recent state is known, returns NULL |
| age | r | double or NULL | age of the state shown in the value field in seconds. If no recent state is known, returns NULL. |
| contextId | r | integer or NULL | Numerical Id of context data. Optional, returns NULL if context data not available. |
| contextMsg | r | string or NULL | Text message of context data. Optional, returns NULL if context data not available. |
| error | r | integer enum | 0: ok<br>1: open circuit<br>2: short circuit<br>4: bus connection problem<br>5: low battery in device<br>6: other device error |
