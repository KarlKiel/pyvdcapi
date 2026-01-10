7 Device and vDC Operation Methods and Notifications
===================================================

- Note: the vDC host and every logical vDC have dSUIDs and can be addressed by some (not all) of the device level methods, in particular reading and writing named properties for vDC configuration and the presence polling method ping.

7.1 Named Property access
-------------------------

- Addressable entities are items within the vdc host that have their own dSUID. The dSUID can be specified in vDC API request to specifically address the entity. The vDC host as a whole, the contained vDC[s] and every virtual device has its own dSUID and thus is a addressable entity.
- Addressable entities have named properties which can be read and written by the vdSM and are in some cases being pushed from the vDC.
- Properties that are defined in the digitalSTROM specifications (including this document) with name, type and behaviour are considered system properties. Implementations conforming to the specification must support these.
- Additionally, implementations might add implementation specific properties to extend functionality beyond what the dS system demands. These properties' names must always be prefixed by "x-". It is further recommended to include an identifier for the party who introduces a property. For example company Abc Inc. could prefix their properties with "x-abc-".
- Supported value types for properties are the simple types integer, double, boolean, string and binary bytes, or a list of property elements which in turn contain a name (key) and either a simple type (value), or yet another level of property elements. Note that while properties can be nested indefinitely this way, it is explicitly recommended to keep nesting levels as low as possible.
- The available properties depend on the kind of the addressable entity (vdc, vdc host, virtual device) - the complete set of properties supported by a virtual device entity is defined in the device profile for that type of device.
- A common set of properties called common properties must be supported by all addressable entities. These properties can be read to identify the type of entity, and get some basic information for this.

7.1.1 Reading Property values
-----------------------------

- Virtual devices can have zero to several buttons, binary (digital) inputs and sensors. The following container properties provide access to the set of properties related to each input. The individual subproperties are described in separate paragraphs further down.

Method: `getProperty` — vdSM -> vDC host

Request

| Request Parameter | Type | Description |
|---|---:|---|
| dSUID | string of 34 hex characters (2*17) | The dSUID of the entity (device, vDC or vDC host) to read properties from |
| query | property elements sub-messages | A property tree structure consisting of property elements, but with no values, specifying the property or properties to be returned. The name of each property element specifies the property on that level to access. If the name is empty, acts as wildcard; if wildcard is last element on branch, deeper levels are returned too. |

Response: ResponseGetProperty

| Response Parameter | Type | Description |
|---|---:|---|
| properties | property elements sub-messages | A property tree structure consisting of property elements and values representing the properties selected by the query structure. The response has basically the same tree structure as the query. Where wildcards were used in the query, the response tree will expand beyond the query structure returning all substructures. Where unknown/nonexisting properties were requested in the query, the response tree will not have a corresponding element. Some properties might exist but not have a value at the time of the query - these will return an explicit NULL value. |

- The response has basically the same tree structure as the query.
- Where wildcards were used in the query, the response tree will expand beyond the query structure returning all substructures.
- Where unknown/nonexisting properties were requested in the query, the response tree will not have a corresponding element.
- Some properties might exist but not have a value at the time of the query - these will return an explicit NULL value.

Error case: GenericResponse

| Field | Type | Description |
|---|---:|---|
| code | integer | RESULT_FORBIDDEN: the property exists but cannot be read (write-only, uncommon case). |
| message | string | explanation text |

7.1.2 Writing property values
-----------------------------

Method: `setProperty` — vdSM -> vDC host

Request

| Request Parameter | Type | Description |
|---|---:|---|
| dSUID | string of 34 hex characters (2*17) | The dSUID of the entity (device, vDC or vDC host) to write properties to |
| properties | property elements sub-messages | A property tree structure consisting of property elements and values representing the properties to be written. The name of each property element specifies a property on that level to access. If the name is specified empty, this is a wildcard meaning all elements of that level (for example: all inputs or all scenes) should be set to the same value. Note: channelState property must not be changed using setProperty, but with the separate setOutputChannelValue action (see below). Note: if writing multiple property values in one request, failing to write any of these will cause setProperty to return an error. However, some of the other properties included in the same request might already be stored (in any order, not necessarily in the order of values as passed in properties). Use separate requests if you need separate ok/failure status for each value. |

Response: GenericResponse

| Field | Type | Description |
|---|---:|---|
| code | integer | 0 = success |

Error case: GenericResponse

| Field | Type | Description |
|---|---:|---|
| code | integer | RESULT_INVALID_VALUE_TYPE: passed type is wrong and cannot be written. RESULT_FORBIDDEN: the property exists but cannot be read (write-only, uncommon case). RESULT_NOT_FOUND: the receiver (device or vDC itself) specified through dSUID is unknown at the callee. |
| message | string | explanation text |

