# vDC API Compliance Fixes - Implementation Guide

**Date:** 2026-02-09  
**Status:** PARTIALLY IMPLEMENTED - SEE BELOW

---

## Implementation Status

### ✅ Issue #1: Device Immutability (PARTIALLY COMPLETE)

**Completed:**
- Added `_announced` flag to VdSD.__init__()  
- Added `mark_announced()` method to VdSD
- Updated docstrings for add_output_channel(), add_button(), add_binary_input(), add_sensor(), configure()

**TODO - Add Runtime Checks:**

Add this check at the START of each method implementation (after docstring, before logic):

```python
# In add_output_channel() - after line ~708
if self._announced:
    raise RuntimeError(
        f"Cannot add output channel to device {self.dsuid} after announcement to vdSM. "
        f"Per vDC API specification, device structure is immutable once announced.\n"
        f"To modify device capabilities:\n"
        f"  1. Send vanish notification: await vdc.vanish_device('{self.dsuid}')\n"
        f"  2. Delete device: vdc.delete_vdsd('{self.dsuid}')\n"
        f"  3. Create new device with desired configuration\n"
        f"  4. New device will be announced automatically"
    )

# In add_button() - after line ~810
if self._announced:
    raise RuntimeError(
        f"Cannot add button to device {self.dsuid} after announcement to vdSM. "
        f"Device structure is immutable once announced per vDC API specification."
    )

# In add_sensor() - after line ~855  
if self._announced:
    raise RuntimeError(
        f"Cannot add sensor to device {self.dsuid} after announcement to vdSM. "
        f"Device structure is immutable once announced per vDC API specification."
    )

# In configure() - after line ~360
if self._announced:
    raise RuntimeError(
        f"Cannot configure device {self.dsuid} after announcement to vdSM. "
        f"Device structure is immutable once announced per vDC API specification."
    )
```

**TODO - Call mark_announced():**

In `pyvdcapi/entities/vdc.py`, after creating device announcements:

```python
def announce_devices(self) -> List[Message]:
    """Create device announcement messages for all vdSDs."""
    announcements = []
    for vdsd in self._vdsds.values():
        message = vdsd.announce_to_vdsm()
        announcements.append(message)
        vdsd.mark_announced()  # ADD THIS LINE
    logger.debug(f"Created {len(announcements)} device announcements")
    return announcements
```

---

## Issue #2: Button ClickType Direct Input (NOT STARTED)

### Required Changes

1. **Rename existing Button class to DSButtonStateMachine**

File: `pyvdcapi/components/button_templates.py` (NEW FILE)

