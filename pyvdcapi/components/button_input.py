"""
ButtonInput - API-compliant button input implementation.

This module implements button inputs that comply with vDC API specification section 4.2
(Button Input). Unlike the legacy Button class that calculates clickType from timing,
ButtonInput accepts clickType values directly from hardware or external logic.

According to vDC API specification (section 4.2.3 Button Input State):
    clickType is an INTEGER INPUT (not a calculated output) with values:
    - 0: tip_1x          (single tap)
    - 1: tip_2x          (double tap)
    - 2: tip_3x          (triple tap)
    - 3: tip_4x          (quad tap)
    - 4: hold_start      (long press started)
    - 5: hold_repeat     (long press continuing)
    - 6: hold_end        (long press released)
    - 7: click_1x        (confirmed single click)
    - 8: click_2x        (confirmed double click)
    - 9: click_3x        (confirmed triple click)
    - 10: short_long     (short press + long press)
    - 11: local_off      (local off action)
    - 12: local_on       (local on action)
    - 13: short_short_long (short + short + long)
    - 14: local_stop     (local stop action)
    - 255: idle          (no recent click)

Use Cases:

1. **Smart Button Hardware**: Devices that detect click patterns internally
   ```python
   button = ButtonInput(vdsd=device, name="Smart Button", button_type=1)
   
   # Hardware callback provides clickType directly
   def on_hardware_event(click_type_value):
       button.set_click_type(click_type_value)
   ```

2. **External Logic**: When you implement custom timing/pattern detection
   ```python
   button = ButtonInput(vdsd=device, name="Custom Button", button_type=1)
   
   # Your custom logic determines clickType
   if is_double_tap(timestamps):
       button.set_click_type(1)  # tip_2x
   ```

3. **Simple Direct Input**: Binary button states
   ```python
   button = ButtonInput(vdsd=device, name="Toggle", button_type=1)
   
   # Simple on/off
   button.set_value(True)   # Active
   button.set_click_type(0)  # tip_1x
   button.set_value(False)  # Inactive
   ```

For buttons that need digitalSTROM-compatible timing-based clickType detection,
use DSButtonStateMachine (separate helper class).
"""

import time
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities.vdsd import VdSD

logger = logging.getLogger(__name__)


# clickType enumeration per vDC API spec (section 4.2.3)
class ClickType:
    """Button click type constants from vDC API specification."""
    
    TIP_1X = 0              # Single tap
    TIP_2X = 1              # Double tap
    TIP_3X = 2              # Triple tap
    TIP_4X = 3              # Quad tap
    HOLD_START = 4          # Long press started
    HOLD_REPEAT = 5         # Long press continuing
    HOLD_END = 6            # Long press released
    CLICK_1X = 7            # Confirmed single click
    CLICK_2X = 8            # Confirmed double click
    CLICK_3X = 9            # Confirmed triple click
    SHORT_LONG = 10         # Short press + long press
    LOCAL_OFF = 11          # Local off action
    LOCAL_ON = 12           # Local on action
    SHORT_SHORT_LONG = 13   # Short + short + long
    LOCAL_STOP = 14         # Local stop action
    IDLE = 255              # No recent click
    
    # Human-readable names
    NAMES = {
        0: "tip_1x",
        1: "tip_2x",
        2: "tip_3x",
        3: "tip_4x",
        4: "hold_start",
        5: "hold_repeat",
        6: "hold_end",
        7: "click_1x",
        8: "click_2x",
        9: "click_3x",
        10: "short_long",
        11: "local_off",
        12: "local_on",
        13: "short_short_long",
        14: "local_stop",
        255: "idle"
    }
    
    @classmethod
    def name(cls, click_type: int) -> str:
        """Get human-readable name for clickType value."""
        return cls.NAMES.get(click_type, f"unknown({click_type})")


