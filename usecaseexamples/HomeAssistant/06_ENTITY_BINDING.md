# Entity Binding Implementation

## Overview

Entity binding connects Home Assistant entities to vDC device components, enabling bidirectional synchronization between HA states and vDC properties.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Home Assistant                           │
│                                                             │
│  ┌──────────────┐         ┌──────────────────────────┐     │
│  │ HA Entity    │         │ Entity Binding Manager   │     │
│  │              │◄────────┤                          │     │
│  │ light.kitchen│  Read   │  • State listeners       │     │
│  │              │         │  • Attribute mapping     │     │
│  │ state: on    │────────►│  • Value conversion      │     │
│  │ brightness:  │  Update │  • Error handling        │     │
│  │   200/255    │         └──────────┬───────────────┘     │
│  └──────────────┘                    │                     │
│                                      │                     │
│                            ┌─────────▼──────────────┐      │
│                            │ vDC Device Component   │      │
│                            │                        │      │
│                            │ OutputChannel          │      │
│                            │  channelType: BRIGHTNESS│      │
│                            │  value: 78.4%          │      │
│                            └────────────────────────┘      │
│                                      │                     │
│                                      ▼                     │
│                            ┌──────────────────┐            │
│                            │ JSON-RPC vDC API │            │
│                            │ (to vdSM/DSS)    │            │
│                            └──────────────────┘            │
└─────────────────────────────────────────────────────────────┘

Bidirectional Flow:
  HA Entity State → Entity Binding → vDC Component → vDC API
  vDC API Command → vDC Component → Entity Binding → HA Entity
```

## Binding Types

### 1. Output Channel Bindings

Map HA light entities to vDC output channels:

```python
# Example binding configuration
{
    "output_channels": [
        {
            "channel_index": 0,  # First channel (brightness)
            "entity_id": "light.kitchen",
            "attribute": "brightness",
            "converter": "brightness_255_to_percent"
        },
        {
            "channel_index": 1,  # Second channel (color)
            "entity_id": "light.kitchen",
            "attribute": "hs_color",
            "converter": "hs_to_rgb"
        }
    ]
}
```

### 2. Sensor Bindings

Map HA sensor entities to vDC sensor components:

```python
{
    "sensors": [
        {
            "sensor_index": 0,
            "entity_id": "sensor.kitchen_temperature",
            "attribute": "state",
            "converter": "float"
        }
    ]
}
```

### 3. Binary Input Bindings

Map HA binary sensors to vDC binary inputs:

```python
{
    "binary_inputs": [
        {
            "input_index": 0,
            "entity_id": "binary_sensor.motion",
            "attribute": "state",
            "converter": "on_off_to_bool"
        }
    ]
}
```

### 4. Button Input Bindings

Map HA events to vDC button presses:

```python
{
    "button_inputs": [
        {
            "button_index": 0,
            "event_type": "zha_event",
            "event_filter": {
                "device_id": "abc123",
                "command": "toggle"
            },
            "button_action": "SINGLE_CLICK"
        }
    ]
}
```

## Implementation

### Entity Binding Manager

Create `entity_binding.py`:

```python
"""Entity binding manager for vDC integration."""
from __future__ import annotations

import logging
from typing import Any, Callable

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_STATE_CHANGED,
    STATE_ON,
    STATE_OFF,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers import entity_registry as er

# pyvdcapi imports
from pyvdcapi.components.output_channel import OutputChannel
from pyvdcapi.components.sensor import Sensor
from pyvdcapi.components.binary_input import BinaryInput
from pyvdcapi.components.button import Button, DSButtonAction

_LOGGER = logging.getLogger(__name__)


