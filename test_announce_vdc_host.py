"""
Minimal test script to announce a vDC host using ServiceAnnouncer.
"""

import asyncio
import logging
from pyvdcapi.network.service_announcement import ServiceAnnouncer

logging.basicConfig(level=logging.INFO)

async def main():
    announcer = ServiceAnnouncer(
        port=8444,  # Example port
        dsuid="test-dsuid-1234",  # Example dSUID
        host_name="test-vdc-host",  # Example host name
        use_avahi=False  # Use zeroconf (cross-platform)
    )
    print("Starting vDC host service announcement...")
    started = await announcer.start()
    if started:
        print("✓ Service announcement started. Press Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping service announcement...")
    else:
        print("✗ Failed to start service announcement.")
    await announcer.stop()
    print("✓ Service announcement stopped.")

if __name__ == "__main__":
    asyncio.run(main())
