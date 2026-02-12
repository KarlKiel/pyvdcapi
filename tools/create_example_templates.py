#!/usr/bin/env python3
"""
Create Comprehensive Example Templates

This script creates two complete example devices that demonstrate all features:
- ExampleTemplateAllFeaturesOutputPushed (pushChanges=True)
- ExampleTemplateAllFeaturesOutputControlOnly (pushChanges=False)

Both devices include:
- 2 Buttons (one clickType mode, one actionId mode)
- 2 Binary Inputs (inputType=0 and inputType=1)
- 1 Sensor with meaningful pushInterval settings
- Output channel (with different pushChanges settings)
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyvdcapi.entities.vdc_host import VdcHost
from pyvdcapi.core.constants import DSGroup, DSChannelType, DSSensorType


async def create_example_templates():
    """Create the two comprehensive example templates."""
    
    print("="*70)
    print("Creating Comprehensive Example Templates")
    print("="*70)
    
    # Create VdC Host
    host = VdcHost(
        name="Template Creator",
        port=8444,
        mac_address="00:11:22:33:44:55",
        vendor_id="TemplateCreator",
        persistence_file="template_creator.yaml",
    )
    
    vdc = host.create_vdc(name="Example Templates VdC", model="Creator v1.0")
    
    # ========================================================================
    # Template 1: Output with pushChanges=True
    # ========================================================================
    print("\n1. Creating ExampleTemplateAllFeaturesOutputPushed...")
    
    device1 = vdc.create_vdsd(
        name="AllFeaturesOutputPushed",
        model="Complete Example Device",
        primary_group=0,  # WHITE group
    )
    
    # Add output channel with pushChanges=True
    # The output is created automatically when adding the first channel
    # Output-level properties (output_function, output_mode, push_changes) go in **properties
    channel1 = device1.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0,
        resolution=0.1,
        initial_value=0.0,
        # These are Output properties, not OutputChannel properties:
        output_function="dimmer",  # vDC API: Output function
        output_mode="gradual",      # vDC API: Output mode  
        push_changes=True,          # vDC API: pushChanges setting (bidirectional sync)
    )
    
    # Add 2 buttons (different modes)
    button1_click = device1.add_button_input(
        name="Button ClickType",
        button_type=1,  # Single pushbutton
        button_id=0,
        use_action_mode=False,  # Standard mode: clickType/value
        group=1,
        mode=0,
    )
    
    button1_action = device1.add_button_input(
        name="Button ActionID",
        button_type=1,  # Single pushbutton
        button_id=1,
        use_action_mode=True,  # Action mode: actionId/actionMode
        group=1,
        mode=0,
    )
    
    # Add 2 binary inputs (different types: contact and motion)
    # Per vDC API: inputType 0=poll only, 1=detects changes
    # Library uses string types that map to these concepts
    binary1_contact = device1.add_binary_input(
        name="Binary Contact",
        input_type="contact",  # Maps to inputType 0 (poll only)
    )
    
    binary1_motion = device1.add_binary_input(
        name="Binary Motion",
        input_type="motion",  # Maps to inputType 1 (detects changes)
    )
    
    # Add 1 sensor with meaningful settings
    # Per vDC API: sensorType 1=Temperature in °C
    sensor1 = device1.add_sensor(
        name="Temperature Sensor",
        sensor_type="temperature",  # Maps to sensorType 1
        unit="°C",
        min_value=-20.0,
        max_value=60.0,
        resolution=0.1,
    )
    # Per vDC API section 4.4.2 (Settings):
    sensor1.min_push_interval = 5.0         # minPushInterval: minimum interval between pushes
    sensor1.changes_only_interval = 300.0   # changesOnlyInterval: interval for same values
    
    # Save template
    template1_path = device1.save_as_template(
        template_name="ExampleTemplateAllFeaturesOutputPushed",
        template_type="deviceType",
        description="Complete example device with bidirectional output (pushChanges=True)",
    )
    
    print(f"✓ Created template: {template1_path}")
    print(f"  - Output: pushChanges=True (bidirectional)")
    print(f"  - Buttons: 2 (clickType + actionId modes)")
    print(f"  - Binary Inputs: 2 (inputType=0 and inputType=1)")
    print(f"  - Sensor: 1 (temperature, minPushInterval=5s)")
    
    # ========================================================================
    # Template 2: Output with pushChanges=False
    # ========================================================================
    print("\n2. Creating ExampleTemplateAllFeaturesOutputControlOnly...")
    
    device2 = vdc.create_vdsd(
        name="AllFeaturesOutputControlOnly",
        model="Complete Example Device",
        primary_group=0,  # WHITE group
    )
    
    # Add output channel with pushChanges=False
    # The output is created automatically when adding the first channel
    # Output-level properties (output_function, output_mode, push_changes) go in **properties
    channel2 = device2.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0,
        resolution=0.1,
        initial_value=0.0,
        # These are Output properties, not OutputChannel properties:
        output_function="dimmer",  # vDC API: Output function
        output_mode="gradual",      # vDC API: Output mode
        push_changes=False,         # vDC API: pushChanges setting (control only, no bidirectional sync)
    )
    
    # Add 2 buttons (different modes)
    button2_click = device2.add_button_input(
        name="Button ClickType",
        button_type=1,
        button_id=0,
        use_action_mode=False,  # Standard mode
        group=1,
        mode=0,
    )
    
    button2_action = device2.add_button_input(
        name="Button ActionID",
        button_type=1,
        button_id=1,
        use_action_mode=True,  # Action mode
        group=1,
        mode=0,
    )
    
    # Add 2 binary inputs (different types: contact and motion)
    # Per vDC API: inputType 0=poll only, 1=detects changes
    binary2_contact = device2.add_binary_input(
        name="Binary Contact",
        input_type="contact",  # Maps to inputType 0 (poll only)
    )
    
    binary2_motion = device2.add_binary_input(
        name="Binary Motion",
        input_type="motion",  # Maps to inputType 1 (detects changes)
    )
    
    # Add 1 sensor
    # Per vDC API: sensorType 1=Temperature in °C
    sensor2 = device2.add_sensor(
        name="Temperature Sensor",
        sensor_type="temperature",  # Maps to sensorType 1
        unit="°C",
        min_value=-20.0,
        max_value=60.0,
        resolution=0.1,
    )
    # Per vDC API section 4.4.2 (Settings):
    sensor2.min_push_interval = 5.0         # minPushInterval: minimum interval between pushes
    sensor2.changes_only_interval = 300.0   # changesOnlyInterval: interval for same values
    
    # Save template
    template2_path = device2.save_as_template(
        template_name="ExampleTemplateAllFeaturesOutputControlOnly",
        template_type="deviceType",
        description="Complete example device with control-only output (pushChanges=False)",
    )
    
    print(f"✓ Created template: {template2_path}")
    print(f"  - Output: pushChanges=False (control only)")
    print(f"  - Buttons: 2 (clickType + actionId modes)")
    print(f"  - Binary Inputs: 2 (inputType=0 and inputType=1)")
    print(f"  - Sensor: 1 (temperature, minPushInterval=5s)")
    
    print("\n" + "="*70)
    print("Templates created successfully!")
    print("="*70)
    print(f"\nTemplates saved to deviceType/UNDEFINED/ (primary_group=0):")
    print(f"  - ExampleTemplateAllFeaturesOutputPushed.yaml")
    print(f"  - ExampleTemplateAllFeaturesOutputControlOnly.yaml")


if __name__ == "__main__":
    asyncio.run(create_example_templates())
