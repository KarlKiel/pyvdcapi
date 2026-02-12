#!/usr/bin/env python3
"""
Example 7: Automatic Input Binding - Property-Driven

This example demonstrates how the vDC API properties (already in templates)
automatically determine the binding behavior. No separate "binding" configuration
is needed - the component properties tell us everything!

Key Points:
- Buttons: ALWAYS event-driven (no polling needed)
- Binary Inputs: Use inputType property to guide binding
- Sensors: Use min_push_interval, changes_only_interval properties
- Outputs: Always bidirectional (push_changes=True)
"""

import asyncio
from pyvdcapi.entities.vdc_host import VdcHost
from pyvdcapi.core.constants import DSGroup


class NativeHardware:
    """
    Simulated native device hardware.
    
    This represents the hardware layer that vDC components bind to.
    Components map their vDC API properties (value, clickType, etc.)
    to these native device variables.
    """
    
    def __init__(self):
        # Native device variables
        self.temperature = 22.5
        self.motion_detected = False
        self.brightness = 0.0
        
        # Event subscribers (hardware supports callbacks)
        self._button_callbacks = []
        self._motion_callbacks = []
    
    # === POLLING INTERFACE (for components that poll) ===
    
    def get_temperature(self):
        """Native variable for sensor 'value' property (polling)."""
        return self.temperature
    
    def get_motion_state(self):
        """Native variable for binary input 'value' property (polling)."""
        return self.motion_detected
    
    def get_brightness(self):
        """Native variable for output channel 'value' property (bi-directional)."""
        return self.brightness
    
    def set_brightness(self, value):
        """Native variable setter for output channel (vdSM→hardware)."""
        self.brightness = value
        print(f"  Hardware: Brightness set to {value:.1f}%")
    
    # === EVENT INTERFACE (for components that use events) ===
    
    def on_button_event(self, callback):
        """Register callback for button clickType/actionID events."""
        self._button_callbacks.append(callback)
    
    def on_motion_change(self, callback):
        """Register callback for motion detection events."""
        self._motion_callbacks.append(callback)
    
    # === HARDWARE SIMULATION ===
    
    def simulate_button_press(self, click_type):
        """Simulate button hardware generating clickType event."""
        print(f"  Hardware: Button click type {click_type}")
        for cb in self._button_callbacks:
            cb(click_type)
    
    def simulate_motion_event(self, detected):
        """Simulate motion sensor hardware generating event."""
        self.motion_detected = detected
        print(f"  Hardware: Motion {'detected' if detected else 'cleared'}")
        for cb in self._motion_callbacks:
            cb(detected)


async def example_button_binding():
    """
    Buttons: ALWAYS Event-Driven
    
    Buttons NEVER need polling because they report discrete events.
    Buttons operate in one of two modes (set at creation, never both):
    - Standard mode: Reports clickType (0-14, 255) and value (active/inactive)
    - Action mode: Reports actionId (scene id) and actionMode (0=normal, 1=force, 2=undo)
    
    The relevant properties must be bound to native device variables that
    change on button activity.
    """
    print("\n" + "="*70)
    print("Example 1: Button Binding (Always Event-Driven)")
    print("="*70)
    
    # Create VdC Host and device
    vdc_host = VdcHost(
        name="ButtonDemo",
        port=8444,
        mac_address="00:11:22:33:44:55",
        vendor_id="Demo",
        persistence_file="button_demo.yaml",
    )
    vdc = vdc_host.create_vdc(name="ButtonVdc", model="v1.0")
    device = vdc.create_vdsd(name="WallSwitch", model="Button", primary_group=DSGroup.YELLOW)
    
    # Add button in STANDARD MODE (clickType/value) - MUST be defined at creation
    button = device.add_button_input(
        button_type=1,  # Single button
        button_id=0,
        name="Wall Button",
        use_action_mode=False,  # Standard mode: clickType/value (REQUIRED)
        group=1,
        mode=0,
    )
    
    print(f"✓ Created button: {button.name}")
    print("  - Button type: 1 (single button)")
    print("  - Button mode: STANDARD (clickType/value)")
    print("  - Binding: ALWAYS event-driven (no polling option)")
    
    # Example: Action mode button (actionId/actionMode)
    scene_button = device.add_button_input(
        button_type=1,  # Single button
        button_id=1,
        name="Scene Button",
        use_action_mode=True,  # Action mode: actionId/actionMode (REQUIRED)
        group=1,
    )
    
    print(f"✓ Created scene button: {scene_button.name}")
    print("  - Button mode: ACTION (actionId/actionMode)")
    
    # Create hardware
    hardware = NativeHardware()
    
    # Bind using vDC API properties - buttons are ALWAYS event-driven
    device.bind_inputs_auto({
        "buttons": [
            {"register": hardware.on_button_event},  # 'register' is required for buttons
        ]
    })
    
    print("✓ Buttons bound to native hardware")
    print("  - Standard mode: clickType property → hardware button event variable")
    print("  - Action mode: actionId property → hardware scene call variable")
    
    # Simulate button press
    print("\nSimulating button press...")
    hardware.simulate_button_press(1)  # Single click (clickType=1)
    await asyncio.sleep(0.1)


