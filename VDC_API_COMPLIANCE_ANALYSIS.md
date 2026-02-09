# vDC API Compliance Analysis

**Date:** 2026-02-09  
**Library:** pyvdcapi v1.0  
**Analysis Scope:** Critical API compliance issues

---

## Executive Summary

This analysis identifies **three critical compliance issues** in the current pyvdcapi implementation:

1. **🔴 CRITICAL:** Dynamic feature addition after device announcement not properly restricted
2. **🔴 CRITICAL:** Button implementation uses timing-based click detection instead of direct clickType input
3. **🔴 CRITICAL:** Multiple outputs per device allowed (API specifies max ONE output per device)

---

## Issue #1: Dynamic Feature Addition After Device Announcement

### API Specification

According to vDC API documentation (06-vdSD-Announcement-host-session.md):

- A device is announced once via `announcedevice` method
- After announcement, device-level methods can be invoked
- **Devices are immutable after announcement** - structure must not change
- To change device capabilities, the device must be:
  1. Removed via `vanish` notification (vDC → vdSM) or `remove` method (vdSM → vDC)
  2. Recreated with new configuration
  3. Re-announced via `announcedevice`

### Current Implementation Issues

**pyvdcapi allows dynamic addition of features after device creation:**

```python
# Current implementation allows this:
device = vdc.create_vdsd(name="Light", model="Simple", primary_group=DSGroup.YELLOW)
# Device gets announced to vdSM here...

# PROBLEM: Can add features after announcement!
device.add_output_channel(DSChannelType.BRIGHTNESS, ...)  # ❌ NOT ALLOWED
device.add_button(name="Toggle", ...)                     # ❌ NOT ALLOWED
device.add_sensor(name="Temperature", ...)                # ❌ NOT ALLOWED
```

**Methods that violate immutability after announcement:**
- `VdSD.add_output_channel()` - line 636
- `VdSD.add_button()` - line 728
- `VdSD.add_binary_input()` - line 776
- `VdSD.add_sensor()` - line 824

### Required Changes

1. **Add announcement state tracking:**
```python
class VdSD:
    def __init__(self, ...):
        self._announced = False
        
    def mark_announced(self):
        """Called by vDC after successful announcedevice."""
        self._announced = True
        logger.info(f"Device {self.dsuid} marked as announced to vdSM")
```

2. **Block feature addition after announcement:**
```python
def add_output_channel(self, ...):
    if self._announced:
        raise RuntimeError(
            f"Cannot add output channel to device {self.dsuid} after announcement. "
            f"To modify device capabilities:\n"
            f"1. Call vdc.vanish_device(dsuid) to remove from vdSM\n"
            f"2. Delete device: vdc.delete_vdsd(dsuid)\n"
            f"3. Create new device with desired configuration\n"
            f"4. Device will be auto-announced on next connection"
        )
    # ... existing implementation
```

3. **Apply to all feature addition methods:**
   - `add_output_channel()`
   - `add_button()`
   - `add_binary_input()`
   - `add_sensor()`
   - `configure()` (should only work before announcement)

4. **Document proper workflow in API_REFERENCE.md:**
```markdown
### Important: Device Immutability After Announcement

Once a device is announced to vdSM, its structure is **immutable**. You cannot add or remove:
- Output channels
- Buttons
- Binary inputs
- Sensors

To modify device capabilities:

1. **Remove the device:**
   ```python
   # Notify vdSM that device vanished
   await vdc.vanish_device(device.dsuid)
   
   # Delete from local collection
   vdc.delete_vdsd(device.dsuid)
   ```

2. **Create new device with updated configuration:**
   ```python
   device = vdc.create_vdsd(
       name="Updated Light",
       model="RGB Dimmer",
       primary_group=DSGroup.YELLOW
   )
   
   # Add all features BEFORE announcement
   device.add_output_channel(DSChannelType.BRIGHTNESS, ...)
   device.add_output_channel(DSChannelType.HUE, ...)
   device.add_output_channel(DSChannelType.SATURATION, ...)
   ```

3. **Device is auto-announced** on next vdSM connection
```

