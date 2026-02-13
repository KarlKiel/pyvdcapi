# Template-Based Device Creation UI

## Overview

This guide explains how to implement a user interface for creating vDC devices from templates, including template selection, parameter input, and entity binding.

## UI Flow

```
┌──────────────────────────────────────────────────────┐
│ Step 1: Choose Creation Method                      │
│  ○ Create from template                             │
│  ○ Create manually                                   │
└──────────────────────────────────────────────────────┘
                    ↓ (Template selected)
┌──────────────────────────────────────────────────────┐
│ Step 2: Select Template Type                        │
│  ○ Device Type (generic configurations)             │
│  ○ Vendor Type (brand-specific)                     │
└──────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│ Step 3: Browse Templates                            │
│  Folder: LIGHT /                                     │
│   □ simple_onoff_light                              │
│   □ dimmable_light                                   │
│   □ rgb_color_light                                  │
│  Folder: BLINDS /                                    │
│   □ motorized_blinds                                 │
└──────────────────────────────────────────────────────┘
                    ↓ (Template chosen)
┌──────────────────────────────────────────────────────┐
│ Step 4: Configure Instance Parameters               │
│  Device Name: [Living Room Light    ]               │
│  Enumeration: [Auto-generated: 001   ]               │
│                                                      │
│  Starting Values (optional):                         │
│  Initial Brightness: [0              ]  %            │
└──────────────────────────────────────────────────────┘
                    ↓
┌──────────────────────────────────────────────────────┐
│ Step 5: Bind Home Assistant Entities                │
│                                                      │
│  Output Channel (Brightness):                        │
│    Entity: [light.living_room ▼]                    │
│    Attribute: [brightness     ▼]                     │
│                                                      │
│  Button Input (Toggle):                              │
│    Event Source: [binary_sensor.wall_switch ▼]      │
│                                                      │
│  Temperature Sensor:                                 │
│    Entity: [sensor.temperature ▼]                    │
│    Attribute: [state          ▼]                     │
└──────────────────────────────────────────────────────┘
                    ↓
         [Create Device]
```

## Implementation

### Service Definition (services.yaml)

```yaml
create_device_from_template:
  name: Create Device from Template
  description: Create a virtual device from a template
  fields:
    template_name:
      name: Template Name
      description: Name of the template to use
      required: true
      selector:
        text:
    template_type:
      name: Template Type
      description: Type of template (deviceType or vendorType)
      required: true
      default: deviceType
      selector:
        select:
          options:
            - deviceType
            - vendorType
    device_name:
      name: Device Name
      description: Name for the new device instance
      required: true
      selector:
        text:
    enumeration:
      name: Enumeration
      description: Device enumeration number (auto if not specified)
      required: false
      selector:
        number:
          min: 1
          max: 9999
          mode: box
    entity_bindings:
      name: Entity Bindings
      description: JSON object mapping component types to HA entities
      required: false
      example: '{"output_channels": [{"entity_id": "light.living_room", "attribute": "brightness"}]}'
      selector:
        object:
```

### Device Creation Service Handler

Create `device_services.py`:

```python
"""Device creation services for vDC integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, entity_registry as er

from .const import DOMAIN, DATA_VDC_MANAGER
from .entity_binding import EntityBindingManager

# pyvdcapi imports
from pyvdcapi.templates import TemplateManager, TemplateType
from pyvdcapi.core.constants import DSChannelType

_LOGGER = logging.getLogger(__name__)

# Service schemas
SERVICE_CREATE_FROM_TEMPLATE_SCHEMA = vol.Schema(
    {
        vol.Required("template_name"): cv.string,
        vol.Required("template_type"): vol.In(["deviceType", "vendorType"]),
        vol.Required("device_name"): cv.string,
        vol.Optional("enumeration"): cv.positive_int,
        vol.Optional("entity_bindings"): dict,
    }
)


async def async_register_services(hass: HomeAssistant) -> None:
    """Register services for device creation."""
    
    async def handle_create_from_template(call: ServiceCall) -> None:
        """Handle create_device_from_template service call."""
        await _async_create_from_template(hass, call.data)
    
    hass.services.async_register(
        DOMAIN,
        "create_device_from_template",
        handle_create_from_template,
        schema=SERVICE_CREATE_FROM_TEMPLATE_SCHEMA,
    )
    
    _LOGGER.info("Device creation services registered")


async def _async_create_from_template(
    hass: HomeAssistant,
    call_data: dict[str, Any],
) -> None:
    """
    Create a device from template.
    
    Args:
        hass: Home Assistant instance
        call_data: Service call data with template info and bindings
    """
    # Get VDC manager
    entry_id = list(hass.data[DOMAIN].keys())[0]  # Get first (should be only one)
    vdc_manager = hass.data[DOMAIN][entry_id][DATA_VDC_MANAGER]
    
    template_name = call_data["template_name"]
    template_type_str = call_data["template_type"]
    device_name = call_data["device_name"]
    enumeration = call_data.get("enumeration")
    entity_bindings = call_data.get("entity_bindings", {})
    
    _LOGGER.info(
        "Creating device from template: %s (type=%s, name=%s)",
        template_name,
        template_type_str,
        device_name,
    )
    
    try:
        # Convert template type string to enum
        template_type = (
            TemplateType.DEVICE_TYPE
            if template_type_str == "deviceType"
            else TemplateType.VENDOR_TYPE
        )
        
        # Auto-generate enumeration if not provided
        if enumeration is None:
            enumeration = len(vdc_manager._devices) + 1
        
        # Create device from template
        device = vdc_manager.vdc.create_vdsd_from_template(
            template_name=template_name,
            template_type=template_type,
            instance_name=device_name,
            enumeration=enumeration,
        )
        
        # Register device
        vdc_manager.add_device(device)
        
        # Bind entities if provided
        if entity_bindings:
            binding_manager = EntityBindingManager(hass, device)
            await binding_manager.async_apply_bindings(entity_bindings)
        
        _LOGGER.info("Device created successfully: %s (%s)", device.name, device.dsuid)
        
    except Exception as err:
        _LOGGER.error("Failed to create device from template: %s", err)
        raise
```

