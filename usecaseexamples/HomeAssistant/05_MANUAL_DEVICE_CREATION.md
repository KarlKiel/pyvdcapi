# Manual Device Creation UI

## Overview

This guide covers creating vDC devices manually without templates, giving users full control over primary groups, properties, inputs, outputs, and sensors.

## UI Flow

```
┌──────────────────────────────────────────────────────┐
│ Step 1: Device Basic Information                    │
│  Device Name:    [Kitchen Sensor        ]           │
│  Device Type:    [Custom Device         ]           │
│  Model ID:       [CUSTOM-001            ]           │
│  Vendor Name:    [Home Assistant        ]           │
│  Enumeration:    [Auto: 005             ]           │
└──────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│ Step 2: Choose Primary Group                        │
│  Select the main device category:                   │
│   ○ LIGHT (48) - Lighting devices                   │
│   ○ CLIMATE (1) - HVAC controls                     │
│   ○ SECURITY (3) - Security & surveillance          │
│   ○ ACCESS (6) - Access control                     │
│   ○ BLINDS (7) - Blinds and shades                  │
│   ● AUDIO (8) - Audio devices                       │
└──────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│ Step 3: Configure Properties                        │
│  Device Properties:                                  │
│   □ Has Output (supports actuation)                 │
│   ☑ Has Temperature Sensor                          │
│   ☑ Has Humidity Sensor                             │
│   □ Has Motion Detector                             │
│                                                      │
│  Common Properties:                                  │
│   DIP Switches: [0               ]                   │
│   Hardware Info: [ESP32-S3       ]                   │
│   Hardware GUID: [Auto-generate  ▼]                 │
└──────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│ Step 4: Add Components                              │
│  ┌────────────────────────────────────────────────┐ │
│  │ Output Channels                         [+ Add]│ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │ Sensors                                 [+ Add]│ │
│  │  • Temperature (°C)              [Configure]  │ │
│  │  • Humidity (%)                  [Configure]  │ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │ Button Inputs                           [+ Add]│ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │ Binary Inputs                           [+ Add]│ │
│  └────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│ Step 5: Configure Sensor Details                    │
│  Sensor 1: Temperature                               │
│   Sensor Type:    [Temperature      ▼]              │
│   Sensor Usage:   [Room             ▼]              │
│   Unit:           [°C (Celsius)     ▼]              │
│   Resolution:     [0.1              ]               │
│   Min Value:      [-40              ]               │
│   Max Value:      [125              ]               │
│   Update Rate:    [30               ] seconds        │
│                                                      │
│  Bind to HA Entity:                                  │
│   Entity:         [sensor.kitchen_temp ▼]           │
│   Attribute:      [state            ▼]              │
└──────────────────────────────────────────────────────┘
                    ↓
         [Create Device]
```

## Implementation

### Service Definition (services.yaml)

