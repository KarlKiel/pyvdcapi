#!/usr/bin/env python3
"""
Example: Using API-compliant ButtonInput

This example demonstrates the new ButtonInput component which accepts
clickType values directly, as specified in vDC API section 4.2.

This is the RECOMMENDED approach for new implementations as it matches
the vDC API specification where clickType is an INPUT (not calculated).

Three approaches are shown:
1. Direct clickType input (smart button hardware)
2. Simple press/release with state machine (dumb button hardware)
3. Custom pattern detection logic
"""

import sys
import os
import time
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pyvdcapi import VdcHost, Vdc, VdSD
from pyvdcapi.core.constants import DSDeviceType, DSChannelType
from pyvdcapi.components import ButtonInput, DSButtonStateMachine


def example_1_direct_clicktype():
    """
    Example 1: Direct clickType input from smart button hardware.
    
    Use this when your button hardware detects click patterns internally
    and provides clickType values directly.
    """
    print("=" * 70)
    print("Example 1: Direct clickType Input (Smart Button Hardware)")
    print("=" * 70)
    print()
    
    # Create device hierarchy
    vdc_host = VdcHost(dsuid="vdc_host_button_demo", name="Button Demo Host")
    vdc = Vdc(dsuid="vdc_button_demo", name="Button Demo vDC", model_name="DemoVdc")
    vdc_host.add_vdc(vdc)
    
    # Create a light device
    light = VdSD(
        vdc=vdc,
        name="Smart Light",
        model_name="SmartBulb RGB",
        device_type=DSDeviceType.LIGHT,
        dsuid="light_001"
    )
    vdc.add_vdsd(light)
    
    # Add output channel
    brightness = light.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0
    )
    
    # Add API-compliant button input
    button = light.add_button_input(
        name="Smart Button",
        button_type=1,  # Single pushbutton
        group=1,
        function=0
    )
    
    print(f"Created device: {light.name}")
    print(f"  - Brightness channel: {brightness}")
    print(f"  - Button input: {button}")
    print()
    
    # Simulate smart button hardware sending clickType events
    print("Simulating smart button hardware events:")
    print()
    
    print("1. Single tap (tip_1x)...")
    button.set_click_type(0)  # tip_1x
    time.sleep(0.1)
    print(f"   Button state: {button.get_state()}")
    print()
    
    print("2. Double tap (tip_2x)...")
    button.set_click_type(1)  # tip_2x
    time.sleep(0.1)
    print(f"   Button state: {button.get_state()}")
    print()
    
    print("3. Long press started (hold_start)...")
    button.set_value(True)  # Pressed
    button.set_click_type(4)  # hold_start
    time.sleep(0.3)
    print(f"   Button state: {button.get_state()}")
    print()
    
    print("4. Long press continuing (hold_repeat)...")
    button.set_click_type(5)  # hold_repeat
    time.sleep(0.3)
    print(f"   Button state: {button.get_state()}")
    print()
    
    print("5. Long press released (hold_end)...")
    button.set_value(False)  # Released
    button.set_click_type(6)  # hold_end
    time.sleep(0.1)
    print(f"   Button state: {button.get_state()}")
    print()
    
    print("6. Local on action (local_on)...")
    button.set_click_type(12)  # local_on
    time.sleep(0.1)
    print(f"   Button state: {button.get_state()}")
    print()


def example_2_state_machine():
    """
    Example 2: Simple press/release with DSButtonStateMachine.
    
    Use this when your button hardware only provides press/release events
    and you want digitalSTROM-compatible timing pattern detection.
    """
    print("=" * 70)
    print("Example 2: State Machine for Timing-Based Detection")
    print("=" * 70)
    print()
    
    # Create device hierarchy
    vdc = Vdc(dsuid="vdc_dimmer_demo", name="Dimmer Demo vDC", model_name="DemoVdc")
    
    dimmer = VdSD(
        vdc=vdc,
        name="Dimmable Light",
        model_name="DimmerLight",
        device_type=DSDeviceType.LIGHT,
        dsuid="dimmer_001"
    )
    vdc.add_vdsd(dimmer)
    
    # Add output
    brightness = dimmer.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0
    )
    
    # Add button input with state machine
    button_input = dimmer.add_button_input(
        name="Dimmer Control",
        button_type=1,
        group=1
    )
    
    # Create state machine for timing-based clickType detection
    state_machine = DSButtonStateMachine(
        button_input,
        enable_tip_to_click=True,
        enable_hold_repeat=True
    )
    
    print(f"Created device: {dimmer.name}")
    print(f"  - Brightness channel: {brightness}")
    print(f"  - Button input with state machine: {button_input}")
    print()
    
    # Simulate hardware press/release events
    print("Simulating hardware press/release events:")
    print()
    
    print("1. Quick tap (single press)...")
    state_machine.on_press()
    time.sleep(0.1)
    state_machine.on_release()
    time.sleep(0.6)  # Wait for tip→click conversion
    print(f"   Detected: {button_input.get_state()}")
    print()
    
    print("2. Double tap...")
    state_machine.on_press()
    time.sleep(0.1)
    state_machine.on_release()
    time.sleep(0.2)
    state_machine.on_press()
    time.sleep(0.1)
    state_machine.on_release()
    time.sleep(0.6)
    print(f"   Detected: {button_input.get_state()}")
    print()
    
    print("3. Long press...")
    state_machine.on_press()
    time.sleep(0.5)  # Hold for 500ms
    print(f"   After hold: {button_input.get_state()}")
    state_machine.on_release()
    time.sleep(0.1)
    print(f"   After release: {button_input.get_state()}")
    print()