### Template Browser Helper

Create `template_browser.py`:

```python
"""Template browsing utilities."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pyvdcapi.templates import TemplateManager, TemplateType

_LOGGER = logging.getLogger(__name__)


class TemplateBrowser:
    """Browse and search templates by group."""

    def __init__(self, templates_path: str | None = None) -> None:
        """Initialize template browser."""
        self.manager = TemplateManager(templates_path)

    def list_templates_by_group(
        self,
        template_type: TemplateType,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        List templates organized by group folder.
        
        Returns:
            Dictionary mapping group name to list of template info dicts
            
        Example:
            {
                "LIGHT": [
                    {
                        "name": "simple_onoff_light",
                        "description": "Simple on/off light...",
                        "path": "deviceType/LIGHT/simple_onoff_light.yaml"
                    }
                ],
                "BLINDS": [...]
            }
        """
        result = {}
        
        # Get template type directory
        type_path = self.manager.templates_path / template_type.value
        
        if not type_path.exists():
            return result
        
        # Iterate through group folders
        for group_dir in type_path.iterdir():
            if not group_dir.is_dir():
                continue
            
            group_name = group_dir.name
            templates = []
            
            # List templates in group
            for template_file in group_dir.glob("*.yaml"):
                try:
                    # Load template to get metadata
                    template_data = self.manager.load_template_file(template_file)
                    metadata = template_data.get("template_metadata", {})
                    
                    templates.append({
                        "name": template_file.stem,
                        "description": metadata.get("description", "No description"),
                        "vendor": metadata.get("vendor"),
                        "vendor_model_id": metadata.get("vendor_model_id"),
                        "path": str(template_file.relative_to(self.manager.templates_path)),
                    })
                except Exception as err:
                    _LOGGER.warning("Failed to load template %s: %s", template_file, err)
            
            if templates:
                result[group_name] = templates
        
        return result

    def search_templates(
        self,
        query: str,
        template_type: TemplateType | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search templates by name or description.
        
        Args:
            query: Search string
            template_type: Optionally filter by template type
            
        Returns:
            List of matching template info dicts
        """
        results = []
        query_lower = query.lower()
        
        # Determine which template types to search
        types_to_search = (
            [template_type] if template_type
            else [TemplateType.DEVICE_TYPE, TemplateType.VENDOR_TYPE]
        )
        
        for ttype in types_to_search:
            grouped = self.list_templates_by_group(ttype)
            
            for group_name, templates in grouped.items():
                for template_info in templates:
                    # Search in name and description
                    if (
                        query_lower in template_info["name"].lower()
                        or query_lower in template_info["description"].lower()
                    ):
                        template_info["group"] = group_name
                        template_info["type"] = ttype.value
                        results.append(template_info)
        
        return results

    def get_template_details(
        self,
        template_name: str,
        template_type: TemplateType,
    ) -> dict[str, Any]:
        """
        Get detailed information about a template.
        
        Returns:
            Dictionary with template metadata and configuration details
        """
        template_data = self.manager.load_template(template_name, template_type)
        
        metadata = template_data.get("template_metadata", {})
        device_config = template_data.get("device_config", {})
        
        # Extract component information
        components = {
            "outputs": bool(device_config.get("output")),
            "button_inputs": len(device_config.get("button_inputs", [])),
            "binary_inputs": len(device_config.get("binary_inputs", [])),
            "sensors": len(device_config.get("sensors", [])),
        }
        
        return {
            "metadata": metadata,
            "components": components,
            "instance_parameters": device_config.get("instance_parameters", {}),
        }
```

### UI Flow Implementation

Create `config_flow.py` additions for device creation:

