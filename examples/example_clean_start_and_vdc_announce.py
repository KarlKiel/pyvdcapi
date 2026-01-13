"""
Interactive example to create and start a vDC host with service announcement.

This is a copy of `example_clean_start.py` named `example_clean_start_and_vdc_announce.py`.
It creates a `VdcHost`, enables service announcement (zeroconf/Avahi) and keeps
the host running until interrupted.

Usage:
    python3 examples/example_clean_start_and_vdc_announce.py

Requirements:
    pip install zeroconf
"""

import asyncio
import logging
import sys
import uuid
from pathlib import Path
import socket
import os
import random

# Allow running from repository examples/ folder
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyvdcapi.entities import VdcHost


def ask(prompt: str, default: str = "") -> str:
    """Prompt helper which always asks the user for input.

    If a default is provided and the user enters nothing, the default is used.
    """
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

    # Determine a sensible host name for service announcement (use FQDN)
    service_host_name = socket.getfqdn()

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
        service_host_name=service_host_name,
    )

    print(f"Created vDC host: {host._common_props.get_name()}")
    print(f"  dSUID: {host.dsuid}")
    print(f"  Port: {host.port}")
    print("Starting host and announcing service...")

    await host.start()

    print("Host is running and discoverable via mDNS/DNS-SD.")
    print("Press Ctrl+C to stop.")

    # Wait for vdSM handshake (Hello exchange) to complete
    print("Waiting for vdSM to connect and complete handshake...")
    while not host.is_connected():
        await asyncio.sleep(0.5)

    # Offer to create or select a vDC to announce
    existing = host.get_all_vdcs()
    if existing:
        print("Existing vDCs:")
        for i, v in enumerate(existing):
            try:
                name = v._common_props.get_name()
            except Exception:
                name = getattr(v, 'name', '<unknown>')
            print(f"  {i+1}. {name} - {v.dsuid}")

    create_new = ask("Create a new vDC to announce? (y/N)", "N").lower() in ("y", "yes")
    if create_new:
        vdc_name = ask("vDC name", "Demo vDC")
        vdc_model = ask("vDC model", "DemoModel")
        vdc = host.create_vdc(name=vdc_name, model=vdc_model)
        print(f"Created vDC: {vdc.dsuid}")
    else:
        # Allow selecting existing by index or entering a dSUID
        if existing:
            default_dsuid = existing[0].dsuid
        else:
            default_dsuid = ""

        # Keep prompting until a valid vDC is chosen or user aborts
        vdc = None
        while vdc is None:
            chosen = ask("Enter vDC dSUID to announce (or index e.g. 1)", default_dsuid)
            if not chosen:
                print("No dSUID provided — aborting announce step.")
                break

            # If user provided an index number, map to existing list
            if chosen.isdigit() and existing:
                idx = int(chosen) - 1
                if 0 <= idx < len(existing):
                    vdc = existing[idx]
                else:
                    print(f"Index {chosen} out of range")
                    vdc = None
                    continue
            else:
                vdc = host.get_vdc(chosen)

            if vdc is None:
                print(f"vDC with dSUID or index '{chosen}' not found.")
                # Loop to ask again (interactive only)
                continue

    # Send announce message if we have a vDC
    def _is_valid_dsuid(dsuid: str) -> bool:
        if not dsuid or not isinstance(dsuid, str):
            return False
        # Reject obviously-empty or zero-only dSUIDs
        if all(c == '0' for c in dsuid):
            return False
        return True

    if vdc:
        if not _is_valid_dsuid(vdc.dsuid):
            print(f"Refusing to announce vDC with invalid dSUID: {vdc.dsuid}")
        elif host._session and host._session.writer:
            from pyvdcapi.network.tcp_server import TCPServer

            # Create announce message with explicit message_id 0 (notification)
            message = vdc.announce_to_vdsm(message_id=0)
            try:
                await TCPServer.send_message(host._session.writer, message)
                print(f"Sent announcevdc for vDC {vdc.dsuid}")
            except Exception as e:
                print(f"Failed to send announce message: {e}")
        else:
            print("No active vdSM session writer available — cannot send announce message")

    # Keep running until interrupted
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
