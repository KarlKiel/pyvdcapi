#!/usr/bin/env python3
"""
Example: Creating Templates with Detailed Descriptions

This example demonstrates how to use the 'description' field when creating
device templates. The description field helps users understand what the
template does and when to use it.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pyvdcapi.entities.vdc_host import VdcHost
from pyvdcapi.core.constants import DSGroup, DSChannelType


async def create_templates_with_descriptions():
    """Demonstrate creating templates with detailed descriptions."""
    
    print("="*70)
    print("Creating Templates with Detailed Descriptions")
    print("="*70)
    
    # Create VdC Host
    host = VdcHost(
        name="Template Demo",
        port=8444,
        mac_address="00:11:22:33:44:66",
        vendor_id="TemplateDemo",
        persistence_file="template_demo.yaml",
    )
    
    vdc = host.create_vdc(name="Demo VdC", model="Demo v1.0")
    
    # ========================================================================
    # Example 1: Simple Light with Basic Description
    # ========================================================================
    print("\n1. Simple On/Off Light...")
    
    simple_light = vdc.create_vdsd(
        name="Simple Light",
        model="On/Off Light",
        primary_group=DSGroup.YELLOW,
    )
    
    simple_light.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0,
        resolution=1.0,
        output_function="switch",
        output_mode="binary",
        push_changes=True,
    )
    
    template_path = simple_light.save_as_template(
        template_name="simple_onoff_light",
        template_type="deviceType",
        description="Simple on/off light switch with binary control (no dimming)",
    )
    
    print(f"✓ Created: {template_path}")
    print(f"  Description: 'Simple on/off light switch with binary control (no dimming)'")
    
    # ========================================================================
    # Example 2: Dimmable Light with Detailed Description
    # ========================================================================
    print("\n2. Dimmable Light...")
    
    dimmable_light = vdc.create_vdsd(
        name="Dimmable Light",
        model="Dimmer Light",
        primary_group=DSGroup.YELLOW,
    )
    
    dimmable_light.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0,
        resolution=0.1,
        output_function="dimmer",
        output_mode="gradual",
        push_changes=True,
    )
    
    template_path = dimmable_light.save_as_template(
        template_name="dimmable_light",
        template_type="deviceType",
        description="Dimmable light with smooth brightness control (0-100%), supports gradual transitions and scene recall",
    )
    
    print(f"✓ Created: {template_path}")
    print(f"  Description: 'Dimmable light with smooth brightness control (0-100%), supports gradual transitions and scene recall'")
    
    # ========================================================================
    # Example 3: RGB Light with Comprehensive Description
    # ========================================================================
    print("\n3. RGB Color Light...")
    
    rgb_light = vdc.create_vdsd(
        name="RGB Light",
        model="RGB Color Light",
        primary_group=DSGroup.YELLOW,
    )
    
    # Add all color channels
    rgb_light.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0,
        resolution=0.1,
        output_function="colordimmer",
        output_mode="gradual",
        push_changes=True,
    )
    
    rgb_light.add_output_channel(
        channel_type=DSChannelType.HUE,
        min_value=0.0,
        max_value=360.0,
        resolution=1.0,
    )
    
    rgb_light.add_output_channel(
        channel_type=DSChannelType.SATURATION,
        min_value=0.0,
        max_value=100.0,
        resolution=0.1,
    )
    
    template_path = rgb_light.save_as_template(
        template_name="rgb_color_light",
        template_type="deviceType",
        description="RGB color light with brightness (0-100%), hue (0-360°), and saturation (0-100%) control, supports smooth color transitions and full scene integration",
    )
    
    print(f"✓ Created: {template_path}")
    print(f"  Description: 'RGB color light with brightness (0-100%), hue (0-360°), and saturation (0-100%) control, supports smooth color transitions and full scene integration'")
    
    # ========================================================================
    # Example 4: Vendor-Specific Template with Vendor Info
    # ========================================================================
    print("\n4. Vendor-Specific Template (Philips Hue)...")
    
    hue_bulb = vdc.create_vdsd(
        name="Hue White Ambiance",
        model="Philips Hue White Ambiance",
        primary_group=DSGroup.YELLOW,
    )
    
    hue_bulb.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0,
        resolution=0.1,
        output_function="ctdimmer",
        output_mode="gradual",
        push_changes=True,
    )
    
    hue_bulb.add_output_channel(
        channel_type=DSChannelType.COLOR_TEMP,
        min_value=2200.0,  # Warm white
        max_value=6500.0,  # Cool white
        resolution=100.0,
    )
    
    template_path = hue_bulb.save_as_template(
        template_name="philips_hue_white_ambiance",
        template_type="vendorType",
        description="Philips Hue White Ambiance bulb with brightness control (0-100%) and color temperature adjustment (2200K-6500K), smooth transitions and scene support",
        vendor="Philips",
        vendor_model_id="8718696548738",
    )
    
    print(f"✓ Created: {template_path}")
    print(f"  Vendor: Philips")
    print(f"  Model ID: 8718696548738")
    print(f"  Description: 'Philips Hue White Ambiance bulb with brightness control (0-100%) and color temperature adjustment (2200K-6500K), smooth transitions and scene support'")
    
    # ========================================================================
    # Example 5: Multi-Sensor with Complex Description
    # ========================================================================
    print("\n5. Multi-Sensor Device...")
    
    multi_sensor = vdc.create_vdsd(
        name="Multi-Sensor",
        model="Environmental Sensor",
        primary_group=DSGroup.UNDEFINED,
    )
    
    # Add temperature sensor
    temp = multi_sensor.add_sensor(
        name="Temperature",
        sensor_type="temperature",
        unit="°C",
        min_value=-20.0,
        max_value=60.0,
        resolution=0.1,
    )
    temp.min_push_interval = 5.0
    temp.changes_only_interval = 300.0
    
    # Add humidity sensor
    humidity = multi_sensor.add_sensor(
        name="Humidity",
        sensor_type="humidity",
        unit="%",
        min_value=0.0,
        max_value=100.0,
        resolution=0.1,
    )
    humidity.min_push_interval = 5.0
    
    # Add motion detector
    motion = multi_sensor.add_binary_input(
        name="Motion",
        input_type="motion",
    )
    
    template_path = multi_sensor.save_as_template(
        template_name="environmental_multi_sensor",
        template_type="deviceType",
        description="Environmental sensor with temperature (-20°C to 60°C), humidity (0-100%), and motion detection. Configurable push intervals (5s minimum) with change-only mode for reduced updates.",
    )
    
    print(f"✓ Created: {template_path}")
    print(f"  Description: 'Environmental sensor with temperature (-20°C to 60°C), humidity (0-100%), and motion detection. Configurable push intervals (5s minimum) with change-only mode for reduced updates.'")
    
    # ========================================================================
    # Summary
    # ========================================================================
    print("\n" + "="*70)
    print("Summary: Best Practices for Template Descriptions")
    print("="*70)
    print("\n✅ GOOD Descriptions:")
    print("  - Include device type and purpose")
    print("  - List all channels/inputs with value ranges")
    print("  - Mention special features (transitions, scenes, etc.)")
    print("  - For vendor templates: include specific model capabilities")
    print("\n❌ POOR Descriptions:")
    print("  - 'Light template' (too vague)")
    print("  - 'Device' (not informative)")
    print("  - 'Template' (useless)")
    print("\n📝 Template Metadata Fields:")
    print("  - template_name: Identifier for creating devices")
    print("  - description: Detailed feature description (IMPORTANT!)")
    print("  - vendor: Manufacturer name (optional, for vendorType)")
    print("  - vendor_model_id: Model/part number (optional)")
    print("  - created_from_model: Original device model name")
    
    print("\n" + "="*70)
    print("Done! Check the templates in pyvdcapi/templates/")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(create_templates_with_descriptions())
