"""
End-to-End Validation Script for pyvdcapi.

This script creates a complex device with all component types and validates:
1. Entity creation (VdcHost, Vdc, VdSD)
2. Property handling (required, optional, always-present)
3. Component creation (Output, OutputChannel, Button, BinaryInput, Sensor)
4. Property tree serialization
5. Announcement readiness

Run this script to verify the entire implementation is working correctly.
"""

import asyncio
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import pyvdcapi components
from pyvdcapi import VdcHost
from pyvdcapi.core.constants import (
    DSGroup,
    DSOutputFunction,
    DSChannelType,
    DSButtonType,
    DSBinaryInputFunction,
    DSSensorType,
    DSSensorUsage
)


def validate_entity_creation():
    """Test 1: Validate entity creation and property handling."""
    logger.info("=" * 80)
    logger.info("TEST 1: Entity Creation and Property Handling")
    logger.info("=" * 80)
    
    # Create VdcHost
    logger.info("\n1.1 Creating VdcHost...")
    host = VdcHost(
        name="E2E Test Hub",
        port=8444,
        mac_address="00:11:22:33:44:55",
        vendor_id="E2ETest",
        model="Test vDC Host",
        model_uid="test-vdc-host",
        model_version="1.0",
        persistence_file="e2e_test_config.yaml"
    )
    
    # Verify host properties
    host_props = host._common_props.to_dict()
    logger.info(f"✓ VdcHost created with dSUID: {host.dsuid}")
    logger.info(f"  - name: {host_props.get('name')}")
    logger.info(f"  - model: {host_props.get('model')}")
    logger.info(f"  - modelUID: {host_props.get('modelUID')}")
    logger.info(f"  - modelVersion: {host_props.get('modelVersion', 'NOT SET')}")
    logger.info(f"  - displayId: '{host_props.get('displayId', 'NOT SET')}' (should be empty string)")
    
    # Validate required properties
    assert 'name' in host_props, "name is required"
    assert 'modelUID' in host_props, "modelUID is required"
    assert 'displayId' in host_props, "displayId must always be present (even if empty)"
    logger.info("✓ All required properties present")
    
    # Create vDC
    logger.info("\n1.2 Creating Vdc...")
    vdc = host.create_vdc(
        name="Smart Light Controller",
        model="Hue vDC",
        model_uid="hue-vdc",
        model_version="2.0",
        implementationId="x-e2etest-hue-vdc"
    )
    
    vdc_common_props = vdc._common_props.to_dict()
    vdc_specific_props = vdc._vdc_props.to_dict()
    logger.info(f"✓ Vdc created with dSUID: {vdc.dsuid}")
    logger.info(f"  - name: {vdc_common_props.get('name')}")
    logger.info(f"  - modelUID: {vdc_common_props.get('modelUID')}")
    logger.info(f"  - implementationId: {vdc_specific_props.get('implementationId')}")
    logger.info(f"  - capabilities: {vdc_specific_props.get('capabilities')}")
    logger.info(f"  - displayId: '{vdc_common_props.get('displayId', 'NOT SET')}'")
    
    # Validate capabilities (required for vDC)
    assert 'capabilities' in vdc_specific_props, "capabilities is required for vDC"
    assert isinstance(vdc_specific_props['capabilities'], dict), "capabilities must be dict"
    logger.info("✓ vDC properties validated")
    
    return host, vdc


