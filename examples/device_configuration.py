"""
Example: Device Configuration and Cloning

This example demonstrates how to:
1. Configure a device from a dictionary
2. Export device configuration
3. Clone devices
4. Use device templates
5. Save/load configurations
"""

import asyncio
import json
from pyvdcapi.entities.vdc_host import VdcHost
from pyvdcapi.core.constants import DSGroup, DSChannelType, DSScene, DSSceneEffect

# Device template for RGB light
RGB_LIGHT_TEMPLATE = {
    'outputs': [{
        'outputID': 0,
        'outputFunction': 'colordimmer',
        'outputMode': 'gradual',
        'pushChanges': True,
        'channels': [
            {
                'channelType': DSChannelType.BRIGHTNESS,
                'name': 'Brightness',
                'min': 0.0,
                'max': 100.0,
                'resolution': 0.1,
                'default': 0.0
            },
            {
                'channelType': DSChannelType.HUE,
                'name': 'Hue',
                'min': 0.0,
                'max': 360.0,
                'resolution': 1.0,
                'default': 0.0
            },
            {
                'channelType': DSChannelType.SATURATION,
                'name': 'Saturation',
                'min': 0.0,
                'max': 100.0,
                'resolution': 0.1,
                'default': 0.0
            }
        ]
    }],
    'buttons': [{
        'name': 'Power Button',
        'buttonType': 'toggle',
        'element': 0
    }],
    'sensors': [{
        'sensorType': 'temperature',
        'name': 'Internal Temperature',
        'unit': '°C',
        'min': -40.0,
        'max': 125.0,
        'resolution': 0.1
    }],
    'scenes': {
        DSScene.PRESENT: {
            'channels': {
                DSChannelType.BRIGHTNESS: 75.0,
                DSChannelType.HUE: 0.0,
                DSChannelType.SATURATION: 0.0
            },
            'effect': DSSceneEffect.SMOOTH
        },
        DSScene.ABSENT: {
            'channels': {
                DSChannelType.BRIGHTNESS: 0.0
            },
            'effect': DSSceneEffect.SMOOTH
        },
        DSScene.SLEEPING: {
            'channels': {
                DSChannelType.BRIGHTNESS: 10.0,
                DSChannelType.HUE: 30.0,
                DSChannelType.SATURATION: 80.0
            },
            'effect': DSSceneEffect.SLOW
        }
    }
}

# Template for motion sensor
MOTION_SENSOR_TEMPLATE = {
    'binary_inputs': [{
        'name': 'Motion Detector',
        'inputType': 'motion',
        'invert': False,
        'initialState': False
    }],
    'sensors': [{
        'sensorType': 'illuminance',
        'name': 'Light Level',
        'unit': 'lux',
        'min': 0.0,
        'max': 10000.0,
        'resolution': 1.0
    }]
}