class EntityBindingManager:
    """Manage entity bindings for a vDC device."""

    def __init__(self, hass: HomeAssistant, device: Any) -> None:
        """
        Initialize entity binding manager.
        
        Args:
            hass: Home Assistant instance
            device: vDC device to bind entities to
        """
        self.hass = hass
        self.device = device
        self._listeners: list[Callable] = []
        self._converters = ValueConverters()

    async def async_apply_bindings(
        self,
        bindings: dict[str, Any],
    ) -> None:
        """
        Apply entity bindings to device components.
        
        Args:
            bindings: Binding configuration dictionary
        """
        # Bind output channels
        if output_bindings := bindings.get("output_channels"):
            await self._bind_output_channels(output_bindings)
        
        # Bind sensors
        if sensor_bindings := bindings.get("sensors"):
            await self._bind_sensors(sensor_bindings)
        
        # Bind binary inputs
        if binary_bindings := bindings.get("binary_inputs"):
            await self._bind_binary_inputs(binary_bindings)
        
        # Bind button inputs
        if button_bindings := bindings.get("button_inputs"):
            await self._bind_button_inputs(button_bindings)

    async def _bind_output_channels(
        self,
        bindings: list[dict[str, Any]],
    ) -> None:
        """Bind output channels to HA entities."""
        if not self.device.output:
            _LOGGER.warning("Device %s has no output", self.device.name)
            return
        
        for binding in bindings:
            channel_index = binding["channel_index"]
            entity_id = binding["entity_id"]
            attribute = binding["attribute"]
            converter_name = binding.get("converter", "passthrough")
            
            if channel_index >= len(self.device.output.channels):
                _LOGGER.error("Invalid channel index: %s", channel_index)
                continue
            
            channel = self.device.output.channels[channel_index]
            converter = self._converters.get_converter(converter_name)
            
            # Set up state listener
            @callback
            def state_changed(event: Event) -> None:
                """Handle entity state change."""
                new_state = event.data.get("new_state")
                if new_state is None:
                    return
                
                # Get attribute value
                if attribute == "state":
                    value = new_state.state
                else:
                    value = new_state.attributes.get(attribute)
                
                if value is None:
                    return
                
                # Convert and apply to channel
                try:
                    converted = converter(value)
                    channel.set_value(converted)
                    _LOGGER.debug(
                        "Channel %s updated: %s -> %s",
                        channel_index,
                        value,
                        converted,
                    )
                except Exception as err:
                    _LOGGER.error("Conversion error: %s", err)
            
            # Track state changes
            listener = async_track_state_change_event(
                self.hass,
                entity_id,
                state_changed,
            )
            self._listeners.append(listener)
            
            _LOGGER.info(
                "Bound channel %s to %s.%s",
                channel_index,
                entity_id,
                attribute,
            )

    async def _bind_sensors(
        self,
        bindings: list[dict[str, Any]],
    ) -> None:
        """Bind sensors to HA entities."""
        for binding in bindings:
            sensor_index = binding["sensor_index"]
            entity_id = binding["entity_id"]
            attribute = binding["attribute"]
            converter_name = binding.get("converter", "float")
            
            if sensor_index >= len(self.device.sensors):
                _LOGGER.error("Invalid sensor index: %s", sensor_index)
                continue
            
            sensor = self.device.sensors[sensor_index]
            converter = self._converters.get_converter(converter_name)
            
            @callback
            def state_changed(event: Event) -> None:
                """Handle entity state change."""
                new_state = event.data.get("new_state")
                if new_state is None:
                    return
                
                if attribute == "state":
                    value = new_state.state
                else:
                    value = new_state.attributes.get(attribute)
                
                if value is None or value == "unavailable":
                    return
                
                try:
                    converted = converter(value)
                    sensor.update_value(converted)
                    _LOGGER.debug(
                        "Sensor %s updated: %s",
                        sensor_index,
                        converted,
                    )
                except Exception as err:
                    _LOGGER.error("Sensor conversion error: %s", err)
            
            listener = async_track_state_change_event(
                self.hass,
                entity_id,
                state_changed,
            )
            self._listeners.append(listener)
            
            _LOGGER.info(
                "Bound sensor %s to %s.%s",
                sensor_index,
                entity_id,
                attribute,
            )

    async def _bind_binary_inputs(
        self,
        bindings: list[dict[str, Any]],
    ) -> None:
        """Bind binary inputs to HA entities."""
        for binding in bindings:
            input_index = binding["input_index"]
            entity_id = binding["entity_id"]
            attribute = binding.get("attribute", "state")
            converter_name = binding.get("converter", "on_off_to_bool")
            
            if input_index >= len(self.device.binary_inputs):
                _LOGGER.error("Invalid binary input index: %s", input_index)
                continue
            
            binary_input = self.device.binary_inputs[input_index]
            converter = self._converters.get_converter(converter_name)
            
            @callback
            def state_changed(event: Event) -> None:
                """Handle entity state change."""
                new_state = event.data.get("new_state")
                if new_state is None:
                    return
                
                if attribute == "state":
                    value = new_state.state
                else:
                    value = new_state.attributes.get(attribute)
                
                if value is None:
                    return
                
                try:
                    converted = converter(value)
                    binary_input.set_state(converted)
                    _LOGGER.debug(
                        "Binary input %s updated: %s",
                        input_index,
                        converted,
                    )
                except Exception as err:
                    _LOGGER.error("Binary input conversion error: %s", err)
            
            listener = async_track_state_change_event(
                self.hass,
                entity_id,
                state_changed,
            )
            self._listeners.append(listener)
            
            _LOGGER.info(
                "Bound binary input %s to %s.%s",
                input_index,
                entity_id,
                attribute,
            )

    async def _bind_button_inputs(
        self,
        bindings: list[dict[str, Any]],
    ) -> None:
        """Bind button inputs to HA events."""
        for binding in bindings:
            button_index = binding["button_index"]
            event_type = binding["event_type"]
            event_filter = binding.get("event_filter", {})
            button_action_name = binding.get("button_action", "SINGLE_CLICK")
            
            if button_index >= len(self.device.button_inputs):
                _LOGGER.error("Invalid button index: %s", button_index)
                continue
            
            button = self.device.button_inputs[button_index]
            button_action = DSButtonAction[button_action_name]
            
            @callback
            def event_handler(event: Event) -> None:
                """Handle HA event."""
                # Check event filter
                for key, value in event_filter.items():
                    if event.data.get(key) != value:
                        return
                
                # Trigger button action
                button.trigger_action(button_action)
                _LOGGER.debug(
                    "Button %s triggered: %s",
                    button_index,
                    button_action_name,
                )
            
            # Listen for events
            self.hass.bus.async_listen(event_type, event_handler)
            
            _LOGGER.info(
                "Bound button %s to event %s",
                button_index,
                event_type,
            )

    def remove_bindings(self) -> None:
        """Remove all entity bindings."""
        for listener in self._listeners:
            listener()
        self._listeners.clear()
        _LOGGER.info("Removed all bindings for device %s", self.device.name)


