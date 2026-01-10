"""
Device Actions and States

This module provides action and state management for vDC devices.

Actions:
- Template-based operations devices can perform
- Standard actions (predefined by device type)
- Custom actions (user-configured)
- Dynamic actions (created by device itself)

States:
- Enumerated device status values
- State change notifications
- Predefined option sets

Device Properties:
- Generic device properties
- Typed values with validation
- Persistent storage

Action Flow:
┌─────────────────────────────────────────────────────────┐
│ 1. vdSM calls action (e.g., "identify")                 │
│    ↓                                                    │
│ 2. VdSD looks up action definition                     │
│    ↓                                                    │
│ 3. Validates parameters against template               │
│    ↓                                                    │
│ 4. Executes action handler callback                    │
│    ↓                                                    │
│ 5. Hardware performs action (e.g., blinks LED)         │
│    ↓                                                    │
│ 6. Returns result to vdSM                              │
└─────────────────────────────────────────────────────────┘

State Change Flow:
┌─────────────────────────────────────────────────────────┐
│ 1. Device state changes (e.g., "off" → "initializing") │
│    ↓                                                    │
│ 2. VdSD updates state value                            │
│    ↓                                                    │
│ 3. Triggers state change callbacks                     │
│    ↓                                                    │
│ 4. Sends push notification to vdSM                     │
│    ↓                                                    │
│ 5. vdSM updates state display                          │
└─────────────────────────────────────────────────────────┘

Common Actions:
- identify: Make device identifiable (blink, beep)
- reset: Reset device to defaults
- calibrate: Run calibration routine
- selftest: Perform self-test
- dim_up/dim_down: Adjust brightness
- move_up/move_down: Adjust position (blinds)

Common States:
- operational: Device state (off, initializing, running, error)
- reachable: Connectivity status
- service: Service mode indicator
- error: Error condition

Usage:
```python
from pyvdcapi.components.actions import ActionManager, StateManager

# Create action manager
actions = ActionManager(vdsd=device)

# Register identify action
def identify_handler(duration=3.0):
    print(f"Identifying device for {duration} seconds")
    hardware.blink_led(duration)
    return {"success": True}

actions.add_standard_action(
    name="identify",
    description="Identify device by blinking LED",
    params={
        "duration": {
            "type": "numeric",
            "min": 1.0,
            "max": 10.0,
            "default": 3.0,
            "siunit": "s"
        }
    },
    handler=identify_handler
)

# Execute action from vdSM
result = actions.call_action("std.identify", duration=5.0)

# Create state manager
states = StateManager(vdsd=device)

# Define operational state
states.add_state_description(
    name="operational",
    options={
        0: "off",
        1: "initializing",
        2: "running",
        3: "error"
    },
    description="Device operational state"
)

# Update state
states.set_state("operational", "running")  # Sends notification to vdSM

# Read state
current = states.get_state("operational")  # Returns "running"
```
"""

import logging
from typing import Dict, List, Optional, Any, Callable, TYPE_CHECKING
from ..utils.callbacks import Observable

if TYPE_CHECKING:
    from ..entities.vdsd import VdSD

logger = logging.getLogger(__name__)


class ActionParameter:
    """
    Parameter definition for an action.
    
    Defines the type, range, and validation for action parameters.
    """
    
    def __init__(
        self,
        param_type: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        resolution: Optional[float] = None,
        siunit: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        default: Optional[Any] = None
    ):
        """
        Initialize action parameter.
        
        Args:
            param_type: Type (numeric, string, boolean, enumeration)
            min_value: Minimum value (numeric only)
            max_value: Maximum value (numeric only)
            resolution: Resolution/precision (numeric only)
            siunit: SI unit (e.g., "s", "°C", "lux")
            options: Options for enumeration type
            default: Default value
        """
        self.type = param_type
        self.min = min_value
        self.max = max_value
        self.resolution = resolution
        self.siunit = siunit
        self.options = options or {}
        self.default = default
    
    def validate(self, value: Any) -> bool:
        """Validate parameter value."""
        if self.type == "numeric":
            if not isinstance(value, (int, float)):
                return False
            if self.min is not None and value < self.min:
                return False
            if self.max is not None and value > self.max:
                return False
            return True
        elif self.type == "enumeration":
            return value in self.options.values()
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {"type": self.type}
        if self.min is not None:
            result["min"] = self.min
        if self.max is not None:
            result["max"] = self.max
        if self.resolution is not None:
            result["resolution"] = self.resolution
        if self.siunit:
            result["siunit"] = self.siunit
        if self.options:
            result["options"] = self.options
        if self.default is not None:
            result["default"] = self.default
        return result


