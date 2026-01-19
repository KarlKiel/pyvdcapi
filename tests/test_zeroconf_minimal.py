"""
Minimal test to check AsyncZeroconf functionality
"""

import asyncio
import logging
import pytest
from zeroconf import ServiceInfo
from zeroconf.asyncio import AsyncZeroconf
import socket
import ipaddress
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_zeroconf():
    """Test creating and registering a service with AsyncZeroconf."""

    try:
        logger.info("Creating AsyncZeroconf instance...")
        aiozc = AsyncZeroconf()

        # Get local IP
        logger.info("Getting local IP address...")
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        logger.info(f"Local IP: {local_ip}")

        ip_obj = ipaddress.IPv4Address(local_ip)
        addresses = [ip_obj.packed]

        # Create service info
        logger.info("Creating ServiceInfo...")
        service_info = ServiceInfo(
            type_="_ds-vdc._tcp.local.",
            name="Test Service._ds-vdc._tcp.local.",
            port=8440,
            addresses=addresses,
            properties={},
            server=f"{socket.gethostname()}.local.",
        )

        logger.info("Registering service...")
        await aiozc.async_register_service(service_info)
        logger.info("✓ Service registered successfully!")

        logger.info("Waiting 5 seconds...")
        await asyncio.sleep(5)

        logger.info("Unregistering service...")
        await aiozc.async_unregister_service(service_info)

        logger.info("Closing AsyncZeroconf...")
        await aiozc.async_close()
        logger.info("✓ Test completed successfully!")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_zeroconf())
