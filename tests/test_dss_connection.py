"""
Test vDC Host with Real DSS Connection

Creates a vDC host with service announcement and waits for DSS to connect.
This tests the complete integration with a real digitalSTROM server (DSS).
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add repository root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyvdcapi import VdcHost  # noqa: E402
from pyvdcapi.core.constants import DSGroup, DSChannelType  # noqa: E402

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main():
    """Create vDC host with demo devices and wait for DSS connection."""

    print("\n" + "=" * 70)
    print("vDC Host - DSS Connection Test")
    print("=" * 70 + "\n")

    # Create vDC host with service announcement
    host = VdcHost(
        name="PyVDC Test Host",
        port=8440,
        mac_address="00:11:22:33:44:55",
        vendor_id="karlkiel.pyvdcapi",
        model="Python vDC Host",
        model_uid="pyvdcapi-test",
        model_version="1.0.0",
        vendorName="Karl Kiel",
        persistence_file="dss_test_config.yaml",
        announce_service=True,  # Enable mDNS/DNS-SD announcement
        use_avahi=False,  # Use zeroconf (cross-platform)
    )

    print(f"✓ Created vDC Host: {host.name}")
    print("  Port: 8440")
    print("  Service announcement: ENABLED")
    print(f"  dSUID: {host.dsuid}\n")

    # Create a virtual device controller (vDC)
    vdc = host.create_vdc(
        name="Demo Light Controller",
        model="Virtual Light Controller",
        model_uid="demo-light-controller",
        model_version="1.0",
    )

    print(f"✓ Created vDC: {vdc.name}")
    print(f"  dSUID: {vdc.dsuid}\n")

    # Create demo devices
    devices = []

    # 1. Dimmable light
    light1 = vdc.create_vdsd(name="Living Room Light", model="Dimmable LED", primary_group=DSGroup.YELLOW)  # Light
    light1.add_output_channel(
        output_id=0, channel_type=DSChannelType.BRIGHTNESS, min_value=0.0, max_value=100.0, initial_value=50.0
    )
    devices.append(light1)

    # 2. On/Off light
    light2 = vdc.create_vdsd(name="Kitchen Light", model="On/Off Switch", primary_group=DSGroup.YELLOW)
    light2.add_output_channel(
        output_id=0, channel_type=DSChannelType.BRIGHTNESS, min_value=0.0, max_value=100.0, initial_value=0.0
    )
    devices.append(light2)

    # 3. Temperature sensor
    sensor = vdc.create_vdsd(
        name="Room Temperature Sensor", model="Temperature Sensor", primary_group=DSGroup.BLACK  # Joker
    )
    sensor.add_sensor(
        sensor_id=0,
        sensor_type="temperature",
        sensor_usage="room",
        min_value=-20.0,
        max_value=50.0,
        resolution=0.1,
        initial_value=21.5,
    )
    devices.append(sensor)

    # 4. Button input
    button = vdc.create_vdsd(name="Wall Switch", model="Button Input", primary_group=DSGroup.BLACK)
    button.add_button(
        button_id=0,
        button_type=1,  # Single button
        element=0,
        group=DSGroup.YELLOW,  # Controls lights
        mode=0,  # Standard mode
    )
    devices.append(button)

    print(f"✓ Created {len(devices)} demo devices:")
    for i, device in enumerate(devices, 1):
        print(f"  {i}. {device.name} (dSUID: {device.dsuid})")

    print("\n" + "-" * 70)
    print("Starting vDC host...")
    print("-" * 70 + "\n")

    # Start the vDC host
    await host.start()

    print("✓ vDC Host started successfully!")
    print("✓ Listening on port 8440")
    print(f"✓ Service announced via mDNS as: {host.name}._ds-vdc._tcp.local.")
    print("\n" + "=" * 70)
    print("Waiting for DSS connection...")
    print("=" * 70)
    print("\nThe DSS should discover this vDC host automatically.")
    print("You can also manually add it in the DSS web interface:")
    print("  - Host: <this-computer-ip>")
    print("  - Port: 8440")
    print("\nPress Ctrl+C to stop\n")

    # Keep running and monitor for connections
    try:
        while True:
            await asyncio.sleep(1)

            # Check if DSS has connected
            if host.tcp_server and host.tcp_server.active_connections > 0:
                if not hasattr(main, "connection_announced"):
                    print("\n" + "=" * 70)
                    print("🎉 DSS CONNECTED!")
                    print("=" * 70)
                    print(f"Active connections: {host.tcp_server.active_connections}")
                    print("\nMonitoring connection... (Press Ctrl+C to stop)")
                    main.connection_announced = True

    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("Shutting down...")
        print("=" * 70 + "\n")

        await host.stop()

        print("✓ vDC Host stopped")
        print("✓ Service announcement stopped")
        print("\nTest complete!\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}\n")
        sys.exit(1)
