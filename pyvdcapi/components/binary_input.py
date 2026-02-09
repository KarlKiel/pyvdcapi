"""
BinaryInput - Contact closure and motion detection input.

A BinaryInput represents a two-state input device:
- Contact sensors (open/closed)
- Motion detectors (motion/no motion)
- Presence sensors (present/absent)
- Window/door sensors (open/closed)
- Water leak detectors (dry/wet)
- Any other binary state sensor

Binary Input States:
┌──────────────────────────────────────────────────────────┐
│ State Values                                             │
├──────────────────────────────────────────────────────────┤
│ 0: Inactive/Off/Open/No Motion                           │
│    - Contact open                                        │
│    - No motion detected                                  │
│    - Sensor inactive                                     │
│                                                          │
│ 1: Active/On/Closed/Motion                               │
│    - Contact closed                                      │
│    - Motion detected                                     │
│    - Sensor active                                       │
└──────────────────────────────────────────────────────────┘

Binary Input Event Flow:
┌─────────────────────────────────────────────────────────┐
│ 1. Physical state changes (door opens, motion detected) │
│    ↓                                                    │
│ 2. Hardware driver detects change                      │
│    ↓                                                    │
│ 3. Application calls binary_input.set_state(True/False)│
│    ↓                                                    │
│ 4. BinaryInput updates state and timestamp             │
│    ↓                                                    │
│ 5. BinaryInput triggers callback                       │
│    ↓                                                    │
│ 6. Application logic (e.g., trigger automation)        │
│    ↓                                                    │
│ 7. BinaryInput sends notification to vdSM              │
│    ↓                                                    │
│ 8. vdSM can trigger scenes or automation rules         │
└─────────────────────────────────────────────────────────┘

Common Use Cases:
- Door/Window Sensors: Trigger alerts when opened
- Motion Detectors: Turn on lights when motion detected
- Presence Sensors: Activate "present" scene when someone enters
- Leak Detectors: Alert and cut off water supply
- Smoke Detectors: Trigger alarm scene

Usage:
```python
# Create motion detector
motion = BinaryInput(
    vdsd=device,
    name="Living Room Motion",
    input_type="motion",
    input_id=0
)

# Set up callback for state changes
def on_motion_change(input_id, state):
    if state:  # Motion detected
        print("Motion detected!")
        device.call_scene(DSScene.PRESENT)  # Turn on lights
    else:  # No motion
        print("No motion")
        # Could trigger "absent" scene after timeout

motion.on_change(on_motion_change)

# When hardware detects motion
motion.set_state(True)  # Triggers callback and vdSM notification

# Later, when motion stops
motion.set_state(False)

# Create door sensor
door = BinaryInput(
    vdsd=device,
    name="Front Door",
    input_type="contact",
    invert=True  # True=closed, False=open (inverted logic)
)

def on_door_change(input_id, state):
    if not state:  # Door opened (inverted)
        print("Front door opened!")
        # Send alert notification

door.on_change(on_door_change)
```
"""

import logging
import time
from typing import Optional, Callable, Dict, Any, TYPE_CHECKING
from ..utils.callbacks import Observable

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..entities.vdsd import VdSD


