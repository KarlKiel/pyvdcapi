#!/usr/bin/env python3
"""
Example demonstrating the VdcHost utility methods:
- get_vdc(dsuid)
- get_all_vdcs()
- delete_vdc(dsuid)

These methods are useful for dynamic vDC management scenarios.
"""

import asyncio
from pyvdcapi.entities import VdcHost
from pyvdcapi.core.constants import DSGroup


async def main():
    # Create vDC host
    host = VdcHost(
        name="Dynamic Host Example",
        port=8444,
        mac_address="AA:BB:CC:DD:EE:FF",
        persistence_file="dynamic_vdcs.yaml"
    )
    
    print("=" * 60)
    print("VdcHost Utility Methods - Usage Examples")
    print("=" * 60)
    
    # Example 1: Create some vDCs
    print("\n1. Creating vDCs...")
    hue_vdc = host.create_vdc(
        name="Philips Hue Bridge",
        model="Hue vDC v1.0"
    )
    print(f"   Created: {hue_vdc._common_props.get_property('name')}")
    print(f"   dSUID: {hue_vdc.dsuid}")
    
    tradfri_vdc = host.create_vdc(
        name="IKEA TRÅDFRI Gateway",
        model="TRÅDFRI vDC v1.0"
    )
    print(f"   Created: {tradfri_vdc._common_props.get_property('name')}")
    print(f"   dSUID: {tradfri_vdc.dsuid}")
    
    # Example 2: Get all vDCs (useful for admin interfaces)
    print("\n2. Getting all vDCs (get_all_vdcs)...")
    all_vdcs = host.get_all_vdcs()
    print(f"   Total vDCs: {len(all_vdcs)}")
    for vdc in all_vdcs:
        name = vdc._common_props.get_property('name')
        model = vdc._common_props.get_property('model')
        device_count = len(vdc._vdsds)
        print(f"   - {name} ({model}) - {device_count} devices")
    
    # Example 3: Get specific vDC by dSUID
    print("\n3. Getting specific vDC (get_vdc)...")
    found_vdc = host.get_vdc(hue_vdc.dsuid)
    if found_vdc:
        print(f"   Found: {found_vdc._common_props.get_property('name')}")
    else:
        print("   Not found")
    
    # Example 4: Check if vDC exists before creating
    print("\n4. Conditional vDC creation...")
    test_dsuid = tradfri_vdc.dsuid
    if host.get_vdc(test_dsuid):
        print(f"   vDC {test_dsuid[:8]}... already exists, skipping creation")
    else:
        print("   vDC doesn't exist, would create new one")
    
    # Example 5: Add some devices to a vDC
    print("\n5. Adding devices to vDCs...")
    hue_light1 = hue_vdc.create_vdsd(
        name="Living Room Light",
        model="Hue White",
        primary_group=DSGroup.YELLOW
    )
    print(f"   Added device to Hue vDC: {hue_light1._common_props.get_property('name')}")
    
    hue_light2 = hue_vdc.create_vdsd(
        name="Bedroom Light",
        model="Hue White",
        primary_group=DSGroup.YELLOW
    )
    print(f"   Added device to Hue vDC: {hue_light2._common_props.get_property('name')}")
    
    # Example 6: Delete a vDC (also deletes all its devices)
    print("\n6. Deleting a vDC (delete_vdc)...")
    print(f"   Before deletion - Total vDCs: {len(host.get_all_vdcs())}")
    
    success = host.delete_vdc(tradfri_vdc.dsuid)
    if success:
        print(f"   ✓ Successfully deleted TRÅDFRI vDC")
    else:
        print(f"   ✗ Failed to delete vDC (not found)")
    
    print(f"   After deletion - Total vDCs: {len(host.get_all_vdcs())}")
    
    # Verify deletion
    if not host.get_vdc(tradfri_vdc.dsuid):
        print("   ✓ Confirmed: vDC no longer exists")
    
    # Example 7: Attempting to delete non-existent vDC
    print("\n7. Attempting to delete non-existent vDC...")
    success = host.delete_vdc("invalid-dsuid-12345")
    if not success:
        print("   ✓ Correctly returned False for non-existent vDC")
    
    # Example 8: Real-world scenario - Gateway reconnection
    print("\n8. Real-world scenario - Gateway reconnection...")
    print("   Simulating: Hue bridge went offline and came back")
    
    # Get the old vDC
    old_hue_vdc = host.get_vdc(hue_vdc.dsuid)
    if old_hue_vdc:
        device_count = len(old_hue_vdc._vdsds)
        print(f"   Found existing Hue vDC with {device_count} devices")
        print(f"   Removing old vDC (will be recreated on rediscovery)...")
        host.delete_vdc(old_hue_vdc.dsuid)
    
    # Rediscover and recreate
    new_hue_vdc = host.create_vdc(
        name="Philips Hue Bridge (Reconnected)",
        model="Hue vDC v1.0"
    )
    print(f"   Created new Hue vDC: {new_hue_vdc.dsuid}")
    print(f"   Note: Devices will be rediscovered and re-added")
    
    # Final status
    print("\n" + "=" * 60)
    print("Final Status:")
    print("=" * 60)
    for vdc in host.get_all_vdcs():
        name = vdc._common_props.get_property('name')
        model = vdc._common_props.get_property('model')
        device_count = len(vdc._vdsds)
        print(f"  • {name}")
        print(f"    Model: {model}")
        print(f"    Devices: {device_count}")
        print(f"    dSUID: {vdc.dsuid}")


if __name__ == "__main__":
    asyncio.run(main())
