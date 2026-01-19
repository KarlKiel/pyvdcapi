"""
Interactive example to create, start and announce a vDC host.

This is a simple, copy-safe example that starts a `VdcHost`, announces
its service via zeroconf (or Avahi) and optionally creates a vDC to
announce to a connected vdSM.

Usage:
    python3 examples/example_clean_start_and_vdc_announce.py

Requires: zeroconf
"""

import asyncio
import logging
import sys
import uuid
from pathlib import Path
import socket

# allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyvdcapi.entities import VdcHost  # noqa: E402


def ask(prompt: str, default: str = "") -> str:
    if default:
        resp = input(f"{prompt} [{default}]: ")
        return resp.strip() or default
    return input(f"{prompt}: ").strip()


async def main():
    logging.basicConfig(level=logging.INFO)

    print("Create a vDC Host — minimal interactive setup")
    port_str = ask("Port", "8444")
    try:
        port = int(port_str)
    except Exception:
        port = 8444

    node = uuid.getnode()
    mac = ":".join([f"{(node >> ele) & 0xff:02x}" for ele in range(40, -1, -8)])
    print(f"Detected MAC address: {mac}")

    name = "vDC Test Server"
    vendor = "KarlKiel"
    model = "TestServer"
    model_uid = "clean_script"
    model_version = "0.8B"

    persistence = ask("Persistence file", "example_announced_config.yaml")
    use_avahi_resp = ask("Use Avahi (Linux only)? (y/N)", "N").lower()
    use_avahi = use_avahi_resp in ("y", "yes")

    service_host_name = socket.getfqdn()

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
        service_host_name=service_host_name,
    )

    print(f"Created vDC host: {host._common_props.get_name()}")
    print(f"  dSUID: {host.dsuid}")
    print(f"  Port: {host.port}")
    print("Starting host and announcing service...")

    await host.start()

    # Wait for vdSM handshake to complete before offering to create a vDC
    # Some vdSMs connect asynchronously; wait up to 60s for a session
    # to become active so we can send announces immediately.
    wait_seconds = 60.0
    waited = 0.0
    interval = 0.5
    if not host.is_connected():
        print(f"Waiting up to {int(wait_seconds)}s for vdSM to complete handshake...")
    while waited < wait_seconds and not host.is_connected():
        await asyncio.sleep(interval)
        waited += interval

    if host.is_connected():
        print("vdSM handshake complete — ready to announce vDCs.")
    else:
        print(f"No vdSM connected after {int(wait_seconds)}s.")
        print("You can still create a vDC, but announces will be queued until a vdSM connects.")

    # Optionally create a vDC and announce it (interactive)
    create_resp = ask("Create a new vDC to announce? (y/N)", "N").lower()
    if create_resp in ("y", "yes"):
        vdc_name = ask("vDC name", "Demo vDC")
        vdc_model = ask("vDC model", "DemoModel")
        vdc = host.create_vdc(name=vdc_name, model=vdc_model)
        print(f"Created vDC: {vdc.dsuid}")

        # Try to send announce if session active
        if host._session and host._session.writer:
            try:
                from pyvdcapi.network.tcp_server import TCPServer

                msg = vdc.announce_to_vdsm()
                await TCPServer.send_message(host._session.writer, msg)
                print(f"Sent announcevdc for vDC {vdc.dsuid}")
            except Exception as e:
                print(f"Failed to send announce message: {e}")
        else:
            print("No active vdSM session writer available — cannot send announce message")

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


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting...")