class ValueConverters:
    """Value conversion utilities."""

    @staticmethod
    def passthrough(value: Any) -> Any:
        """Pass value through unchanged."""
        return value

    @staticmethod
    def float(value: Any) -> float:
        """Convert to float."""
        return float(value)

    @staticmethod
    def brightness_255_to_percent(value: int) -> float:
        """
        Convert HA brightness (0-255) to vDC percentage (0-100).
        
        Args:
            value: HA brightness value (0-255)
            
        Returns:
            Percentage value (0-100)
        """
        return (int(value) / 255.0) * 100.0

    @staticmethod
    def brightness_percent_to_255(value: float) -> int:
        """
        Convert vDC percentage (0-100) to HA brightness (0-255).
        
        Args:
            value: Percentage value (0-100)
            
        Returns:
            HA brightness value (0-255)
        """
        return int((float(value) / 100.0) * 255)

    @staticmethod
    def on_off_to_bool(value: str) -> bool:
        """Convert on/off string to boolean."""
        return value.lower() == "on"

    @staticmethod
    def bool_to_on_off(value: bool) -> str:
        """Convert boolean to on/off string."""
        return "on" if value else "off"

    @staticmethod
    def kelvin_to_celsius(value: float) -> float:
        """Convert temperature from Kelvin to Celsius."""
        return float(value) - 273.15

    @staticmethod
    def celsius_to_kelvin(value: float) -> float:
        """Convert temperature from Celsius to Kelvin."""
        return float(value) + 273.15

    @staticmethod
    def hs_to_rgb(value: tuple[float, float]) -> tuple[int, int, int]:
        """
        Convert HS color to RGB.
        
        Args:
            value: Tuple of (hue, saturation) where hue is 0-360 and saturation is 0-100
            
        Returns:
            Tuple of (red, green, blue) where each is 0-255
        """
        import colorsys
        
        h, s = value
        h = h / 360.0  # Convert to 0-1
        s = s / 100.0  # Convert to 0-1
        
        r, g, b = colorsys.hsv_to_rgb(h, s, 1.0)
        
        return (
            int(r * 255),
            int(g * 255),
            int(b * 255),
        )

    def get_converter(self, name: str) -> Callable:
        """Get converter function by name."""
        converter = getattr(self, name, None)
        if converter is None:
            raise ValueError(f"Unknown converter: {name}")
        return converter
```

### Reverse Bindings (vDC → HA)

For controlling HA entities from vDC commands:

```python
"""Reverse binding from vDC to HA entities."""