```yaml
create_device_manual:
  name: Create Device Manually
  description: Create a virtual device with manual configuration
  fields:
    device_name:
      name: Device Name
      description: Name for the device
      required: true
      selector:
        text:
    model_id:
      name: Model ID
      description: Device model identifier
      required: true
      selector:
        text:
    vendor_name:
      name: Vendor Name
      description: Device vendor/manufacturer name
      required: true
      default: "Home Assistant"
      selector:
        text:
    primary_group:
      name: Primary Group
      description: Primary functional group (0-254)
      required: true
      selector:
        number:
          min: 0
          max: 254
          mode: box
    enumeration:
      name: Enumeration
      description: Device enumeration number (auto if not specified)
      required: false
      selector:
        number:
          min: 1
          max: 9999
          mode: box
    output_config:
      name: Output Configuration
      description: Output configuration (if device has output)
      required: false
      selector:
        object:
    sensors:
      name: Sensors
      description: List of sensor configurations
      required: false
      selector:
        object:
    button_inputs:
      name: Button Inputs
      description: List of button input configurations
      required: false
      selector:
        object:
    binary_inputs:
      name: Binary Inputs
      description: List of binary input configurations
      required: false
      selector:
        object:
    entity_bindings:
      name: Entity Bindings
      description: Entity bindings for components
      required: false
      selector:
        object:

add_sensor_to_device:
  name: Add Sensor to Device
  description: Add a sensor component to an existing device
  fields:
    device_dsuid:
      name: Device DSUID
      description: DSUID of the target device
      required: true
      selector:
        text:
    sensor_type:
      name: Sensor Type
      description: Type of sensor (TEMPERATURE, HUMIDITY, etc.)
      required: true
      selector:
        select:
          options:
            - TEMPERATURE
            - HUMIDITY
            - BRIGHTNESS
            - POWER
            - AIR_PRESSURE
            - WIND_SPEED
            - SOUND_PRESSURE_LEVEL
            - ROOM_TEMPERATURE_CONTROL_VARIABLE
    sensor_usage:
      name: Sensor Usage
      description: Usage context for the sensor
      required: true
      selector:
        select:
          options:
            - UNDEFINED
            - ROOM
            - OUTDOOR
    unit:
      name: Unit
      description: Measurement unit
      required: true
      selector:
        text:
    resolution:
      name: Resolution
      description: Sensor resolution/precision
      required: false
      default: 0.1
      selector:
        number:
          min: 0.001
          max: 100
          step: 0.001
          mode: box
    min_value:
      name: Minimum Value
      description: Minimum sensor reading
      required: false
      selector:
        number:
          mode: box
    max_value:
      name: Maximum Value
      description: Maximum sensor reading
      required: false
      selector:
        number:
          mode: box
    entity_id:
      name: Home Assistant Entity
      description: HA entity to bind to this sensor
      required: false
      selector:
        entity:
```

### Manual Creation Service Handler

Add to `device_services.py`:

```python
"""Manual device creation services."""
from pyvdcapi.components.sensor import Sensor
from pyvdcapi.components.binary_input import BinaryInput
from pyvdcapi.components.button import Button
from pyvdcapi.components.output import Output
from pyvdcapi.components.output_channel import OutputChannel
from pyvdcapi.core.constants import (
    DSSensorType,
    DSSensorUsage,
    DSChannelType,
    DSInputType,
)

# Service schemas
SERVICE_CREATE_MANUAL_SCHEMA = vol.Schema(
    {
        vol.Required("device_name"): cv.string,
        vol.Required("model_id"): cv.string,
        vol.Required("vendor_name"): cv.string,
        vol.Required("primary_group"): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=254)
        ),
        vol.Optional("enumeration"): cv.positive_int,
        vol.Optional("output_config"): dict,
        vol.Optional("sensors"): list,
        vol.Optional("button_inputs"): list,
        vol.Optional("binary_inputs"): list,
        vol.Optional("entity_bindings"): dict,
    }
)

SERVICE_ADD_SENSOR_SCHEMA = vol.Schema(
    {
        vol.Required("device_dsuid"): cv.string,
        vol.Required("sensor_type"): cv.string,
        vol.Required("sensor_usage"): cv.string,
        vol.Required("unit"): cv.string,
        vol.Optional("resolution", default=0.1): vol.Coerce(float),
        vol.Optional("min_value"): vol.Coerce(float),
        vol.Optional("max_value"): vol.Coerce(float),
        vol.Optional("entity_id"): cv.entity_id,
    }
)


async def async_register_services(hass: HomeAssistant) -> None:
    """Register services for manual device creation."""
    
    # ... (previous template service registration) ...
    
    async def handle_create_manual(call: ServiceCall) -> None:
        """Handle create_device_manual service call."""
        await _async_create_manual(hass, call.data)
    
    async def handle_add_sensor(call: ServiceCall) -> None:
        """Handle add_sensor_to_device service call."""
        await _async_add_sensor(hass, call.data)
    
    hass.services.async_register(
        DOMAIN,
        "create_device_manual",
        handle_create_manual,
        schema=SERVICE_CREATE_MANUAL_SCHEMA,
    )
    
    hass.services.async_register(
        DOMAIN,
        "add_sensor_to_device",
        handle_add_sensor,
        schema=SERVICE_ADD_SENSOR_SCHEMA,
    )


async def _async_create_manual(
    hass: HomeAssistant,
    call_data: dict[str, Any],
) -> None:
    """
    Create a device manually with full configuration.
    
    Args:
        hass: Home Assistant instance
        call_data: Service call data with device configuration
    """
    # Get VDC manager
    entry_id = list(hass.data[DOMAIN].keys())[0]
    vdc_manager = hass.data[DOMAIN][entry_id][DATA_VDC_MANAGER]
    
    device_name = call_data["device_name"]
    model_id = call_data["model_id"]
    vendor_name = call_data["vendor_name"]
    primary_group = call_data["primary_group"]
    enumeration = call_data.get("enumeration")
    
    _LOGGER.info("Creating manual device: %s (group=%s)", device_name, primary_group)
    
    try:
        # Auto-generate enumeration if not provided
        if enumeration is None:
            enumeration = len(vdc_manager._devices) + 1
        
        # Create base device
        device = vdc_manager.vdc.create_vdsd(
            name=device_name,
            model=model_id,
            vendor_name=vendor_name,
            primary_group=primary_group,
            enumeration=enumeration,
        )
        
        # Add output if configured
        if output_config := call_data.get("output_config"):
            await _add_output_to_device(device, output_config)
        
        # Add sensors if configured
        if sensors := call_data.get("sensors"):
            for sensor_config in sensors:
                await _add_sensor_to_device(device, sensor_config)
        
        # Add button inputs if configured
        if button_inputs := call_data.get("button_inputs"):
            for button_config in button_inputs:
                await _add_button_to_device(device, button_config)
        
        # Add binary inputs if configured
        if binary_inputs := call_data.get("binary_inputs"):
            for binary_config in binary_inputs:
                await _add_binary_input_to_device(device, binary_config)
        
        # Register device
        vdc_manager.add_device(device)
        
        # Bind entities if provided
        if entity_bindings := call_data.get("entity_bindings"):
            binding_manager = EntityBindingManager(hass, device)
            await binding_manager.async_apply_bindings(entity_bindings)
        
        _LOGGER.info("Manual device created successfully: %s (%s)", device.name, device.dsuid)
        
    except Exception as err:
        _LOGGER.error("Failed to create manual device: %s", err)
        raise


async def _add_output_to_device(
    device: Any,
    output_config: dict[str, Any],
) -> None:
    """Add output to device."""
    output = Output(device=device)
    
    # Add channels based on configuration
    for channel_config in output_config.get("channels", []):
        channel_type = DSChannelType[channel_config["type"]]
        
        channel = OutputChannel(
            output=output,
            channel_type=channel_type,
            resolution=channel_config.get("resolution", 1.0),
        )
        
        output.add_channel(channel)
    
    device.output = output


async def _add_sensor_to_device(
    device: Any,
    sensor_config: dict[str, Any],
) -> None:
    """Add sensor to device."""
    sensor_type = DSSensorType[sensor_config["type"]]
    sensor_usage = DSSensorUsage[sensor_config["usage"]]
    
    sensor = Sensor(
        device=device,
        sensor_type=sensor_type,
        sensor_usage=sensor_usage,
        unit=sensor_config["unit"],
        resolution=sensor_config.get("resolution", 0.1),
        min_value=sensor_config.get("min_value"),
        max_value=sensor_config.get("max_value"),
    )
    
    device.add_sensor(sensor)


async def _add_button_to_device(
    device: Any,
    button_config: dict[str, Any],
) -> None:
    """Add button input to device."""
    button = Button(
        device=device,
        button_id=button_config.get("button_id", 0),
        button_type=button_config.get("button_type", DSInputType.SINGLE_BUTTON),
    )
    
    device.add_button(button)


async def _add_binary_input_to_device(
    device: Any,
    binary_config: dict[str, Any],
) -> None:
    """Add binary input to device."""
    binary_input = BinaryInput(
        device=device,
        input_type=DSInputType[binary_config["input_type"]],
        input_usage=binary_config.get("input_usage", 0),
    )
    
    device.add_binary_input(binary_input)


async def _async_add_sensor(
    hass: HomeAssistant,
    call_data: dict[str, Any],
) -> None:
    """
    Add a sensor to an existing device.
    
    Args:
        hass: Home Assistant instance
        call_data: Service call data with sensor configuration
    """
    entry_id = list(hass.data[DOMAIN].keys())[0]
    vdc_manager = hass.data[DOMAIN][entry_id][DATA_VDC_MANAGER]
    
    device_dsuid = call_data["device_dsuid"]
    
    # Find device
    device = vdc_manager.get_device_by_dsuid(device_dsuid)
    if device is None:
        _LOGGER.error("Device not found: %s", device_dsuid)
        return
    
    # Create sensor configuration
    sensor_config = {
        "type": call_data["sensor_type"],
        "usage": call_data["sensor_usage"],
        "unit": call_data["unit"],
        "resolution": call_data.get("resolution", 0.1),
        "min_value": call_data.get("min_value"),
        "max_value": call_data.get("max_value"),
    }
    
    # Add sensor
    await _add_sensor_to_device(device, sensor_config)
    
    # Bind to HA entity if provided
    if entity_id := call_data.get("entity_id"):
        binding_manager = EntityBindingManager(hass, device)
        bindings = {
            "sensors": [{
                "sensor_index": len(device.sensors) - 1,
                "entity_id": entity_id,
                "attribute": "state",
            }]
        }
        await binding_manager.async_apply_bindings(bindings)
    
    _LOGGER.info("Sensor added to device %s", device.name)
```

