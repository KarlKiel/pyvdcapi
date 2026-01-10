"""
Button - User interaction input for vDC devices.

A Button represents a physical or virtual button/switch that generates
events when activated by a user. Buttons are fundamental input devices
in the digitalSTROM ecosystem.

Button Types and Events:
┌──────────────────────────────────────────────────────────┐
│ Button Event Types                                       │
├──────────────────────────────────────────────────────────┤
│ 0: Single Press                                          │
│    - Quick press and release                             │
│    - Most common button action                           │
│    - Example: Toggle light on/off                        │
│                                                          │
│ 1: Double Press                                          │
│    - Two quick presses in succession                     │
│    - Requires timing detection                           │
│    - Example: Switch to preset scene                     │
│                                                          │
│ 2: Long Press                                            │
│    - Press and hold for extended time                    │
│    - Continuous action while held                        │
│    - Example: Dim up/down                                │
│                                                          │
│ 3: Release                                               │
│    - Button released after long press                    │
│    - Stops continuous action                             │
│    - Example: Stop dimming                               │
└──────────────────────────────────────────────────────────┘

Button Event Flow:
┌─────────────────────────────────────────────────────────┐
│ 1. User presses physical button                        │
│    ↓                                                    │
│ 2. Hardware driver detects press                       │
│    ↓                                                    │
│ 3. Application calls button.press()                    │
│    ↓                                                    │
│ 4. Button determines event type (single/double/long)   │
│    ↓                                                    │
│ 5. Button triggers callback                            │
│    ↓                                                    │
│ 6. Application logic (toggle light, call scene, etc.)  │
│    ↓                                                    │
│ 7. Button sends notification to vdSM                   │
│    ↓                                                    │
│ 8. vdSM can trigger automation rules                   │
└─────────────────────────────────────────────────────────┘

Common Button Patterns:
- Toggle: Single press toggles output on/off
- Dimmer: Long press dims up/down, release stops
- Scene Recall: Single press recalls preset, double press saves
- Multi-function: Different press types trigger different actions

Usage:
```python
# Create a toggle button
toggle_btn = Button(
    vdsd=device,
    name="Power Toggle",
    button_type=0,  # Single press
    button_id=0
)

# Set up callback for button events
def on_button_press(button_id, event_type):
    if event_type == 0:  # Single press
        device.toggle_output()
    print(f"Button {button_id} pressed: type {event_type}")

toggle_btn.on_press(on_button_press)

# When hardware detects button press
toggle_btn.press()  # Triggers callback and vdSM notification

# Create dimming buttons
dim_up = Button(vdsd=device, name="Dim Up", button_type=2)
dim_down = Button(vdsd=device, name="Dim Down", button_type=2)

def on_dim_up(button_id, event_type):
    if event_type == 2:  # Long press
        device.start_dimming(direction=+1)
    elif event_type == 3:  # Release
        device.stop_dimming()

dim_up.on_press(on_dim_up)
```
"""

import logging
import time
from typing import Optional, Callable, Dict, Any
from ..utils.callbacks import Observable

logger = logging.getLogger(__name__)