class ActionManager:
    """
    Manages device actions.
    
    Actions are operations that devices can perform:
    - Standard actions (built-in, immutable)
    - Custom actions (user-configured, persistent)
    - Dynamic actions (device-created, dynamic)
    
    Each action has:
    - Name/ID
    - Parameters with validation
    - Handler callback
    - Description
    """
    
    def __init__(self, vdsd: 'VdSD'):
        """
        Initialize action manager.
        
        Args:
            vdsd: Parent VdSD device
        """
        self.vdsd = vdsd
        
        # Action templates (action descriptions)
        self._templates: Dict[str, Dict[str, Any]] = {}
        
        # Standard actions (immutable, device-defined)
        self._standard_actions: Dict[str, Dict[str, Any]] = {}
        
        # Custom actions (user-configured, persistent)
        self._custom_actions: Dict[str, Dict[str, Any]] = {}
        
        # Dynamic actions (device-created)
        self._dynamic_actions: Dict[str, Dict[str, Any]] = {}
        
        # Action handlers: action_name -> callable
        self._handlers: Dict[str, Callable] = {}
        
        logger.debug(f"Created ActionManager for vdSD {vdsd.dsuid}")
    
    def add_action_template(
        self,
        name: str,
        params: Optional[Dict[str, ActionParameter]] = None,
        description: str = ""
    ) -> None:
        """
        Add action template definition.
        
        Templates define action structure that standard/custom actions
        can be based on.
        
        Args:
            name: Template name
            params: Parameter definitions
            description: Human-readable description
        """
        self._templates[name] = {
            "name": name,
            "params": {k: v.to_dict() for k, v in (params or {}).items()},
            "description": description
        }
        
        logger.debug(f"Added action template: {name}")
    
    def add_standard_action(
        self,
        name: str,
        description: str = "",
        params: Optional[Dict[str, ActionParameter]] = None,
        handler: Optional[Callable] = None
    ) -> None:
        """
        Add standard action (immutable, built-in).
        
        Args:
            name: Action name (will be prefixed with "std.")
            description: Human-readable description
            params: Parameter definitions
            handler: Callback to execute action
        
        Example:
            def identify(duration=3.0):
                hardware.blink_led(duration)
                return {"success": True}
            
            actions.add_standard_action(
                name="identify",
                description="Identify device",
                params={"duration": ActionParameter("numeric", min_value=1.0, max_value=10.0)},
                handler=identify
            )
        """
        action_id = f"std.{name}"
        
        self._standard_actions[action_id] = {
            "name": action_id,
            "action": name,
            "params": {k: v.to_dict() for k, v in (params or {}).items()},
            "description": description
        }
        
        if handler:
            self._handlers[action_id] = handler
        
        logger.info(f"Added standard action: {action_id}")
    
    def add_custom_action(
        self,
        name: str,
        title: str,
        action_template: str,
        params: Optional[Dict[str, Any]] = None,
        handler: Optional[Callable] = None
    ) -> None:
        """
        Add custom action (user-configured).
        
        Args:
            name: Unique action ID (will be prefixed with "custom.")
            title: Human-readable title
            action_template: Template action this is based on
            params: Parameter value overrides
            handler: Optional callback to execute action
        """
        action_id = f"custom.{name}"
        
        self._custom_actions[action_id] = {
            "name": action_id,
            "action": action_template,
            "title": title,
            "params": params or {}
        }
        
        if handler:
            self._handlers[action_id] = handler
        
        logger.info(f"Added custom action: {action_id}")
    
    def has_action(self, action_name: str) -> bool:
        """
        Check if action exists.
        
        Args:
            action_name: Full action name (e.g., "std.identify")
        
        Returns:
            True if action has a handler
        """
        return action_name in self._handlers
    
    async def call_action(self, action_name: str, **params) -> Dict[str, Any]:
        """
        Execute an action.
        
        Args:
            action_name: Full action name (e.g., "std.identify")
            **params: Action parameters
        
        Returns:
            Action result dictionary
        
        Example:
            result = await actions.call_action("std.identify", duration=5.0)
        """
        handler = self._handlers.get(action_name)
        if not handler:
            logger.error(f"No handler for action: {action_name}")
            return {"success": False, "error": "Action not found"}
        
        # TODO: Validate parameters against action definition
        
        try:
            result = handler(**params)
            # Handle async handlers
            if hasattr(result, '__await__'):
                result = await result
            logger.info(f"Executed action {action_name}: {result}")
            return result if isinstance(result, dict) else {"success": True, "result": result}
        except Exception as e:
            logger.error(f"Action {action_name} failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_action_descriptions(self) -> Dict[str, Any]:
        """Get all action templates."""
        return {"deviceActionDescriptions": list(self._templates.values())}
    
    def get_standard_actions(self) -> Dict[str, Any]:
        """Get all standard actions."""
        return {"standardActions": list(self._standard_actions.values())}
    
    def get_custom_actions(self) -> Dict[str, Any]:
        """Get all custom actions."""
        return {"customActions": list(self._custom_actions.values())}
    
    def to_dict(self) -> Dict[str, Any]:
        """Export all actions to dictionary."""
        return {
            **self.get_action_descriptions(),
            **self.get_standard_actions(),
            **self.get_custom_actions()
        }


class StateManager:
    """
    Manages device states.
    
    States are enumerated status values with limited options:
    - operational: Device running state
    - reachable: Network connectivity
    - service: Service mode indicator
    - error: Error conditions
    
    States differ from properties in having predefined option sets.
    """
    
    def __init__(self, vdsd: 'VdSD'):
        """
        Initialize state manager.
        
        Args:
            vdsd: Parent VdSD device
        """
        self.vdsd = vdsd
        
        # State descriptions: state_name -> {options, description}
        self._descriptions: Dict[str, Dict[str, Any]] = {}
        
        # Current state values: state_name -> option_value
        self._values: Dict[str, Any] = {}
        
        # Observable for state changes
        self._change_observable = Observable()
        
        logger.debug(f"Created StateManager for vdSD {vdsd.dsuid}")
    
    def add_state_description(
        self,
        name: str,
        options: Dict[int, str],
        description: str = ""
    ) -> None:
        """
        Define a state with its possible values.
        
        Args:
            name: State name (e.g., "operational")
            options: Map of option_id -> option_name
            description: Human-readable description
        
        Example:
            states.add_state_description(
                name="operational",
                options={
                    0: "off",
                    1: "initializing",
                    2: "running",
                    3: "error"
                },
                description="Device operational state"
            )
        """
        self._descriptions[name] = {
            "name": name,
            "options": options,
            "description": description
        }
        
        # Initialize with first option
        if options and name not in self._values:
            self._values[name] = list(options.values())[0]
        
        logger.debug(f"Added state description: {name} with {len(options)} options")
    
    def set_state(self, name: str, value: Any) -> None:
        """
        Set state value.
        
        Args:
            name: State name
            value: New value (must be in options)
        
        Example:
            states.set_state("operational", "running")
        """
        if name not in self._descriptions:
            logger.error(f"Unknown state: {name}")
            return
        
        # Validate value
        options = self._descriptions[name]["options"]
        if value not in options.values():
            logger.error(f"Invalid value '{value}' for state {name}")
            return
        
        old_value = self._values.get(name)
        if old_value == value:
            return  # No change
        
        self._values[name] = value
        
        logger.info(f"State {name}: {old_value} → {value}")
        
        # Trigger callbacks
        self._change_observable.notify(name, value)
        
        # TODO: Send push notification to vdSM
    
    def get_state(self, name: str) -> Optional[Any]:
        """
        Get current state value.
        
        Args:
            name: State name
        
        Returns:
            Current state value or None
        """
        return self._values.get(name)
    
    def on_change(self, callback: Callable[[str, Any], None]) -> None:
        """
        Register callback for state changes.
        
        Args:
            callback: Function(state_name, new_value)
        
        Example:
            def on_state_change(name, value):
                print(f"State {name} changed to {value}")
            
            states.on_change(on_state_change)
        """
        self._change_observable.subscribe(callback)
    
    def get_descriptions(self) -> Dict[str, Any]:
        """Get all state descriptions."""
        return {"deviceStateDescriptions": list(self._descriptions.values())}
    
    def get_values(self) -> Dict[str, Any]:
        """Get all current state values."""
        return {
            "deviceStates": [
                {"name": name, "value": value}
                for name, value in self._values.items()
            ]
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Export all states to dictionary."""
        return {
            **self.get_descriptions(),
            **self.get_values()
        }


class DevicePropertyManager:
    """
    Manages generic device properties.
    
    Device properties are typed values that don't fit into
    outputs, inputs, or states categories.
    """
    
    def __init__(self, vdsd: 'VdSD'):
        """
        Initialize property manager.
        
        Args:
            vdsd: Parent VdSD device
        """
        self.vdsd = vdsd
        
        # Property descriptions
        self._descriptions: Dict[str, ActionParameter] = {}
        
        # Property values
        self._values: Dict[str, Any] = {}
        
        logger.debug(f"Created DevicePropertyManager for vdSD {vdsd.dsuid}")
    
    def add_property(
        self,
        name: str,
        param_type: str,
        default: Optional[Any] = None,
        **kwargs
    ) -> None:
        """
        Add device property definition.
        
        Args:
            name: Property name
            param_type: Type (numeric, string, boolean, enumeration)
            default: Default value
            **kwargs: Additional parameters (min, max, resolution, siunit, options)
        """
        self._descriptions[name] = ActionParameter(
            param_type=param_type,
            default=default,
            **kwargs
        )
        
        if default is not None:
            self._values[name] = default
    
    def set_property(self, name: str, value: Any) -> bool:
        """
        Set property value.
        
        Args:
            name: Property name
            value: New value
        
        Returns:
            True if successful, False if validation failed
        """
        if name not in self._descriptions:
            logger.error(f"Unknown property: {name}")
            return False
        
        if not self._descriptions[name].validate(value):
            logger.error(f"Invalid value for property {name}: {value}")
            return False
        
        self._values[name] = value
        return True
    
    def get_property(self, name: str) -> Optional[Any]:
        """Get property value."""
        return self._values.get(name)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export properties to dictionary."""
        return {
            "devicePropertyDescriptions": [
                {"name": name, **desc.to_dict()}
                for name, desc in self._descriptions.items()
            ],
            "deviceProperties": [
                {"name": name, "value": value}
                for name, value in self._values.items()
            ]
        }
