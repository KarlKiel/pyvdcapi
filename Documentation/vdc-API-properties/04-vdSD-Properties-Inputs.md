### 4.1.2 Inputs

- Virtual devices can have zero to several buttons, binary (digital) inputs and sensors. The following container properties provide access to the set of properties related to each input. The individual subproperties are described in separate paragraphs further down.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| buttonInputDescriptions | r | optional list of property elements | Descriptions (invariable properties) of the buttons in the device.<br>• represented as a list of property elements, one for each button in the device.<br>• The property elements are named sequentially "0","1",...<br><br>See 4.2.1 Button Input Descriptions for details |
| buttonInputSettings | r/w | optional list of property elements | Settings (properties that can be changed and are stored persistently in the vDC) of the buttons in the device.<br>See 4.2.2 Button Input Settings for details |
| buttonInputStates | r/w | optional list of property elements | State (changing during operation of the device, but not persistently stored in the vDC) of a button.<br>See 4.2.3 Button Input States for details |
| binaryInputDescriptions | r | optional list of property elements | Descriptions of the binary inputs in the device.<br>See 4.3.1 Binary Input Descriptions for details |
| binaryInputSettings | r/w | optional list of property elements | Settings (properties that can be changed and are stored persistently in the vDC) of the binary inputs in the device.<br>See 4.3.2 Binary Input Settings for details |
| binaryInputStates | r/w | optional list of property elements | State (changing during operation of the device, but not persistently stored in the vDC) of a binary input.<br>See 4.3.3 Binary Input States for details |
| sensorDescriptions | r | optional list of property elements | Descriptions of the sensors in the device.<br>See 4.4.1 Sensor Input Descriptions for details |
| sensorSettings | r/w | optional list of property elements | Settings (properties that can be changed and are stored persistently in the vDC) of the sensors in the device.<br>See 4.5.3 Sensor Input Settings for details |
| sensorStates | r/w | optional list of property elements | Value of a sensor. Changing during operation of the device, but not persistently stored in the vDC.<br>See 4.4.3 Sensor Input States for details |
| deviceActionDescriptions | r | optional list of property elements | Descriptions of the available action methods in the device.<br>See 4.5 Action Descriptions for details |
| customActions | r/w | optional list of property elements | Descriptions of the user defined actions methods in the device.<br>See 4.5 Action Descriptions for details |
| deviceStateDescriptions | r | optional list of property elements | Descriptions of the available state objects in the device.<br>See 4.6.1 State Descriptions for details |
| deviceStates | r/w | optional list of property elements | Value of the state objects.<br>See 4.6.2 State Descriptions for details |
| devicePropertyDescriptions | r | optional list of property elements | Descriptions of the available property objects in the device.<br>See 4.6.3 Property Descriptions for details |
| deviceProperties | r/w | optional list of property elements | Value of the property objects.<br>See 4.6.4 Property Descriptions for details |
| deviceEventDescriptions | r | optional list of property elements | Descriptions of the available events in the device.<br>See 4.7 Event Descriptions for details |
