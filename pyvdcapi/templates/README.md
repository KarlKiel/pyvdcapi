# Device Templates

This directory contains reusable device configuration templates for pyvdcapi. Templates enable quick deployment of common device configurations and facilitate community sharing of device configs.

## Template Types

### deviceType Templates
Standard hardware configurations independent of specific vendors. These templates represent common device types like:
- Simple on/off lights
- Dimmable lights
- Wall switches
- Sensors
- Motorized blinds

**Location**: `deviceType/{GROUP}/`

**Use when**: You want to create devices based on common functionality patterns, regardless of manufacturer.

### vendorType Templates
Vendor-specific hardware configurations for particular products. These templates capture the exact specifications of a specific vendor's product, including:
- Channel configurations
- Hardware capabilities
- Default scenes
- Vendor identification

**Location**: `vendorType/{GROUP}/`

**Use when**: You want to create devices that match a specific manufacturer's product exactly.

## Template Structure

Templates are YAML files with two main sections:

### template_metadata
Information about the template itself:
```yaml
template_metadata:
  template_name: "simple_onoff_light"
  description: "Simple on/off light with brightness control (0-100%)"
  vendor: "ACME"  # Optional, for vendorType
  vendor_model_id: "12345"  # Optional, vendor's model number
  created_from_model: "OnOff Light"
  template_version: "1.0"
```

### device_config
Complete device configuration:
```yaml
device_config:
  model: "OnOff Light"
  model_uid: "onoff-light"
  primary_group: 1  # DSGroup (1=LIGHT, 2=BLINDS, etc.)
  
  instance_parameters:
    name: REQUIRED
    enumeration: REQUIRED
  
  output:
    channels:
      - channel_type: 1  # BRIGHTNESS
        min_value: 0.0
        max_value: 100.0
        resolution: 1.0
        initial_value_param: CONFIGURABLE
  
  button_inputs: [...]  # Optional
  sensors: [...]        # Optional
  binary_inputs: [...]  # Optional
  scenes: {...}         # Optional
```

## Organization

Templates are organized by **template type** and **device group**:

```
templates/
├── deviceType/
│   ├── LIGHT/
│   │   ├── simple_onoff_light.yaml
│   │   ├── dimmable_light_with_scenes.yaml
│   │   └── wall_switch_single_button.yaml
│   ├── BLINDS/
│   │   └── motorized_blinds.yaml
│   ├── HEATING/
│   ├── COOLING/
│   └── ...
└── vendorType/
    ├── LIGHT/
    │   └── philips_hue_lily_garden_spot.yaml
    ├── HEATING/
    └── ...
```

## Usage

### Saving a Device as Template

```python
from pyvdcapi.entities.vdc_host import VdcHost

# Create and configure a device
host = VdcHost(name="MyHost", ...)
vdc = host.create_vdc(name="MyVDC", ...)
device = vdc.create_vdsd(name="MyDevice", model="OnOff Light", primary_group=1)

# Configure the device...
output = device.create_output()
output.add_output_channel(channel_type=1, min_value=0.0, max_value=100.0)

# Save as template
template_path = device.save_as_template(
    template_name="my_custom_light",
    template_type="deviceType",  # or "vendorType"
    description="My custom light configuration",
)
```

### Creating Devices from Templates

```python
# Create a single device from template
device = vdc.create_vdsd_from_template(
    template_name="simple_onoff_light",
    instance_name="Living Room Light",
    template_type="deviceType",
    initial_brightness=0.0,  # Optional instance parameter
)

# Create multiple devices from the same template
for i in range(1, 6):
    device = vdc.create_vdsd_from_template(
        template_name="philips_hue_lily_garden_spot",
        instance_name=f"Garden Spot {i}",
        template_type="vendorType",
        initial_brightness=0.0,
        initial_hue=120.0,  # Green
    )
```

### Managing Templates

```python
from pyvdcapi.templates import TemplateManager, TemplateType

manager = TemplateManager()

# List all templates
all_templates = manager.list_templates()
for category, templates in all_templates.items():
    print(f"{category}: {templates}")

# List only deviceType templates
device_templates = manager.list_templates(template_type=TemplateType.DEVICE_TYPE)

# List only LIGHT group templates
light_templates = manager.list_templates(group="LIGHT")

# Load and inspect a template
template_data = manager.load_template("simple_onoff_light", TemplateType.DEVICE_TYPE)
print(template_data["template_metadata"]["description"])

# Delete a template
manager.delete_template("old_template", TemplateType.DEVICE_TYPE)
```