class Button:
    """
    Represents a button input on a device.
    
    A Button generates events when activated, supporting different
    interaction types (single, double, long press). The button:
    
    - Detects press/release events from hardware
    - Determines event type based on timing
    - Triggers application callbacks
    - Sends notifications to vdSM
    - Tracks button state and history
    
    Button Configuration:
    - button_id: Unique identifier within device
    - button_type: Primary event type this button generates
    - name: Human-readable label
    
    Event Detection:
    The button can detect various interaction patterns:
    - Single press: Quick tap
    - Double press: Two quick taps (within 500ms)
    - Long press: Hold for >1 second
    - Release: Released after long press
    
    Attributes:
        vdsd: Parent device
        button_id: Button identifier (0-based index)
        button_type: Default button event type
        name: Button name
    """
    
    # Timing constants for button event detection
    DOUBLE_PRESS_INTERVAL = 0.5  # Max time between presses for double-press (500ms)
    LONG_PRESS_THRESHOLD = 1.0   # Min time held for long press (1 second)
    
    def __init__(
        self,
        vdsd: 'VdSD',
        name: str,
        button_type: int = 0,
        button_id: Optional[int] = None
    ):
        """
        Initialize button input.
        
        Args:
            vdsd: Parent VdSD device
            name: Human-readable button name (e.g., "Power Toggle")
            button_type: Default event type (0=single, 1=double, 2=long, 3=release)
            button_id: Unique button identifier (auto-assigned if None)
        
        Example:
            # Simple toggle button
            toggle = Button(
                vdsd=device,
                name="On/Off Toggle",
                button_type=0  # Single press
            )
            
            # Dimmer control button
            dim_up = Button(
                vdsd=device,
                name="Brightness Up",
                button_type=2  # Long press
            )
        """
        self.vdsd = vdsd
        self.name = name
        self.button_type = button_type
        
        # Auto-assign button ID if not provided
        # (Based on number of existing buttons in device)
        if button_id is None:
            # This would be set by VdSD when button is added
            self.button_id = 0
        else:
            self.button_id = button_id
        
        # Button state tracking
        self._pressed = False
        self._press_start_time: Optional[float] = None
        self._last_press_time: Optional[float] = None
        self._press_count = 0
        
        # Observable for button events
        # Subscribers receive: callback(button_id, event_type)
        self._event_observable = Observable()
        
        logger.debug(
            f"Created button: id={self.button_id}, "
            f"name='{name}', type={button_type}"
        )
    
    def press(self) -> None:
        """
        Handle button press event from hardware.
        
        This should be called when the physical button is pressed down.
        The method tracks timing to determine the event type:
        - If pressed soon after previous press → double press
        - If held down → long press (detected on release)
        - Otherwise → single press (detected on release)
        
        Example:
            # Hardware interrupt/polling detects button press
            gpio_button.on_press(lambda: button.press())
        """
        if self._pressed:
            logger.warning(f"Button {self.button_id} already pressed")
            return
        
        current_time = time.time()
        
        # Check for double press
        # If this press is within DOUBLE_PRESS_INTERVAL of last press
        if (self._last_press_time and 
            current_time - self._last_press_time < self.DOUBLE_PRESS_INTERVAL):
            self._press_count += 1
        else:
            self._press_count = 1
        
        # Mark as pressed and record time
        self._pressed = True
        self._press_start_time = current_time
        
        logger.debug(f"Button {self.button_id} pressed (count={self._press_count})")
    
    def release(self) -> None:
        """
        Handle button release event from hardware.
        
        This should be called when the physical button is released.
        Based on timing since press(), this determines the event type
        and triggers appropriate callbacks.
        
        Event Type Determination:
        1. If press_count >= 2 → Double press (type 1)
        2. If held > LONG_PRESS_THRESHOLD → Long press (type 2) or Release (type 3)
        3. Otherwise → Single press (type 0)
        
        Example:
            # Hardware interrupt/polling detects button release
            gpio_button.on_release(lambda: button.release())
        """
        if not self._pressed:
            logger.warning(f"Button {self.button_id} not currently pressed")
            return
        
        current_time = time.time()
        press_duration = current_time - self._press_start_time
        
        # Determine event type based on timing
        event_type = self.button_type  # Default to configured type
        
        if self._press_count >= 2:
            # Double press detected
            event_type = 1
            self._press_count = 0  # Reset counter
        elif press_duration >= self.LONG_PRESS_THRESHOLD:
            # Long press - generate release event
            # Note: Some implementations send long press (2) on threshold,
            # then release (3) when actually released
            event_type = 3  # Release after long press
        else:
            # Single press
            event_type = 0
        
        # Update state
        self._pressed = False
        self._last_press_time = current_time
        self._press_start_time = None
        
        logger.info(
            f"Button {self.button_id} released: event_type={event_type}, "
            f"duration={press_duration:.3f}s"
        )
        
        # Trigger callbacks
        self._event_observable.notify(self.button_id, event_type)
        
        # TODO: Send button event notification to vdSM
        # self.vdsd.send_button_notification(self.button_id, event_type)
    
    def click(self, event_type: Optional[int] = None) -> None:
        """
        Simulate a button click (press + release).
        
        Convenience method for testing or programmatic button activation.
        
        Args:
            event_type: Specific event type to generate (overrides detection)
        
        Example:
            # Simulate single press
            button.click()
            
            # Simulate double press
            button.click(event_type=1)
            
            # Simulate long press
            button.click(event_type=2)
        """
        if event_type is None:
            # Normal press/release sequence
            self.press()
            time.sleep(0.1)  # Brief press
            self.release()
        else:
            # Directly trigger event
            logger.debug(f"Button {self.button_id} simulated click: type={event_type}")
            self._event_observable.notify(self.button_id, event_type)
    
    def on_press(self, callback: Callable[[int, int], None]) -> None:
        """
        Register callback for button events.
        
        The callback will be invoked when button events occur.
        
        Callback signature: callback(button_id: int, event_type: int)
        
        Event types:
        - 0: Single press
        - 1: Double press
        - 2: Long press
        - 3: Release (after long press)
        
        Args:
            callback: Function to call on button events
        
        Example:
            def handle_button(button_id, event_type):
                if event_type == 0:  # Single press
                    print("Toggle light")
                    device.toggle_output()
                elif event_type == 1:  # Double press
                    print("Recall favorite scene")
                    device.call_scene(32)  # Preset 0
                elif event_type == 2:  # Long press
                    print("Start dimming up")
                    device.start_dimming(+1)
                elif event_type == 3:  # Release
                    print("Stop dimming")
                    device.stop_dimming()
            
            button.on_press(handle_button)
        """
        self._event_observable.subscribe(callback)
    
    def remove_callback(self, callback: Callable[[int, int], None]) -> None:
        """
        Remove a button event callback.
        
        Args:
            callback: Function to remove from subscribers
        """
        self._event_observable.unsubscribe(callback)
    
    def is_pressed(self) -> bool:
        """
        Check if button is currently pressed.
        
        Returns:
            True if button is pressed down, False if released
        """
        return self._pressed
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert button to dictionary for property tree.
        
        Returns:
            Dictionary representation of button configuration
        """
        return {
            'inputType': 'button',
            'buttonID': self.button_id,
            'buttonType': self.button_type,
            'name': self.name,
            'pressed': self._pressed,
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update button configuration from dictionary.
        
        Args:
            data: Dictionary with button properties
        """
        if 'name' in data:
            self.name = data['name']
        if 'buttonType' in data:
            self.button_type = data['buttonType']
    
    def __repr__(self) -> str:
        """String representation of button."""
        return (
            f"Button(id={self.button_id}, "
            f"name='{self.name}', "
            f"type={self.button_type}, "
            f"pressed={self._pressed})"
        )