async def example_binary_input_binding():
    """
    Binary Inputs: Property-Driven
    
    The inputType property defines whether the vDC pushes updates or
    only responds to polls from dSS. The 'value' or 'extendedValue'
    property is bound to a boolean or integer native device variable.
    """
    print("\n" + "="*70)
    print("Example 2: Binary Input Binding (Event-Driven)")
    print("="*70)
    
    vdc_host = VdcHost(
        name="BinaryDemo",
        port=8445,
        mac_address="00:11:22:33:44:66",
        vendor_id="Demo",
        persistence_file="binary_demo.yaml",
    )
    vdc = vdc_host.create_vdc(name="BinaryVdc", model="v1.0")
    device = vdc.create_vdsd(name="MotionSensor", model="Motion", primary_group=DSGroup.YELLOW)
    
    # Add binary input - inputType property defines behavior
    binary = device.add_binary_input(
        input_type=1,  # Presence (typically push)
        input_usage=1,  # Room
        name="Motion Detector",
    )
    
    print(f"✓ Created binary input: {binary.name}")
    print(f"  - Input type: {binary.input_type} (presence)")
    print("  - Binding: Event-driven (hardware supports callbacks)")
    
    hardware = NativeHardware()
    
    # Bind using hardware capability
    device.bind_inputs_auto({
        "binary_inputs": [
            {"register": hardware.on_motion_change},  # Event-driven (preferred)
            # Could also use: {"getter": hardware.get_motion_state, "poll_interval": 0.2}
        ]
    })
    
    print("✓ Binary input bound to native hardware")
    print("  - 'value' property → hardware motion variable")
    
    # Simulate motion event
    print("\nSimulating motion detection...")
    hardware.simulate_motion_event(True)
    await asyncio.sleep(0.5)
    hardware.simulate_motion_event(False)
    await asyncio.sleep(0.1)