---

## Issue #2: Button Click Type Detection Logic

### API Specification

According to vDC API documentation (05-Button-Input.md, section 4.2.3):

**Button Input State:**
```
| clickType | r | integer enum | Most recent click state of the button:
|           |   |              | 0: tip_1x
|           |   |              | 1: tip_2x
|           |   |              | 2: tip_3x
|           |   |              | 3: tip_4x
|           |   |              | 4: hold_start
|           |   |              | 5: hold_repeat
|           |   |              | 6: hold_end
|           |   |              | 7: click_1x
|           |   |              | 8: click_2x
|           |   |              | 9: click_3x
|           |   |              | 10: short_long
|           |   |              | 11: local_off
|           |   |              | 12: local_on
|           |   |              | 13: short_short_long
|           |   |              | 14: local_stop
|           |   |              | 255: idle (no recent click)
```

**The clickType is an INPUT to the API, not a calculated output.**

The vDC API expects:
- Physical button hardware (or virtual button logic) determines the clickType
- VdSD receives clickType as an integer value
- VdSD reports this clickType to vdSM via property push

### Current Implementation Issues

**pyvdcapi implements timing-based click detection in the Button class:**

```python
# components/button.py, lines 203-290
class Button:
    DOUBLE_PRESS_INTERVAL = 0.5  # 500ms
    LONG_PRESS_THRESHOLD = 1.0   # 1 second
    
    def press(self):
        # Tracks press timing
        self._press_start_time = current_time
        
    def release(self):
        # CALCULATES click type based on timing
        press_duration = current_time - self._press_start_time
        
        if self._press_count >= 2:
            event_type = 1  # Double press
        elif press_duration >= self.LONG_PRESS_THRESHOLD:
            event_type = 3  # Release after long press
        else:
            event_type = 0  # Single press
```

**Problems:**

1. **API Violation:** The Button class determines clickType internally, but the API expects clickType as direct input
2. **Limited Click Types:** Only supports 4 types (0, 1, 2, 3), API defines 15+ types (0-14, 255)
3. **Inflexible:** Hardcoded timing thresholds don't match all hardware behaviors
4. **Not Compliant:** Cannot represent `tip_2x`, `tip_3x`, `hold_repeat`, `local_off`, etc.

### Required Changes

1. **Separate Core API from Optional Template**

Create two components:

**A) ButtonInput - Core API-compliant implementation:**

```python
# components/button_input.py
class ButtonInput:
    """
    API-compliant button input that accepts clickType directly.
    
    This is the core implementation matching vDC API specification.
    Use this when:
    - Hardware provides clickType directly (e.g., smart button devices)
    - External logic determines click type
    - Integration with non-standard button behaviors
    """
    
    def __init__(self, vdsd: "VdSD", name: str, button_type: int = 0, button_id: Optional[int] = None):
        self.vdsd = vdsd
        self.name = name
        self.button_type = button_type
        self.button_id = button_id or 0
        
        # Current state (API properties)
        self._click_type: int = 255  # 255 = idle
        self._value: Optional[bool] = None
        self._age: float = 0.0
        
    def set_click_type(self, click_type: int) -> None:
        """
        Set button click type directly (API-compliant method).
        
        Args:
            click_type: Integer from API specification:
                0: tip_1x, 1: tip_2x, 2: tip_3x, 3: tip_4x,
                4: hold_start, 5: hold_repeat, 6: hold_end,
                7: click_1x, 8: click_2x, 9: click_3x,
                10: short_long, 11: local_off, 12: local_on,
                13: short_short_long, 14: local_stop,
                255: idle
        
        Example:
            # Hardware reports double click
            button.set_click_type(1)  # tip_2x
            
            # Long press started
            button.set_click_type(4)  # hold_start
            
            # Button released
            button.set_click_type(6)  # hold_end
        """
        if click_type not in range(15) and click_type != 255:
            raise ValueError(f"Invalid clickType: {click_type}")
            
        self._click_type = click_type
        self._age = 0.0
        
        logger.info(f"Button {self.button_id} clickType={click_type}")
        
        # Push property to vdSM
        self.vdsd.push_button_state(self.button_id, click_type)
        
    def get_state(self) -> Dict[str, Any]:
        """Get current button state (for property queries)."""
        return {
            "value": self._value,
            "clickType": self._click_type,
            "age": self._age,
            "error": 0
        }
```