class ButtonInput:
    """
    API-compliant button input that accepts clickType directly.
    
    This implementation matches vDC API specification section 4.2 (Button Input).
    The clickType is provided as an integer input value, not calculated from timing.
    
    Button State (section 4.2.3):
    - value: bool/None - Active state (true=active, false=inactive, None=unknown)
    - clickType: int - Most recent click type (0-14, 255)
    - age: float - Age of state in seconds
    - error: int - Error state (0=ok, 1=open circuit, etc.)
    
    Button Settings (section 4.2.2):
    - group: dS group number
    - function: Function type (0=device, 5=room, etc.)
    - mode: Button mode (0=standard, 2=presence, etc.)
    - channel: Channel to control
    - setsLocalPriority: Should set local priority
    - callsPresent: Should call present when system is absent
    
    Button Description (section 4.2.1):
    - name: Human-readable name
    - dsIndex: Button index (0..N-1)
    - buttonID: Physical button ID (optional)
    - buttonType: Type of physical button (0=undefined, 1=single, 2=2-way, etc.)
    - buttonElementID: Element of multi-contact button (0=center, 1=down, 2=up, etc.)
    """
    
    def __init__(
        self,
        vdsd: "VdSD",
        name: str,
        button_type: int = 0,
        button_id: Optional[int] = None,
        button_element_id: int = 0,
        use_action_mode: bool = False,
        **properties
    ):
        """
        Initialize API-compliant button input.
        
        Args:
            vdsd: Parent VdSD device
            name: Human-readable button name (e.g., "Power Button")
            button_type: Physical button type per API (0=undefined, 1=single pushbutton,
                        2=2-way pushbutton, 3=4-way navigation, etc.)
            button_id: Physical button ID (optional, for multi-function buttons)
            button_element_id: Element ID for multi-contact buttons (0=center, 1=down,
                              2=up, 3=left, 4=right, etc.)
            use_action_mode: If True, button will report actionId/actionMode instead of
                           clickType/value. Default is False (use clickType mode).
            **properties: Additional settings (group, function, mode, channel, etc.)
        
        Button Modes:
            Standard mode (use_action_mode=False, default):
                - Reports button clicks via clickType (0-14, 255)
                - Reports active/inactive state via value (bool)
                - Use set_click_type() to update button state
            
            Action mode (use_action_mode=True):
                - Reports direct scene calls via actionId (scene id)
                - Reports scene call mode via actionMode (0=normal, 1=force, 2=undo)
                - Use set_action() to update button state
        
        Example:
            # Standard click-based button (default)
            button = ButtonInput(
                vdsd=device,
                name="Light Switch",
                button_type=1  # Single pushbutton
            )
            button.set_click_type(7)  # click_1x
            
            # Direct scene call button
            scene_button = ButtonInput(
                vdsd=device,
                name="Scene 5 Button",
                button_type=1,
                use_action_mode=True  # Enable action mode
            )
            scene_button.set_action(action_id=5, action_mode=0)
            
            # Multi-function 4-way navigation button (up element)
            nav_up = ButtonInput(
                vdsd=device,
                name="Navigation Up",
                button_type=4,  # 4-way with center
                button_id=0,    # Physical button 0
                button_element_id=2,  # Up element
                group=1,
                function=0
            )
        """
        self.vdsd = vdsd
        self.name = name
        self.button_type = button_type
        self.button_id = button_id if button_id is not None else 0
        self.button_element_id = button_element_id
        
        # Button mode configuration (set during instantiation)
        self._use_action_mode: bool = use_action_mode
        
        # Button state per API specification (section 4.2.3)
        # Standard click-based mode:
        self._click_type: int = ClickType.IDLE  # 255 = idle (no recent click)
        self._value: Optional[bool] = None  # false=inactive, true=active, None=unknown
        
        # Alternative: Direct scene call mode (actionId/actionMode instead of clickType/value)
        self._action_id: Optional[int] = None  # Scene id for direct scene calls
        self._action_mode: Optional[int] = None  # 0=normal, 1=force, 2=undo
        
        # Common state fields:
        self._age: float = 0.0  # Age of state in seconds
        self._error: int = 0  # 0=ok, 1=open circuit, 2=short circuit, etc.
        
        # Timestamp for age calculation
        self._last_update_time: float = time.time()
        
        # Settings (section 4.2.2) - stored persistently in vDC
        self.group = properties.get("group", 1)  # dS group number (default: light)
        self.function = properties.get("function", 0)  # 0=device, 5=room, etc.
        self.mode = properties.get("mode", 0)  # 0=standard, 2=presence, etc.
        self.channel = properties.get("channel", 0)  # Channel to control (0=default)
        self.sets_local_priority = properties.get("setsLocalPriority", False)
        self.calls_present = properties.get("callsPresent", False)
        
        # Description (section 4.2.1) - invariable properties
        self.supports_local_key_mode = properties.get("supportsLocalKeyMode", True)
        self.ds_index = self.button_id  # 0..N-1 where N=number of buttons
        
        logger.debug(
            f"Created ButtonInput: id={self.button_id}, name='{name}', "
            f"type={button_type}, element={button_element_id}"
        )
        
    def set_click_type(self, click_type: int) -> None:
        """
        Set button click type directly (PRIMARY API METHOD).
        
        This is how hardware or external logic reports button events to the vDC.
        The clickType value is sent to vdSM via property push notification.
        
        Args:
            click_type: Integer from API specification (0-14 or 255)
                0: tip_1x - Single tap
                1: tip_2x - Double tap
                2: tip_3x - Triple tap
                3: tip_4x - Quad tap
                4: hold_start - Long press started
                5: hold_repeat - Long press continuing
                6: hold_end - Long press released
                7: click_1x - Confirmed single click
                8: click_2x - Confirmed double click
                9: click_3x - Confirmed triple click
                10: short_long - Short press + long press
                11: local_off - Local off action
                12: local_on - Local on action
                13: short_short_long - Short + short + long
                14: local_stop - Local stop action
                255: idle - No recent click
        
        Raises:
            ValueError: If clickType is not valid per API specification
        
        Example:
            # Hardware detected double tap
            button.set_click_type(1)  # tip_2x
            
            # User started long press
            button.set_click_type(4)  # hold_start
            
            # User released long press
            button.set_click_type(6)  # hold_end
            
            # Local off button action
            button.set_click_type(11)  # local_off
        """
        # Validate clickType per API specification
        # Warn if button is configured for action mode
        if self._use_action_mode:
            logger.warning(
                f"Button {self.button_id} '{self.name}' is configured for action mode "
                f"(use_action_mode=True) but set_click_type() was called. "
                f"Use set_action() instead, or create button with use_action_mode=False."
            )
        
        valid_types = list(range(15)) + [255]
        if click_type not in valid_types:
            raise ValueError(
                f"Invalid clickType: {click_type}. "
                f"Must be 0-14 or 255 per vDC API specification (section 4.2.3)."
            )
        
        # Clear action mode (allows switching mode at runtime if needed)
        self._action_id = None
        self._action_mode = None
            
        self._click_type = click_type
        self._last_update_time = time.time()
        self._age = 0.0
        
        logger.info(
            f"Button {self.button_id} '{self.name}' clickType={click_type} "
            f"({ClickType.name(click_type)})"
        )
        
        # Push property notification to vdSM
        # This sends the button state change to the digital STROM server
        self.vdsd.push_button_state(self.button_id, click_type)
    
    def set_action(self, action_id: int, action_mode: int = 0) -> None:
        """
        Set button to direct scene call mode (ALTERNATIVE API METHOD).
        
        This is used when the button emits direct scene calls instead of regular
        button clicks. When actionId is set, the button state returns actionId/actionMode
        instead of value/clickType.
        
        Per vDC API section 4.2.3: \"Alternatively, buttons can emit direct scene calls
        instead of button clicks. So the buttonInputState can contain the actionId and
        actionMode properties instead of value and clickType when the most current button
        action was not a regular click event, but a direct scene call.\"
        
        Args:
            action_id: Scene id to call (integer)
            action_mode: Action mode
                0: normal - Standard scene call
                1: force - Force scene call (ignore local priority)
                2: undo - Undo scene call
        
        Raises:
            ValueError: If action_mode is not valid per API specification
        
        Example:
            # Button configured to call scene 5 directly
            button.set_action(action_id=5, action_mode=0)
            
            # Button calls scene with force
            button.set_action(action_id=10, action_mode=1)
            
            # Button calls undo scene
            button.set_action(action_id=8, action_mode=2)
        
        Note:
            When actionId/actionMode are set, value/clickType are not included
            in the button state returned by get_state().
        """
        # Warn if button is configured for click mode
        if not self._use_action_mode:
            logger.warning(
                f"Button {self.button_id} '{self.name}' is configured for click mode "
                f"(use_action_mode=False) but set_action() was called. "
                f"Use set_click_type() instead, or create button with use_action_mode=True."
            )
        
        # Validate action mode
        if action_mode not in [0, 1, 2]:
            raise ValueError(
                f"Invalid actionMode {action_mode}. Must be 0 (normal), 1 (force), or 2 (undo)."
            )
        
        # Clear click mode (allows switching mode at runtime if needed)
        self._click_type = ClickType.IDLE
        self._value = None
        
        # Update state
        self._action_id = action_id
        self._action_mode = action_mode
        self._last_update_time = time.time()
        self._age = 0.0
        
        logger.info(
            f"Button {self.button_id} '{self.name}' set to action mode: "
            f"actionId={action_id}, actionMode={action_mode}"
        )
        
        # Push property notification to vdSM
        self.vdsd.push_button_state(self.button_id, None)  # Use None to indicate action mode
        
    def set_value(self, value: Optional[bool]) -> None:
        """
        Set button active/inactive state.
        
        The 'value' field indicates whether the button is currently active (pressed)
        or inactive (released). This is separate from clickType.
        
        Args:
            value: Button state
                False - Inactive (released)
                True - Active (pressed)
                None - Unknown state
        
        Example:
            # Button pressed
            button.set_value(True)
            
            # Button released
            button.set_value(False)
        """
        self._value = value
        self._last_update_time = time.time()
        self._age = 0.0
        
        logger.debug(f"Button {self.button_id} value={value}")
        
    def set_error(self, error_code: int) -> None:
        """
        Set button error state.
        
        Args:
            error_code: Error code per API specification
                0 - OK (no error)
                1 - Open circuit
                2 - Short circuit
                4 - Bus connection problem
                5 - Low battery in device
                6 - Other device error
        """
        self._error = error_code
        logger.warning(f"Button {self.button_id} error={error_code}")
        
    def get_click_type(self) -> int:
        """
        Get current clickType value.
        
        Returns:
            Current clickType (0-14 or 255)
        """
        return self._click_type
        
    def get_value(self) -> Optional[bool]:
        """
        Get current button value (active/inactive state).
        
        Returns:
            Current value (True/False/None)
        """
        return self._value
        
    def get_state(self) -> Dict[str, Any]:
        """
        Get current button state for property queries.
        
        Returns API-compliant state per section 4.2.3.
        This is called when vdSM queries button properties.
        
        Returns:
            Dictionary with state fields:
                Standard mode (button clicks):
                    - value: bool/None - Active state
                    - clickType: int - Most recent click type
                    - age: float - Age of state in seconds
                    - error: int - Error code
                
                Alternative mode (direct scene calls):
                    - actionId: int - Scene id
                    - actionMode: int - 0=normal, 1=force, 2=undo
                    - age: float - Age of state in seconds
                    - error: int - Error code
        """
        # Update age since last state change
        self._age = time.time() - self._last_update_time
        
        # Return based on configured mode (set during instantiation)
        if self._use_action_mode:
            # Action mode: Return actionId/actionMode
            # Use current values if set, otherwise return defaults
            return {
                "actionId": self._action_id if self._action_id is not None else 0,
                "actionMode": self._action_mode if self._action_mode is not None else 0,
                "age": self._age,
                "error": self._error
            }
        else:
            # Click mode (default): Return value/clickType
            return {
                "value": self._value,
                "clickType": self._click_type,
                "age": self._age,
                "error": self._error
            }
        
    def get_description(self) -> Dict[str, Any]:
        """
        Get button description for property queries.
        
        Returns API-compliant description per section 4.2.1.
        These are invariable properties that describe the button hardware.
        
        Returns:
            Dictionary with description fields:
                - name: Human-readable name
                - dsIndex: Button index (0..N-1)
                - supportsLocalKeyMode: Can be local button
                - buttonID: Physical button ID (optional)
                - buttonType: Type of physical button
                - buttonElementID: Element of multi-contact button
        """
        return {
            "name": self.name,
            "dsIndex": self.ds_index,
            "supportsLocalKeyMode": self.supports_local_key_mode,
            "buttonID": self.button_id,
            "buttonType": self.button_type,
            "buttonElementID": self.button_element_id
        }
        
    def get_settings(self) -> Dict[str, Any]:
        """
        Get button settings for property queries.
        
        Returns API-compliant settings per section 4.2.2.
        These are writable properties stored persistently in the vDC.
        
        Returns:
            Dictionary with settings fields:
                - group: dS group number
                - function: Function type
                - mode: Button mode
                - channel: Channel to control
                - setsLocalPriority: Should set local priority
                - callsPresent: Should call present
        """
        return {
            "group": self.group,
            "function": self.function,
            "mode": self.mode,
            "channel": self.channel,
            "setsLocalPriority": self.sets_local_priority,
            "callsPresent": self.calls_present
        }
        
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """
        Update button settings from vdSM property set request.
        
        Args:
            settings: Dictionary with setting fields to update
        
        Example:
            # vdSM changes button group
            button.update_settings({"group": 2})  # Change to blind group
        """
        if "group" in settings:
            self.group = settings["group"]
        if "function" in settings:
            self.function = settings["function"]
        if "mode" in settings:
            self.mode = settings["mode"]
        if "channel" in settings:
            self.channel = settings["channel"]
        if "setsLocalPriority" in settings:
            self.sets_local_priority = settings["setsLocalPriority"]
        if "callsPresent" in settings:
            self.calls_present = settings["callsPresent"]
            
        logger.debug(f"Button {self.button_id} settings updated: {settings}")
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert button to dictionary for persistence/serialization.
        
        Returns:
            Complete button representation with description, settings, state, and mode config
        """
        return {
            "description": self.get_description(),
            "settings": self.get_settings(),
            "state": self.get_state(),
            "useActionMode": self._use_action_mode  # Save mode configuration
        }
        
    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update button from dictionary (for deserialization).
        
        Args:
            data: Dictionary with button data
        """
        # Description fields (mostly immutable after creation)
        if "description" in data:
            desc = data["description"]
            if "name" in desc:
                self.name = desc["name"]
            if "buttonType" in desc:
                self.button_type = desc["buttonType"]
            if "buttonElementID" in desc:
                self.button_element_id = desc["buttonElementID"]
                
        # Settings (writable)
        if "settings" in data:
            self.update_settings(data["settings"])
            
        # State (for restoration)
        if "state" in data:
            state = data["state"]
            if "value" in state:
                self._value = state["value"]
            if "clickType" in state:
                self._click_type = state["clickType"]
            if "actionId" in state:
                self._action_id = state["actionId"]
                # If actionId is present, button was in action mode
                if "useActionMode" not in data:
                    self._use_action_mode = True
            if "actionMode" in state:
                self._action_mode = state["actionMode"]
            if "error" in state:
                self._error = state["error"]
        
        # Restore mode configuration if present
        if "useActionMode" in data:
            self._use_action_mode = data["useActionMode"]
                
    def __repr__(self) -> str:
        """String representation of button."""
        return (
            f"ButtonInput(id={self.button_id}, name='{self.name}', "
            f"type={self.button_type}, clickType={self._click_type})"
        )
