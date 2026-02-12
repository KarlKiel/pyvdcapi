#!/usr/bin/env python3
"""
Template System Example

Demonstrates how to:
1. Create and configure devices
2. Save devices as templates
3. Create new devices from templates
4. List and manage templates

Templates enable:
- Quick deployment of common device configurations
- Community sharing of device configs
- Consistent device setup across installations
"""

import asyncio
import sys
from pathlib import Path

# Add package to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyvdcapi.entities.vdc_host import VdcHost
from pyvdcapi.core.constants import DSGroup, DSChannelType, DSSensorType, DSButtonType
from pyvdcapi.templates import TemplateManager, TemplateType
from pyvdcapi.components.output import Output


async def main():
    print("=" * 70)
    print("pyvdcapi Template System Example")
    print("=" * 70)
    print()

    # 1. Create vDC host and vDC
    print("1. Setting up vDC host and vDC...")
    host = VdcHost(
        name="Template Demo Host",
        port=8444,
        mac_address="00:11:22:33:44:55",
        vendor_id="TemplateDemo",
        persistence_file="template_demo.yaml",
    )
    
    vdc = host.create_vdc(name="Template Demo vDC", model="Demo v1.0")
    print(f"   ✓ Created vDC: {vdc.name}")
    print()

    # 2. Create and configure a simple on/off light device
    print("2. Creating simple on/off light...")
    simple_light = vdc.create_vdsd(
        name="Simple Light Master",
        model="OnOff Light",
        primary_group=DSGroup.YELLOW,  # Light
    )
    
    # Add output channel (brightness)
    output = simple_light.create_output()
    output.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0,
        resolution=1.0,
        initial_value=0.0,
    )
    print(f"   ✓ Created device: {simple_light.name}")
    print(f"     - Output channels: 1 (Brightness)")
    print()

    # 3. Save as deviceType template
    print("3. Saving as deviceType template...")
    template_path = simple_light.save_as_template(
        template_name="simple_onoff_light",
        template_type="deviceType",
        description="Simple on/off light with brightness control (0-100%)",
    )
    print(f"   ✓ Template saved: {template_path}")
    print()

    # 4. Create more complex device (dimmer with sensor)
    print("4. Creating complex dimmer with temperature sensor...")
    smart_dimmer = vdc.create_vdsd(
        name="Smart Dimmer Master",
        model="Smart Dimmer Pro",
        primary_group=DSGroup.YELLOW,
    )
    
    # Add brightness output
    output = smart_dimmer.create_output()
    output.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0,
        resolution=0.1,
        initial_value=0.0,
    )
    
    # Add temperature sensor
    smart_dimmer.add_sensor(
        sensor_type=DSSensorType.TEMPERATURE,
        min_value=-10.0,
        max_value=50.0,
        resolution=0.1,
        update_interval=60,
        name="Temperature Sensor",
    )
    
    print(f"   ✓ Created device: {smart_dimmer.name}")
    print(f"     - Output channels: 1 (Brightness with 0.1° resolution)")
    print(f"     - Sensors: 1 (Temperature)")
    print()

    # 5. Save as vendorType template
    print("5. Saving as vendorType template...")
    template_path = smart_dimmer.save_as_template(
        template_name="acme_smart_dimmer_pro",
        template_type="vendorType",
        description="ACME Smart Dimmer Pro with integrated temperature sensor",
        vendor="ACME Corporation",
        vendor_model_id="SD-PRO-2024",
    )
    print(f"   ✓ Template saved: {template_path}")
    print()

    # 6. Create device with button input
    print("6. Creating wall switch with button...")
    wall_switch = vdc.create_vdsd(
        name="Wall Switch Master",
        model="Wall Switch Single",
        primary_group=DSGroup.YELLOW,
    )
    
    # Add button input
    wall_switch.add_button_input(
        button_type=DSButtonType.SINGLE_BUTTON,
        button_id=0,
        name="Main Button",
        group=1,
        mode=0,
    )
    
    # Add output for the light controlled by button
    output = wall_switch.create_output()
    output.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0,
        initial_value=0.0,
    )
    
    print(f"   ✓ Created device: {wall_switch.name}")
    print(f"     - Button inputs: 1")
    print(f"     - Output channels: 1")
    print()

    # 7. Save wall switch as template
    print("7. Saving wall switch as deviceType template...")
    template_path = wall_switch.save_as_template(
        template_name="wall_switch_single_button",
        template_type="deviceType",
        description="Single button wall switch with connected light output",
    )
    print(f"   ✓ Template saved: {template_path}")
    print()

    # 8. List all available templates
    print("8. Listing all available templates...")
    template_mgr = TemplateManager()
    all_templates = template_mgr.list_templates()
    
    for category, templates in sorted(all_templates.items()):
        print(f"   {category}:")
        for template_name in templates:
            print(f"     - {template_name}")
    print()

    # 9. Create new devices from templates
    print("9. Creating new devices from templates...")
    print()
    
    # Create 3 simple lights from deviceType template
    print("   a) Creating 3 simple lights from template:")
    created_lights = []
    for i in range(1, 4):
        light = vdc.create_vdsd_from_template(
            template_name="simple_onoff_light",
            instance_name=f"Living Room Light {i}",
            template_type="deviceType",
            brightness=0.0,  # Starting value for the channel
        )
        print(f"      ✓ {light.name} (dSUID: {light.dsuid})")
        created_lights.append(light)
    print()
    
    # IMPORTANT: Demonstrate bidirectional binding
    print("   📌 BIDIRECTIONAL BINDING DEMONSTRATION:")
    print("      Templates create REAL channels with full callback support!")
    print()
    
    # Get the first light's brightness channel
    demo_light = created_lights[0]
    output = demo_light.get_output()
    brightness_channel = output.get_channel(DSChannelType.BRIGHTNESS)
    
    # Hardware state storage (simulating actual hardware)
    hardware_state = {"brightness": 0.0}
    
    # Set up bidirectional binding via callback
    async def apply_brightness_to_hardware(channel_type: int, value: float):
        """Direction 1: vdSM → Hardware (when vdSM changes value)"""
        hardware_state["brightness"] = value
        print(f"      → Hardware updated: Brightness set to {value}%")
    
    # Subscribe to channel changes
    brightness_channel.subscribe(apply_brightness_to_hardware)
    print(f"      ✓ Callback registered for '{demo_light.name}'")
    print()
    
    # Simulate vdSM changing brightness (Direction 1: vdSM → Hardware)
    print("      Testing Direction 1 (vdSM → Hardware):")
    await brightness_channel.set_value(50.0)  # vdSM sets brightness
    print(f"      ✓ Channel value: {brightness_channel.get_value()}%")
    print(f"      ✓ Hardware state: {hardware_state['brightness']}%")
    print()
    
    # Simulate hardware changing brightness manually (Direction 2: Hardware → vdSM)
    print("      Testing Direction 2 (Hardware → vdSM):")
    print("      (Simulating manual dimmer adjustment to 75%)")
    hardware_state["brightness"] = 75.0  # Hardware changed
    brightness_channel.update_value(75.0)  # Notify vdSM
    print(f"      ✓ Channel value: {brightness_channel.get_value()}%")
    print(f"      ✓ Hardware state: {hardware_state['brightness']}%")
    print(f"      ✓ Push notification sent to vdSM automatically")
    print()
    
    print("      Summary: Channels are LIVE variables with:")
    print("      • subscribe() - Register hardware callbacks")
    print("      • set_value() - vdSM → Hardware direction")
    print("      • update_value() - Hardware → vdSM direction")
    print("      • get_value() - Read current state")
    print()

    # Create 2 smart dimmers from vendorType template
    print("   b) Creating 2 smart dimmers from template:")
    for i in range(1, 3):
        dimmer = vdc.create_vdsd_from_template(
            template_name="acme_smart_dimmer_pro",
            instance_name=f"Bedroom Dimmer {i}",
            template_type="vendorType",
            brightness=0.0,  # Starting value
        )
        print(f"      ✓ {dimmer.name} (dSUID: {dimmer.dsuid})")
        print(f"         Sensors: {len(dimmer._sensors)}, Outputs: {len(dimmer._output.channels) if dimmer._output else 0}")
    print()

    # Create wall switches from template
    print("   c) Creating 2 wall switches from template:")
    for i in range(1, 3):
        switch = vdc.create_vdsd_from_template(
            template_name="wall_switch_single_button",
            instance_name=f"Kitchen Switch {i}",
            template_type="deviceType",
        )
        print(f"      ✓ {switch.name}")
        print(f"         Buttons: {len(switch._button_inputs)}, Outputs: {len(switch._output.channels) if switch._output else 0}")
    print()

    # 10. Show device summary
    print("10. Device Summary:")
    print(f"   Total devices in vDC: {len(vdc._vdsds)}")
    print(f"   Devices by type:")
    device_types = {}
    for device in vdc._vdsds.values():
        model = device._common_props.get_property("model")
        device_types[model] = device_types.get(model, 0) + 1
    
    for model, count in sorted(device_types.items()):
        print(f"     - {model}: {count}")
    print()

    # 11. Template operations
    print("11. Additional template operations:")
    print()
    
    # List only deviceType templates
    print("   a) deviceType templates:")
    device_templates = template_mgr.list_templates(template_type=TemplateType.DEVICE_TYPE)
    for category, templates in sorted(device_templates.items()):
        print(f"      {category}: {', '.join(templates)}")
    print()

    # List only vendorType templates
    print("   b) vendorType templates:")
    vendor_templates = template_mgr.list_templates(template_type=TemplateType.VENDOR_TYPE)
    for category, templates in sorted(vendor_templates.items()):
        print(f"      {category}: {', '.join(templates)}")
    print()

    # List only LIGHT group templates
    print("   c) LIGHT group templates across all types:")
    light_templates = template_mgr.list_templates(group="LIGHT")
    for category, templates in sorted(light_templates.items()):
        print(f"      {category}: {', '.join(templates)}")
    print()

    # 12. Load and inspect a template
    print("12. Inspecting a template:")
    template_data = template_mgr.load_template("simple_onoff_light", TemplateType.DEVICE_TYPE)
    
    metadata = template_data.get("template_metadata", {})
    print(f"   Template: {metadata.get('template_name')}")
    print(f"   Description: {metadata.get('description')}")
    print(f"   Created from model: {metadata.get('created_from_model')}")
    
    device_config = template_data.get("device_config", {})
    print(f"   Primary group: {device_config.get('primary_group')}")
    print(f"   Model: {device_config.get('model')}")
    
    if "output" in device_config:
        channels = device_config["output"].get("channels", [])
        print(f"   Output channels: {len(channels)}")
        for i, channel in enumerate(channels):
            print(f"     Channel {i}: Type {channel.get('channel_type')}, "
                  f"Range {channel.get('min_value')}-{channel.get('max_value')}")
    print()

    print("=" * 70)
    print("Template System Demo Complete!")
    print("=" * 70)
    print()
    print("Key Features Demonstrated:")
    print("  ✓ Save configured devices as templates")
    print("  ✓ deviceType templates (standard hardware)")
    print("  ✓ vendorType templates (vendor-specific)")
    print("  ✓ Create devices from templates with minimal info")
    print("  ✓ List and filter templates")
    print("  ✓ Templates organized by type and group")
    print("  ✓ Community-shareable template files")
    print()
    print(f"Templates saved to: {template_mgr.templates_path}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