async def example_sensor_binding():
    """
    Sensors: Throttled Push
    
    Sensors use min_push_interval and changes_only_interval properties
    to control push throttling. The 'value' property is bound to a native
    device variable. Hardware can update faster, but pushes are throttled.
    """
    print("\n" + "="*70)
    print("Example 3: Sensor Binding (Polling with Throttling)")
    print("="*70)
    
    vdc_host = VdcHost(
        name="SensorDemo",
        port=8446,
        mac_address="00:11:22:33:44:77",
        vendor_id="Demo",
        persistence_file="sensor_demo.yaml",
    )
    vdc = vdc_host.create_vdc(name="SensorVdc", model="v1.0")
    device = vdc.create_vdsd(name="TempSensor", model="Sensor", primary_group=DSGroup.YELLOW)
    
    # Add sensor - vDC API properties define behavior
    sensor = device.add_sensor(
        sensor_type=9,  # Temperature
        sensor_usage=1,  # Room
        min_value=0.0,
        max_value=100.0,
        resolution=0.1,
        update_interval=5,  # Normal update frequency
        name="Temperature",
    )
    
    print(f"✓ Created sensor: {sensor.name}")
    print(f"  - Sensor type: {sensor.sensor_type} (temperature)")
    print(f"  - Update interval: {sensor.update_interval}s")
    print(f"  - Min push interval: {sensor.min_push_interval}s (throttling)")
    
    hardware = NativeHardware()
    
    # Bind using vDC API properties
    device.bind_inputs_auto({
        "sensors": [
            {
                "getter": hardware.get_temperature,  # Poll at min_push_interval rate
                # Optional: override poll interval
                # "poll_interval": 1.0,
                # Optional: add event binding too
                # "register": hardware.on_temp_change,
            }
        ]
    })
    
    print("✓ Sensor bound to native hardware")
    print("  - 'value' property → hardware temperature variable")
    print("  - Polling uses sensor.min_push_interval (default)")
    
    # Hardware might update faster, but pushes are throttled
    print("\nNote: Hardware can update faster than min_push_interval,")
    print("      but vDC throttles pushes to dSS per API specification")


async def example_output_binding():
    """
    Outputs: Always Bidirectional
    
    The output's push_changes setting (ALWAYS True) determines that
    bi-directional binding is required. Channel 'value' property is
    bound to a native variable. Both getter and setter are needed.
    """
    print("\n" + "="*70)
    print("Example 4: Output Binding (Always Bidirectional)")
    print("="*70)
    
    vdc_host = VdcHost(
        name="OutputDemo",
        port=8447,
        mac_address="00:11:22:33:44:88",
        vendor_id="Demo",
        persistence_file="output_demo.yaml",
    )
    vdc = vdc_host.create_vdc(name="OutputVdc", model="v1.0")
    device = vdc.create_vdsd(name="Dimmer", model="Light", primary_group=DSGroup.YELLOW)
    
    # Add output channel
    output = device.create_output()
    channel = output.add_output_channel(
        channel_type=1,  # Brightness
        min_value=0.0,
        max_value=100.0,
        resolution=0.1,
        initial_value=0.0,
    )
    
    print(f"✓ Created output channel")
    print(f"  - Channel type: {channel.channel_type} (brightness)")
    print(f"  - Push changes: {output.push_changes} (ALWAYS True)")
    
    hardware = NativeHardware()
    
    # Bind output channel - ALWAYS bidirectional
    device.bind_output_channel(
        channel_type=1,
        getter=hardware.get_brightness,  # Hardware→vdSM
        setter=hardware.set_brightness,  # vdSM→hardware
        poll_interval=0.1,  # Check for hardware changes
    )
    
    print("✓ Output channel bound to native hardware")
    print("  - 'value' property → hardware brightness variable")
    print("  - Bidirectional: getter AND setter required")
    
    # Simulate vdSM setting brightness
    print("\nSimulating vdSM command (set brightness to 75%)...")
    channel.set_value(75.0)
    await asyncio.sleep(0.1)


async def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("AUTOMATIC INPUT BINDING - Property-Driven")
    print("="*70)
    print("\nThe vDC API properties define binding behavior:")
    print("• Buttons: ALWAYS event-driven (clickType is discrete event)")
    print("• Binary Inputs: inputType property guides binding choice")
    print("• Sensors: min_push_interval/changes_only_interval control throttling")
    print("• Outputs: push_changes=True (ALWAYS bidirectional)")
    
    await example_button_binding()
    await example_binary_input_binding()
    await example_sensor_binding()
    await example_output_binding()
    
    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70)
    print("\nKey Takeaway: No separate 'binding' config needed!")
    print("The vDC API properties already define the behavior.")


if __name__ == "__main__":
    asyncio.run(main())