class ReverseEntityBinding:
    """Handle vDC commands and update HA entities."""

    def __init__(self, hass: HomeAssistant, device: Any) -> None:
        """Initialize reverse binding."""
        self.hass = hass
        self.device = device
        self._entity_mappings: dict[str, str] = {}

    async def async_setup_reverse_bindings(
        self,
        bindings: dict[str, str],
    ) -> None:
        """
        Set up reverse bindings (vDC → HA).
        
        Args:
            bindings: Map of component IDs to entity IDs
                Example: {"output_channel_0": "light.kitchen"}
        """
        self._entity_mappings = bindings
        
        # Register callbacks on vDC components
        if self.device.output:
            for idx, channel in enumerate(self.device.output.channels):
                component_id = f"output_channel_{idx}"
                if entity_id := self._entity_mappings.get(component_id):
                    channel.on_value_changed = self._create_channel_callback(
                        entity_id, idx
                    )

    def _create_channel_callback(
        self,
        entity_id: str,
        channel_index: int,
    ) -> Callable:
        """Create callback for channel value changes."""
        
        async def on_value_changed(new_value: float) -> None:
            """Handle channel value change."""
            # Determine entity domain
            domain = entity_id.split(".")[0]
            
            if domain == "light":
                # Convert value to HA brightness
                brightness = int((new_value / 100.0) * 255)
                
                # Call HA light service
                await self.hass.services.async_call(
                    "light",
                    "turn_on" if brightness > 0 else "turn_off",
                    {
                        "entity_id": entity_id,
                        "brightness": brightness,
                    },
                )
                
                _LOGGER.debug(
                    "Updated %s from vDC: brightness=%s",
                    entity_id,
                    brightness,
                )
        
        return on_value_changed
```

## Persistence

Store bindings for restoration after restart:

```python
"""Binding persistence."""
import json
from pathlib import Path

class BindingPersistence:
    """Persist entity bindings."""

    def __init__(self, storage_path: str) -> None:
        """Initialize persistence."""
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_bindings(
        self,
        device_dsuid: str,
        bindings: dict[str, Any],
    ) -> None:
        """Save bindings for a device."""
        file_path = self.storage_path / f"{device_dsuid}_bindings.json"
        
        with open(file_path, "w") as f:
            json.dump(bindings, f, indent=2)

    def load_bindings(self, device_dsuid: str) -> dict[str, Any] | None:
        """Load bindings for a device."""
        file_path = self.storage_path / f"{device_dsuid}_bindings.json"
        
        if not file_path.exists():
            return None
        
        with open(file_path, "r") as f:
            return json.load(f)

    def delete_bindings(self, device_dsuid: str) -> None:
        """Delete bindings for a device."""
        file_path = self.storage_path / f"{device_dsuid}_bindings.json"
        
        if file_path.exists():
            file_path.unlink()
```

## Usage Example

```python
"""Example usage of entity binding."""

# During device creation
device = vdc.create_vdsd_from_template(
    template_name="dimmable_light",
    template_type=TemplateType.DEVICE_TYPE,
    instance_name="Living Room Light",
    enumeration=1,
)

# Create binding manager
binding_manager = EntityBindingManager(hass, device)

# Define bindings
bindings = {
    "output_channels": [
        {
            "channel_index": 0,
            "entity_id": "light.living_room",
            "attribute": "brightness",
            "converter": "brightness_255_to_percent",
        }
    ],
    "sensors": [
        {
            "sensor_index": 0,
            "entity_id": "sensor.living_room_temperature",
            "attribute": "state",
            "converter": "float",
        }
    ],
}

# Apply bindings
await binding_manager.async_apply_bindings(bindings)

# Save for later restoration
persistence = BindingPersistence(hass.config.path("vdc_bindings"))
persistence.save_bindings(device.dsuid, bindings)

# Later, on restart
saved_bindings = persistence.load_bindings(device.dsuid)
if saved_bindings:
    await binding_manager.async_apply_bindings(saved_bindings)
```

## Testing Entity Bindings

```python
"""Test entity bindings."""
import pytest

@pytest.mark.asyncio
async def test_output_channel_binding(hass):
    """Test output channel binding updates channel value."""
    # Create test device
    device = create_test_device()
    
    # Create binding manager
    binding_manager = EntityBindingManager(hass, device)
    
    # Apply binding
    await binding_manager.async_apply_bindings({
        "output_channels": [{
            "channel_index": 0,
            "entity_id": "light.test",
            "attribute": "brightness",
            "converter": "brightness_255_to_percent",
        }]
    })
    
    # Update entity state
    hass.states.async_set("light.test", "on", {"brightness": 128})
    await hass.async_block_till_done()
    
    # Check channel value
    channel = device.output.channels[0]
    assert channel.value == pytest.approx(50.2, 0.1)  # 128/255 * 100
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Binding not updating** | Check entity exists, verify attribute name, check converter |
| **Conversion errors** | Validate converter function, check value types |
| **Performance issues** | Limit update frequency, use debouncing |
| **Memory leaks** | Call `remove_bindings()` when device removed |

## Next Steps

- **[COMPLETE_EXAMPLE.md](COMPLETE_EXAMPLE.md)** - Complete integration code

## Key Takeaways

✅ **Bidirectional sync**: HA entities ↔ vDC components
✅ **Value conversion**: Handle different units/scales
✅ **Event-driven**: Use HA state change events
✅ **Persistence**: Save bindings for restoration
✅ **Flexible mapping**: Support attributes, state, events