**B) DSButtonStateMachine - Optional Template:**

```python
# components/button_templates.py
class DSButtonStateMachine:
    """
    Optional state machine implementing digitalSTROM native button behavior.
    
    This is a TEMPLATE/HELPER, not core API. Use this when:
    - Emulating native dS buttons (wall switches, etc.)
    - Physical button only provides press/release signals
    - Want standard dS timing behavior
    
    For custom button logic, implement your own state machine and
    call ButtonInput.set_click_type() directly.
    """
    
    # digitalSTROM standard timing
    DOUBLE_PRESS_INTERVAL = 0.5
    TRIPLE_PRESS_INTERVAL = 0.5
    LONG_PRESS_THRESHOLD = 1.0
    
    def __init__(self, button_input: ButtonInput):
        self.button_input = button_input
        self._pressed = False
        self._press_start_time: Optional[float] = None
        self._last_release_time: Optional[float] = None
        self._press_count = 0
        
    def press(self) -> None:
        """Handle physical button press."""
        current_time = time.time()
        
        if not self._pressed:
            self._pressed = True
            self._press_start_time = current_time
            
            # Check for multi-press
            if self._last_release_time and \
               current_time - self._last_release_time < self.DOUBLE_PRESS_INTERVAL:
                self._press_count += 1
            else:
                self._press_count = 1
                
    def release(self) -> None:
        """Handle physical button release - determines clickType."""
        if not self._pressed:
            return
            
        current_time = time.time()
        duration = current_time - self._press_start_time
        
        # Determine clickType based on dS logic
        if duration >= self.LONG_PRESS_THRESHOLD:
            # Long press
            click_type = 6  # hold_end
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
                
        self._pressed = False
        self._last_release_time = current_time
        
        # Send to API-compliant ButtonInput
        self.button_input.set_click_type(click_type)
```

2. **Update VdSD to use ButtonInput:**

```python
class VdSD:
    def add_button(self, name: str, button_type: int = 0, **properties) -> ButtonInput:
        """Add API-compliant button input."""
        if self._announced:
            raise RuntimeError("Cannot add button after device announcement")
            
        button = ButtonInput(self, name, button_type)
        self._buttons.append(button)
        return button
        
    def add_ds_button(self, name: str, **properties) -> DSButtonStateMachine:
        """
        Convenience method: Add button with dS standard behavior.
        
        Returns state machine that can be used with physical buttons.
        """
        button_input = self.add_button(name, **properties)
        return DSButtonStateMachine(button_input)
```

3. **Update API_REFERENCE.md documentation:**

```markdown
## Button Input Handling

### Direct ClickType (API-Compliant)

For hardware that provides clickType directly:

```python
# Smart button that reports click types
button = device.add_button(name="Smart Button")

# Hardware event callback
def on_smart_button_event(event):
    button.set_click_type(event.click_type)

smart_button_device.on_event(on_smart_button_event)
```

### Using dS Button Template (Optional)

For simple press/release buttons wanting dS behavior:

```python
# Create button with dS timing logic
ds_button = device.add_ds_button(name="Wall Switch")

# Wire physical GPIO
gpio.on_press(lambda: ds_button.press())
gpio.on_release(lambda: ds_button.release())
```

### Custom Button Logic

Implement your own state machine for custom behaviors:

```python
button = device.add_button(name="Custom Button")

def custom_logic(press_pattern):
    if press_pattern == "quick_triple":
        button.set_click_type(2)  # tip_3x
    elif press_pattern == "hold_with_wiggle":
        button.set_click_type(13)  # short_short_long
```
```

---

## Issue #3: Multiple Outputs Per Device

### API Specification

According to vDC API documentation (11-Output.md, section 4.8):

