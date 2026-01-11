"""
Demo: Run vDC Host with vdSM Simulator

This script demonstrates the complete vDC API protocol by:
1. Creating and starting a vDC host with devices
2. Running a vdSM simulator that discovers and interacts with the devices
3. Showing all protocol messages and interactions

Usage:
    python examples/demo_with_simulator.py
"""

import asyncio
import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pyvdcapi import VdcHost
from pyvdcapi.core.constants import DSGroup, DSChannelType
from examples.vdsm_simulator import VdsmSimulator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def create_demo_setup():
    """Create a vDC host with some example devices."""
    logger.info("\n" + "=" * 80)
    logger.info("CREATING vDC HOST WITH DEMO DEVICES")
    logger.info("=" * 80)
    
    # Create vDC host
    host = VdcHost(
        name="Demo Smart Home Hub",
        port=8444,
        model="Demo vDC Host",
        model_uid="demo-vdc-host",
        persistence_file="demo_config.yaml",
        vendorName="PyVDC Demo"
    )
    
    logger.info(f"✓ Created vDC host: {host._common_props.get_name()}")
    
    # Create a vDC for lights
    lights_vdc = host.create_vdc(
        vendor="Demo Vendor",
        model_name="Smart Lights Controller",
        model_guid="demo-lights-vdc-v1",
        implementationId="x-demo-lights-vdc"
    )
    
    logger.info(f"✓ Created vDC: Smart Lights Controller")
    
    # Create some light devices
    logger.info("\nCreating light devices...")
    
    # 1. Dimmable white light
    living_room_light = lights_vdc.create_vdsd(
        name="Living Room Ceiling Light",
        model="SmartBulb Pro",
        model_uid="smartbulb-pro",
        primary_group=DSGroup.YELLOW,  # Light group
        displayId="LR-CEIL-001",
        vendorName="Demo Lights Inc"
    )
    
    # Add brightness channel
    living_room_light.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        name="brightness",
        min_value=0.0,
        max_value=100.0,
        resolution=1.0
    )
    
    # Add on/off button
    living_room_light.add_button(
        button_type=0,  # Single press
        name="Main Switch",
        on_click=lambda: logger.info("Living room light button clicked!")
    )
    
    logger.info("  ✓ Living Room Ceiling Light (dimmable)")
    
    # 2. RGB color light
    bedroom_light = lights_vdc.create_vdsd(
        name="Bedroom RGB Strip",
        model="ColorStrip Max",
        model_uid="colorstrip-max",
        primary_group=DSGroup.YELLOW,
        displayId="BR-RGB-001",
        vendorName="Demo Lights Inc"
    )
    
    # Add brightness, hue, saturation channels
    bedroom_light.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        name="brightness"
    )
    bedroom_light.add_output_channel(
        channel_type=DSChannelType.HUE,
        name="hue"
    )
    bedroom_light.add_output_channel(
        channel_type=DSChannelType.SATURATION,
        name="saturation"
    )
    
    logger.info("  ✓ Bedroom RGB Strip (RGB color)")
    
    # Create a vDC for sensors
    sensors_vdc = host.create_vdc(
        vendor="Demo Vendor",
        model_name="Environmental Sensors",
        model_guid="demo-sensors-vdc-v1",
        implementationId="x-demo-sensors-vdc"
    )
    
    logger.info(f"\n✓ Created vDC: Environmental Sensors")
    
    # 3. Multi-sensor device
    kitchen_sensor = sensors_vdc.create_vdsd(
        name="Kitchen Multisensor",
        model="SensorHub v2",
        model_uid="sensorhub-v2",
        primary_group=DSGroup.BLACK,  # Joker/generic
        displayId="KITCHEN-SENS-001",
        vendorName="Demo Sensors Co"
    )
    
    # Add temperature sensor
    kitchen_sensor.add_sensor(
        sensor_type="temperature",
        name="Temperature",
        unit="°C",
        min_value=-20.0,
        max_value=60.0
    )
    
    # Add humidity sensor
    kitchen_sensor.add_sensor(
        sensor_type="humidity",
        name="Humidity",
        unit="%",
        min_value=0.0,
        max_value=100.0
    )
    
    # Add motion sensor (binary input)
    kitchen_sensor.add_button(
        button_type=0,
        name="Motion Detector",
        on_click=lambda: logger.info("Motion detected in kitchen!")
    )
    
    logger.info("  ✓ Kitchen Multisensor (temp, humidity, motion)")
    
    logger.info(f"\n✓ Setup complete:")
    logger.info(f"  - 2 vDCs")
    logger.info(f"  - 3 devices (2 lights, 1 sensor)")
    
    return host


async def run_demo():
    """Run the complete demo."""
    # Create vDC host with devices
    host = await create_demo_setup()
    
    # Start the vDC host
    logger.info("\n" + "=" * 80)
    logger.info("STARTING vDC HOST SERVER")
    logger.info("=" * 80)
    await host.start()
    logger.info("✓ vDC host is running on port 8444")
    
    # Give the server a moment to start
    await asyncio.sleep(0.5)
    
    # Create and run simulator
    logger.info("\n" + "=" * 80)
    logger.info("STARTING vdSM SIMULATOR")
    logger.info("=" * 80)
    
    simulator = VdsmSimulator(host='localhost', port=8444)
    
    try:
        # Connect to vDC host
        if not await simulator.connect():
            logger.error("Failed to connect to vDC host")
            return
        
        # Perform handshake
        if not await simulator.send_hello():
            logger.error("Handshake failed")
            return
        
        # Discover all entities
        await simulator.full_discovery()
        
        # Run some interactive commands
        if simulator.devices:
            logger.info("\n" + "=" * 80)
            logger.info("RUNNING INTERACTIVE TEST COMMANDS")
            logger.info("=" * 80)
            
            # Find the first light device
            light_device = None
            for device in simulator.devices.values():
                if device.primary_group == 1:  # Light group
                    light_device = device
                    break
            
            if light_device:
                logger.info(f"\nTesting with device: {light_device.name}")
                
                # Turn on to 50%
                logger.info("\n1. Setting brightness to 50%...")
                await simulator.set_output_value(
                    light_device.dsuid, 
                    DSChannelType.BRIGHTNESS, 
                    50.0, 
                    transition_time=1.0
                )
                await asyncio.sleep(2)
                
                # Turn on to 100%
                logger.info("\n2. Setting brightness to 100%...")
                await simulator.set_output_value(
                    light_device.dsuid, 
                    DSChannelType.BRIGHTNESS, 
                    100.0, 
                    transition_time=2.0
                )
                await asyncio.sleep(3)
                
                # Call scene 5 (preset)
                logger.info("\n3. Calling scene 5...")
                await simulator.call_scene(light_device.dsuid, 5, force=True)
                await asyncio.sleep(1)
                
                # Save current state as scene 1
                logger.info("\n4. Saving current state to scene 1...")
                await simulator.save_scene(light_device.dsuid, 1)
                await asyncio.sleep(1)
                
                logger.info("\n✓ Test commands completed successfully")
        
        # Keep running for a bit
        logger.info("\n" + "=" * 80)
        logger.info("DEMO RUNNING - Press Ctrl+C to stop")
        logger.info("=" * 80)
        await asyncio.sleep(5)
        
    except KeyboardInterrupt:
        logger.info("\nStopping demo...")
    finally:
        # Cleanup
        await simulator.disconnect()
        await host.stop()
        logger.info("\n✓ Demo stopped cleanly")


if __name__ == '__main__':
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        logger.info("\nDemo interrupted by user")