### Manual Creation Config Flow

Add to `config_flow.py`:

```python
"""Manual device creation flow."""

class ManualDeviceCreationFlow(config_entries.FlowHandler):
    """Handle manual device creation flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self._device_config: dict[str, Any] = {}
        self._components: dict[str, list] = {
            "sensors": [],
            "button_inputs": [],
            "binary_inputs": [],
        }

    async def async_step_basic_info(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure basic device information."""
        if user_input is not None:
            self._device_config.update(user_input)
            return await self.async_step_primary_group()
        
        return self.async_show_form(
            step_id="basic_info",
            data_schema=vol.Schema({
                vol.Required("device_name"): selector.TextSelector(),
                vol.Required("model_id"): selector.TextSelector(),
                vol.Required("vendor_name", default="Home Assistant"): (
                    selector.TextSelector()
                ),
            }),
        )

    async def async_step_primary_group(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose primary group."""
        if user_input is not None:
            self._device_config["primary_group"] = int(user_input["primary_group"])
            return await self.async_step_add_components()
        
        # Primary group options
        group_options = [
            {"label": "LIGHT (48) - Lighting devices", "value": "48"},
            {"label": "CLIMATE (1) - HVAC controls", "value": "1"},
            {"label": "SECURITY (3) - Security & surveillance", "value": "3"},
            {"label": "ACCESS (6) - Access control", "value": "6"},
            {"label": "BLINDS (7) - Blinds and shades", "value": "7"},
            {"label": "AUDIO (8) - Audio devices", "value": "8"},
            {"label": "VIDEO (9) - Video devices", "value": "9"},
            {"label": "JOKER (64) - Uncategorized", "value": "64"},
        ]
        
        return self.async_show_form(
            step_id="primary_group",
            data_schema=vol.Schema({
                vol.Required("primary_group"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=group_options,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }),
        )

    async def async_step_add_components(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add components to device."""
        if user_input is not None:
            action = user_input.get("action")
            
            if action == "add_sensor":
                return await self.async_step_configure_sensor()
            elif action == "add_output":
                return await self.async_step_configure_output()
            elif action == "done":
                return await self.async_step_finalize()
        
        # Show current components and actions
        components_summary = self._format_components_summary()
        
        actions = [
            {"label": "Add Sensor", "value": "add_sensor"},
            {"label": "Add Output", "value": "add_output"},
            {"label": "Add Button Input", "value": "add_button"},
            {"label": "Add Binary Input", "value": "add_binary"},
            {"label": "Done - Create Device", "value": "done"},
        ]
        
        return self.async_show_form(
            step_id="add_components",
            data_schema=vol.Schema({
                vol.Required("action"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=actions,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }),
            description_placeholders={
                "components": components_summary,
            },
        )

    async def async_step_configure_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure a sensor."""
        if user_input is not None:
            self._components["sensors"].append(user_input)
            return await self.async_step_add_components()
        
        sensor_types = [
            {"label": "Temperature", "value": "TEMPERATURE"},
            {"label": "Humidity", "value": "HUMIDITY"},
            {"label": "Brightness", "value": "BRIGHTNESS"},
            {"label": "Power", "value": "POWER"},
            {"label": "Air Pressure", "value": "AIR_PRESSURE"},
        ]
        
        sensor_usages = [
            {"label": "Room", "value": "ROOM"},
            {"label": "Outdoor", "value": "OUTDOOR"},
            {"label": "Undefined", "value": "UNDEFINED"},
        ]
        
        return self.async_show_form(
            step_id="configure_sensor",
            data_schema=vol.Schema({
                vol.Required("type"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=sensor_types,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required("usage"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=sensor_usages,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required("unit"): selector.TextSelector(),
                vol.Optional("resolution", default=0.1): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.001,
                        max=100,
                        step=0.001,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Optional("entity_id"): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            }),
        )

    def _format_components_summary(self) -> str:
        """Format components summary for display."""
        lines = ["Current components:"]
        lines.append(f"  Sensors: {len(self._components['sensors'])}")
        lines.append(f"  Button Inputs: {len(self._components['button_inputs'])}")
        lines.append(f"  Binary Inputs: {len(self._components['binary_inputs'])}")
        return "\n".join(lines)

    async def async_step_finalize(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Finalize and create device."""
        # Create device with all configured components
        device_data = {
            **self._device_config,
            **self._components,
        }
        
        # Call service to create device
        # (would integrate with device_services.py)
        
        return self.async_create_entry(
            title=self._device_config["device_name"],
            data=device_data,
        )
```

