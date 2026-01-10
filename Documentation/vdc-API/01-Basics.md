
1 Basics
========

1.1 Connection Management
-------------------------

- Transport level is a TCP socket connection, established by the vdSM to the vDC.
- The TCP stream consists of a 2-byte header containing the message length (16 bits, in network byte order, maximum accepted length is 16384 bytes) followed by the payload, which is a Google protocol buffer message. (as described in this document)
- The life time of the connection defines the vDC session. If the connection breaks, a new session needs to be established.

1.2 Generic Response
--------------------

In case of command failures the VDC returns a generic response message.

The `errorType` and `userMessageToBeTranslated` field are typically used to decide about program flow and error recovery. The user message is suitable to be shown in user interfaces.

The `code` and `description` field are informational, and typically not designed to be shown to users.

Error case: GenericResponse

| code | integer | numerical result code |
|------|---------:|------------------------|
| errorType | integer | kind of failure with implication to error recovery |
| description | string | explanation text, for developers only |
| userMessageToBeTranslated | string | message suitable to be shown in user interfaces, will be translated by dSS |

1.2.1 Error Codes
-----------------

The following error codes are defined.

| Error Code | Number | Description |
|---|---:|---|
| ERR_OK | 0 | Everything alright. |
| ERR_MESSAGE_UNKNOWN | 1 | The message id is unknown. This might happen due to incomplete or incompatible implementation. |
| ERR_INCOMPATIBLE_API | 2 | The API version of the VDSM is not compatible with this VDC. |
| ERR_SERVICE_NOT_AVAILABLE | 3 | The VDC cannot respond. Might happen because the VDC is already connected to another VDSM. |
| ERR_INSUFFICIENT_STORAGE | 4 | The VDC could not store the related data. |
| ERR_FORBIDDEN | 5 | The call is not allowed. |
| ERR_NOT_IMPLEMENTED | 6 | Not (yet) implemented. |
| ERR_NO_CONTENT_FOR_ARRAY | 7 | Array data was expected. |
| ERR_INVALID_VALUE_TYPE | 8 | Invalid data type. |
| ERR_MISSING_SUBMESSAGE | 9 | Submessage was expected. |
| ERR_MISSING_DATA | 10 | Additional data was expected. |
| ERR_NOT_FOUND | 11 | Addressed entity or object was not found. |
| ERR_NOT_AUTHORIZED | 12 | The caller is not authorized with the Native Device |

1.2.2 Error Types
-----------------

The following error types are defined.

| Error Type | Number | Description |
|---|---:|---|
| ERROR_TYPE_FAILED | 0 | Something went wrong. This is the usual error type. |
| ERROR_TYPE_OVERLOADED | 1 | The call failed because of a temporary lack of resources. The operation might work if tried again, but it should NOT be repeated immediately as this may simply exacerbate the problem. |
| ERROR_TYPE_DISCONNECTED | 2 | The call required communication over a connection that has been lost. The caller will need to try again. |
| ERROR_TYPE_UNIMPLEMENTED | 3 | The requested method is not implemented. The caller may wish to revert to a fallback approach based on other methods. |


