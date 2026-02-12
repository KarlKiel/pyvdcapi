"""
Template management for vDC device configuration.

Provides functionality to:
- Save configured devices as reusable templates
- Create new devices from templates with minimal configuration
- Organize templates by type (deviceType/vendorType) and group

Template Types:
- deviceType: Standard hardware configurations (e.g., simple on/off light)
- vendorType: Vendor-specific hardware (e.g., "Philips HUE Lily Garden Spot")

Templates are stored as individual YAML files in:
  pyvdcapi/templates/{templateType}/{groupName}/{templateName}.yaml

This enables:
- Easy community sharing of device templates
- Version control of individual templates
- Clear organization by device type and functional group
"""

import yaml
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging
from enum import Enum

from pyvdcapi.core.constants import DSGroup

logger = logging.getLogger(__name__)


class TemplateType(Enum):
    """Template type classification."""
    DEVICE_TYPE = "deviceType"  # Standard hardware configuration
    VENDOR_TYPE = "vendorType"  # Vendor-specific hardware


class TemplateManager:
    """
    Manages device configuration templates.
    
    Templates allow saving a fully configured device as a reusable template
    and creating new device instances from templates with minimal information.
    """

    # Map DSGroup enum values to folder names
    GROUP_FOLDER_MAP = {
        DSGroup.YELLOW: "LIGHT",
        DSGroup.GREY: "BLINDS",
        DSGroup.BLUE: "HEATING",
        DSGroup.CYAN: "COOLING",
        DSGroup.MAGENTA: "VENTILATION",
        DSGroup.RED: "AUDIO",
        DSGroup.GREEN: "VIDEO",
        DSGroup.BLACK: "JOKER",
        DSGroup.WHITE: "WHITE",
        DSGroup.UNDEFINED: "UNDEFINED",
        1: "LIGHT",
        2: "BLINDS",
        3: "HEATING",
        4: "AUDIO",
        5: "VIDEO",
        8: "JOKER",
        9: "COOLING",
        10: "VENTILATION",
        11: "WINDOW",
        12: "RECIRCULATION",
        48: "TEMPERATURE_CONTROL",
        64: "APARTMENT_VENTILATION",
        66: "SECURITY",
        70: "ACCESS",
    }

    def __init__(self, templates_base_path: Optional[str] = None):
        """
        Initialize template manager.
        
        Args:
            templates_base_path: Base path for templates folder
                                (default: pyvdcapi/templates/)
        """
        if templates_base_path is None:
            # Default to package templates directory
            package_dir = Path(__file__).parent.parent
            self.templates_path = package_dir / "templates"
        else:
            self.templates_path = Path(templates_base_path)
        
        # Ensure base structure exists
        self._ensure_structure()
        
        logger.info(f"Template manager initialized with base path: {self.templates_path}")

    def _ensure_structure(self):
        """Ensure template directory structure exists."""
        for template_type in TemplateType:
            type_path = self.templates_path / template_type.value
            type_path.mkdir(parents=True, exist_ok=True)

    def _get_group_folder_name(self, primary_group: int) -> str:
        """
        Get folder name for a primary group.
        
        Args:
            primary_group: DSGroup enum value or integer
            
        Returns:
            Folder name (e.g., "LIGHT", "HEATING")
        """
        folder_name = self.GROUP_FOLDER_MAP.get(primary_group)
        if folder_name:
            return folder_name
        
        # Fallback: use group number if not in map
        logger.warning(f"Unknown primary group {primary_group}, using GROUP_{primary_group}")
        return f"GROUP_{primary_group}"

    def save_device_as_template(
        self,
        vdsd: "VdSD",
        template_name: str,
        template_type: TemplateType,
        description: Optional[str] = None,
        vendor: Optional[str] = None,
        vendor_model_id: Optional[str] = None,
    ) -> str:
        """
        Save a configured device as a reusable template.
        
        Args:
            vdsd: Fully configured VdSD instance
            template_name: Template name (will be sanitized for filename)
            template_type: TemplateType.DEVICE_TYPE or TemplateType.VENDOR_TYPE
            description: Optional human-readable description
            vendor: Optional vendor name (for vendorType templates)
            vendor_model_id: Optional vendor model identifier
            
        Returns:
            Path to created template file
            
        Raises:
            ValueError: If template_name contains invalid characters
            
        Example:
            # Save configured light as deviceType template
            template_path = template_mgr.save_device_as_template(
                vdsd=my_light,
                template_name="simple_onoff_light",
                template_type=TemplateType.DEVICE_TYPE,
                description="Simple on/off light with 50% threshold"
            )
            
            # Save vendor-specific device as vendorType template
            template_path = template_mgr.save_device_as_template(
                vdsd=hue_lily,
                template_name="philips_hue_lily_spot",
                template_type=TemplateType.VENDOR_TYPE,
                description="Philips HUE Lily Garden Spot",
                vendor="Philips",
                vendor_model_id="915005730801"
            )
        """
        # Sanitize template name for filesystem
        safe_name = self._sanitize_filename(template_name)
        
        # Determine group folder
        primary_group = vdsd._vdsd_props.get_property("primaryGroup")
        group_folder = self._get_group_folder_name(primary_group)
        
        # Build template path
        template_dir = self.templates_path / template_type.value / group_folder
        template_dir.mkdir(parents=True, exist_ok=True)
        template_file = template_dir / f"{safe_name}.yaml"
        
        # Extract device configuration
        template_data = self._extract_device_config(
            vdsd,
            template_name=template_name,
            description=description,
            vendor=vendor,
            vendor_model_id=vendor_model_id,
        )
        
        # Save template
        with open(template_file, 'w') as f:
            yaml.dump(template_data, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Template saved: {template_file}")
        return str(template_file)

    def _extract_device_config(
        self,
        vdsd: "VdSD",
        template_name: str,
        description: Optional[str] = None,
        vendor: Optional[str] = None,
        vendor_model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract device configuration suitable for template.
        
        Instance-specific values (dSUID, name) are marked as parameters
        that must be provided when creating from template.
        """
        config = {
            "template_metadata": {
                "template_name": template_name,
                "description": description or f"Template for {vdsd._common_props.get_property('model')}",
                "vendor": vendor,
                "vendor_model_id": vendor_model_id,
                "created_from_model": vdsd._common_props.get_property("model"),
            },
            "device_config": {
                # Common properties (instance-specific marked as PARAM_)
                "model": vdsd._common_props.get_property("model"),
                "model_uid": vdsd._common_props.get_property("modelUID"),
                "model_version": vdsd._common_props.get_property("modelVersion"),
                
                # vdSD properties
                "primary_group": vdsd._vdsd_props.get_property("primaryGroup"),
                
                # Mark instance parameters that need to be provided
                "instance_parameters": {
                    "name": "REQUIRED",  # Device instance name
                    "enumeration": "REQUIRED",  # Device enumeration number
                },
            },
        }
        
        # Add output configuration if present
        if vdsd._output:
            output_config = self._extract_output_config(vdsd._output)
            if output_config:
                config["device_config"]["output"] = output_config
        
        # Add button inputs if present
        if vdsd._button_inputs:
            button_configs = []
            for button in vdsd._button_inputs:
                button_configs.append(self._extract_button_config(button))
            config["device_config"]["button_inputs"] = button_configs
        
        # Add binary inputs if present
        if vdsd._binary_inputs:
            binary_configs = []
            for binary_input in vdsd._binary_inputs:
                binary_configs.append(self._extract_binary_input_config(binary_input))
            config["device_config"]["binary_inputs"] = binary_configs
        
        # Add sensors if present
        if vdsd._sensors:
            sensor_configs = []
            for sensor in vdsd._sensors:
                sensor_configs.append(self._extract_sensor_config(sensor))
            config["device_config"]["sensors"] = sensor_configs
        
        # Add scenes if saved
        if hasattr(vdsd, '_scenes') and vdsd._scenes:
            config["device_config"]["scenes"] = dict(vdsd._scenes)
        
        return config

    def _extract_output_config(self, output: "Output") -> Dict[str, Any]:
        """Extract output channel configuration."""
        channels_config = []
        for channel in output.channels:
            channels_config.append({
                "channel_type": channel.channel_type,
                "min_value": channel.min_value,
                "max_value": channel.max_value,
                "resolution": channel.resolution,
                # Mark as configurable - sets starting value, channel remains mutable
                "value_param": "CONFIGURABLE",
            })
        
        return {
            "channels": channels_config,
        }

    def _extract_button_config(self, button: "ButtonInput") -> Dict[str, Any]:
        """Extract button input configuration."""
        return {
            "button_type": button.button_type,
            "button_id": button.button_id,
            "name": button.name,
            "group": button.group,
            "mode": button.mode,
        }

    def _extract_binary_input_config(self, binary_input: "BinaryInput") -> Dict[str, Any]:
        """Extract binary input configuration."""
        return {
            "input_type": binary_input.input_type,
            "input_usage": binary_input.input_usage,
            "name": binary_input.name,
        }

    def _extract_sensor_config(self, sensor: "Sensor") -> Dict[str, Any]:
        """Extract sensor configuration."""
        return {
            "sensor_type": sensor.sensor_type,
            "sensor_usage": sensor.sensor_usage,
            "min_value": sensor.min_value,
            "max_value": sensor.max_value,
            "resolution": sensor.resolution,
            "update_interval": sensor.update_interval,
            "name": sensor.name,
        }

    def create_device_from_template(
        self,
        vdc: "Vdc",
        template_name: str,
        template_type: TemplateType,
        instance_name: str,
        enumeration: int,
        group_override: Optional[int] = None,
        **instance_params,
    ) -> "VdSD":
        """
        Create a new device instance from a template.
        
        Args:
            vdc: Parent Vdc instance
            template_name: Name of template to use
            template_type: TemplateType.DEVICE_TYPE or TemplateType.VENDOR_TYPE
            instance_name: Name for the new device instance
            enumeration: Device enumeration number (for dSUID generation)
            group_override: Optional group override (uses template group if not provided)
            **instance_params: Additional instance-specific parameters
                              (e.g., initial_values for output channels)
            
        Returns:
            Configured VdSD instance
            
        Raises:
            FileNotFoundError: If template doesn't exist
            ValueError: If template is malformed
            
        Example:
            # Create device from deviceType template
            light = template_mgr.create_device_from_template(
                vdc=my_vdc,
                template_name="simple_onoff_light",
                template_type=TemplateType.DEVICE_TYPE,
                instance_name="Kitchen Light",
                enumeration=1,
                initial_brightness=0.0
            )
            
            # Create device from vendorType template
            hue_spot = template_mgr.create_device_from_template(
                vdc=my_vdc,
                template_name="philips_hue_lily_spot",
                template_type=TemplateType.VENDOR_TYPE,
                instance_name="Garden Spot 1",
                enumeration=5
            )
        """
        # Load template
        template_data = self.load_template(template_name, template_type)
        
        # Extract configuration
        device_config = template_data.get("device_config", {})
        
        # Use group from template or override
        primary_group = group_override or device_config.get("primary_group")
        
        # Import VdSD here to avoid circular import
        from pyvdcapi.entities.vdsd import VdSD
        
        # Create device instance
        device = VdSD(
            vdc=vdc,
            name=instance_name,
            model=device_config.get("model", "Unknown"),
            primary_group=primary_group,
            mac_address=vdc.host.mac_address,
            vendor_id=vdc.host.vendor_id,
            enumeration=enumeration,
            model_uid=device_config.get("model_uid"),
            model_version=device_config.get("model_version", "1.0"),
        )
        
        # Configure output channels if present in template
        if "output" in device_config:
            self._apply_output_config(device, device_config["output"], instance_params)
        
        # Configure button inputs if present
        if "button_inputs" in device_config:
            self._apply_button_configs(device, device_config["button_inputs"])
        
        # Configure binary inputs if present
        if "binary_inputs" in device_config:
            self._apply_binary_input_configs(device, device_config["binary_inputs"])
        
        # Configure sensors if present
        if "sensors" in device_config:
            self._apply_sensor_configs(device, device_config["sensors"])
        
        # Restore scenes if present
        if "scenes" in device_config:
            device._scenes = device_config["scenes"]
        
        logger.info(
            f"Created device '{instance_name}' from template '{template_name}' "
            f"(type: {template_type.value})"
        )
        
        return device

    def _apply_output_config(
        self,
        device: "VdSD",
        output_config: Dict[str, Any],
        instance_params: Dict[str, Any],
    ):
        """Apply output configuration from template to device."""
        channels_config = output_config.get("channels", [])
        
        if not channels_config:
            return
        
        # Create output
        output = device.create_output()
        
        # Add each channel
        for idx, channel_config in enumerate(channels_config):
            # Get instance-specific value or use default (0.0)
            # Support multiple parameter naming schemes for backward compatibility
            param_key = f"value_{idx}" if len(channels_config) > 1 else "value"
            
            # Try new naming first, then legacy names
            value = instance_params.get(
                param_key,
                instance_params.get(f"initial_value_{idx}",
                    instance_params.get("brightness", 0.0)  # Common fallback
                )
            )
            
            output.add_output_channel(
                channel_type=channel_config["channel_type"],
                min_value=channel_config["min_value"],
                max_value=channel_config["max_value"],
                resolution=channel_config.get("resolution", 1.0),
                initial_value=value,
            )

    def _apply_button_configs(self, device: "VdSD", button_configs: List[Dict[str, Any]]):
        """Apply button configurations from template."""
        for button_config in button_configs:
            device.add_button_input(
                button_type=button_config["button_type"],
                button_id=button_config.get("button_id", 0),
                name=button_config.get("name", "Button"),
                group=button_config.get("group", 1),
                mode=button_config.get("mode", 0),
            )

    def _apply_binary_input_configs(self, device: "VdSD", binary_configs: List[Dict[str, Any]]):
        """Apply binary input configurations from template."""
        for binary_config in binary_configs:
            device.add_binary_input(
                input_type=binary_config["input_type"],
                input_usage=binary_config.get("input_usage"),
                name=binary_config.get("name", "Binary Input"),
            )

    def _apply_sensor_configs(self, device: "VdSD", sensor_configs: List[Dict[str, Any]]):
        """Apply sensor configurations from template."""
        for sensor_config in sensor_configs:
            device.add_sensor(
                sensor_type=sensor_config["sensor_type"],
                sensor_usage=sensor_config.get("sensor_usage"),
                min_value=sensor_config.get("min_value", 0.0),
                max_value=sensor_config.get("max_value", 100.0),
                resolution=sensor_config.get("resolution", 1.0),
                update_interval=sensor_config.get("update_interval", 60),
                name=sensor_config.get("name", "Sensor"),
            )

    def load_template(
        self,
        template_name: str,
        template_type: TemplateType,
        group: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Load a template from file.
        
        Args:
            template_name: Template name (without .yaml extension)
            template_type: TemplateType.DEVICE_TYPE or TemplateType.VENDOR_TYPE
            group: Optional group folder name (will search all groups if not provided)
            
        Returns:
            Template data dictionary
            
        Raises:
            FileNotFoundError: If template doesn't exist
        """
        safe_name = self._sanitize_filename(template_name)
        
        if group:
            # Direct path if group is known
            template_file = self.templates_path / template_type.value / group / f"{safe_name}.yaml"
            if not template_file.exists():
                raise FileNotFoundError(f"Template not found: {template_file}")
        else:
            # Search all group folders
            type_path = self.templates_path / template_type.value
            template_file = None
            
            for group_folder in type_path.iterdir():
                if group_folder.is_dir():
                    candidate = group_folder / f"{safe_name}.yaml"
                    if candidate.exists():
                        template_file = candidate
                        break
            
            if not template_file:
                raise FileNotFoundError(
                    f"Template '{template_name}' not found in {template_type.value}"
                )
        
        # Load template
        with open(template_file, 'r') as f:
            template_data = yaml.safe_load(f)
        
        logger.info(f"Loaded template: {template_file}")
        return template_data

    def list_templates(
        self,
        template_type: Optional[TemplateType] = None,
        group: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        """
        List available templates.
        
        Args:
            template_type: Filter by template type (None = all types)
            group: Filter by group folder (None = all groups)
            
        Returns:
            Dictionary mapping group names to list of template names
            
        Example:
            # List all templates
            all_templates = template_mgr.list_templates()
            # {'LIGHT': ['simple_onoff', 'dimmer'], 'HEATING': ['thermostat']}
            
            # List only deviceType templates
            device_templates = template_mgr.list_templates(
                template_type=TemplateType.DEVICE_TYPE
            )
            
            # List only LIGHT group templates
            light_templates = template_mgr.list_templates(group="LIGHT")
        """
        templates = {}
        
        # Determine which template types to scan
        types_to_scan = [template_type] if template_type else list(TemplateType)
        
        for ttype in types_to_scan:
            type_path = self.templates_path / ttype.value
            
            if not type_path.exists():
                continue
            
            for group_folder in type_path.iterdir():
                if not group_folder.is_dir():
                    continue
                
                # Skip if filtering by specific group
                if group and group_folder.name != group:
                    continue
                
                # Find all YAML files in this group
                group_templates = []
                for template_file in group_folder.glob("*.yaml"):
                    template_name = template_file.stem
                    group_templates.append(template_name)
                
                if group_templates:
                    key = f"{ttype.value}/{group_folder.name}"
                    templates[key] = sorted(group_templates)
        
        return templates

    def delete_template(
        self,
        template_name: str,
        template_type: TemplateType,
        group: Optional[str] = None,
    ) -> bool:
        """
        Delete a template file.
        
        Args:
            template_name: Template name
            template_type: TemplateType.DEVICE_TYPE or TemplateType.VENDOR_TYPE
            group: Optional group folder name (will search all if not provided)
            
        Returns:
            True if deleted, False if not found
        """
        safe_name = self._sanitize_filename(template_name)
        
        if group:
            template_file = self.templates_path / template_type.value / group / f"{safe_name}.yaml"
            if template_file.exists():
                template_file.unlink()
                logger.info(f"Deleted template: {template_file}")
                return True
        else:
            # Search all groups
            type_path = self.templates_path / template_type.value
            for group_folder in type_path.iterdir():
                if group_folder.is_dir():
                    template_file = group_folder / f"{safe_name}.yaml"
                    if template_file.exists():
                        template_file.unlink()
                        logger.info(f"Deleted template: {template_file}")
                        return True
        
        return False

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Sanitize filename by replacing invalid characters.
        
        Args:
            filename: Original filename
            
        Returns:
            Safe filename
        """
        # Replace spaces and special characters with underscores
        safe = filename.replace(" ", "_").replace("-", "_")
        # Remove any other non-alphanumeric characters except underscore
        safe = "".join(c for c in safe if c.isalnum() or c == "_")
        return safe.lower()