7.1.3 Getting notified of property value (changes)
--------------------------------------------------

- Some properties (especially button/input/sensor states) might change within the device and can be reported to the dS system via pushProperty, avoiding the need for the vdSM to poll values.

Notification: `pushProperty` — vDC host -> vdSM

| Notification Parameter | Type | Description |
|---|---:|---|
| dSUID | string of 34 hex characters (2*17) | The dSUID of the entity (device, vDC or vDC host) from where this notification originates |
| properties | property elements sub-messages | A property tree structure consisting of property elements and values representing the information pushed to the vdSM. |

7.2 Presence polling
--------------------

- Presence polling is available for every addressable entity (vDC host, vDCs and all devices). Implementation should return a pong only if the entity can be considered active in the system. If possible at reasonable cost, a connection test with the device's hardware should be made. In some cases (unidirectional sensors) it might not be possible to query the device; in these cases the vDC should apply reasonable heuristics to decide whether to report the device as active or not.

Notification name: `ping` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| dSUID | string of 34 hex characters (2*17) | The dSUID of the entity (device, vDC or vDC host) to send the ping to |

Notification name: `pong` — vDC host -> vdSM

| Notification Parameter | Type | Description |
|---|---:|---|
| dSUID | string of 34 hex characters (2*17) | The dSUID of the entity (device, vDC or vDC host) from where this pong originates |

7.3 Actions
-----------

- Actions are operations that may change the internal state of the device and/or its outputs, often depending on preconditions, but do not cause a distinct change of a single status value that could be read back.
- Distinct, unconditional state changes that can be read back are always implemented as properties, not actions.

7.3.1 Call Scene
----------------

- calls a scene on the device

Notification name: `callScene` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| dSUID | string of 34 hex characters (2*17) | One or multiple dSIDs of device(s) this call applies to. |
| scene | integer | dS scene number to call |
| force | boolean | if true, local priority is overridden |
| group | optional integer | dS group number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |
| zoneID | optional integer | dS global zone ID number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |

7.3.2 Save Scene
----------------

- save the relevant parts of the current state of the device (usually the output value, but possibly multiple output values, flags, etc. in future devices) as scene.

Notification name: `saveScene` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| dSUID | string of 34 hex characters (2*17) | One or multiple dSIDs of device(s) this call applies to. |
| scene | integer | dS scene number to save state into |
| group | optional integer | dS group number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |
| zoneID | optional integer | dS global zone ID number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |

7.3.3 Undo Scene
----------------

- Undoes a scene call. All output values are restored to the state they had before the scene call.

Notification name: `undoScene` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| dSUID | string of 34 hex characters (2*17) | One or multiple dSIDs of device(s) this call applies to. |
| scene | integer | This specifies the scene call to undo. Undo is executed only if device's last called scene matches scene. This is to prevent undoing a scene which might have been called in the meantime from another origin (like a local on or off). |
| group | optional integer | dS group number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |
| zoneID | optional integer | dS global zone ID number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |

7.3.4 Set local priority
------------------------

- Sets the device into local priority mode (i.e. sets the `localPriority` property) if the passed scene does not have the `dontCare` flag set. This is used for including devices into area operations. Note that this is a compatibility method to simplify dS 1.0 interfacing and might be removed later in dS 2.x.

Notification name: `setLocalPriority` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| dSUID | string of 34 hex characters (2*17) | One or multiple dSIDs of device(s) this call applies to. |
| scene | integer | This specifies the scene to check for the `dontCare` flag. If it is set, nothing happens; if it is not set, the `localPriority` flag will be set on the device level. |
| group | optional integer | dS group number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |
| zoneID | optional integer | dS global zone ID number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |

7.3.5 Dim Channel
-----------------

- performs dimming a specific channel of the device. If the device does not have an output of the specified channel type, this method call is ignored.

Notification name: `dimChannel` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| dSUID | string of 34 hex characters (2*17) | One or multiple dSIDs of device(s) this call applies to. |
| channel | integer | Channel to start or stop dimming: 0: dim the default channel (e.g. brightness for lights) 1..239: dim channel of the specified type, if any |
| mode | integer | 1: start dimming upwards (incrementing output value) -1: start dimming downwards (decrementing output value) 0: stop dimming |
| area | integer | 0: no area restriction 1..4: only perform dimming action if the corresponding area on scene (Tx_S1) does not have the dontCare() flag set. |
| group | optional integer | dS group number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |
| zoneID | optional integer | dS global zone ID number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |

7.3.6 Call Minimum Scene
------------------------

- If the device is off, set it to the minimal value needed to become logically switched on and participate in dimming. Otherwise, no action is taken.