```python
"""
Optional button state machine templates implementing standard timing behaviors.

These are HELPERS, not core API. Use ButtonInput for API-compliant implementation.
"""

import time
import logging
from typing import Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities.vdsd import VdSD
    from .button_input import ButtonInput

logger = logging.getLogger(__name__)


class DSButtonStateMachine:
    """
    Optional state machine implementing digitalSTROM native button behavior.
    
    This is a TEMPLATE/HELPER for emulating dS physical buttons.
    It converts press/release events into clickType values.
    
    Use this when:
    - Emulating native dS buttons (wall switches)
    - Physical button only provides press/release signals
    - Want standard dS timing behavior
    
    For custom button logic or hardware that provides clickType directly,
    use ButtonInput.set_click_type() instead.
    """
    
    # digitalSTROM standard timing constants
    DOUBLE_PRESS_INTERVAL = 0.5   # 500ms between presses
    TRIPLE_PRESS_INTERVAL = 0.5   # 500ms for triple
    LONG_PRESS_THRESHOLD = 1.0    # 1 second for long press
    
    def __init__(self, button_input: "ButtonInput"):
        """
        Initialize state machine.
        
        Args:
            button_input: ButtonInput to send clickType values to
        """
        self.button_input = button_input
        self._pressed = False
        self._press_start_time: Optional[float] = None
        self._last_release_time: Optional[float] = None
        self._press_count = 0
        self._long_press_sent = False
        
    def press(self) -> None:
        """
        Handle physical button press.
        
        Call this when hardware detects button pressed down.
        """
        current_time = time.time()
        
        if self._pressed:
            logger.warning("Button already pressed")
            return
            
        self._pressed = True
        self._press_start_time = current_time
        self._long_press_sent = False
        
        # Check for multi-press
        if self._last_release_time and \
           current_time - self._last_release_time < self.DOUBLE_PRESS_INTERVAL:
            self._press_count += 1
        else:
            self._press_count = 1
            
        logger.debug(f"Button pressed (count={self._press_count})")
        
    def release(self) -> None:
        """
        Handle physical button release.
        
        Call this when hardware detects button released.
        Determines and sends appropriate clickType.
        """
        if not self._pressed:
            logger.warning("Button not currently pressed")
            return
            
        current_time = time.time()
        duration = current_time - self._press_start_time
        
        # Determine clickType based on digitalSTROM logic
        if duration >= self.LONG_PRESS_THRESHOLD:
            # Long press - send hold_end
            click_type = 6  # hold_end
            self._press_count = 0  # Reset multi-press counter
        else:
            # Short press - use press count
            if self._press_count == 1:
                click_type = 0  # tip_1x
            elif self._press_count == 2:
                click_type = 1  # tip_2x  
            elif self._press_count == 3:
                click_type = 2  # tip_3x
            else:
                click_type = 3  # tip_4x
                self._press_count = 0  # Reset after 4 presses
                
        self._pressed = False
        self._last_release_time = current_time
        
        logger.info(f"Button released: clickType={click_type}, duration={duration:.3f}s")
        
        # Send to API-compliant ButtonInput
        self.button_input.set_click_type(click_type)
        
    def check_long_press(self) -> None:
        """
        Check if long press threshold reached (call periodically if needed).
        
        Some implementations send hold_start when threshold is reached,
        before button is released. Call this method periodically (e.g., every 100ms)
        if you need this behavior.
        """
        if self._pressed and not self._long_press_sent:
            if time.time() - self._press_start_time >= self.LONG_PRESS_THRESHOLD:
                self.button_input.set_click_type(4)  # hold_start
                self._long_press_sent = True
```

2. **Create new API-compliant ButtonInput class**

File: `pyvdcapi/components/button_input.py` (NEW FILE)