def example_3_custom_logic():
    """
    Example 3: Custom pattern detection logic.
    
    Use this when you need custom button behavior not covered by
    the standard state machine.
    """
    print("=" * 70)
    print("Example 3: Custom Pattern Detection Logic")
    print("=" * 70)
    print()
    
    # Create device
    vdc = Vdc(dsuid="vdc_custom_demo", name="Custom Demo vDC", model_name="DemoVdc")
    device = VdSD(
        vdc=vdc,
        name="Custom Device",
        model_name="CustomDevice",
        device_type=DSDeviceType.LIGHT,
        dsuid="custom_001"
    )
    vdc.add_vdsd(device)
    
    # Add button
    button = device.add_button_input(
        name="Gesture Button",
        button_type=1
    )
    
    print(f"Created device: {device.name}")
    print(f"  - Button: {button}")
    print()
    
    # Custom pattern detector
    class CustomPatternDetector:
        def __init__(self, button_input):
            self.button_input = button_input
            self.press_times = []
            self.last_press = 0
            
        def on_press(self):
            current = time.time()
            
            # Clear old presses (>2 seconds old)
            self.press_times = [t for t in self.press_times if current - t < 2.0]
            
            # Add new press
            self.press_times.append(current)
            
            # Detect patterns
            if len(self.press_times) == 3:
                # Three quick presses in sequence
                if self.press_times[2] - self.press_times[0] < 1.0:
                    print("   Detected: Triple tap pattern!")
                    self.button_input.set_click_type(2)  # tip_3x
                    self.press_times = []
            elif len(self.press_times) == 2:
                # Two presses - check spacing
                if self.press_times[1] - self.press_times[0] < 0.3:
                    print("   Detected: Fast double tap!")
                    self.button_input.set_click_type(1)  # tip_2x
                elif self.press_times[1] - self.press_times[0] < 1.0:
                    print("   Detected: Slow double tap!")
                    self.button_input.set_click_type(8)  # click_2x
            
            self.last_press = current
    
    detector = CustomPatternDetector(button)
    
    print("Testing custom patterns:")
    print()
    
    print("1. Single tap...")
    detector.on_press()
    time.sleep(0.1)
    button.set_click_type(0)  # Manually set since no release tracking
    print(f"   State: {button.get_state()}")
    print()
    
    print("2. Fast double tap (< 300ms)...")
    detector.on_press()
    time.sleep(0.2)
    detector.on_press()
    time.sleep(0.1)
    print(f"   State: {button.get_state()}")
    print()
    
    print("3. Slow double tap (< 1s)...")
    time.sleep(1.5)  # Reset
    detector.on_press()
    time.sleep(0.6)
    detector.on_press()
    time.sleep(0.1)
    print(f"   State: {button.get_state()}")
    print()


def main():
    """Run all examples."""
    print()
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "API-Compliant ButtonInput Examples" + " " * 19 + "║")
    print("╚" + "=" * 68 + "╝")
    print()
    
    # Run examples
    example_1_direct_clicktype()
    print("\n" + "-" * 70 + "\n")
    
    example_2_state_machine()
    print("\n" + "-" * 70 + "\n")
    
    example_3_custom_logic()
    
    print()
    print("=" * 70)
    print("All examples completed successfully!")
    print()
    print("Key Takeaways:")
    print("  • ButtonInput accepts clickType directly (API-compliant)")
    print("  • Use ButtonInput for all new implementations")
    print("  • DSButtonStateMachine provides optional timing detection")
    print("  • Custom logic is easy to implement")
    print("  • Legacy Button class remains for backward compatibility")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
