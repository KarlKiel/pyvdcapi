"""
Example: Complete vDC Light Device with Motion Sensor

This example demonstrates a complete virtual device that combines
multiple components:
- Output channel (brightness control)
- Button input (wall switch)
- Binary input (motion detector)
- Sensor (light level sensor)

The device implements automation logic:
- Motion triggers lights on
- Manual button overrides automation
- Light sensor prevents daylight activation
- Auto-off timer when motion stops

This showcases the component system working together.
"""

import asyncio
import logging
from pyvdcapi.entities.vdc_host import VdcHost
from pyvdcapi.entities.vdc import Vdc
from pyvdcapi.entities.vdsd import VdSD
from pyvdcapi.components import Output, OutputChannel, Button, BinaryInput, Sensor
from pyvdcapi.core.constants import DSGroup, DSChannelType, DSScene, ButtonEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HardwareInterface:
    """
    Mock hardware interface for demonstration.
    
    In a real implementation, this would interface with:
    - GPIO pins for outputs
    - PWM controllers for dimming
    - I2C/SPI sensors
    - Interrupt handlers for inputs
    """
    
    def __init__(self):
        self.brightness_value = 0.0
        self.manual_override = False
        
    def set_brightness(self, value: float):
        """Set physical LED brightness (0-100%)."""
        self.brightness_value = value
        logger.info(f"Hardware: Set brightness to {value}%")
    
    def read_light_sensor(self) -> float:
        """Read ambient light level in lux."""
        # Mock: Return simulated value
        return 300.0
    
    def setup_motion_interrupt(self, callback):
        """Set up hardware interrupt for motion detector."""
        logger.info("Hardware: Motion detector interrupt configured")
        # In real hardware, this would configure GPIO interrupt


