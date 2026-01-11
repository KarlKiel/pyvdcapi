"""
Output - Container for output channels with configuration.

An Output represents a controllable aspect of a device and contains
one or more OutputChannels. The Output provides:
- Output configuration (mode, push changes, etc.)
- Channel grouping and management
- Output-level properties
- Channel coordination

Output vs OutputChannel:
┌──────────────────────────────────────────────────────────┐
│ Output (Container)                                       │
├──────────────────────────────────────────────────────────┤
│ - Output ID                                              │
│ - Output function (e.g., "dimmer", "color light")       │
│ - Output mode (disabled, binary, gradual)               │
│ - Push changes flag                                      │
│ - Contains 1+ OutputChannels                            │
│                                                          │
│   ┌────────────────────────────────────────────┐        │
│   │ OutputChannel 1: Brightness (0-100%)       │        │
│   └────────────────────────────────────────────┘        │
│   ┌────────────────────────────────────────────┐        │
│   │ OutputChannel 2: Hue (0-360°)              │        │
│   └────────────────────────────────────────────┘        │
│   ┌────────────────────────────────────────────┐        │
│   │ OutputChannel 3: Saturation (0-100%)       │        │
│   └────────────────────────────────────────────┘        │
└──────────────────────────────────────────────────────────┘

Output Functions (examples):
- "dimmer": Simple dimmable light (brightness channel)
- "colordimmer": RGB/HSV color light (brightness, hue, saturation)
- "ctdimmer": Color temperature light (brightness, color temp)
- "positional": Blinds, shades (position, angle channels)
- "heating": Heater control (power, temperature setpoint)
- "cooling": AC control (power, temperature setpoint)

Output Modes:
┌──────────────────────────────────────────────────────────┐
│ Mode      │ Description                                  │
├──────────────────────────────────────────────────────────┤
│ disabled  │ Output is disabled, won't accept commands   │
│ binary    │ Output is on/off only (no gradual dimming)  │
│ gradual   │ Output supports smooth transitions          │
└──────────────────────────────────────────────────────────┘

Usage:
```python
# Simple dimmer (one channel)
dimmer = Output(
    vdsd=device,
    output_id=0,
    output_function="dimmer",
    output_mode="gradual"
)
dimmer.add_channel(OutputChannel(
    vdsd=device,
    channel_type=DSChannelType.BRIGHTNESS,
    name="Light Brightness",
    min_value=0.0,
    max_value=100.0
))

# Color light (three channels)
color_light = Output(
    vdsd=device,
    output_id=0,
    output_function="colordimmer",
    output_mode="gradual"
)
color_light.add_channel(OutputChannel(
    vdsd=device,
    channel_type=DSChannelType.BRIGHTNESS,
    name="Brightness"
))
color_light.add_channel(OutputChannel(
    vdsd=device,
    channel_type=DSChannelType.HUE,
    name="Hue"
))
color_light.add_channel(OutputChannel(
    vdsd=device,
    channel_type=DSChannelType.SATURATION,
    name="Saturation"
))

# Set values on all channels
dimmer.set_channel_value(DSChannelType.BRIGHTNESS, 75.0)

# Get channel by type
brightness_ch = color_light.get_channel(DSChannelType.BRIGHTNESS)
```
"""

import logging
from typing import Dict, List, Optional, Any
from .output_channel import OutputChannel
from ..core.constants import DSChannelType

logger = logging.getLogger(__name__)


