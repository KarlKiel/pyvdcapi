"""Simple vdSM test client to handshake with the vDC host.

Connects to localhost:8444, sends a vdsm_RequestHello, prints received
messages, then remains idle to allow the host inactivity watcher to close
the connection (expected ~60s).
"""

import asyncio
import struct
import random
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from pyvdcapi.network import genericVDC_pb2 as pb  # noqa: E402

MESSAGE_LENGTH_FORMAT = "!H"


async def run_client(host="127.0.0.1", port=8444):
    logging.basicConfig(level=logging.INFO)
    reader, writer = await asyncio.open_connection(host, port)
    peer = writer.get_extra_info("peername")
    print(f"Connected to {peer}")

    # Build Hello message (use message.vdsm_request_hello submessage)
    msg = pb.Message()
    msg.message_id = random.getrandbits(31)
    # Fill Hello submessage
    msg.vdsm_request_hello.dSUID = "test-client-0001"
    try:
        msg.vdsm_request_hello.api_version = 1
    except Exception:
        pass

    # Serialize and send with 2-byte length prefix
    body = msg.SerializeToString()
    length = struct.pack(MESSAGE_LENGTH_FORMAT, len(body))
    writer.write(length + body)
    await writer.drain()
    print(f"Sent Hello (message_id={msg.message_id})")

    try:
        while True:
            # Read 2-byte length
            length_bytes = await reader.readexactly(2)
            msg_len = struct.unpack(MESSAGE_LENGTH_FORMAT, length_bytes)[0]
            data = await reader.readexactly(msg_len)
            m = pb.Message()
            m.ParseFromString(data)
            print("RECV:", m)
    except asyncio.IncompleteReadError:
        print("Connection closed by server")
    except Exception as e:
        print("Client error:", e)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(run_client())
