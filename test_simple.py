"""Simple test to verify basic functionality."""
import asyncio
from pyvdcapi import VdcHost

async def test():
    # Create simple host
    host = VdcHost(name="Test", port=8444)
    
    # Create vDC
    vdc = host.create_vdc(
        name="Test vDC",
        model="Test Model"
    )
    
    # Create device
    device = vdc.create_vdsd(
        name="Test Device",
        model="Test Model",
        primary_group=1
    )
    
    print("✓ Created host, vDC, and device successfully")
    print(f"  Host: {host._common_props.get_name()}")
    print(f"  VdC: {vdc._common_props.get_property('name')}")
    print(f"  Device: {device._common_props.get_property('name')}")

asyncio.run(test())
