## 4.6 States and Properties

Device State represent a status within a device. States differ from Properties in the way that they have limited number of possible values, whereas Properties are more generic and do have limitations on their value, with respect to their type.

### 4.6.1 Device State Descriptions

- Description of the state. The properties described here are contained in the elements of the deviceStateDescriptions property (invariable).
- State changes are signaled along with the new state value.

| Property Name | Attributes | Type | Description |
|---|---|---|---|
| name | mandatory | string | name of this state property entry |
| options | mandatory | list of Option Id : Value pairs | option list related to this state, e.g. 0: Off, 1: Initializing, 2: Running, 3: Shutdown |
| description | optional | string | description of this state |

### 4.6.2 Device State Values

- Value of the state. The properties described here are contained in the elements of the deviceStates property.

| Property Name | Attributes | Type | Description |
|---|---|---|---|
| name | mandatory | string | name of this state property entry |
| value | mandatory | string | option value |

### 4.6.3 Device Property Descriptions

- Description of a device property. The properties described here are contained in the elements of the devicePropertyDescriptions property (invariable).

| Property Name | Attributes | Type | Description |
|---|---|---|---|
| name | mandatory | string | name of this property entry |
| type | mandatory | numeric enumeration string | data type of the property value |
| min | opt, numeric only | double | minimum value |
| max | opt, numeric only | double | maximum value |
| resolution | opt, numeric only | double | resolution (size of LSB of actual HW sensor) |
| siunit | opt, numeric only | string | The SI Unit as a string, incl. prefixes like kilo or milli. For examples see http://www.ebyte.it/library/educards/siunits/TablesOfSiUnitsAndPrefixes.html |
| options | opt, enumeration only | list of key:value pairs | the option values for the enumeration |
| default | opt, all types | double, string or option | the default value of this property |

### 4.6.4 Device Property Values

- Value of the property. The properties described here are contained in the elements of the deviceProperties property.

| Property Name | Attributes | Type | Description |
|---|---|---|---|
| name | mandatory | string | name of this state property entry |
| value | mandatory | string | property value |