class Output:
    """
    Represents an output with one or more channels.
    
    An Output groups related OutputChannels together and provides
    output-level configuration:
    
    - Output mode (disabled/binary/gradual)
    - Push changes behavior
    - Channel management
    - Output function (dimmer, color, positional, etc.)
    
    The Output acts as a container and coordinator for its channels,
    ensuring they work together correctly.
    
    Output Configuration:
    - output_id: Unique identifier within device
    - output_function: Type of output (dimmer, colordimmer, etc.)
    - output_mode: How output operates (disabled/binary/gradual)
    - push_changes: Whether to immediately push value changes
    
    Channel Management:
    - channels: Dictionary of OutputChannel objects by type
    - add_channel(): Add a channel to this output
    - get_channel(): Get channel by type
    - set_channel_value(): Set value on specific channel
    
    Attributes:
        vdsd: Parent device
        output_id: Output identifier
        output_function: Function type
        output_mode: Operating mode
        channels: Dictionary of channels by type
    """
    
    def __init__(
        self,
        vdsd: 'VdSD',
        output_id: int,
        output_function: str = "dimmer",
        output_mode: str = "gradual",
        push_changes: bool = True
    ):
        """
        Initialize output.
        
        Args:
            vdsd: Parent VdSD device
            output_id: Unique output identifier
            output_function: Type of output:
                           - "dimmer": Simple dimmable light
                           - "colordimmer": RGB/HSV color light
                           - "ctdimmer": Color temperature light
                           - "positional": Blinds/shades with position
                           - "heating": Heating control
                           - "cooling": Cooling control
                           - "audio": Audio output
                           - "video": Video output
            output_mode: Operating mode:
                        - "disabled": Output disabled
                        - "binary": On/off only (no gradual)
                        - "gradual": Smooth transitions supported
            push_changes: If True, immediately send changes to hardware.
                         If False, changes buffered until apply()
        
        Example:
            # Simple dimmer
            dimmer = Output(
                vdsd=device,
                output_id=0,
                output_function="dimmer",
                output_mode="gradual"
            )
            
            # Color light
            rgb_light = Output(
                vdsd=device,
                output_id=0,
                output_function="colordimmer",
                output_mode="gradual",
                push_changes=True
            )
            
            # Binary switch (on/off only)
            switch = Output(
                vdsd=device,
                output_id=0,
                output_function="switch",
                output_mode="binary"
            )
        """
        self.vdsd = vdsd
        self.output_id = output_id
        self.output_function = output_function
        self.output_mode = output_mode
        self.push_changes = push_changes
        
        # Channel storage: channel_type -> OutputChannel
        self.channels: Dict[DSChannelType, OutputChannel] = {}
        
        logger.debug(
            f"Created output: id={output_id}, function={output_function}, "
            f"mode={output_mode}"
        )
    
    def add_channel(self, channel: OutputChannel) -> None:
        """
        Add a channel to this output.
        
        Args:
            channel: OutputChannel to add
        
        Example:
            output = Output(vdsd=device, output_id=0)
            
            brightness = OutputChannel(
                vdsd=device,
                channel_type=DSChannelType.BRIGHTNESS,
                name="Brightness"
            )
            output.add_channel(brightness)
            
            hue = OutputChannel(
                vdsd=device,
                channel_type=DSChannelType.HUE,
                name="Hue"
            )
            output.add_channel(hue)
        """
        channel_type = channel.channel_type
        
        if channel_type in self.channels:
            logger.warning(
                f"Output {self.output_id} already has channel {channel_type}, "
                f"replacing"
            )
        
        self.channels[channel_type] = channel
        
        logger.debug(
            f"Added channel {channel_type} to output {self.output_id}"
        )
    
    def get_channel(self, channel_type: DSChannelType) -> Optional[OutputChannel]:
        """
        Get channel by type.
        
        Args:
            channel_type: Type of channel to retrieve
        
        Returns:
            OutputChannel if found, None otherwise
        
        Example:
            brightness_ch = output.get_channel(DSChannelType.BRIGHTNESS)
            if brightness_ch:
                current_value = brightness_ch.get_value()
        """
        return self.channels.get(channel_type)
    
    def set_channel_value(
        self,
        channel_type: DSChannelType,
        value: float,
        transition_time: Optional[float] = None,
        apply_now: bool = True
    ) -> bool:
        """
        Set value on a specific channel.
        
        Args:
            channel_type: Type of channel to set
            value: New value for channel
            transition_time: Transition time in seconds (optional)
            apply_now: Whether to apply immediately (affects push notification)
        
        Returns:
            True if channel found and value set, False otherwise
        
        Example:
            # Set brightness to 75%
            output.set_channel_value(DSChannelType.BRIGHTNESS, 75.0)
            
            # Set hue to red (0°) with 2 second transition
            output.set_channel_value(DSChannelType.HUE, 0.0, transition_time=2.0)
        """
        channel = self.channels.get(channel_type)
        if not channel:
            logger.warning(
                f"Output {self.output_id} has no channel {channel_type}"
            )
            return False
        
        # Check if output is disabled
        if self.output_mode == "disabled":
            logger.warning(
                f"Output {self.output_id} is disabled, ignoring set request"
            )
            return False
        
        # For binary mode, snap to 0 or max
        if self.output_mode == "binary":
            if value > 0:
                value = channel.max_value
            else:
                value = 0.0
        
        # Set the value
        channel.set_value(value, transition_time=transition_time)
        
        # Trigger push notification if push_changes is enabled
        if self.push_changes and apply_now:
            self._notify_value_change(channel_type, value)
        
        return True
    
    def get_channel_value(self, channel_type: DSChannelType) -> Optional[float]:
        """
        Get current value of a channel.
        
        Args:
            channel_type: Type of channel to query
        
        Returns:
            Current value if channel exists, None otherwise
        
        Example:
            brightness = output.get_channel_value(DSChannelType.BRIGHTNESS)
            if brightness is not None:
                print(f"Current brightness: {brightness}%")
        """
        channel = self.channels.get(channel_type)
        return channel.get_value() if channel else None
    
    def get_all_channel_values(self) -> Dict[DSChannelType, float]:
        """
        Get current values of all channels.
        
        Returns:
            Dictionary mapping channel type to current value
        
        Example:
            values = output.get_all_channel_values()
            # values = {
            #     DSChannelType.BRIGHTNESS: 75.0,
            #     DSChannelType.HUE: 120.0,
            #     DSChannelType.SATURATION: 80.0
            # }
        """
        return {
            channel_type: channel.get_value()
            for channel_type, channel in self.channels.items()
        }
    
    def set_mode(self, mode: str) -> None:
        """
        Set output operating mode.
        
        Args:
            mode: New mode ("disabled", "binary", "gradual")
        
        Example:
            # Temporarily disable output
            output.set_mode("disabled")
            
            # Switch to binary (on/off only)
            output.set_mode("binary")
            
            # Enable gradual dimming
            output.set_mode("gradual")
        """
        if mode not in ("disabled", "binary", "gradual"):
            logger.error(f"Invalid output mode: {mode}")
            return
        
        old_mode = self.output_mode
        self.output_mode = mode
        
        logger.info(
            f"Output {self.output_id} mode changed: {old_mode} → {mode}"
        )
    
    def apply_scene_values(
        self, 
        scene_values: Dict[DSChannelType, float],
        effect: Optional[int] = None,
        mode: str = 'normal'
    ) -> None:
        """
        Apply scene values to all channels.
        
        This is called when a scene is recalled. Values for all
        channels in the scene are applied simultaneously.
        
        Args:
            scene_values: Dictionary of channel type to value
            effect: Scene effect (smooth, slow, alert) - determines transition
            mode: Application mode:
                  - 'normal': Apply unconditionally
                  - 'min': Apply only if scene values are higher than current
        
        Example:
            # Scene values with smooth transition
            scene = {
                DSChannelType.BRIGHTNESS: 80.0,
                DSChannelType.HUE: 30.0,
                DSChannelType.SATURATION: 70.0
            }
            output.apply_scene_values(scene, effect=DSSceneEffect.SMOOTH)
            
            # Apply only if scene increases brightness
            output.apply_scene_values(scene, mode='min')
        """
        if self.output_mode == "disabled":
            logger.warning(
                f"Output {self.output_id} is disabled, ignoring scene"
            )
            return
        
        for channel_type, scene_value in scene_values.items():
            # In 'min' mode, only apply if scene value is higher
            if mode == 'min':
                channel = self.channels.get(channel_type)
                if channel and channel.value >= scene_value:
                    # Current value is already higher, skip
                    continue
            
            # Apply the value
            # effect determines transition time (handled by OutputChannel)
            self.set_channel_value(channel_type, scene_value)
        
        logger.info(
            f"Output {self.output_id} applied scene with {len(scene_values)} values "
            f"(effect={effect}, mode={mode})"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert output to dictionary for property tree.
        
        Returns:
            Dictionary representation of output
        """
        return {
            'outputID': self.output_id,
            'outputFunction': self.output_function,
            'outputMode': self.output_mode,
            'pushChanges': self.push_changes,
            'channels': {
                str(channel_type): channel.to_dict()
                for channel_type, channel in self.channels.items()
            }
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update output configuration from dictionary.
        
        Args:
            data: Dictionary with output properties
        """
        if 'outputFunction' in data:
            self.output_function = data['outputFunction']
        if 'outputMode' in data:
            self.output_mode = data['outputMode']
        if 'pushChanges' in data:
            self.push_changes = data['pushChanges']
        
        # Update channel configurations
        if 'channels' in data:
            for channel_type_str, channel_data in data['channels'].items():
                try:
                    channel_type = DSChannelType(int(channel_type_str))
                    channel = self.channels.get(channel_type)
                    if channel:
                        channel.from_dict(channel_data)
                except (ValueError, KeyError) as e:
                    logger.error(f"Error loading channel config: {e}")
    
    def __repr__(self) -> str:
        """String representation of output."""
        return (
            f"Output(id={self.output_id}, "
            f"function={self.output_function}, "
            f"mode={self.output_mode}, "
            f"channels={len(self.channels)})"
        )
    
    # ===================================================================
    # Dimming Operations (Protocol Integration)
    # ===================================================================
    
    def start_dimming(self, channel_id: int, direction: str = 'up', rate: float = 10.0) -> None:
        """
        Start continuous dimming of a channel.
        
        Typically triggered by holding a button. Dimming continues
        until stop_dimming() is called or limits are reached.
        
        Args:
            channel_id: Channel type ID to dim
            direction: 'up' or 'down'
            rate: Dimming rate in percent/second (default: 10.0)
        
        Message Flow:
            vdSM → vDC: DimChannel(mode=start_up/start_down)
            vDC: Begin continuous value adjustment
            vDC → vdSM: Push notifications as value changes
            
            User releases button:
            vdSM → vDC: DimChannel(mode=stop)
            vDC: Halt dimming at current value
        
        Example:
            # Start dimming brightness up at 15%/second
            output.start_dimming(DSChannelType.BRIGHTNESS, 'up', rate=15.0)
            
            # Later: stop dimming
            output.stop_dimming(DSChannelType.BRIGHTNESS)
        """
        try:
            channel_type = DSChannelType(channel_id)
        except ValueError:
            logger.error(f"Invalid channel ID: {channel_id}")
            return
        
        channel = self.channels.get(channel_type)
        if not channel:
            logger.warning(f"Channel {channel_type} not found")
            return
        
        logger.info(f"Start dimming {channel_type} {direction} at {rate}%/s")
        
        # Store dimming state
        if not hasattr(self, '_dimming_channels'):
            self._dimming_channels = {}
        
        self._dimming_channels[channel_type] = {
            'direction': direction,
            'rate': rate
        }
        
        # Trigger dimming via hardware callback
        # Real implementation would start a task that continuously updates value
        if self._hardware_callback:
            self._hardware_callback('start_dimming', {
                'channel': channel_type,
                'direction': direction,
                'rate': rate
            })
    
    def stop_dimming(self, channel_id: int) -> None:
        """
        Stop continuous dimming of a channel.
        
        Args:
            channel_id: Channel type ID to stop dimming
        
        Example:
            output.stop_dimming(DSChannelType.BRIGHTNESS)
        """
        try:
            channel_type = DSChannelType(channel_id)
        except ValueError:
            logger.error(f"Invalid channel ID: {channel_id}")
            return
        
        logger.info(f"Stop dimming {channel_type}")
        
        if hasattr(self, '_dimming_channels'):
            self._dimming_channels.pop(channel_type, None)
        
        # Notify hardware
        if self._hardware_callback:
            self._hardware_callback('stop_dimming', {
                'channel': channel_type
            })
    
    def _notify_value_change(self, channel_type: DSChannelType, value: float) -> None:
        """
        Notify device that a channel value changed.
        
        This triggers push notifications to vdSM when output values change.
        
        Args:
            channel_type: Channel that changed
            value: New value
        """
        # Notify parent device if it has a callback
        if hasattr(self.vdsd, '_on_output_change'):
            self.vdsd._on_output_change(self.output_id, channel_type, value)