async def main():
    """Run the example device."""
    
    # Create vDC host
    host = VdcHost(
        name="Motion Light Controller",
        port=8440,
        persistence_file="motion_light.yaml"
    )
    
    # Create vDC for light devices
    vdc = host.create_vdc(
        vendor="Example Inc",
        model_name="Smart Motion Light",
        model_guid="example-motion-light-v1"
    )
    
    # Create virtual device (smart light)
    device = vdc.create_vdsd(
        name="Living Room Light",
        group=DSGroup.LIGHT,
        model="ML-100",
        vendor="Example",
        serial="ML100-001"
    )
    
    # Hardware interface
    hardware = HardwareInterface()
    
    # ═══════════════════════════════════════════════════════════
    # Component 1: Output with Brightness Channel
    # ═══════════════════════════════════════════════════════════
    
    # Create output container
    main_output = Output(
        vdsd=device,
        output_id=0,
        output_function="dimmer",
        output_mode="gradual",
        push_changes=True
    )
    
    # Create brightness channel
    brightness = OutputChannel(
        vdsd=device,
        channel_type=DSChannelType.BRIGHTNESS,
        name="Main Light",
        min_value=0.0,
        max_value=100.0,
        default_value=0.0
    )
    
    # Connect to hardware
    def update_hardware_brightness(channel_type: DSChannelType, value: float):
        """Called when vdSM changes brightness."""
        hardware.set_brightness(value)
    
    brightness.on_hardware_change(update_hardware_brightness)
    
    # Add channel to output
    main_output.add_channel(brightness)
    
    # Add output to device (not just the channel)
    # device.add_output(main_output)  # This would be the proper way
    
    # ═══════════════════════════════════════════════════════════
    # Component 2: Button (Wall Switch)
    # ═══════════════════════════════════════════════════════════
    
    wall_switch = Button(
        vdsd=device,
        name="Wall Switch",
        button_type="toggle",
        element=0
    )
    
    def handle_button_event(button_id: int, event_type: ButtonEvent):
        """Handle wall switch events."""
        logger.info(f"Wall switch: {event_type}")
        
        if event_type == ButtonEvent.SINGLE_PRESS:
            # Toggle light
            current = brightness.get_value()
            if current > 0:
                brightness.set_value(0.0)  # Turn off
                hardware.manual_override = False
            else:
                brightness.set_value(100.0)  # Turn on full
                hardware.manual_override = True
        
        elif event_type == ButtonEvent.LONG_PRESS:
            # Start dimming
            logger.info("Long press: Start dimming")
            # Could implement smooth dimming here
        
        elif event_type == ButtonEvent.DOUBLE_PRESS:
            # Set to 50%
            brightness.set_value(50.0)
            hardware.manual_override = True
    
    wall_switch.on_event(handle_button_event)
    
    # Add to device
    device.add_button(wall_switch)
    
    # ═══════════════════════════════════════════════════════════
    # Component 3: Binary Input (Motion Detector)
    # ═══════════════════════════════════════════════════════════
    
    motion_detector = BinaryInput(
        vdsd=device,
        name="Motion Detector",
        input_type="motion",
        input_id=0,
        initial_state=False
    )
    
    # Auto-off timer
    auto_off_task = None
    
    async def auto_off_timer():
        """Turn off lights after 5 minutes of no motion."""
        await asyncio.sleep(300)  # 5 minutes
        
        if not hardware.manual_override:
            logger.info("Auto-off: No motion for 5 minutes, turning off")
            brightness.set_value(0.0)
    
    def handle_motion_change(input_id: int, state: bool):
        """Handle motion detector state changes."""
        nonlocal auto_off_task
        
        if state:
            # Motion detected
            logger.info("Motion detected!")
            
            # Cancel any pending auto-off
            if auto_off_task and not auto_off_task.done():
                auto_off_task.cancel()
                auto_off_task = None
            
            # Turn on light if not manual override and it's dark
            if not hardware.manual_override:
                # Check light sensor
                ambient = light_sensor.get_value()
                if ambient is not None and ambient < 100.0:  # Dark
                    logger.info("Dark and motion detected - turning on light")
                    brightness.set_value(75.0)  # Turn on to 75%
                else:
                    logger.info("Bright enough - not turning on light")
        
        else:
            # No motion
            logger.info("Motion stopped")
            
            # Start auto-off timer if light is on and not manual override
            if not hardware.manual_override and brightness.get_value() > 0:
                logger.info("Starting 5-minute auto-off timer")
                auto_off_task = asyncio.create_task(auto_off_timer())
    
    motion_detector.on_change(handle_motion_change)
    
    # Simulate hardware motion detection
    hardware.setup_motion_interrupt(lambda: motion_detector.set_state(True))
    
    # ═══════════════════════════════════════════════════════════
    # Component 4: Sensor (Ambient Light)
    # ═══════════════════════════════════════════════════════════
    
    light_sensor = Sensor(
        vdsd=device,
        name="Ambient Light",
        sensor_type="illuminance",
        unit="lux",
        min_value=0.0,
        max_value=10000.0,
        resolution=1.0,
        initial_value=300.0
    )
    
    def handle_light_change(sensor_id: int, value: float):
        """Handle ambient light changes."""
        if value is None:
            logger.error("Light sensor error!")
            return
        
        logger.info(f"Ambient light: {value} lux")
        
        # If it gets bright enough, turn off auto-controlled lights
        if value > 500.0 and not hardware.manual_override:
            current = brightness.get_value()
            if current > 0:
                logger.info("Daylight detected - turning off lights")
                brightness.set_value(0.0)
    
    # Trigger callback only if light changes by ≥50 lux
    light_sensor.on_change(handle_light_change, hysteresis=50.0)
    
    # Periodic sensor reading
    async def poll_light_sensor():
        """Poll light sensor every 30 seconds."""
        while True:
            await asyncio.sleep(30)
            value = hardware.read_light_sensor()
            light_sensor.update_value(value)
    
    asyncio.create_task(poll_light_sensor())
    
    # ═══════════════════════════════════════════════════════════
    # Start the vDC host
    # ═══════════════════════════════════════════════════════════
    
    logger.info("Starting vDC host...")
    await host.start()
    
    logger.info("vDC host running. Device ready!")
    logger.info("Device has:")
    logger.info("  - Brightness output (0-100%)")
    logger.info("  - Wall switch button")
    logger.info("  - Motion detector")
    logger.info("  - Ambient light sensor")
    logger.info("")
    logger.info("Automation rules:")
    logger.info("  - Motion + dark = turn on light (75%)")
    logger.info("  - No motion for 5min = auto-off")
    logger.info("  - Bright daylight = auto-off")
    logger.info("  - Button press = manual override")
    logger.info("")
    logger.info("Press Ctrl+C to stop")
    
    # ═══════════════════════════════════════════════════════════
    # Simulate some events
    # ═══════════════════════════════════════════════════════════
    
    async def simulate_events():
        """Simulate some hardware events for demonstration."""
        
        # Wait for startup
        await asyncio.sleep(2)
        
        logger.info("\n" + "="*60)
        logger.info("SIMULATION: Motion detected")
        logger.info("="*60)
        motion_detector.set_state(True)
        
        await asyncio.sleep(3)
        
        logger.info("\n" + "="*60)
        logger.info("SIMULATION: Button single press")
        logger.info("="*60)
        wall_switch.press()
        await asyncio.sleep(0.1)
        wall_switch.release()
        
        await asyncio.sleep(5)
        
        logger.info("\n" + "="*60)
        logger.info("SIMULATION: Motion stopped")
        logger.info("="*60)
        motion_detector.set_state(False)
        
        await asyncio.sleep(3)
        
        logger.info("\n" + "="*60)
        logger.info("SIMULATION: Ambient light increased (daylight)")
        logger.info("="*60)
        light_sensor.update_value(600.0)
        
        await asyncio.sleep(5)
        
        logger.info("\n" + "="*60)
        logger.info("SIMULATION: Button long press")
        logger.info("="*60)
        wall_switch.press()
        await asyncio.sleep(1.5)  # Hold for 1.5 seconds
        wall_switch.release()
    
    asyncio.create_task(simulate_events())
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        await host.stop()


if __name__ == "__main__":
    asyncio.run(main())
