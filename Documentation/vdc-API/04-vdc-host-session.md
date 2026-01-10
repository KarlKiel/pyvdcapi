4 vDC host session
===================

4.1 Basics
----------

- a session represents the connection from a single vdSM to a single vDC host (which may host one or multiple logical vDCs)
- a session is identical with having a TCP connection.
- a vdSM aims to keep the vDC sessions active all the time.
- if a session is terminated for any reason, the vdSM must try to establish a new session.
- Only if fundamental incompatibility between vDC host and vdSM is detected (no common API version), the vdSM might cease trying to establish a session.
- at a given time, a vdSM might have at most one single session with one particular vDC host (it may of course have connections to multiple distinct vDC hosts).
- a vDC session must always start with a session initialisation phase, before it changes into the operation phase.

4.2 vDC host Session initialisation
-----------------------------------

- vdSM connects to the vDC host
- vdSM calls "Hello" method on vDC host.

Method: hello — vdSM -> vDC host

Request Parameter | Type | Description
---|---:|---
dSUID | string of 34 hex characters (2*17) | dSUID of the vdSM
api_version | integer | vDC API version The API version as described in this document is 2

Response

Response Parameter | Type | Description
---|---:|---
dSUID | string of 34 hex characters (2*17) | dSUID of the vDC host Note: although the vDC host does not yet appear as a logical entity in the current digitalSTROM specification, it still has a dSUID in order to be addressable by custom apps and for future dS system evolution

Error case: GenericResponse

Field | Type | Description / Notes
---|---:|---
code | integer | RESULT_SERVICE_NOT_AVAILABLE: This means the vDC host cannot accept the connection because it is already connected to another vdSM. RESULT_INCOMPATIBLE_API: The vdSM does not support the API version presented in APIVersion
message | string | explanation text

4.3 vDC host Session operation
------------------------------

- session operation consists of announcing one or multiple logical vDCs (see below) and then announcing none, one or multiple vdSDs (see below).
- To avoid a vDC host session to implicitly end, some minimal communication must occur between vdSM and vDC host in regular intervals (for example: ping/pong).

4.4 vDC host Session termination
--------------------------------

- a vDC session is explicitly terminated when the Bye command is called:

Method: bye — vdSM -> vDC host

Request Parameter | Type | Description
---|---:|---
- | - | -

Response: Generic Response

Field | Type | Description
---|---:|---
code | integer | 0 - success

- a vDC session is implicitly terminated when a Hello command asks for starting a new vDC session
- Closing the connection implicitly terminates the vDC session as well