async def main():
    """Demonstrate device configuration."""
    
    # Create vDC host
    host = VdcHost(
        name="Configuration Demo",
        port=8440,
        persistence_file="config_demo.yaml"
    )
    
    # Create vDC
    vdc = host.create_vdc(
        vendor="Example Inc",
        model_name="Configurable Devices",
        model_guid="example-config-demo-v1"
    )
    
    print("=" * 60)
    print("1. CREATE RGB LIGHT FROM TEMPLATE")
    print("=" * 60)
    
    # Create device
    rgb_light = vdc.create_vdsd(
        name="Living Room RGB Light",
        group=DSGroup.LIGHT,
        model="RGB-100",
        vendor="Example",
        serial="RGB100-001"
    )
    
    # Configure from template
    rgb_light.configure(RGB_LIGHT_TEMPLATE)
    
    print(f"Created RGB light: {rgb_light}")
    print(f"  - Outputs: {len(rgb_light._outputs)}")
    print(f"  - Buttons: {len(rgb_light._buttons)}")
    print(f"  - Sensors: {len(rgb_light._sensors)}")
    print(f"  - Scenes: {len(rgb_light._scenes)}")
    
    print("\n" + "=" * 60)
    print("2. EXPORT CONFIGURATION")
    print("=" * 60)
    
    # Export configuration
    config = rgb_light.export_configuration()
    
    # Save to JSON file
    with open('rgb_light_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("Configuration exported to rgb_light_config.json")
    print(f"Configuration keys: {list(config.keys())}")
    
    print("\n" + "=" * 60)
    print("3. CLONE DEVICE (with unique dSUID)")
    print("=" * 60)
    
    # Clone device to another room using the proper clone method
    bedroom_light = rgb_light.clone("Bedroom RGB Light")
    
    print(f"Original device: {rgb_light._common_props.get('name')}")
    print(f"  dSUID: {rgb_light.dsuid}")
    print(f"\nCloned device: {bedroom_light._common_props.get('name')}")
    print(f"  dSUID: {bedroom_light.dsuid}")
    print(f"\nUnique dSUIDs: {rgb_light.dsuid != bedroom_light.dsuid}")
    print(f"Same configuration: {len(rgb_light._outputs) == len(bedroom_light._outputs)}")
    
    print("\n" + "=" * 60)
    print("4. APPLY TEMPLATE TO EXISTING DEVICE")
    print("=" * 60)
    
    # Create empty device
    kitchen_light = vdc.create_vdsd(
        name="Kitchen Light",
        group=DSGroup.LIGHT,
        model="RGB-100",
        vendor="Example",
        serial="RGB100-003"
    )
    
    # Apply template configuration
    kitchen_light.configure(RGB_LIGHT_TEMPLATE)
    
    # Apply template configuration
    kitchen_light.configure(RGB_LIGHT_TEMPLATE)
    
    print(f"Created and configured: {kitchen_light}")
    print(f"  Outputs: {len(kitchen_light._outputs)}")
    print(f"  Unique dSUID: {kitchen_light.dsuid}")
    
    print("\n" + "=" * 60)
    print("5. MODIFY CLONED DEVICE")
    print("=" * 60)
    
    # Export bedroom light config
    bedroom_config = bedroom_light.export_configuration()
    
    # Modify configuration - add motion sensor
    bedroom_config['binary_inputs'] = [{
        'name': 'Motion Detector',
        'inputType': 'motion',
        'invert': False,
        'initialState': False
    }]
    
    # Add panic scene
    bedroom_config['scenes'][DSScene.PANIC] = {
        'channels': {
            DSChannelType.BRIGHTNESS: 100.0,
            DSChannelType.HUE: 0.0,
            DSChannelType.SATURATION: 100.0
        },
        'effect': DSSceneEffect.ALERT
    }
    
    # Apply modified configuration
    bedroom_light.configure(bedroom_config)
    
    print("Modified cloned device")
    print(f"  Scenes: {len(bedroom_light._scenes)}")
    print(f"  Binary inputs: {len(bedroom_light._binary_inputs)}")
    print(f"  Different from original: {len(bedroom_light._binary_inputs) != len(rgb_light._binary_inputs)}")
    
    print(f"  Different from original: {len(bedroom_light._binary_inputs) != len(rgb_light._binary_inputs)}")
    
    print("\n" + "=" * 60)
    print("6. CREATE MOTION SENSOR FROM TEMPLATE")
    print("=" * 60)
    
    # Create motion sensor device
    motion_sensor = vdc.create_vdsd(
        name="Hallway Motion Sensor",
        group=DSGroup.SECURITY,
        model="MS-50",
        vendor="Example",
        serial="MS50-001"
    )
    
    # Configure from motion sensor template
    motion_sensor.configure(MOTION_SENSOR_TEMPLATE)
    
    print(f"Created motion sensor: {motion_sensor}")
    print(f"  - Binary inputs: {len(motion_sensor._binary_inputs)}")
    print(f"  - Sensors: {len(motion_sensor._sensors)}")
    
    print("\n" + "=" * 60)
    print("7. LOAD CONFIGURATION FROM FILE")
    print("=" * 60)
    
    # Load previously saved configuration
    with open('rgb_light_config.json', 'r') as f:
        loaded_config = json.load(f)
    
    # Create new device from loaded config
    office_light = vdc.create_vdsd(
        name="Office RGB Light",
        group=DSGroup.LIGHT,
        model="RGB-100",
        vendor="Example",
        serial="RGB100-003"
    )
    
    office_light.configure(loaded_config)
    
    print("Device created from file configuration")
    print(f"  Device: {office_light}")
    print(f"  Unique dSUID: {office_light.dsuid}")
    
    print("\n" + "=" * 60)
    print("8. BULK DEVICE CREATION WITH CLONING")
    print("=" * 60)
    
    # Clone to multiple rooms
    rooms = ["Kitchen", "Bathroom", "Garage"]
    
    for room in rooms:
        cloned = rgb_light.clone(f"{room} Light")
        print(f"  Created: {cloned._common_props.get('name')} (dSUID: {cloned.dsuid[:16]}...)")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total devices created: {len(vdc._vdsds)}")
    print(f"All devices configured from templates")
    print(f"Configuration saved to YAML: config_demo.yaml")
    
    # Start host briefly to demonstrate persistence
    await host.start()
    await asyncio.sleep(1)
    await host.stop()
    
    print("\nConfiguration persisted to disk!")


if __name__ == "__main__":
    asyncio.run(main())
