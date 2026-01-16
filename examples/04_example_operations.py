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
import os
import argparse
import subprocess
import importlib

# allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))


def ask(prompt: str, default: str = "") -> str:
    if default:
        resp = input(f"{prompt} [{default}]: ")
        return resp.strip() or default
    return input(f"{prompt}: ").strip()


def ask_required(prompt: str) -> str:
    """Prompt until a non-empty value is provided."""
    while True:
        val = ask(prompt)
        if val:
            return val
        print("This field is required.")


def ensure_requirements() -> None:
    """Check for required third-party packages and offer to install them.

    Packages checked: protobuf (module `google`), pyyaml (`yaml`), zeroconf (`zeroconf`).
    This function prompts the user to confirm installation when missing and
    attempts to install into the current Python environment using `pip`.
    """
    # mapping pip package -> top-level module name
    checks = {
        'protobuf': 'google',
        'pyyaml': 'yaml',
        'zeroconf': 'zeroconf',
    }

    missing = []
    for pkg, mod in checks.items():
        try:
            importlib.import_module(mod)
        except Exception:
            missing.append(pkg)

    if not missing:
        return

    print("Missing required packages: " + ", ".join(missing))
    resp = ask("Install missing packages now? (y/N)", "N").lower()
    if resp not in ("y", "yes", ""):
        print("Skipping installation. The script may fail if required packages are absent.")
        return

    cmd = [sys.executable, "-m", "pip", "install"] + missing
    print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        print(f"Installation failed: {e}")
        print("Please install the packages manually and re-run the script.")
        sys.exit(1)

    # Try importing installed modules to ensure availability
    for pkg in missing:
        mod = checks[pkg]
        try:
            importlib.import_module(mod)
        except Exception:
            print(f"Unable to import {mod} after installation. Please verify environment.")
            sys.exit(1)


