5 vDC Announcement
==================

- after vDC session is established, the vDC host must announce every logical vDC it hosts, before it announces any of that logical vDC's devices.
- It does so by calling the `announcevdc` method
- unlike individual devices (see below), logical vDCs cannot vanish during an established vDC session.

vDC Method: announcevdc — vDC host -> vdSM

Request Parameter | Type | Description
---|---:|---
dSUID | string of 34 hex characters (2*17) | The dSUID of the vDC to be announced

Response: GenericResponse

Field | Type | Description
---|---:|---
code | integer | 0 - success

Error case: GenericResponse

Field | Type | Description
---|---:|---
code | integer | RESULT_INSUFFICIENT_STORAGE: vdSM cannot handle another vDC
description | string | explanation text
errorType | enum | kind of failure with implication to error recovery
userMessageToBeTranslated | string | message suitable to be shown in user interfaces, translated by the dSS

