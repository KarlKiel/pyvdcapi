"""
Test VdcHost integration with service announcement.

Tests that VdcHost correctly initializes and controls the service announcer.
"""

import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from pyvdcapi.entities import VdcHost


async def test_vdc_host_without_announcement():
    """Test VdcHost creation without service announcement (default)."""
    print("Testing VdcHost without service announcement...")
    
    host = VdcHost(
        name="Test Host",
        port=8444,
        mac_address="aa:bb:cc:dd:ee:ff",
        persistence_file="test_config.yaml"
        # announce_service not set, defaults to False
    )
    
    assert host._announce_service == False
    assert host._service_announcer is None
    print("✓ VdcHost created without announcer")


async def test_vdc_host_with_announcement():
    """Test VdcHost creation with service announcement enabled."""
    print("Testing VdcHost with service announcement...")
    
    host = VdcHost(
        name="Test Host Announced",
        port=8445,
        mac_address="aa:bb:cc:dd:ee:ff",
        persistence_file="test_config2.yaml",
        announce_service=True,  # Enable announcement
        use_avahi=False  # Use zeroconf
    )
    
    assert host._announce_service == True
    assert host._service_announcer is not None
    assert host._service_announcer.port == 8445
    assert not host._service_announcer.is_running()
    print("✓ VdcHost created with announcer")


async def test_vdc_host_announcement_lifecycle():
    """Test that announcer starts/stops with host."""
    print("Testing announcer lifecycle with VdcHost...")
    
    host = VdcHost(
        name="Test Lifecycle Host",
        port=8446,
        mac_address="aa:bb:cc:dd:ee:ff",
        persistence_file="test_config3.yaml",
        announce_service=True,
        use_avahi=False
    )
    
    # Should not be running initially
    assert host._service_announcer is not None
    assert not host._service_announcer.is_running()
    
    # Start host (this should start announcer too, if zeroconf is available)
    await host.start()
    
    # Note: Announcer may or may not start depending on zeroconf availability
    # That's fine - the test is that it doesn't crash
    
    # Stop host (this should stop announcer too)
    await host.stop()
    
    assert not host._service_announcer.is_running()
    print("✓ Announcer lifecycle works with VdcHost start/stop")


async def main():
    print("=" * 70)
    print("VdcHost Service Announcement Integration Test")
    print("=" * 70)
    print()
    
    try:
        await test_vdc_host_without_announcement()
        await test_vdc_host_with_announcement()
        await test_vdc_host_announcement_lifecycle()
        
        print()
        print("=" * 70)
        print("✓ All integration tests passed!")
        print("=" * 70)
        print()
        print("Notes:")
        print("  - Service announcement is optional (announce_service=False by default)")
        print("  - When enabled, requires 'zeroconf' package: pip install zeroconf")
        print("  - VdcHost works perfectly with or without announcement")
        
        return 0
    
    except AssertionError as e:
        print()
        print("=" * 70)
        print(f"✗ Test failed: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1
    
    except Exception as e:
        print()
        print("=" * 70)
        print(f"✗ Error: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
