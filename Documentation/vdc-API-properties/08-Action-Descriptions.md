## 4.5 Action Descriptions

### 4.5.1 Parameter Objects

- Parameter descriptions used by action method and properties

| Field Name | Attributes | Type | Description |
|---|---|---|---|
| type | mandatory | numeric enumeration string | data type of the parameter value |
| min | opt, numeric only | double | minimum value |
| max | opt, numeric only | double | maximum value |
| resolution | opt, numeric only | double | resolution (size of LSB of actual HW sensor) |
| siunit | opt, numeric only | string | The SI Unit as a string, incl. prefixes like kilo or milli. For examples see http://www.ebyte.it/library/educards/siunits/TablesOfSiUnitsAndPrefixes.html |
| options | opt, enumeration only | list of key:value pairs | the option values for the enumeration |
| default | opt, all types | double, string or option | the default value of this parameter |

### 4.5.2 Device Action Descriptions

Action descriptions describe basic functionalities and operation processes of a device. They serve as a template to create custom defined actions as variation of templates with modified parameter sets.

- Description of the basic device actions methods. The properties described here are contained in the elements of the deviceActionDescriptions property (invariable).

| Property Name | Attributes | Type | Description |
|---|---|---|---|
| name | mandatory | string | name of this action property entry |
| params | optional | list of Parameter Objects | parameter list related to this action |
| description | optional | string | description of this template action |

### 4.5.3 Standard and Custom and Dynamic Actions

- Standard actions are static and immutable, and as such implemented and defined by the device.
- Custom actions are configured by the user. They can be created via API and are persistently stored on the VDC.
- Dynamic device actions are created on the native device side. They can be created, changed or deleted by interaction on the device itself.
- Actions properties described here are contained in the elements of the standardActions property (invariable).

| Property Name | Attributes | Type | Description |
|---|---|---|---|
| name | mandatory | string | unique id of this standard action property entry, always has prefix std. |
| action | mandatory | string | name of the template action, on which this standard action is based upon |
| params | optional | list of Parameter Name : Value pairs | list of parameter values that are different to the template action |

- Actions properties described here are contained in the elements of the customActions property.

| Property Name | Attributes | Type | Description |
|---|---|---|---|
| name | mandatory | string | unique id of this custom action property entry, always has prefix custom. |
| action | mandatory | string | reference id of the template action, on which this standard action is based upon |
| title | mandatory | string | human readable name of this custom action, in most cases given the user |
| params | optional | list of Parameter Name : Value pairs | list of parameter values that are different to the template action |

- Actions properties described here are contained in the elements of the dynamicDeviceActions property.

| Property Name | Attributes | Type | Description |
|---|---|---|---|
| name | mandatory | string | unique id of this custom action property entry, always has prefix dynamic. |
| title | mandatory | string | human readable name of this custom action, in most cases given the user |