**Output Description** (singular, not plural):
```
4.8 Output

Note: devices with no output functionality return a NULL response 
when queried for outputDescription, outputSettings or outputState
```

**The API defines ONE output per device, not multiple outputs.**

However, ONE output can have **multiple output channels:**

From Documentation/vdc-API-properties/12-Output-Channel.md:
```
4.8.4 Output Channel Descriptions
- Description of a single output channel
- The properties described here are contained in the elements 
  of the output-level 4.8.1 channelDescriptions property
```

**Structure:**
```
Device
  └── Output (singular, max 1)
       ├── OutputChannel (brightness)
       ├── OutputChannel (hue)
       ├── OutputChannel (saturation)
       └── OutputChannel (colortemp)
```

### Current Implementation Issues

**pyvdcapi allows multiple outputs per device:**

```python
# pyvdcapi/entities/vdsd.py, line 302
self._outputs: Dict[int, "Output"] = {}  # outputID -> Output

# Line 711-722
if output_id not in self._outputs:
    self._outputs[output_id] = Output(...)  # Multiple outputs possible!
```

**Current implementation structure:**
```
Device
  ├── Output[0]  # outputID=0
  │    ├── Channel (brightness)
  │    └── Channel (hue)
  ├── Output[1]  # outputID=1  ❌ SHOULD NOT EXIST
  │    └── Channel (position)
  └── Output[2]  # outputID=2  ❌ SHOULD NOT EXIST
       └── Channel (temperature)
```

**API-compliant structure should be:**
```
Device
  └── Output  # Only ONE
       ├── Channel (brightness)
       ├── Channel (hue)
       ├── Channel (position)
       └── Channel (temperature)
```

### Required Changes

1. **Refactor VdSD to enforce single output:**

```python
class VdSD:
    def __init__(self, ...):
        # Change from Dict to Optional single Output
        self._output: Optional["Output"] = None  # Only ONE output per device
        
    def add_output_channel(
        self,
        channel_type: int,
        **properties
    ) -> "OutputChannel":
        """Add a channel to this device's output."""
        if self._announced:
            raise RuntimeError("Cannot add channels after device announcement")
            
        # Create output container if needed (only once!)
        if self._output is None:
            from ..components.output import Output
            self._output = Output(
                vdsd=self,
                output_function=properties.get("output_function", "dimmer"),
                output_mode=properties.get("output_mode", "gradual")
            )
            
        # Add channel to THE output
        channel = OutputChannel(
            vdsd=self,
            channel_type=channel_type,
            ...
        )
        self._output.add_channel(channel)
        
        return channel
```

2. **Remove outputID concept entirely:**

The `output_id` parameter should be removed from:
- `add_output_channel()` parameters
- `Output.__init__()` parameters
- All property queries
- YAML persistence

**Rationale:** Since there's only ONE output per device, no ID is needed.

3. **Update Output class:**

```python
# components/output.py
class Output:
    """
    Device output container (max ONE per device).
    
    Per vDC API specification, a device has zero or one output.
    That output contains multiple channels.
    """
    
    def __init__(
        self,
        vdsd: "VdSD",
        output_function: str = "dimmer",
        output_mode: str = "gradual",
        **properties
    ):
        self.vdsd = vdsd
        self.output_function = output_function
        self.output_mode = output_mode
        self._channels: Dict[int, "OutputChannel"] = {}  # channelType -> Channel
        
    # Remove: output_id, outputID properties
```

4. **Update configure() method:**

```python
def configure(self, config: Dict[str, Any]) -> None:
    # OLD (multiple outputs):
    if "outputs" in config:
        for output_config in config["outputs"]:  # ❌ Multiple!
            ...
    
    # NEW (single output):
    if "output" in config:  # Singular!
        output_config = config["output"]
        for channel_config in output_config.get("channels", []):
            self.add_output_channel(
                channel_type=channel_config["channelType"],
                ...
            )
```

5. **Update examples and documentation:**

