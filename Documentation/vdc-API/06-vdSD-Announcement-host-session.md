6 vdSD Announcement host session
================================

- for every vDC announced, the vDC must announce all devices managed by the vDC.
- a device is considered managed by the vDC when the vDC has reasonably reliable information that the device is in fact connected to or connectable from the vDC. This means that the vDC should announce devices even if the device is temporarily offline.
- the vdSM can explicitly request removal of managed devices.

6.1 Device Announcement
-----------------------

- vDC calls `announcedevice` method on vdSM

Method: `announcedevice` — vDC host -> vdSM

Request Parameter | Type | Description
---|---:|---
dSUID | string of 34 hex characters (2*17) | The dSUID of the device to be announced
vdc_dSUID | string of 34 hex characters (2*17) | The dSUID of the logical vDC which contains this device

Response: GenericResponse

| Field | Type | Description |
|---|---:|---|
| code | integer | 0 - success |

Error case: GenericResponse

| Field | Type | Description |
|---|---:|---|
| code | integer | RESULT_INSUFFICIENT_STORAGE: vdSM cannot handle another device |
| message | string | explanation text |

6.2 Device Operation
--------------------

- after announcing a device, device-level methods can be invoked by either party on the other, and device-level notifications can be sent by either party to the other.
- See Chapter 7 on Device Level Method Notifications for a specification of the supported individual methods and notifications.

6.3 Ending Device Operation
---------------------------

- either vDC sends "Vanish" notification to vdSM to indicate a device has been physically disconnected or unlearned (think: enOcean unidirectional switches for example) from the vDC.

Method: `vanish` — vDC host -> vdSM

Request Parameter | Type | Description
---|---:|---
- | - | -

Response: Generic Response

Field | Type | Description
---|---:|---
code | string of 34 hex characters (2*17) | The dSUID of the device that has vanished

- or vdSM calls `remove` method on vDC to request a device to be removed from this vDC (but might have been connected to another vDC in the meantime). vDC may reject removal only if it has 100% knowledge the device is actually connected and operable (in which case the higher levels in dSS should see the device as active anyway and will not allow users to delete it).

Method: `remove` — vdSM -> vDC host

Request Parameter | Type | Description
---|---:|---
dSUID | string of 34 hex characters (2*17) | The dSUID of the device to be removed

Response: GenericResponse

Field | Type | Description
---|---:|---
code | integer | 0 - success

Error case: GenericResponse

Field | Type | Description
---|---:|---
code | integer | RESULT_FORBIDDEN: vDC does not allow to remove the device, for example because it is verifiably physically connected to the vDC. However, consider that for example wireless devices might get carried away with being un-paired from their former vDC, and then paired with another vDC in the same installation. In such a case, dss/dsa will want to remove the device from the former vDC/vdSM - the vDC must not reject such a deletion attempt.
message | string | explanation text