## Key Differences from Template Creation

| Aspect | Template Creation | Manual Creation |
|--------|------------------|-----------------|
| **Speed** | Fast (pre-configured) | Slower (configure everything) |
| **Flexibility** | Limited to template options | Full control |
| **Complexity** | Low | High |
| **Use Case** | Standard devices | Custom/unique devices |
| **Component Setup** | Automatic | Manual selection |
| **Validation** | Template ensures correctness | User responsible |

## Best Practices

✅ **Provide defaults**: Pre-fill common values (vendor name, resolutions)
✅ **Validate inputs**: Check value ranges before creating
✅ **Show summaries**: Display current configuration as user builds
✅ **Allow removal**: Let users remove added components before finalizing
✅ **Save presets**: Allow saving configurations as custom templates

## Next Steps

- **[06_ENTITY_BINDING.md](06_ENTITY_BINDING.md)** - Entity binding implementation
- **[COMPLETE_EXAMPLE.md](COMPLETE_EXAMPLE.md)** - Complete integration code

## Key Takeaways

✅ **Full control**: Manual creation for unique device configurations
✅ **Component-by-component**: Add sensors, inputs, outputs individually
✅ **Primary group first**: Determines device category and capabilities
✅ **Incremental services**: Support adding components to existing devices
✅ **Flexible binding**: Bind entities during or after creation
