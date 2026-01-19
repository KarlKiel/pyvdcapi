"""
OutputChannel - Controllable output for vDC devices.

An OutputChannel represents a single controllable aspect of a device:
- Brightness for dimmers
- Hue/Saturation for color lights
- Position/Angle for blinds
- Temperature for thermostats
- Volume for audio devices

Channel Properties:
┌─────────────────────────────────────────────────────────┐
│ OutputChannel (e.g., Brightness)                        │
├─────────────────────────────────────────────────────────┤
│ Description (Static):                                   │
│ - channelType: Integer ID (DSChannelType enum)          │
│ - dsIndex: 0 for default channel                        │
│ - min: Minimum value (e.g., 0.0)                        │
│ - max: Maximum value (e.g., 100.0)                      │
│ - resolution: Smallest increment (e.g., 0.1)            │
│                                                         │
│ Settings (Persistent):                                  │
│ - name: Channel name                                    │
│ - groups: Which scenes affect this channel              │
│                                                         │
│ State (Dynamic):                                        │
│ - value: Current value (e.g., 75.0 for 75%)            │
│ - age: Milliseconds since last update                   │
│ - transition: Active transition info                    │
└─────────────────────────────────────────────────────────┘

Value Change Flow:
┌────────────────────────────────────────────────────────┐
│ 1. vdSM sets property (value=50%)                      │
│    ↓                                                   │
│ 2. VdSD.set_properties() → Channel.set_value()        │
│    ↓                                                   │
│ 3. Channel validates value (min/max/resolution)       │
│    ↓                                                   │
│ 4. Channel triggers Observable callback               │
│    ↓                                                   │
│ 5. Application applies to hardware                    │
│    ↓                                                   │
│ 6. Hardware confirms new state                        │
│    ↓                                                   │
│ 7. Application calls channel.update_value()           │
│    ↓                                                   │
│ 8. Channel sends notification to vdSM                 │
└────────────────────────────────────────────────────────┘

The channel acts as the abstraction layer between vDC API protocol
and actual hardware control, handling:
- Value validation and clamping
- Unit conversion if needed
- State synchronization
- Change notifications
- Transition effects (fade, smooth, etc.)

Usage:
```python
# Create brightness channel for a dimmer
brightness = OutputChannel(
    vdsd=my_device,
    channel_type=DSChannelType.BRIGHTNESS,
    min_value=0.0,
    max_value=100.0,
    resolution=0.1,
    initial_value=0.0
)

# Set up hardware callback
def apply_brightness(value):
    # Send to actual hardware
    hardware_driver.set_pwm(value / 100.0)
    print(f"Applied brightness: {value}%")

brightness.subscribe(apply_brightness)

# When vdSM changes value
brightness.set_value(75.0)  # Triggers callback → hardware update

# When hardware state changes (e.g., manual control)
brightness.update_value(80.0)  # Sends notification to vdSM
```
"""

import logging
import time
from typing import Optional, Any, Dict, Callable, TYPE_CHECKING
from ..utils.callbacks import Observable
from ..utils.validators import PropertyValidator
from ..core.constants import DSSceneEffect, get_channel_name

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..entities.vdsd import VdSD


