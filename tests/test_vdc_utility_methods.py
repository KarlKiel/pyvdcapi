#!/usr/bin/env python3
"""
Test script to verify the new VdcHost utility methods.

Tests:
- get_vdc(dsuid)
- get_all_vdcs()
- delete_vdc(dsuid)
"""

import asyncio
import sys
import os
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pyvdcapi.entities import VdcHost
from pyvdcapi.core.constants import DSGroup


async def test_vdc_utility_methods():
    """Test the new utility methods."""
    
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config_file = f.name
    
    try:
        print("=" * 60)
        print("Testing VdcHost Utility Methods")
        print("=" * 60)
        
        # Create host
        host = VdcHost(
            name="Test Host",
            port=8444,
            mac_address="AA:BB:CC:DD:EE:FF",
            persistence_file=config_file
        )
        
        # Test 1: get_all_vdcs() when empty
        print("\n✓ Test 1: get_all_vdcs() on empty host")
        all_vdcs = host.get_all_vdcs()
        assert len(all_vdcs) == 0, "Should be empty initially"
        print(f"  Result: {len(all_vdcs)} vDCs (expected 0) ✓")
        
        # Create some vDCs
        print("\n✓ Test 2: Create 3 vDCs")
        vdc1 = host.create_vdc(name="Lights", model="Light Controller")
        vdc2 = host.create_vdc(name="Sensors", model="Sensor Controller")
        vdc3 = host.create_vdc(name="Blinds", model="Blind Controller")
        print(f"  Created vDC1: {vdc1.dsuid}")
        print(f"  Created vDC2: {vdc2.dsuid}")
        print(f"  Created vDC3: {vdc3.dsuid}")
        
        # Test 2: get_all_vdcs() with data
        print("\n✓ Test 3: get_all_vdcs() after creating vDCs")
        all_vdcs = host.get_all_vdcs()
        assert len(all_vdcs) == 3, f"Should have 3 vDCs, got {len(all_vdcs)}"
        print(f"  Result: {len(all_vdcs)} vDCs (expected 3) ✓")
        
        # Test 3: get_vdc() with valid dSUID
        print("\n✓ Test 4: get_vdc() with valid dSUID")
        retrieved = host.get_vdc(vdc1.dsuid)
        assert retrieved is not None, "Should find vDC"
        assert retrieved.dsuid == vdc1.dsuid, "Should return correct vDC"
        print(f"  Retrieved vDC: {retrieved._common_props.get_property('name')} ✓")
        
        # Test 4: get_vdc() with invalid dSUID
        print("\n✓ Test 5: get_vdc() with invalid dSUID")
        retrieved = host.get_vdc("invalid-dsuid-12345")
        assert retrieved is None, "Should return None for invalid dSUID"
        print(f"  Result: None (expected) ✓")
        
        # Add some devices to vdc2 to test cascade delete
        print("\n✓ Test 6: Add devices to vDC2")
        device1 = vdc2.create_vdsd(
            name="Temperature Sensor",
            model="TempSensor",
            primary_group=DSGroup.YELLOW
        )
        device2 = vdc2.create_vdsd(
            name="Humidity Sensor",
            model="HumSensor",
            primary_group=DSGroup.YELLOW
        )
        print(f"  Added device1: {device1.dsuid}")
        print(f"  Added device2: {device2.dsuid}")
        
        # Test 5: delete_vdc() with valid dSUID
        print("\n✓ Test 7: delete_vdc() with valid dSUID (should also delete devices)")
        result = host.delete_vdc(vdc2.dsuid)
        assert result is True, "Should return True on successful delete"
        print(f"  Result: {result} (expected True) ✓")
        
        all_vdcs = host.get_all_vdcs()
        assert len(all_vdcs) == 2, f"Should have 2 vDCs left, got {len(all_vdcs)}"
        print(f"  Remaining vDCs: {len(all_vdcs)} (expected 2) ✓")
        
        retrieved = host.get_vdc(vdc2.dsuid)
        assert retrieved is None, "Deleted vDC should not be found"
        print(f"  Deleted vDC lookup: None (expected) ✓")
        
        # Test 6: delete_vdc() with invalid dSUID
        print("\n✓ Test 8: delete_vdc() with invalid dSUID")
        result = host.delete_vdc("invalid-dsuid-12345")
        assert result is False, "Should return False for invalid dSUID"
        print(f"  Result: {result} (expected False) ✓")
        
        # Test 7: Verify persistence
        print("\n✓ Test 9: Verify persistence was updated")
        # Check that vdc2 is removed from persistence
        vdc2_config = host._persistence.get_vdc(vdc2.dsuid)
        assert vdc2_config is None, "Deleted vDC should not be in persistence"
        print(f"  Deleted vDC in persistence: None (expected) ✓")
        
        # Check that devices were also removed
        device1_config = host._persistence.get_vdsd(device1.dsuid)
        device2_config = host._persistence.get_vdsd(device2.dsuid)
        assert device1_config is None, "Device1 should be deleted from persistence"
        assert device2_config is None, "Device2 should be deleted from persistence"
        print(f"  Associated devices also deleted from persistence ✓")
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    finally:
        # Cleanup
        if os.path.exists(config_file):
            os.unlink(config_file)
        backup_file = config_file + ".bak"
        if os.path.exists(backup_file):
            os.unlink(backup_file)


if __name__ == "__main__":
    try:
        asyncio.run(test_vdc_utility_methods())
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
