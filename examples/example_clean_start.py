"""
Interactive example to create and start a vDC host with service announcement.

Prompts the user for the minimal set of parameters required to instantiate
`VdcHost`, starts the host with service announcement enabled (zeroconf by
default) and keeps it running until interrupted.

Usage:
    python3 examples/example_clean_start.py

Requirements:
    pip install zeroconf
"""

import asyncio
import logging
import sys
import uuid
from pathlib import Path

# Allow running from repository examples/ folder
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyvdcapi.entities import VdcHost


def ask(prompt: str, default: str = "") -> str:
    if default:
        resp = input(f"{prompt} [{default}]: ")
        return resp.strip() or default
    return input(f"{prompt}: ").strip()


async def main():
    logging.basicConfig(level=logging.INFO)

    print("Create a vDC Host — minimal interactive setup")
    # Use fixed name and vendor/model metadata per request
    name = "vDC Test Server"
    port_str = ask("Port", "8444")
    try:
        port = int(port_str)
    except Exception:
        port = 8444

    # Determine host MAC address automatically
    node = uuid.getnode()
    mac = ":".join([f"{(node >> ele) & 0xff:02x}" for ele in range(40, -1, -8)])
    print(f"Detected MAC address: {mac}")
    vendor = "KarlKiel"
    model = "TestServer"
    model_uid = "clean_script"
    model_version = "0.8B"
    persistence = ask("Persistence file", "example_announced_config.yaml")

    use_avahi_resp = ask("Use Avahi (Linux only)? (y/N)", "N").lower()
    use_avahi = use_avahi_resp in ("y", "yes")

    # Create the host with service announcement enabled
    host = VdcHost(
        name=name,
        port=port,
        mac_address=mac,
        vendor_id=vendor,
        model=model,
        model_uid=model_uid,
        model_version=model_version,
        persistence_file=persistence,
        announce_service=True,
        use_avahi=use_avahi,
    )

    print(f"Created vDC host: {host._common_props.get_name()}")
    print(f"  dSUID: {host.dsuid}")
    print(f"  Port: {host.port}")
    print("Starting host and announcing service...")

    await host.start()

    print("Host is running and discoverable via mDNS/DNS-SD.")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await host.stop()
        print("Stopped.")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting...")
