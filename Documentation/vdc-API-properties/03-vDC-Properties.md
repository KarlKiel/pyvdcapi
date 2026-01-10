# 3 Virtual device connector (vDC) properties

- The following table applies to entities which have a value of "vDC" for the "type" property.
- All vDCs must also support the basic set of properties as described under 2 "Common properties" above.

## 3.1 Properties on the vDC level

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| capabilities | r | list of property elements | Descriptions (invariable properties) of the vdc's capabilities.<br>• each capability is represented as a property element (key/value)<br><br>See 3.2 below for defined capabilities |
| zoneID | r/w | integer, global dS Zone ID | this should be updated by the vdSM to reflect the default zone the vdc has. |
| implementationId | r | string | Unique id used to identify vdc implementation. Non-digitalSTROM vdcs must use "x-company-" prefix to avoid collisions. |

## 3.2 vDC Capabilities

- Capabilities of the vDC. The properties described here are part of the vDC-level property. See property capabilities above.

| Property Name | acc | Type / Range | Description |
|---|---|---|---|
| metering | r | optional boolean | if true, the vdc provides metering data |
| identification | r | optional boolean | if true, the vdc provides a way of identifying itself. E.g. a LED that can be blinked. |
| dynamicDefinitions | r | optional boolean | if true, the vdc supports dynamic device definitions, e.g. propertyDescriptions and actionsDescriptions. |
