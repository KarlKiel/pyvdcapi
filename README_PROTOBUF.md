# Python Protocol Buffer Files

This directory contains the Python representation of the vDC API protocol buffer definitions.

## Generated Files

- `genericVDC_pb2.py` - Generated Python code from `Documentation/proto/genericVDC.proto`

## How to Use

The generated Python file contains classes for all message types defined in the proto file. You can import and use them as follows:

```python
import genericVDC_pb2

# Create a message
hello_request = genericVDC_pb2.vdsm_RequestHello()
hello_request.dSUID = "device-id-123"
hello_request.api_version = 2

# Serialize to bytes
serialized_data = hello_request.SerializeToString()

# Deserialize from bytes
new_request = genericVDC_pb2.vdsm_RequestHello()
new_request.ParseFromString(serialized_data)

# Create a complete message
message = genericVDC_pb2.Message()
message.type = genericVDC_pb2.VDSM_REQUEST_HELLO
message.message_id = 1
message.vdsm_request_hello.CopyFrom(hello_request)
```

## Available Message Types

The generated file includes the following main message types:

- **Request/Response Messages:**
  - `vdsm_RequestHello` / `vdc_ResponseHello`
  - `vdsm_RequestGetProperty` / `vdc_ResponseGetProperty`
  - `vdsm_RequestSetProperty`
  - `vdsm_RequestGenericRequest`

- **Notification Messages:**
  - `vdsm_NotificationCallScene`
  - `vdsm_NotificationSaveScene`
  - `vdsm_NotificationUndoScene`
  - `vdsm_NotificationSetLocalPrio`
  - `vdsm_NotificationCallMinScene`
  - `vdsm_NotificationIdentify`
  - `vdsm_NotificationSetControlValue`
  - `vdsm_NotificationDimChannel`
  - `vdsm_NotificationSetOutputChannelValue`

- **Send Messages:**
  - `vdc_SendAnnounceDevice`
  - `vdc_SendAnnounceVdc`
  - `vdc_SendVanish`
  - `vdc_SendIdentify`
  - `vdsm_SendPing` / `vdc_SendPong`
  - `vdsm_SendBye`
  - `vdsm_SendRemove`

- **Property Types:**
  - `PropertyValue`
  - `PropertyElement`

- **Enums:**
  - `Type` - Message type identifiers
  - `ResultCode` - Error/success codes

## Requirements

```bash
pip install protobuf>=6.31.1
```

## Regenerating

If you need to regenerate the Python files from the proto definition:

```bash
python -m grpc_tools.protoc -I./Documentation/proto --python_out=. Documentation/proto/genericVDC.proto
```

Or if you only have the protobuf package:

```bash
protoc -I./Documentation/proto --python_out=. Documentation/proto/genericVDC.proto
```