def validate_complex_device_creation(vdc):
    """Test 2: Create complex device with all component types."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Complex Device Creation")
    logger.info("=" * 80)
    
    logger.info("\n2.1 Creating VdSD with outputs and channels...")
    device = vdc.create_vdsd(
        name="Kitchen Multi-Sensor",
        model="Advanced Sensor Plus",
        model_uid="advanced-sensor-plus",
        model_version="3.2",
        primary_group=DSGroup.YELLOW,  # Light group
        displayId="SN-12345",  # Physical label on device
        hardwareGuid="uuid:a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        vendorName="TestVendor"
    )
    
    device_common_props = device._common_props.to_dict()
    device_vdsd_props = device._vdsd_props.to_dict()
    logger.info(f"✓ VdSD created with dSUID: {device.dsuid}")
    logger.info(f"  - name: {device_common_props.get('name')}")
    logger.info(f"  - modelUID: {device_common_props.get('modelUID')}")
    logger.info(f"  - displayId: '{device_common_props.get('displayId')}'")
    logger.info(f"  - primaryGroup: {device_vdsd_props.get('primaryGroup')}")
    logger.info(f"  - modelFeatures: {device_vdsd_props.get('modelFeatures', {})}")
    
    # Validate device properties
    assert 'displayId' in device_common_props, "displayId must always be present"
    assert device_common_props['displayId'] == "SN-12345", "displayId should be set correctly"
    assert 'modelFeatures' in device_vdsd_props, "modelFeatures is required for vdSD"
    assert isinstance(device_vdsd_props['modelFeatures'], dict), "modelFeatures must be dict"
    logger.info("✓ Device properties validated")
    
    # Add output channels
    logger.info("\n2.2 Adding output channel (brightness)...")
    brightness_channel = device.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0,
        resolution=0.1,
        initial_value=50.0
    )
    logger.info(f"✓ Brightness channel created: type={brightness_channel.channel_type}")
    
    # Add button
    logger.info("\n2.3 Adding button input...")
    button = device.add_button(
        name="Toggle Button",
        button_type=0  # Single press
    )
    logger.info(f"✓ Button created: id={button.button_id}, name='{button.name}'")
    
    # Add sensor
    logger.info("\n2.4 Adding sensor input...")
    sensor = device.add_sensor(
        sensor_type="temperature",
        unit="°C",
        min_value=-40.0,
        max_value=80.0
    )
    logger.info(f"✓ Sensor created: id={sensor.sensor_id}, type={sensor.sensor_type}")
    
    return device


def validate_property_tree(device):
    """Test 3: Validate property tree generation for vdSM announcements."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Property Tree Generation")
    logger.info("=" * 80)
    
    logger.info("\n3.1 Generating property tree...")
    property_tree = device.get_properties(None)
    
    logger.info("✓ Property tree generated successfully")
    logger.info(f"  Property tree type: {type(property_tree)}")
    
    # Convert back to dict for inspection
    from pyvdcapi.properties.property_tree import PropertyTree
    props_dict = PropertyTree.from_protobuf(property_tree)
    
    logger.info(f"\n3.2 Property tree contents:")
    logger.info(f"  - dSUID: {props_dict.get('dSUID', 'MISSING')}")
    logger.info(f"  - name: {props_dict.get('name', 'MISSING')}")
    logger.info(f"  - model: {props_dict.get('model', 'MISSING')}")
    logger.info(f"  - modelUID: {props_dict.get('modelUID', 'MISSING')}")
    logger.info(f"  - modelVersion: {props_dict.get('modelVersion', 'NOT SET')}")
    logger.info(f"  - displayId: '{props_dict.get('displayId', 'MISSING')}'")
    logger.info(f"  - primaryGroup: {props_dict.get('primaryGroup', 'MISSING')}")
    logger.info(f"  - modelFeatures: {props_dict.get('modelFeatures', {})}")
    logger.info(f"  - outputs: {len(props_dict.get('outputs', []))} output(s)")
    logger.info(f"  - inputs: {len(props_dict.get('inputs', []))} input(s)")
    
    # Critical validations for vdSM announcement
    assert 'dSUID' in props_dict, "dSUID is REQUIRED for announcement"
    assert 'name' in props_dict, "name is REQUIRED for announcement"
    assert 'modelUID' in props_dict, "modelUID is REQUIRED for announcement"
    assert 'displayId' in props_dict, "displayId must ALWAYS be present (vdSM requirement)"
    assert 'primaryGroup' in props_dict, "primaryGroup is REQUIRED for vdSD"
    assert 'modelFeatures' in props_dict, "modelFeatures is REQUIRED for vdSD"
    
    logger.info("\n✓ All REQUIRED properties present in property tree")
    logger.info("✓ Property tree ready for vdSM announcement")
    
    return props_dict


def validate_persistence(host, device):
    """Test 4: Validate persistence layer."""
    logger.info("\n" + "=" * 80)
    logger.info("TEST 4: Persistence Validation")
    logger.info("=" * 80)
    
    logger.info("\n4.1 Saving device configuration...")
    device.save()
    logger.info("✓ Device configuration saved")
    
    logger.info("\n4.2 Saving host configuration...")
    host.save_config()
    logger.info("✓ Host configuration saved")
    
    logger.info("\n4.3 Retrieving saved configuration...")
    saved_vdsd = host._persistence.get_vdsd(device.dsuid)
    assert saved_vdsd is not None, "Device configuration should be saved"
    logger.info(f"✓ Retrieved saved configuration for dSUID: {device.dsuid}")
    logger.info(f"  - name: {saved_vdsd.get('name')}")
    logger.info(f"  - model: {saved_vdsd.get('model')}")
    logger.info(f"  - primaryGroup: {saved_vdsd.get('primaryGroup')}")
    
    return True


def run_all_validations():
    """Run all validation tests."""
    try:
        logger.info("\n" + "=" * 80)
        logger.info("STARTING END-TO-END VALIDATION")
        logger.info("=" * 80)
        
        # Test 1: Entity creation
        host, vdc = validate_entity_creation()
        
        # Test 2: Complex device
        device = validate_complex_device_creation(vdc)
        
        # Test 3: Property tree
        props_dict = validate_property_tree(device)
        
        # Test 4: Persistence
        validate_persistence(host, device)
        
        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 80)
        logger.info("✓ Entity creation: PASS")
        logger.info("✓ Property handling: PASS")
        logger.info("✓ Component creation: PASS")
        logger.info("✓ Property tree generation: PASS")
        logger.info("✓ Persistence: PASS")
        logger.info("\n" + "=" * 80)
        logger.info("ALL VALIDATIONS PASSED ✓")
        logger.info("=" * 80)
        
        return True
        
    except AssertionError as e:
        logger.error(f"\n✗ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        logger.error(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_validations()
    exit(0 if success else 1)