## Instance Parameters

Templates use special keywords to indicate instance-specific values:

- **REQUIRED**: User must provide this value when creating from template
  - Example: `name: REQUIRED`, `enumeration: REQUIRED`
  
- **CONFIGURABLE**: User can optionally override the default value
  - Example: `initial_value_param: CONFIGURABLE`

When creating a device from a template:
```python
device = vdc.create_vdsd_from_template(
    template_name="simple_onoff_light",
    instance_name="My Light",  # REQUIRED parameter
    # enumeration auto-calculated if not provided
    initial_brightness=50.0,   # CONFIGURABLE parameter (override)
)
```

## Community Sharing

Templates are designed to be easily shared:

1. **Each template is a single YAML file** - easy to distribute
2. **Human-readable format** - can be edited with any text editor
3. **Organized structure** - clear categorization by type and group
4. **Self-documenting** - includes description and metadata

### Contributing Templates

To share your template:

1. Create and test your device configuration
2. Save as template with clear name and description
3. Share the YAML file from `templates/{type}/{group}/`
4. Include any special notes in the description

### Using Community Templates

To use a shared template:

1. Copy the YAML file to `templates/{type}/{group}/`
2. Verify the template loads: `manager.load_template("name", type)`
3. Create devices: `vdc.create_vdsd_from_template(...)`

## Available Templates

### deviceType Templates

#### LIGHT Group
- **simple_onoff_light**: Basic on/off light with brightness (0-100%)
- **dimmable_light_with_scenes**: Dimmable light with standard scene presets (25%, 50%, 75%, 100%)
- **wall_switch_single_button**: Single button wall switch with light output

#### BLINDS Group
- **motorized_blinds**: Motorized window blinds with position control (0-100%)

#### CLIMATE_CONTROL Group
- **temperature_humidity_sensor**: Combined temperature and humidity sensor

### vendorType Templates

#### LIGHT Group
- **philips_hue_lily_garden_spot**: Philips HUE Lily outdoor spotlight with RGB+White control

## Template Development

### Creating a New Template

1. **Start with a working device**:
   ```python
   device = vdc.create_vdsd(name="Test", model="MyModel", primary_group=1)
   # Configure all components...
   ```

2. **Save as template**:
   ```python
   device.save_as_template(
       template_name="my_template",
       template_type="deviceType",
       description="Clear description of what this template does",
   )
   ```

3. **Test the template**:
   ```python
   test_device = vdc.create_vdsd_from_template(
       template_name="my_template",
       instance_name="Test Instance",
   )
   # Verify all components work correctly
   ```

4. **Share or commit** the YAML file

### Best Practices

1. **Use descriptive names**: `motorized_blinds` not `blinds1`
2. **Include clear descriptions**: Explain what the template configures
3. **Set sensible defaults**: Choose default values that work for most cases
4. **Document special features**: Note any unique capabilities in metadata
5. **Test thoroughly**: Create multiple instances to verify template works
6. **Version your templates**: Use `template_version` to track changes

## Channel Types Reference

Common channel types used in templates:

- `1`: BRIGHTNESS (0-100%)
- `2`: HUE (0-360°)
- `3`: SATURATION (0-100%)
- `4`: COLOR_TEMPERATURE (Kelvin)
- `5`: POSITION (0-100%, blinds/shutters)

See `pyvdcapi/core/constants.py` for complete list.

## Group IDs Reference

Primary group IDs for template organization:

- `1`: LIGHT (Yellow)
- `2`: BLINDS (Grey)
- `3`: HEATING (Blue)
- `4`: COOLING (Blue)
- `5`: VENTILATION (Blue)
- `8`: AUDIO (Cyan)
- `9`: CLIMATE_CONTROL (Blue)

See `DSGroup` enum in `pyvdcapi/core/constants.py` for complete list.

## Examples

See `examples/06_template_system.py` for comprehensive usage examples demonstrating:
- Creating and configuring devices
- Saving devices as templates
- Creating multiple devices from templates
- Managing and inspecting templates
- Both deviceType and vendorType workflows