async def main():
    logging.basicConfig(level=logging.INFO)

    # Parse CLI args / environment for persistence selection
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--persistence', '-p', help='Persistence YAML file to use')
    parser.add_argument('--force-interactive', action='store_true', help='Force interactive prompts even if persistence exists')
    args, _ = parser.parse_known_args()

    # Compute MAC and service hostname early
    node = uuid.getnode()
    mac = ":".join([f"{(node >> ele) & 0xff:02x}" for ele in range(40, -1, -8)])
    service_host_name = socket.getfqdn()

    # Determine persistence file: CLI > ENV > prompt
    persistence = args.persistence or os.getenv('PERSIST')
    if not persistence:
        persistence = ask("Persistence file", "example_announced_config.yaml")
    ppath = Path(persistence)
    skip_interactive_creation = False
    persisted_host_cfg = {}
    if ppath.exists() and not args.force_interactive:
        print(f"Found existing persistence file: {persistence} — recreating host from it without prompts")
        try:
            from pyvdcapi.persistence.yaml_store import YAMLPersistence
            pers = YAMLPersistence(persistence)
            persisted_host_cfg = pers.get_vdc_host() or {}
            skip_interactive_creation = True
        except Exception as e:
            print(f"Warning: failed to inspect persistence file: {e}")

    # If no persistence file, perform interactive prompts
    if not skip_interactive_creation:
        print("Create a vDC Host — minimal interactive setup")
        port_str = ask("Port", "8444")
        try:
            port = int(port_str)
        except Exception:
            port = 8444

        print(f"Detected MAC address: {mac}")

        name = "vDC Test Server"
        vendor = "KarlKiel"
        model = "TestServer"
        model_uid = "clean_script"
        model_version = "0.8B"

        use_avahi_resp = ask("Use Avahi (Linux only)? (y/N)", "N").lower()
        use_avahi = use_avahi_resp in ("y", "yes")

        # Ensure third-party requirements are available before importing package
        ensure_requirements()
    else:
        # Use persisted values where available; fall back to sensible defaults
        port = int(persisted_host_cfg.get('port', 8444))
        name = persisted_host_cfg.get('name', 'vDC Test Server')
        vendor = persisted_host_cfg.get('vendor_id', persisted_host_cfg.get('vendor', 'KarlKiel'))
        model = persisted_host_cfg.get('model', 'TestServer')
        model_uid = persisted_host_cfg.get('model_uid', persisted_host_cfg.get('modelUID', 'clean_script'))
        model_version = persisted_host_cfg.get('model_version', persisted_host_cfg.get('modelVersion', '0.8B'))
        use_avahi = persisted_host_cfg.get('use_avahi', False)
        # Ensure requirements so imports succeed
        ensure_requirements()

    # If a persistence file already exists, inspect it and use its
    # configured vDC/vdSD entries for automatic announces after Hello.
    skip_interactive_creation = False
    ppath = Path(persistence)
    if ppath.exists():
        print(f"Found existing persistence file: {persistence}")
        try:
            # Import lazily to avoid requiring package before ensure_requirements
            from pyvdcapi.persistence.yaml_store import YAMLPersistence

            pers = YAMLPersistence(persistence)
            vdcs = pers.get_all_vdcs()
            if vdcs:
                print(f"  Persisted vDCs: {len(vdcs)}")
                for dsuid, cfg in vdcs.items():
                    name = cfg.get('name') or cfg.get('model') or ''
                    print(f"    {dsuid}: {name}")
                    vdsds = pers.get_vdsds_for_vdc(dsuid)
                    if vdsds:
                        print(f"      Devices: {len(vdsds)}")
                        for ddsuid, dcfg in vdsds.items():
                            dname = dcfg.get('name') or dcfg.get('model') or ''
                            print(f"        {ddsuid}: {dname}")
            else:
                print("  No persisted vDCs found in file.")

            # When a persistence file exists, use its config and avoid
            # creating new vDCs interactively by default.
            skip_interactive_creation = True
        except Exception as e:
            print(f"Warning: failed to inspect persistence file: {e}")

    from pyvdcapi.entities import VdcHost
    from pyvdcapi.core.constants import DSGroup

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
        print(f"No vdSM connected after {int(wait_seconds)}s — you can still create a vDC, but announces will be queued until a vdSM connects.")

    # Optionally create a vDC and announce it (interactive)
    if skip_interactive_creation:
        print("Persistence present — skipping interactive vDC creation; persisted vDCs will be announced on handshake.")
        create_resp = "n"
    else:
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

    # Optionally create a vdSD (device) asking only for required fields
    if skip_interactive_creation:
        print("Persistence present — skipping interactive device creation; persisted devices will be announced on handshake.")
        create_device_resp = "n"
    else:
        create_device_resp = ask("Create a new vdSD (device) now? (y/N)", "N").lower()

    if create_device_resp in ("y", "yes"):
        # Ensure we have a vDC to attach the device to
        vdcs = host.get_all_vdcs()
        chosen_vdc = None
        if not vdcs:
            create_parent = ask("No vDCs exist. Create a vDC to hold devices? (y/N)", "N").lower()
            if create_parent in ("y", "yes"):
                vdc_name = ask_required("vDC name")
                vdc_model = ask_required("vDC model")
                chosen_vdc = host.create_vdc(name=vdc_name, model=vdc_model)
                print(f"Created vDC: {chosen_vdc.dsuid}")
            else:
                print("Cannot create device without a vDC. Skipping device creation.")
        else:
            if len(vdcs) == 1:
                chosen_vdc = vdcs[0]
            else:
                print("Available vDCs:")
                for i, v in enumerate(vdcs):
                    try:
                        display_name = v._common_props.get_name()
                    except Exception:
                        display_name = str(v)
                    print(f"  {i}: {display_name} ({v.dsuid})")
                idx_str = ask("Select vDC index", "0")
                try:
                    idx = int(idx_str)
                    chosen_vdc = vdcs[idx]
                except Exception:
                    chosen_vdc = vdcs[0]

        if chosen_vdc:
            # Required vdSD fields: name, model, primary_group
            device_name = ask_required("vdSD name")
            device_model = ask_required("vdSD model")

            # Show available DSGroup values
            print("Select primary_group from DSGroup (enter number):")
            for g in DSGroup:
                print(f"  {g.value}: {g.name}")
            primary_group = None
            while primary_group is None:
                grp = ask("Primary group (number)")
                try:
                    grp_i = int(grp)
                    if any(g.value == grp_i for g in DSGroup):
                        primary_group = grp_i
                    else:
                        print("Invalid group number, try again.")
                except Exception:
                    print("Invalid input, enter the numeric group value.")

            # Create the device with only required parameters
            vdsd = chosen_vdc.create_vdsd(name=device_name, model=device_model, primary_group=primary_group)
            print(f"Created vdSD: {vdsd.dsuid}")

            # Try to announce device if session active
            if host._session and host._session.writer:
                try:
                    from pyvdcapi.network.tcp_server import TCPServer
                    msg = vdsd.announce_to_vdsm()
                    await TCPServer.send_message(host._session.writer, msg)
                    print(f"Sent announcevdsd for vdSD {vdsd.dsuid}")
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


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting...")