```python
"""
API-compliant button input implementation.

ButtonInput accepts clickType values directly as specified in vDC API.
"""

import time
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities.vdsd import VdSD

logger = logging.getLogger(__name__)


class ButtonInput:
    """
    API-compliant button input that accepts clickType directly.
    
    This is the core implementation matching vDC API specification (section 4.2.3).
    
    Per API specification, clickType is an integer input (not calculated):
    - 0: tip_1x
    - 1: tip_2x
    - 2: tip_3x
    - 3: tip_4x
    - 4: hold_start
    - 5: hold_repeat
    - 6: hold_end
    - 7: click_1x
    - 8: click_2x
    - 9: click_3x
    - 10: short_long
    - 11: local_off
    - 12: local_on
    - 13: short_short_long
    - 14: local_stop
    - 255: idle (no recent click)
    
    Use this when:
    - Hardware provides clickType directly (smart button devices)
    - External logic determines click type
    - Custom button behaviors needed
    
    For simple press/release buttons wanting dS timing, use DSButtonStateMachine.
    """
    
    def __init__(
        self,
        vdsd: "VdSD",
        name: str,
        button_type: int = 0,
        button_id: Optional[int] = None,
        button_element_id: int = 0,
        **properties
    ):
        """
        Initialize button input.
        
        Args:
            vdsd: Parent VdSD device
            name: Human-readable button name
            button_type: Physical button type (0=undefined, 1=single, 2=2-way, 3=4-way, etc.)
            button_id: Physical button ID (optional)
            button_element_id: Element of multi-contact button (default: 0=center)
            **properties: Additional properties (group, function, mode, channel, etc.)
        """
        self.vdsd = vdsd
        self.name = name
        self.button_type = button_type
        self.button_id = button_id if button_id is not None else 0
        self.button_element_id = button_element_id
        
        # Button state per API specification (section 4.2.3)
        self._click_type: int = 255  # 255 = idle (no recent click)
        self._value: Optional[bool] = None  # false=inactive, true=active, None=unknown
        self._age: float = 0.0  # Age of state in seconds
        self._error: int = 0  # 0=ok, 1=open circuit, 2=short circuit, etc.
        
        # Timestamp for age calculation
        self._last_update_time: float = time.time()
        
        # Settings (section 4.2.2)
        self.group = properties.get("group", 1)  # dS group
        self.function = properties.get("function", 0)  # 0=device, 5=room, etc.
        self.mode = properties.get("mode", 0)  # 0=standard, 2=presence, etc.
        self.channel = properties.get("channel", 0)  # Channel to control
        self.sets_local_priority = properties.get("setsLocalPriority", False)
        self.calls_present = properties.get("callsPresent", False)
        
        logger.debug(f"Created ButtonInput: id={self.button_id}, name='{name}', type={button_type}")
        
    def set_click_type(self, click_type: int) -> None:
        """
        Set button click type directly (API-compliant method).
        
        This is the primary method for reporting button events to vdSM.
        
        Args:
            click_type: Integer from API specification (0-14, 255)
        
        Raises:
            ValueError: If clickType is not valid per API spec
        
        Example:
            # Hardware reports double click
            button.set_click_type(1)  # tip_2x
            
            # Long press started
            button.set_click_type(4)  # hold_start
            
            # Button released after long press
            button.set_click_type(6)  # hold_end
            
            # Local off action
            button.set_click_type(11)  # local_off
        """
        # Validate clickType per API specification
        valid_types = list(range(15)) + [255]
        if click_type not in valid_types:
            raise ValueError(
                f"Invalid clickType: {click_type}. "
                f"Must be 0-14 or 255 per vDC API specification."
            )
            
        self._click_type = click_type
        self._last_update_time = time.time()
        self._age = 0.0
        
        logger.info(f"Button {self.button_id} clickType={click_type} ({self._click_type_name(click_type)})")
        
        # Push property to vdSM
        self.vdsd.push_button_state(self.button_id, click_type)
        
    def set_value(self, value: Optional[bool]) -> None:
        """
        Set button active/inactive state.
        
        Args:
            value: False=inactive, True=active, None=unknown
        """
        self._value = value
        self._last_update_time = time.time()
        self._age = 0.0
        
    def get_state(self) -> Dict[str, Any]:
        """
        Get current button state (for property queries).
        
        Returns API-compliant state per section 4.2.3.
        """
        # Update age
        self._age = time.time() - self._last_update_time
        
        return {
            "value": self._value,
            "clickType": self._click_type,
            "age": self._age,
            "error": self._error
        }
        
    def get_description(self) -> Dict[str, Any]:
        """
        Get button description (for property queries).
        
        Returns API-compliant description per section 4.2.1.
        """
        return {
            "name": self.name,
            "dsIndex": self.button_id,
            "supportsLocalKeyMode": True,
            "buttonID": self.button_id,
            "buttonType": self.button_type,
            "buttonElementID": self.button_element_id
        }
        
    def get_settings(self) -> Dict[str, Any]:
        """
        Get button settings (for property queries).
        
        Returns API-compliant settings per section 4.2.2.
        """
        return {
            "group": self.group,
            "function": self.function,
            "mode": self.mode,
            "channel": self.channel,
            "setsLocalPriority": self.sets_local_priority,
            "callsPresent": self.calls_present
        }
        
    @staticmethod
    def _click_type_name(click_type: int) -> str:
        """Get human-readable name for clickType."""
        names = {
            0: "tip_1x", 1: "tip_2x", 2: "tip_3x", 3: "tip_4x",
            4: "hold_start", 5: "hold_repeat", 6: "hold_end",
            7: "click_1x", 8: "click_2x", 9: "click_3x",
            10: "short_long", 11: "local_off", 12: "local_on",
            13: "short_short_long", 14: "local_stop",
            255: "idle"
        }
        return names.get(click_type, f"unknown({click_type})")
```

3. **Update VdSD.add_button() method**