```python
"""Config flow additions for device creation."""
from typing import Any
import voluptuous as vol

from homeassistant.helpers import selector

from .template_browser import TemplateBrowser
from pyvdcapi.templates import TemplateType


class DeviceCreationFlow(config_entries.FlowHandler):
    """Handle device creation flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize device creation flow."""
        self._browser = TemplateBrowser()
        self._selected_template: str | None = None
        self._selected_type: TemplateType | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Choose creation method."""
        if user_input is not None:
            if user_input["creation_method"] == "template":
                return await self.async_step_template_type()
            else:
                return await self.async_step_manual_create()
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("creation_method"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {"label": "Create from template", "value": "template"},
                            {"label": "Create manually", "value": "manual"},
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }),
        )

    async def async_step_template_type(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select template type."""
        if user_input is not None:
            self._selected_type = (
                TemplateType.DEVICE_TYPE
                if user_input["template_type"] == "deviceType"
                else TemplateType.VENDOR_TYPE
            )
            return await self.async_step_browse_templates()
        
        return self.async_show_form(
            step_id="template_type",
            data_schema=vol.Schema({
                vol.Required("template_type"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            {
                                "label": "Device Type (Generic configurations)",
                                "value": "deviceType",
                            },
                            {
                                "label": "Vendor Type (Brand-specific)",
                                "value": "vendorType",
                            },
                        ],
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }),
        )

    async def async_step_browse_templates(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Browse and select template."""
        if user_input is not None:
            self._selected_template = user_input["template"]
            return await self.async_step_configure_instance()
        
        # Get templates organized by group
        templates_by_group = self._browser.list_templates_by_group(self._selected_type)
        
        # Build options list with group headers
        options = []
        for group_name, templates in sorted(templates_by_group.items()):
            # Add group header (disabled option)
            options.append({
                "label": f"─── {group_name} ───",
                "value": f"__header_{group_name}",
            })
            
            # Add templates in group
            for template in templates:
                options.append({
                    "label": f"  {template['name']}",
                    "value": template["name"],
                })
        
        return self.async_show_form(
            step_id="browse_templates",
            data_schema=vol.Schema({
                vol.Required("template"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            description_placeholders={
                "template_info": "Select a template from the list below",
            },
        )

    async def async_step_configure_instance(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure instance parameters."""
        if user_input is not None:
            # Store instance config, proceed to entity binding
            self._instance_config = user_input
            return await self.async_step_bind_entities()
        
        # Get template details
        details = self._browser.get_template_details(
            self._selected_template,
            self._selected_type,
        )
        
        # Build schema from template requirements
        schema_dict = {
            vol.Required("device_name"): selector.TextSelector(),
        }
        
        # Add configurable parameters from template
        # (e.g., initial brightness for lights)
        if details["components"]["outputs"]:
            schema_dict[vol.Optional("initial_brightness", default=0)] = (
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=100,
                        step=1,
                        unit_of_measurement="%",
                        mode=selector.NumberSelectorMode.SLIDER,
                    )
                )
            )
        
        return self.async_show_form(
            step_id="configure_instance",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "template_name": self._selected_template,
                "description": details["metadata"].get("description", ""),
            },
        )

    async def async_step_bind_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Bind Home Assistant entities to device components."""
        if user_input is not None:
            # Create the device with bindings
            await self._create_device_with_bindings(user_input)
            return self.async_create_entry(
                title=self._instance_config["device_name"],
                data={},
            )
        
        # Get template details to know what to bind
        details = self._browser.get_template_details(
            self._selected_template,
            self._selected_type,
        )
        
        # Build entity binding schema
        schema_dict = {}
        
        # Output channel binding
        if details["components"]["outputs"]:
            schema_dict[vol.Required("output_entity")] = (
                selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="light"),
                )
            )
        
        # Sensor bindings
        for i in range(details["components"]["sensors"]):
            schema_dict[vol.Optional(f"sensor_{i}_entity")] = (
                selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor"),
                )
            )
        
        # Binary input bindings
        for i in range(details["components"]["binary_inputs"]):
            schema_dict[vol.Optional(f"binary_input_{i}_entity")] = (
                selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="binary_sensor"),
                )
            )
        
        return self.async_show_form(
            step_id="bind_entities",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "info": "Select Home Assistant entities to bind to the device components",
            },
        )

    async def _create_device_with_bindings(
        self, bindings: dict[str, Any]
    ) -> None:
        """Create device and apply entity bindings."""
        # This would call the service to create device
        # See device_services.py implementation
        pass
```

## Next Steps

- **[05_MANUAL_DEVICE_CREATION.md](05_MANUAL_DEVICE_CREATION.md)** - Manual device creation flow
- **[06_ENTITY_BINDING.md](06_ENTITY_BINDING.md)** - Entity binding implementation details

## Key Takeaways

✅ **Service-based creation**: Use HA services for device creation
✅ **Template browser**: Organize by groups for easy discovery
✅ **Multi-step flow**: Template type → Browse → Configure → Bind
✅ **Auto-enumeration**: Generate device IDs automatically
✅ **Entity binding**: Map HA entities to vDC components during creation
