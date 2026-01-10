## 4.11 Control Values

- Control Values are not regular properties, but like properties, control values are named values and thus similar to properties. Unlike properties, control values cannot be read but only written to a vdSD, using the setControlValue call.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| heatingLevel | w | double | (dS Sensortype 50): level of heating intensity -100..100:<br>0=no heating or cooling<br>100=max heating<br>-100=max cooling |
