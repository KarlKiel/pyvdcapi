"""Run a headless vDC host (no interactive prompts) for testing.

Creates a VdcHost with sensible defaults and starts it.
"""
import asyncio
import logging
from pathlib import Path
import uuid

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyvdcapi.entities import VdcHost

async def main():
    logging.basicConfig(level=logging.INFO)

    # Minimal fixed configuration
    node = uuid.getnode()
    mac = ":".join([f"{(node >> ele) & 0xff:02x}" for ele in range(40, -1, -8)])

    host = VdcHost(
        name="Headless Test Host",
        port=8444,
        mac_address=mac,
        vendor_id="TestVendor",
        model="HeadlessModel",
        model_uid="headless",
        model_version="0.1",
        persistence_file="headless_config.yaml",
        announce_service=False,
    )

    await host.start()

    # Keep running until killed
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await host.stop()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
