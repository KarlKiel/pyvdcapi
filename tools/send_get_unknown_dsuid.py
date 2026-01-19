import asyncio
import struct
from pyvdcapi.network import genericVDC_pb2 as pb

MESSAGE_LENGTH_FORMAT = "!H"


async def send_message(writer, message):
    data = message.SerializeToString()
    writer.write(struct.pack(MESSAGE_LENGTH_FORMAT, len(data)) + data)
    await writer.drain()


async def read_message(reader):
    length_bytes = await reader.readexactly(2)
    length = struct.unpack(MESSAGE_LENGTH_FORMAT, length_bytes)[0]
    data = await reader.readexactly(length)
    msg = pb.Message()
    msg.ParseFromString(data)
    return msg


async def main():
    reader, writer = await asyncio.open_connection("127.0.0.1", 8444)

    # Send Hello
    hello = pb.Message()
    hello.type = pb.VDSM_REQUEST_HELLO
    hello.message_id = 10
    hello.vdsm_request_hello.dSUID = "TEST-CLIENT"
    hello.vdsm_request_hello.api_version = 3
    await send_message(writer, hello)
    resp = await read_message(reader)
    print("HELLO-RESP:", resp)

    # Send GetProperty for unknown device
    getp = pb.Message()
    getp.type = pb.VDSM_REQUEST_GET_PROPERTY
    getp.message_id = 11
    # Use an unknown dSUID
    getp.vdsm_request_get_property.dSUID = "00000002FFFFFFFFFFFFFFFFFFFFFFFF"
    pe = pb.PropertyElement()
    pe.name = "name"
    pe.elements.add().name = ""
    getp.vdsm_request_get_property.query.extend([pe])

    await send_message(writer, getp)
    prop_resp = await read_message(reader)
    print("GET-RESP:", prop_resp)

    writer.close()
    await writer.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
