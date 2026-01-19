import asyncio
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from pyvdcapi.entities.vdc_host import VdcHost  # noqa: E402
from pyvdcapi.network import genericVDC_pb2 as pb  # noqa: E402

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


async def run_test():
    # Start host
    host = VdcHost(name="Test Host", announce_service=False)
    await host.start()

    # Create vDC
    vdc = host.create_vdc(name="testVdc", model="testModel", model_uid="testmodel")
    print("Created vDC:", vdc.dsuid)

    # Connect as vdSM client
    reader, writer = await asyncio.open_connection("127.0.0.1", host.port)

    # Send Hello
    hello = pb.Message()
    hello.type = pb.VDSM_REQUEST_HELLO
    hello.message_id = 1
    hello.vdsm_request_hello.dSUID = "TESTVDMSUID"
    hello.vdsm_request_hello.api_version = 3
    await send_message(writer, hello)

    # Read Hello response
    resp = await read_message(reader)
    print("RECV (hello resp):", resp)

    # Build GetProperty request for name and model
    getp = pb.Message()
    getp.type = pb.VDSM_REQUEST_GET_PROPERTY
    getp.message_id = 2
    getp.vdsm_request_get_property.dSUID = vdc.dsuid

    # add query elements for 'name' and 'model'
    q_name = pb.PropertyElement()
    q_name.name = "name"
    q_name.elements.add().name = ""  # terminate

    q_model = pb.PropertyElement()
    q_model.name = "model"
    q_model.elements.add().name = ""

    getp.vdsm_request_get_property.query.extend([q_name, q_model])

    await send_message(writer, getp)

    # Read property response
    prop_resp = await read_message(reader)
    print("RECV (get prop resp):", prop_resp)

    # Cleanup
    writer.close()
    await writer.wait_closed()
    await host.stop()


if __name__ == "__main__":
    asyncio.run(run_test())