Notification name: `callSceneMin` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| dSUID | string of 34 hex characters (2*17) | One or multiple dSIDs of device(s) this call applies to. |
| scene | integer | This specifies the scene to check for the `dontCare` flag. If it is set, nothing happens; if it is not set, and the device is off, the minimum output level will be set. |
| group | optional integer | dS group number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |
| zoneID | optional integer | dS global zone ID number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |

7.3.7 Identify
--------------

- identify the device for the user - usually implemented as blinking the controlled light or an indicator LED the device might have. Depending on device type, the alert might be implemented differently, such as a beep, or hum or short movement.

Notification name: `identify` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| dSUID | string of 34 hex characters (2*17) | One or multiple dSIDs of device(s) this call applies to. |
| group | optional integer | dS group number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |
| zoneID | optional integer | dS global zone ID number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |

7.3.8 Set Control Value
-----------------------

- sets the value of an output channel.

Notification name: `setControlValue` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| dSUID | string of 34 hex characters (2*17) | One or multiple dSIDs of device(s) this call applies to. |
| name | string | The name of the control value. This defines the semantic meaning of the value and thus how the value will affect (or not) the output(s) of the device. In dS 1.0, control name values are mapped to dS "sensor type" numbers. See chapter "Control Values" in "vDC API properties" for a list of available control values. |
| value | double | control value (aka dS sensor value) |
| group | optional integer | dS group number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |
| zoneID | optional integer | dS global zone ID number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |

7.3.9 Set Output Channel Value
------------------------------

- sets the value of an output channel.

Notification name: `setOutputChannelValue` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| dSUID | string of 34 hex characters (2*17) | One or multiple dSIDs of device(s) this call applies to. |
| channel | integer | Channel to start or stop dimming: 0: dim the default channel (e.g. brightness for lights) 1..239: dim channel of the specified type, if any |
| apply_now | optional boolean | if omitted or set to false, the new output value will be buffered but not yet applied to the hardware. The next setOutputChannelValue call with apply_now omitted or set to true will apply all buffered values. |
| value | double | Value to be applied to the output; maybe omitted if "automatic" flag is set |
| automatic | optional boolean | Switch device to internal automatic control logic |
| group | optional integer | dS group number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |
| zoneID | optional integer | dS global zone ID number, present if the scene call was not applied to a single device, but a zone/group (informational only, vdSM already creates separate calls for every involved device) |

7.3.10 Call Action
------------------

- calls an action on the device

Notification name: `GenericRequest` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| method | string | invokeDeviceAction |
| dSUID | string of 34 hex characters (2*17) | One or multiple dSUIDs of device(s) this call applies to. |
| id | string | device action to execute |
| params | optional | additional parameters, json encoded object |

7.4 Configuration Control and Processes
--------------------------------------

7.4.1 Learn-In and -Out
-----------------------

- starts the learn-in or learn-out process

Notification name: `GenericRequest` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| method | string | pair |
| dSUID | string of 34 hex characters (2*17) | One or multiple dSUIDs of device(s) this call applies to. |
| establish | bool | true = learn-in, false = learn-out |
| timeout | integer | timeout in seconds, -1 to disable timeout |
| params | optional | additional parameters, json encoded object |


7.4.2 Authenticate
------------------

- starts the authentication process

Notification name: `GenericRequest` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| method | string | authenticate |
| dSUID | string of 34 hex characters (2*17) | One or multiple dSUIDs of device(s) this call applies to. |
| authData | string | json encoded object with authentication tokens |
| authScope | string | context, e.g. user id or device reference |
| params | optional | additional parameters, json encoded object |

7.4.3 Firmware Update
---------------------

- starts the firmware upgrade process

Notification name: `GenericRequest` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| method | string | firmwareUpgrade |
| dSUID | string of 34 hex characters (2*17) | One or multiple dSUIDs of device(s) this call applies to. |
| checkonly | bool | true for a dry-run check only |
| clearsettings | bool | true for upgrade and reset of all configuration data to factory defaults |
| params | optional | additional parameters, json encoded object |


7.4.4 Change dS-Device Configuration/Profile
--------------------------------------------

- activate new dS-Device configuration, e.g. profile
- as result the Submodules of the dS-Device may be modified, reordered or being removed at all

Notification name: `GenericRequest` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| method | string | setConfiguration |
| dSUID | string of 34 hex characters (2*17) | One or multiple dSUIDs of device(s) this call applies to. |
| id | string | New Configuration ID |

7.4.5 Identify vDC host device
------------------------------

- This call triggers the visual (and/or acustic) identification signal of the platform the vDC is running on.
- The "identification" capability indicates whether the vDCs supports this kind of identification.

Notification name: `GenericRequest` — vdSM -> vDC host

| Notification Parameter | Type | Description |
|---|---:|---|
| method | string | identify |
| dSUID | string of 34 hex characters (2*17) | The dSUIDs of the vDC to be identified. |