```python
# In pyvdcapi/entities/vdsd.py

def add_button(
    self,
    name: str,
    button_type: int = 0,
    **properties
) -> "ButtonInput":
    """
    Add API-compliant button input to this device.
    
    Returns ButtonInput that accepts clickType directly per vDC API spec.
    
    For simple press/release buttons wanting digitalSTROM timing behavior,
    use add_ds_button() instead.
    """
    if self._announced:
        raise RuntimeError(
            f"Cannot add button to device {self.dsuid} after announcement to vdSM."
        )
        
    from ..components.button_input import ButtonInput
    
    button = ButtonInput(self, name, button_type, **properties)
    self._buttons.append(button)
    
    logger.info(f"Added button '{name}' to vdSD {self.dsuid}")
    return button

def add_ds_button(
    self,
    name: str,
    **properties
) -> "DSButtonStateMachine":
    """
    Add button with digitalSTROM standard timing behavior.
    
    Convenience method that creates ButtonInput + DSButtonStateMachine.
    Returns state machine for wiring to physical button press/release.
    
    Example:
        ds_button = device.add_ds_button("Wall Switch")
        gpio.on_press(lambda: ds_button.press())
        gpio.on_release(lambda: ds_button.release())
    """
    button_input = self.add_button(name, **properties)
    
    from ..components.button_templates import DSButtonStateMachine
    return DSButtonStateMachine(button_input)
```

---

## Issue #3: Single Output Per Device (NOT STARTED)

### Required Changes

1. **Refactor VdSD._outputs from Dict to Optional[Output]**

```python
# In VdSD.__init__()
# OLD:
self._outputs: Dict[int, "Output"] = {}  # outputID -> Output

# NEW:
self._output: Optional["Output"] = None  # Max ONE output per device per API
```

2. **Update add_output_channel() to use single output**

```python
def add_output_channel(
    self,
    channel_type: int,
    min_value: float = 0.0,
    max_value: float = 100.0,
    resolution: float = 0.1,
    initial_value: Optional[float] = None,
    **properties
) -> "OutputChannel":
    """
    Add an output channel to this device's output.
    
    Per vDC API specification, a device has maximum ONE output,
    but that output can have multiple channels.
    
    Correct: Device → Output → [Channel(brightness), Channel(hue), Channel(saturation)]
    Wrong: Device → [Output(brightness), Output(hue), Output(saturation)]
    """
    if self._announced:
        raise RuntimeError(...)
        
    # Remove output_id parameter - not needed with single output
    # properties.get("output_id", 0) - DELETE THIS
    
    # Create single output if needed
    if self._output is None:
        from ..components.output import Output
        self._output = Output(
            vdsd=self,
            output_function=properties.get("output_function", "dimmer"),
            output_mode=properties.get("output_mode", "gradual")
        )
    
    # Create channel
    from ..components.output_channel import OutputChannel
    channel = OutputChannel(
        vdsd=self,
        channel_type=channel_type,
        min_value=min_value,
        max_value=max_value,
        resolution=resolution,
        initial_value=initial_value
    )
    
    # Add channel to THE output (singular)
    self._output.add_channel(channel)
    
    logger.info(f"Added channel type {channel_type} to device {self.dsuid}")
    return channel
```

3. **Update Output class to remove output_id**

```python
# In pyvdcapi/components/output.py

class Output:
    """
    Device output container (max ONE per device per vDC API).
    
    An output contains multiple channels representing different
    control aspects (brightness, hue, saturation, position, etc.).
    """
    
    def __init__(
        self,
        vdsd: "VdSD",
        output_function: str = "dimmer",
        output_mode: str = "gradual",
        **properties
    ):
        """
        Initialize output.
        
        Args:
            vdsd: Parent device
            output_function: Output function type (dimmer, colordimmer, etc.)
            output_mode: Output mode (gradual, switched, disabled)
        
        NOTE: output_id parameter REMOVED - not needed per API spec
        """
        self.vdsd = vdsd
        self.output_function = output_function
        self.output_mode = output_mode
        self._channels: Dict[int, "OutputChannel"] = {}  # channelType -> Channel
        # ... rest of implementation
```

4. **Update configure() to use singular 'output' key**

```python
def configure(self, config: Dict[str, Any]) -> None:
    """Configure device from config dict."""
    if self._announced:
        raise RuntimeError(...)
        
    # OLD (wrong - plural):
    # if "outputs" in config:
    #     for output_config in config["outputs"]:
    
    # NEW (correct - singular):
    if "output" in config:
        output_config = config["output"]
        
        # Set output properties
        self._output_function = output_config.get("function", "dimmer")
        self._output_mode = output_config.get("mode", "gradual")
        
        # Add all channels to the single output
        for channel_config in output_config.get("channels", []):
            self.add_output_channel(
                channel_type=channel_config["channelType"],
                min_value=channel_config.get("min", 0.0),
                max_value=channel_config.get("max", 100.0),
                resolution=channel_config.get("resolution", 0.1),
                initial_value=channel_config.get("default")
            )
```