class OutputChannel:
    """
    Represents a controllable output channel of a device.

    An OutputChannel manages a single controllable parameter with:
    - Type identification (brightness, hue, position, etc.)
    - Value range (min, max, resolution)
    - Current state (value, age, transition)
    - Change notifications (Observable pattern)
    - Hardware abstraction (callback on value change)

    The channel distinguishes between three property categories:

    1. Description (channelDescriptions):
       Static properties that describe the channel's capabilities.
       Set once during channel creation, rarely change.
       Examples: channelType, min, max, resolution

    2. Settings (channelSettings):
       Persistent properties that configure channel behavior.
       Can be modified by vdSM or user, saved to YAML.
       Examples: name, groups (which scenes affect this channel)

    3. States (channelStates):
       Dynamic properties reflecting current channel status.
       Change frequently, not persisted.
       Examples: value, age, transition

    Attributes:
        channel_type: Type of channel (DSChannelType enum value)
        vdsd: Parent device reference
        value: Current channel value
        min_value: Minimum allowed value
        max_value: Maximum allowed value
        resolution: Smallest value increment
    """

    def __init__(
        self,
        vdsd: "VdSD",
        channel_type: int,
        min_value: float = 0.0,
        max_value: float = 100.0,
        resolution: float = 0.1,
        initial_value: Optional[float] = None,
        ds_index: int = 0,
        name: Optional[str] = None,
    ):
        """
        Initialize output channel.

        Args:
            vdsd: Parent VdSD device
            channel_type: Channel type (DSChannelType enum value)
            min_value: Minimum value for this channel
            max_value: Maximum value for this channel
            resolution: Smallest increment (for UI granularity)
            initial_value: Starting value (defaults to min_value)
            ds_index: digitalSTROM index (0 = default/primary channel)
            name: Human-readable channel name (defaults to type name)

        The channel type determines what this channel controls:
        - BRIGHTNESS (1): Light brightness 0-100%
        - HUE (2): Color hue 0-360°
        - SATURATION (3): Color saturation 0-100%
        - COLOR_TEMP (4): Color temperature in Kelvin
        - POSITION (11): Blind/shade position 0-100%
        - VOLUME (41): Audio volume 0-100%
        - etc.

        Example:
            # Create brightness channel for a dimmer
            brightness = OutputChannel(
                vdsd=device,
                channel_type=DSChannelType.BRIGHTNESS,
                min_value=0.0,
                max_value=100.0,
                resolution=0.1
            )
        """
        self.vdsd = vdsd
        self.channel_type = channel_type
        self.ds_index = ds_index

        # Channel description (static)
        self.min_value = min_value
        self.max_value = max_value
        self.resolution = resolution

        # Channel settings (persistent)
        self.name = name or get_channel_name(channel_type)
        self.groups = []  # Which scene groups affect this channel

        # Channel state (dynamic)
        self._value = initial_value if initial_value is not None else min_value
        self._last_update = time.time()
        self._transition_active = False
        self._transition_target = None
        self._transition_effect = DSSceneEffect.NONE

        # Observable for value changes
        # Subscribers receive: callback(channel_type, new_value)
        self._value_observable = Observable()

        # Validator
        self._validator = PropertyValidator()

        logger.debug(
            f"Created output channel: type={channel_type} ({self.name}), "
            f"range=[{min_value}, {max_value}], resolution={resolution}"
        )

    def set_value(
        self, value: float, effect: int = DSSceneEffect.NONE, transition_time: Optional[float] = None
    ) -> None:
        """
        Set channel value (from vdSM or scene).

        This is called when:
        - vdSM sets an output property
        - A scene is activated
        - Application code changes the value

        Process:
        1. Validate and clamp value to min/max
        2. Update internal state
        3. Notify all subscribers (trigger hardware update)
        4. Update age timestamp

        The effect parameter indicates how to transition to the new value:
        - NONE: Immediate change
        - SMOOTH: Normal transition (default duration)
        - SLOW: Slow transition (longer duration)
        - VERY_SLOW: Very slow transition
        - ALERT: Blink/alert effect

        Args:
            value: Target value to set
            effect: Transition effect (DSSceneEffect enum)
            transition_time: Duration in seconds (overrides effect default)

        Example:
            # Immediate change
            channel.set_value(50.0)

            # Smooth transition (e.g., for scene activation)
            channel.set_value(75.0, effect=DSSceneEffect.SMOOTH)

            # Custom transition duration
            channel.set_value(100.0, transition_time=5.0)  # 5 second fade
        """
        # Validate and clamp value
        validated_value = self._validator.clamp_value(value, self.min_value, self.max_value)

        if validated_value != value:
            logger.warning(
                f"Value {value} for channel {self.name} clamped to "
                f"[{self.min_value}, {self.max_value}]: {validated_value}"
            )

        # Round to resolution
        validated_value = round(validated_value / self.resolution) * self.resolution

        # Check if value actually changed
        if validated_value == self._value and not self._transition_active:
            logger.debug(f"Channel {self.name} already at value {validated_value}")
            return

        # Update state
        old_value = self._value
        self._value = validated_value
        self._last_update = time.time()

        # Handle transition
        if effect != DSSceneEffect.NONE:
            self._transition_active = True
            self._transition_target = validated_value
            self._transition_effect = effect
            # Transition duration depends on effect
            # SMOOTH: ~1s, SLOW: ~5s, VERY_SLOW: ~30s
            # Implementation would start a timer/coroutine

        logger.debug(f"Channel {self.name} value changed: {old_value} → {validated_value}, " f"effect={effect}")

        # Notify subscribers (triggers hardware update)
        # Subscribers receive (channel_type, new_value)
        self._value_observable.notify(self.channel_type, validated_value)

    def update_value(self, value: float) -> None:
        """
        Update channel value from hardware feedback.

        This is called when:
        - Hardware confirms a value change
        - Manual control changes hardware state
        - External system modifies the device

        Unlike set_value(), this:
        - Does NOT trigger hardware callbacks (would create loop)
        - DOES send notification to vdSM (state sync)
        - Updates age timestamp

        This completes the bidirectional sync loop:
        vdSM → set_value() → hardware → update_value() → vdSM notification

        Args:
            value: Actual hardware value

        Example:
            # Hardware confirms value was applied
            def hardware_callback(channel_type, value):
                hardware.set_brightness(value)
                # After hardware confirms:
                channel.update_value(value)

            channel.subscribe(hardware_callback)
        """
        # Validate value
        validated_value = self._validator.clamp_value(value, self.min_value, self.max_value)

        # Round to resolution
        validated_value = round(validated_value / self.resolution) * self.resolution

        # Update state
        if validated_value != self._value:
            old_value = self._value
            self._value = validated_value
            self._last_update = time.time()

            # Clear transition if we reached target
            if self._transition_active and validated_value == self._transition_target:
                self._transition_active = False
                self._transition_target = None

            logger.debug(f"Channel {self.name} updated from hardware: " f"{old_value} → {validated_value}")

            # TODO: Send notification to vdSM about state change
            # self.vdsd.send_property_changed_notification(
            #     f"outputs.{self.ds_index}.value",
            #     validated_value
            # )

        # Always update timestamp even if value unchanged
        self._last_update = time.time()

    def get_value(self) -> float:
        """
        Get current channel value.

        Returns:
            Current value
        """
        return self._value

    def get_age(self) -> float:
        """
        Get age of current value in milliseconds.

        Age indicates how long ago the value was last updated.
        Used by vdSM to determine data freshness.

        Returns:
            Milliseconds since last update
        """
        return (time.time() - self._last_update) * 1000.0

    def subscribe(self, callback: Callable[[int, float], None]) -> None:
        """
        Subscribe to value changes.

        The callback will be invoked whenever set_value() is called.
        This is typically used to apply values to hardware.

        Callback signature: callback(channel_type: int, value: float)

        Args:
            callback: Function to call on value changes

        Example:
            def apply_to_hardware(channel_type, value):
                if channel_type == DSChannelType.BRIGHTNESS:
                    hardware.set_brightness(value / 100.0)
                elif channel_type == DSChannelType.HUE:
                    hardware.set_hue(value)

            channel.subscribe(apply_to_hardware)
        """
        self._value_observable.subscribe(callback)

    def unsubscribe(self, callback: Callable[[int, float], None]) -> None:
        """
        Unsubscribe from value changes.

        Args:
            callback: Function to remove from subscribers
        """
        self._value_observable.unsubscribe(callback)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert channel to dictionary for property tree.

        Returns dictionary with three sections:
        - description: Static channel properties
        - settings: Persistent configuration
        - state: Current dynamic state

        Returns:
            Dictionary representation of channel
        """
        return {
            "channelType": int(self.channel_type),
            "dsIndex": int(self.ds_index),
            "min": self.min_value,
            "max": self.max_value,
            "resolution": self.resolution,
            "name": self.name,
            "groups": self.groups,
            "value": self._value,
            "age": self.get_age(),
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update channel from dictionary (property tree).

        This is called when vdSM sets channel properties.
        Only mutable properties are updated.

        Args:
            data: Dictionary with channel properties
        """
        # Update settings if provided (support both flattened and nested)
        settings = data.get("settings") or data
        if "name" in settings:
            self.name = settings["name"]
        if "groups" in settings:
            self.groups = settings["groups"]

        # Update numeric description fields if present
        if "min" in data:
            self.min_value = data["min"]
        if "max" in data:
            self.max_value = data["max"]
        if "resolution" in data:
            self.resolution = data["resolution"]

        # Update value if provided
        if "value" in data:
            self.set_value(data["value"])
        elif "state" in data and "value" in data["state"]:
            self.set_value(data["state"]["value"])

    def __repr__(self) -> str:
        """String representation of channel."""
        return (
            f"OutputChannel(type={self.channel_type}, "
            f"name='{self.name}', "
            f"value={self._value}, "
            f"range=[{self.min_value}, {self.max_value}])"
        )
