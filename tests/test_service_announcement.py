"""
Quick test to verify service announcement functionality.

Tests both zeroconf and basic configuration.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyvdcapi.network.service_announcement import ServiceAnnouncer

def test_announcer_init():
    """Test that ServiceAnnouncer can be initialized."""
    print("Testing ServiceAnnouncer initialization...")
    
    # Test basic initialization
    announcer = ServiceAnnouncer(
        port=8444,
        host_name="test-host",
        use_avahi=False
    )
    
    assert announcer.port == 8444
    assert announcer.host_name == "test-host"
    assert announcer.use_avahi == False
    assert announcer._service_type == "_ds-vdc._tcp.local."
    assert "test-host" in announcer._service_name
    assert not announcer.is_running()
    
    print("✓ ServiceAnnouncer initialized correctly")


def test_announcer_properties():
    """Test ServiceAnnouncer properties."""
    print("Testing ServiceAnnouncer properties...")
    
    announcer = ServiceAnnouncer(
        port=9999,
        host_name="custom-vdc",
        use_avahi=False
    )
    
    assert announcer.port == 9999
    assert announcer.host_name == "custom-vdc"
    assert announcer._service_name == "digitalSTROM vDC host on custom-vdc"
    
    print("✓ Properties set correctly")


def test_zeroconf_availability():
    """Test if zeroconf library is available."""
    print("Testing zeroconf availability...")
    
    try:
        import zeroconf
        print("✓ zeroconf library is available")
        return True
    except ImportError:
        print("⚠ zeroconf library not installed (optional)")
        print("  Install with: pip install zeroconf")
        return False


def test_start_stop_dry_run():
    """Test start/stop without actually announcing (dry run)."""
    print("Testing start/stop (dry run)...")
    
    announcer = ServiceAnnouncer(
        port=8444,
        host_name="test-host",
        use_avahi=False
    )
    
    # Should be not running
    assert not announcer.is_running()
    
    # Try to start (may fail if zeroconf not installed, which is OK)
    result = announcer.start()
    
    if result:
        print("✓ Announcer started successfully")
        assert announcer.is_running()
        
        # Stop
        announcer.stop()
        assert not announcer.is_running()
        print("✓ Announcer stopped successfully")
    else:
        print("⚠ Announcer failed to start (expected if zeroconf not installed)")
        assert not announcer.is_running()


def main():
    print("=" * 70)
    print("Service Announcement Module Test")
    print("=" * 70)
    print()
    
    try:
        test_announcer_init()
        test_announcer_properties()
        has_zeroconf = test_zeroconf_availability()
        test_start_stop_dry_run()
        
        print()
        print("=" * 70)
        print("✓ All tests passed!")
        print("=" * 70)
        
        if not has_zeroconf:
            print()
            print("Note: Install zeroconf for full functionality:")
            print("  pip install zeroconf")
        
        return 0
    
    except AssertionError as e:
        print()
        print("=" * 70)
        print(f"✗ Test failed: {e}")
        print("=" * 70)
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
    sys.exit(main())