```python
# INCORRECT (current):
rgb_config = {
    'outputs': [  # ❌ Plural, array
        {
            'outputID': 0,  # ❌ No ID needed
            'channels': [...]
        }
    ]
}

# CORRECT (API-compliant):
rgb_config = {
    'output': {  # ✅ Singular, object
        'function': 'colordimmer',
        'mode': 'gradual',
        'channels': [
            {'channelType': DSChannelType.BRIGHTNESS, ...},
            {'channelType': DSChannelType.HUE, ...},
            {'channelType': DSChannelType.SATURATION, ...}
        ]
    }
}

device.configure(rgb_config)
```

---

## Migration Strategy

### Phase 1: Add Warnings (Non-Breaking)

1. Add deprecation warnings to current methods:
```python
def add_output_channel(self, ..., output_id=0):
    if output_id != 0:
        warnings.warn(
            "output_id parameter is deprecated. "
            "vDC API specifies max ONE output per device. "
            "All channels should use output_id=0.",
            DeprecationWarning
        )
```

2. Add warning when features added after announcement:
```python
def add_output_channel(self, ...):
    if self._announced:
        warnings.warn(
            "Adding features after device announcement violates vDC API. "
            "Use vanish/recreate pattern instead.",
            UserWarning
        )
```

### Phase 2: Implement Restrictions (Breaking)

1. Enforce single output (raise error for output_id != 0)
2. Block feature addition after announcement (raise RuntimeError)
3. Update all examples and documentation
4. Release as v2.0 with migration guide

### Phase 3: Refactor Implementation

1. Remove `_outputs` dict, replace with `_output` Optional
2. Remove `output_id` parameter completely
3. Update persistence format
4. Provide migration tool for existing YAML configs

---

## Testing Recommendations

1. **Add API Compliance Tests:**
```python
def test_single_output_per_device():
    """Verify only one output allowed per device."""
    device = vdc.create_vdsd(...)
    device.add_output_channel(DSChannelType.BRIGHTNESS)
    device.add_output_channel(DSChannelType.HUE)  # Same output, OK
    
    # Multiple outputs should fail (after fix)
    with pytest.raises(ValueError):
        device.add_output_channel(
            DSChannelType.POSITION,
            output_id=1  # ❌ Second output
        )

def test_immutable_after_announcement():
    """Verify features cannot be added after announcement."""
    device = vdc.create_vdsd(...)
    device.add_output_channel(DSChannelType.BRIGHTNESS)
    
    # Simulate announcement
    device.mark_announced()
    
    # Should fail
    with pytest.raises(RuntimeError):
        device.add_button("New Button")
```

2. **Add Button API Compliance Tests:**
```python
def test_button_direct_clicktype():
    """Verify button accepts direct clickType values."""
    button = device.add_button("Test")
    
    # Should accept all API-defined clickTypes
    for click_type in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 255]:
        button.set_click_type(click_type)
        assert button.get_state()["clickType"] == click_type
```

---

## Priority Recommendations

| Issue | Priority | Impact | Effort |
|-------|----------|--------|--------|
| #3 Output Implementation | **CRITICAL** | Breaking API violation | High |
| #2 Button ClickType | **CRITICAL** | Cannot represent all API values | Medium |
| #1 Immutability | **HIGH** | Can cause vdSM sync issues | Low |

**Recommended order:**
1. Fix Issue #1 (add immutability checks) - **LOW EFFORT, prevents future issues**
2. Fix Issue #2 (refactor button) - **MEDIUM EFFORT, enables full API support**
3. Fix Issue #3 (single output) - **HIGH EFFORT, but most critical API violation**

---

## Conclusion

The pyvdcapi library requires significant refactoring to fully comply with the vDC API specification. The three identified issues represent fundamental architectural misalignments that should be addressed before production deployment.

**Immediate Actions:**
1. Document these issues prominently in README.md
2. Add API compliance warnings to affected methods
3. Create GitHub issues tracking each violation
4. Plan v2.0 release with breaking changes to fix compliance

**Long-term Actions:**
1. Implement proposed architectural changes
2. Update all examples and documentation
3. Provide migration guide for existing users
4. Add comprehensive API compliance test suite