class BinaryInput:
    """
    Represents a binary state input on a device.

    A BinaryInput tracks a two-state condition and generates events
    when the state changes. The input:

    - Tracks current state (active/inactive, on/off, etc.)
    - Detects state transitions
    - Triggers callbacks on changes
    - Sends notifications to vdSM
    - Maintains state history and timing

    Binary Input Configuration:
    - input_id: Unique identifier within device
    - input_type: Type of sensor (motion, contact, presence, etc.)
    - name: Human-readable label
    - invert: Whether to invert the logic (True=inactive, False=active)

    State Tracking:
    - state: Current boolean state (True=active, False=inactive)
    - last_change: Timestamp of last state change
    - age: Time since last change

    Attributes:
        vdsd: Parent device
        input_id: Binary input identifier
        input_type: Type of sensor
        name: Input name
        state: Current state (True/False)
        invert: Logic inversion flag
    """

    def __init__(
        self,
        vdsd: "VdSD",
        name: str,
        input_type: str = "contact",
        input_id: Optional[int] = None,
        invert: bool = False,
        initial_state: bool = False,
    ):
        """
        Initialize binary input.

        Args:
            vdsd: Parent VdSD device
            name: Human-readable input name (e.g., "Motion Detector")
            input_type: Type of binary input:
                       - "contact": Contact closure (door, window)
                       - "motion": Motion detector
                       - "presence": Presence sensor
                       - "leak": Water leak detector
                       - "smoke": Smoke detector
                       - "custom": Custom binary sensor
            input_id: Unique input identifier (auto-assigned if None)
            invert: If True, inverts state logic (True=inactive, False=active)
            initial_state: Starting state (default False=inactive)

        Example:
            # Motion detector (active-high logic)
            motion = BinaryInput(
                vdsd=device,
                name="Room Motion",
                input_type="motion",
                initial_state=False
            )

            # Door sensor (active-low logic - True=closed)
            door = BinaryInput(
                vdsd=device,
                name="Front Door",
                input_type="contact",
                invert=True,  # Inverted: True=closed, False=open
                initial_state=True  # Start as closed
            )
        """
        self.vdsd = vdsd
        self.name = name
        self.input_type = input_type
        self.invert = invert

        # Auto-assign input ID if not provided
        if input_id is None:
            self.input_id = 0  # Would be set by VdSD when added
        else:
            self.input_id = input_id

        # Description properties (API section 4.3.1)
        self.ds_index = self.input_id  # Device input index (0..N-1)
        self.input_usage = 0  # 0=undefined, 1=room, 2=outdoors, 3=user
        self.sensor_function = 0  # Sensor function enum (default undefined)

        # Settings properties (API section 4.3.2) - configurable from DSS
        self.group = 0  # dS group number (0=undefined)
        # Note: sensor_function is r/w in settings but also r in description
        # The description shows hardwired function, settings allows override

        # State tracking
        self._state = initial_state
        self._last_change_time = time.time()

        # Observable for state changes
        # Subscribers receive: callback(input_id, state)
        self._change_observable = Observable()

        logger.debug(
            f"Created binary input: id={self.input_id}, "
            f"name='{name}', type={input_type}, "
            f"invert={invert}, state={initial_state}"
        )

    def set_state(self, state: bool) -> None:
        """
        Update binary input state from hardware.

        This should be called when the hardware detects a state change.
        If the state actually changed, this:
        1. Updates internal state
        2. Records timestamp
        3. Triggers callbacks
        4. Sends notification to vdSM

        Args:
            state: New state (True=active, False=inactive)
                  Note: Affected by invert flag

        Example:
            # Hardware interrupt detects motion
            def motion_interrupt():
                motion_input.set_state(True)

            # Hardware polling detects door opened
            if gpio.read_door_sensor() == GPIO.HIGH:
                door_input.set_state(False)  # Open (if inverted)
        """
        # Apply inversion if configured
        effective_state = not state if self.invert else state

        # Check if state actually changed
        if effective_state == self._state:
            logger.debug(f"Binary input {self.input_id} already in state {effective_state}")
            return

        # Update state
        old_state = self._state
        self._state = effective_state
        self._last_change_time = time.time()

        logger.info(f"Binary input {self.input_id} ('{self.name}') state changed: " f"{old_state} → {effective_state}")

        # Trigger callbacks
        self._change_observable.notify(self.input_id, effective_state)

        # Send binary input state change notification to vdSM
        # Pattern A: Device → DSS (push notification on state change)
        self.vdsd.push_binary_input_state(
            self.input_id,
            effective_state
        )

    def get_state(self) -> bool:
        """
        Get current input state.

        Returns:
            Current state (True=active, False=inactive)
        """
        return self._state

    def get_age(self) -> float:
        """
        Get age of current state in seconds.

        Indicates how long the input has been in current state.
        Per vDC API spec section 4.3.3, age is returned in seconds.

        Returns:
            Seconds since last state change
        """
        return time.time() - self._last_change_time

    def on_change(self, callback: Callable[[int, bool], None]) -> None:
        """
        Register callback for state changes.

        The callback will be invoked whenever the state changes.

        Callback signature: callback(input_id: int, state: bool)

        Args:
            callback: Function to call on state changes

        Example:
            def handle_motion(input_id, state):
                if state:  # Motion detected
                    print("Motion detected - turning on lights")
                    device.set_output(DSChannelType.BRIGHTNESS, 100.0)
                else:  # No motion
                    print("No motion - setting timer for auto-off")
                    # Start 5-minute timer to turn off lights

            motion_input.on_change(handle_motion)

            def handle_door(input_id, state):
                # State is inverted for this sensor
                if state:  # Door closed
                    print("Door secured")
                else:  # Door open
                    print("Door opened - sending alert!")
                    send_security_alert()

            door_input.on_change(handle_door)
        """
        self._change_observable.subscribe(callback)

    def remove_callback(self, callback: Callable[[int, bool], None]) -> None:
        """
        Remove a state change callback.

        Args:
            callback: Function to remove from subscribers
        """
        self._change_observable.unsubscribe(callback)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert binary input to dictionary for property tree.

        Returns:
            Dictionary representation of binary input per API section 4.3
        """
        return {
            # Description properties (section 4.3.1) - read-only, invariable
            "name": self.name,
            "dsIndex": self.ds_index,
            "inputType": self.input_type,
            "inputUsage": self.input_usage,
            "sensorFunction": self.sensor_function,
            # Legacy compatibility
            "inputID": self.input_id,
            "sensorType": self.input_type,
            # Settings (section 4.3.2) - configurable
            "settings": {
                "group": self.group,
                "sensorFunction": self.sensor_function,  # Also r/w in settings
                "invert": self.invert,
            },
            # State (section 4.3.3) - dynamic
            "state": {"value": self._state, "age": self.get_age()},
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update binary input configuration from dictionary.
        
        Handles settings updates from DSS (API section 4.3.2).

        Args:
            data: Dictionary with input properties
        """
        # Description properties (mostly read-only)
        if "name" in data:
            self.name = data["name"]
            
        # Settings properties (section 4.3.2) - DSS → Device (Pattern B)
        # Accept settings nested or top-level
        settings = data.get("settings", data)
        
        if "group" in settings:
            old_group = self.group
            self.group = settings["group"]
            logger.info(
                f"BinaryInput {self.input_id} group changed: {old_group} → {self.group}"
            )
        
        if "sensorFunction" in settings:
            old_function = self.sensor_function
            self.sensor_function = settings["sensorFunction"]
            logger.info(
                f"BinaryInput {self.input_id} sensorFunction changed: "
                f"{old_function} → {self.sensor_function}"
            )
        
        if "invert" in settings:
            self.invert = settings["invert"]
            
        # Legacy support
        if "sensorType" in settings:
            self.input_type = settings["sensorType"]
        if "inputType" in settings:
            # normalize possible values like 'binary' or integer codes
            pass

    def __repr__(self) -> str:
        """String representation of binary input."""
        return (
            f"BinaryInput(id={self.input_id}, "
            f"name='{self.name}', "
            f"type={self.input_type}, "
            f"state={self._state}, "
            f"invert={self.invert})"
        )
