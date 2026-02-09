#!/usr/bin/env python3
"""
Test script to verify Issue #1 implementation: Device immutability after announcement.

This script tests that:
1. Features can be added before announcement
2. Features CANNOT be added after announcement (raises RuntimeError)
3. The error messages are clear and helpful
"""

import sys
sys.path.insert(0, '/home/arne/Dokumente/vdc/pyvdcapi')

from pyvdcapi.entities.vdc_host import VdcHost
from pyvdcapi.entities.vdc import Vdc
from pyvdcapi.entities.vdsd import VdSD
from pyvdcapi.constants import DSDeviceType, DSChannelType


def test_immutability_checks():
    """Test that devices become immutable after announcement."""
    
    print("=" * 70)
    print("TESTING ISSUE #1: Device Immutability After Announcement")
    print("=" * 70)
    print()
    
    # Create test hierarchy
    print("1. Creating VdcHost, Vdc, and VdSD...")
    vdc_host = VdcHost(dsuid="vdc_host_test", name="Test VDC Host")
    vdc = Vdc(dsuid="vdc_test", name="Test vDC", model_name="TestModel")
    vdc_host.add_vdc(vdc)
    
    device = VdSD(
        vdc=vdc,
        name="Test Device",
        model_name="TestDevice",
        device_type=DSDeviceType.LIGHT,
        dsuid="device_test"
    )
    vdc.add_vdsd(device)
    print("   ✓ Created hierarchy: VdcHost → Vdc → VdSD")
    print()
    
    # Test 1: Add features BEFORE announcement (should work)
    print("2. Testing feature addition BEFORE announcement...")
    try:
        device.add_output_channel(
            channel_type=DSChannelType.BRIGHTNESS,
            min_value=0.0,
            max_value=100.0
        )
        print("   ✓ add_output_channel() succeeded (as expected)")
    except RuntimeError as e:
        print(f"   ✗ FAILED: {e}")
        return False
    
    try:
        device.add_button_input(name="Test Button", button_type=1, button_element_id=0)
        print("   ✓ add_button_input() succeeded (as expected)")
    except RuntimeError as e:
        print(f"   ✗ FAILED: {e}")
        return False
    
    try:
        device.add_sensor(
            sensor_type="temperature",
            unit="°C",
            min_value=-40.0,
            max_value=125.0
        )
        print("   ✓ add_sensor() succeeded (as expected)")
    except RuntimeError as e:
        print(f"   ✗ FAILED: {e}")
        return False
    print()
    
    # Announce the device
    print("3. Announcing device to vdSM (simulated)...")
    device.mark_announced()
    print(f"   ✓ Device marked as announced (_announced={device._announced})")
    print()
    
    # Test 2: Try to add features AFTER announcement (should fail)
    print("4. Testing feature addition AFTER announcement...")
    
    # Test add_output_channel
    print("   Testing add_output_channel()...")
    try:
        device.add_output_channel(
            channel_type=DSChannelType.SATURATION,
            min_value=0.0,
            max_value=100.0
        )
        print("   ✗ FAILED: add_output_channel() should have raised RuntimeError!")
        return False
    except RuntimeError as e:
        print(f"   ✓ Correctly blocked with error:")
        print(f"      {str(e)[:100]}...")
    
    # Test add_button
    print("   Testing add_button_input()...")
    try:
        device.add_button_input(name="Another Button", button_type=1, button_element_id=0)
        print("   ✗ FAILED: add_button_input() should have raised RuntimeError!")
        return False
    except RuntimeError as e:
        print(f"   ✓ Correctly blocked with error:")
        print(f"      {str(e)[:80]}...")
    
    # Test add_sensor
    print("   Testing add_sensor()...")
    try:
        device.add_sensor(
            sensor_type="humidity",
            unit="%",
            min_value=0.0,
            max_value=100.0
        )
        print("   ✗ FAILED: add_sensor() should have raised RuntimeError!")
        return False
    except RuntimeError as e:
        print(f"   ✓ Correctly blocked with error:")
        print(f"      {str(e)[:80]}...")
    
    # Test configure
    print("   Testing configure()...")
    try:
        device.configure({
            "outputs": [{
                "channels": [{"type": DSChannelType.HUE}]
            }]
        })
        print("   ✗ FAILED: configure() should have raised RuntimeError!")
        return False
    except RuntimeError as e:
        print(f"   ✓ Correctly blocked with error:")
        print(f"      {str(e)[:80]}...")
    
    print()
    print("=" * 70)
    print("✓ ALL TESTS PASSED: Issue #1 implementation is working correctly!")
    print("=" * 70)
    return True


def test_vdc_announce_devices():
    """Test that Vdc.announce_devices() calls mark_announced() on all devices."""
    
    print()
    print("=" * 70)
    print("TESTING: Vdc.announce_devices() Integration")
    print("=" * 70)
    print()
    
    # Create test hierarchy
    print("1. Creating Vdc with multiple devices...")
    vdc = Vdc(dsuid="vdc_test2", name="Test vDC 2", model_name="TestModel2")
    
    device1 = VdSD(
        vdc=vdc,
        name="Device 1",
        model_name="Model1",
        device_type=DSDeviceType.LIGHT,
        dsuid="device1"
    )
    device2 = VdSD(
        vdc=vdc,
        name="Device 2",
        model_name="Model2",
        device_type=DSDeviceType.LIGHT,
        dsuid="device2"
    )
    
    vdc.add_vdsd(device1)
    vdc.add_vdsd(device2)
    print(f"   ✓ Created vDC with {len(vdc.get_all_vdsds())} devices")
    print()
    
    # Verify devices are NOT announced yet
    print("2. Verifying initial state...")
    if device1._announced or device2._announced:
        print("   ✗ FAILED: Devices should not be announced initially!")
        return False
    print("   ✓ Both devices have _announced=False")
    print()
    
    # Call announce_devices()
    print("3. Calling vdc.announce_devices()...")
    messages = vdc.announce_devices()
    print(f"   ✓ Generated {len(messages)} announcement messages")
    print()
    
    # Verify devices ARE announced now
    print("4. Verifying devices were marked as announced...")
    if not device1._announced:
        print("   ✗ FAILED: Device 1 should be marked as announced!")
        return False
    if not device2._announced:
        print("   ✗ FAILED: Device 2 should be marked as announced!")
        return False
    print("   ✓ Both devices have _announced=True")
    print()
    
    # Verify immutability is enforced
    print("5. Verifying immutability is enforced...")
    try:
        device1.add_button_input(name="Test", button_type=1, button_element_id=0)
        print("   ✗ FAILED: Should not be able to add button after announcement!")
        return False
    except RuntimeError:
        print("   ✓ Device 1 correctly blocks modifications")
    
    try:
        device2.add_sensor(sensor_type="temperature", unit="°C", min_value=0, max_value=100)
        print("   ✗ FAILED: Should not be able to add sensor after announcement!")
        return False
    except RuntimeError:
        print("   ✓ Device 2 correctly blocks modifications")
    
    print()
    print("=" * 70)
    print("✓ Vdc.announce_devices() integration works correctly!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = test_immutability_checks()
    if success:
        success = test_vdc_announce_devices()
    
    sys.exit(0 if success else 1)