5. **Update all references from _outputs to _output**

Search and replace in vdsd.py:
- `self._outputs` → `self._output`
- `if self._outputs:` → `if self._output:`
- `.values()` iterations need to be removed (single output)
- Dict access `self._outputs[output_id]` → `self._output`

6. **Update YAML persistence format**

```python
# OLD format:
{
    'outputs': [
        {
            'outputID': 0,
            'channels': [...]
        }
    ]
}

# NEW format:
{
    'output': {
        'function': 'colordimmer',
        'mode': 'gradual',
        'channels': [...]
    }
}
```

---

## Testing

After implementing fixes, run:

```bash
# Test immutability
python3 -c "
from pyvdcapi import VdcHost
host = VdcHost(port=8444, mac_address='00:11:22:33:44:55')
vdc = host.create_vdc('Test', 'Test')
device = vdc.create_vdsd('Light', 'Dimmer', 1)
device.mark_announced()
try:
    device.add_output_channel(1)  # Should raise RuntimeError
    print('ERROR: Should have raised RuntimeError!')
except RuntimeError as e:
    print(f'✓ Correctly blocked: {e}')
"

# Test button API
python3 -c "
from pyvdcapi.components.button_input import ButtonInput
from pyvdcapi.components.button_templates import DSButtonStateMachine
# Test that ButtonInput accepts all API clickTypes
button = ButtonInput(None, 'Test', 0)
for ct in [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,255]:
    button.set_click_type(ct)
print('✓ ButtonInput accepts all API clickTypes')
"

# Test single output
python3 -c "
device = vdc.create_vdsd('Light', 'RGB', 1)
device.add_output_channel(1)  # brightness
device.add_output_channel(2)  # hue  
device.add_output_channel(3)  # saturation
assert device._output is not None
assert len(device._output._channels) == 3
print('✓ Single output with multiple channels')
"
```

---

## Migration Guide for Existing Code

### For Users Currently Adding Features Dynamically

**OLD (non-compliant):**
```python
device = vdc.create_vdsd(...)
# Device might get announced here
device.add_output_channel(...)  # ERROR if already announced
```

**NEW (compliant):**
```python
device = vdc.create_vdsd(...)
# Configure BEFORE announcement
device.add_output_channel(...)
device.add_button(...)
# Now device can be announced
```

### For Users Using Button Timing

**OLD (timing-based):**
```python
button = device.add_button("Toggle")
gpio.on_press(lambda: button.press())
gpio.on_release(lambda: button.release())
```

**NEW (use template):**
```python
ds_button = device.add_ds_button("Toggle")
gpio.on_press(lambda: ds_button.press())
gpio.on_release(lambda: ds_button.release())
```

**NEW (direct clickType):**
```python
button = device.add_button("Smart Button")
smart_device.on_event(lambda event: button.set_click_type(event.click_type))
```

### For Users With Multiple Outputs

**OLD (non-compliant):**
```python
device.add_output_channel(DSChannelType.BRIGHTNESS, output_id=0)
device.add_output_channel(DSChannelType.POSITION, output_id=1)  # ❌ Wrong!
```

**NEW (compliant):**
```python
# All channels go to ONE output
device.add_output_channel(DSChannelType.BRIGHTNESS)
device.add_output_channel(DSChannelType.HUE)
device.add_output_channel(DSChannelType.SATURATION)
# All in device._output with multiple channels
```

---

## Priority Implementation Order

1. ✅ **Issue #1** - Device immutability checks (PARTIALLY DONE - add runtime checks)
2. **Issue #2** - Button refactoring (create new files, update VdSD)
3. **Issue #3** - Single output refactoring (most invasive, do last)

**Estimated Effort:**
- Issue #1 completion: 30 minutes
- Issue #2: 2-3 hours
- Issue #3: 4-6 hours

**Total:** ~8 hours of focused development work
