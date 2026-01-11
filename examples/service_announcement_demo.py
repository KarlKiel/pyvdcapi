"""
Service Announcement Demo

Demonstrates how to enable mDNS/DNS-SD service announcement for vDC host auto-discovery.

This shows:
1. Creating a vDC host with service announcement enabled
2. Adding devices to the host
3. Starting the host with auto-discovery
4. vdSMs can now discover the host via mDNS

Requirements:
    pip install zeroconf

For Avahi (Linux only, requires root):
    # Ensure avahi-daemon is running
    sudo systemctl status avahi-daemon
    
    # Run with use_avahi=True
"""

import asyncio
import logging
import sys

# Add parent directory to path for imports
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyvdcapi.entities import VdcHost
from pyvdcapi.core.constants import DSGroup, DSChannelType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Run vDC host with service announcement."""
    
    print("=" * 70)
    print("vDC Host with Service Announcement Demo")
    print("=" * 70)
    print()
    
    # Create vDC host with service announcement enabled
    # Use zeroconf (cross-platform) by default
    # Set use_avahi=True on Linux for native Avahi daemon
    host = VdcHost(
        name="Demo Smart Home Hub",
        port=8444,
        mac_address="aa:bb:cc:dd:ee:ff",
        vendor_id="DemoVendor",
        model="Smart Hub Pro",
        model_uid="smart-hub-pro",
        model_version="1.0",
        persistence_file="demo_announced_config.yaml",
        announce_service=True,  # Enable service announcement
        use_avahi=False  # Use zeroconf (set to True for Avahi on Linux)
    )
    
    print(f"✓ Created vDC host: {host._common_props.get_name()}")
    print(f"  dSUID: {host.dsuid}")
    print(f"  Port: {host.port}")
    print(f"  Service announcement: {'Enabled (zeroconf)' if not host._service_announcer else 'Enabled'}")
    print()
    
    # Create a lighting vDC
    light_vdc = host.create_vdc(
        name="Demo Light Controller",
        model="Generic Light vDC"
    )
    print(f"✓ Created vDC: {light_vdc._common_props.get_name()}")
    print(f"  dSUID: {light_vdc.dsuid}")
    print()
    
    # Add some devices
    dimmer = light_vdc.create_vdsd(
        name="Living Room Dimmer",
        model="Dimmer 1ch",
        primary_group=DSGroup.YELLOW
    )
    dimmer.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        channel_id="brightness",
        resolution=1.0
    )
    print(f"✓ Created device: {dimmer._common_props.get_name()}")
    print(f"  dSUID: {dimmer.dsuid}")
    print()
    
    switch = light_vdc.create_vdsd(
        name="Kitchen Light Switch",
        model="Switch 1ch",
        primary_group=DSGroup.YELLOW
    )
    switch.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        channel_id="brightness",
        resolution=1.0
    )
    print(f"✓ Created device: {switch._common_props.get_name()}")
    print(f"  dSUID: {switch.dsuid}")
    print()
    
    # Start the host
    print("=" * 70)
    print("Starting vDC host...")
    print("=" * 70)
    print()
    
    await host.start()
    
    print()
    print("=" * 70)
    print("vDC Host is now running and discoverable!")
    print("=" * 70)
    print()
    print("Service Details:")
    print(f"  Service Type: _ds-vdc._tcp")
    print(f"  Service Name: digitalSTROM vDC host on {host._service_announcer._service_name if host._service_announcer else 'N/A'}")
    print(f"  Port: {host.port}")
    print()
    print("How to discover this host:")
    print()
    print("  1. Using avahi-browse (Linux):")
    print("     avahi-browse -r _ds-vdc._tcp")
    print()
    print("  2. Using dns-sd (macOS/Windows):")
    print("     dns-sd -B _ds-vdc._tcp")
    print()
    print("  3. From Python (zeroconf):")
    print("     from zeroconf import Zeroconf, ServiceBrowser")
    print("     zeroconf = Zeroconf()")
    print("     browser = ServiceBrowser(zeroconf, '_ds-vdc._tcp.local.', MyListener())")
    print()
    print("  4. vdSM will automatically discover and connect")
    print()
    print("=" * 70)
    print("Press Ctrl+C to stop")
    print("=" * 70)
    print()
    
    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print()
        print("Shutting down...")
        
    finally:
        await host.stop()
        print("✓ vDC host stopped")
        print("✓ Service announcement stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
