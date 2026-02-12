# Template Description Field - Quick Reference

## Overview

The `description` field in template metadata provides a detailed, human-readable explanation of what the template does, what features it includes, and when to use it.

## Location in Template YAML

```yaml
template_metadata:
  template_name: "my_template"
  description: "Detailed description goes here"  # ← This field
  vendor: null
  vendor_model_id: null
  created_from_model: "Original Model"
```

## Usage

### When Saving a Template

```python
template_path = device.save_as_template(
    template_name="my_template",
    template_type="deviceType",
    description="Your detailed description here",  # ← Use this parameter
)
```

### Complete Example

```python
# Create and configure device
device = vdc.create_vdsd(
    name="RGB Light",
    model="RGB Color Light",
    primary_group=DSGroup.YELLOW,
)

# Add channels
device.add_output_channel(
    channel_type=DSChannelType.BRIGHTNESS,
    min_value=0.0,
    max_value=100.0,
    output_function="colordimmer",
)

# Save with detailed description
template_path = device.save_as_template(
    template_name="rgb_color_light",
    template_type="deviceType",
    description="RGB color light with brightness (0-100%), hue (0-360°), and saturation (0-100%) control, supports smooth color transitions",
)
```

## Best Practices

### ✅ Good Descriptions

Include these elements:
1. **Device type** - What kind of device is this?
2. **Key features** - What channels/inputs does it have?
3. **Value ranges** - What are the min/max values?
4. **Special capabilities** - Any unique features?

**Examples**:
```python
# Simple device
description="Simple on/off light switch with binary control (no dimming)"

# Dimmable light
description="Dimmable light with smooth brightness control (0-100%), supports gradual transitions and scene recall"

# RGB light
description="RGB color light with brightness (0-100%), hue (0-360°), and saturation (0-100%) control, supports smooth color transitions and full scene integration"

# Multi-sensor
description="Environmental sensor with temperature (-20°C to 60°C), humidity (0-100%), and motion detection. Configurable push intervals (5s minimum) with change-only mode for reduced updates."

# Vendor-specific
description="Philips Hue White Ambiance bulb with brightness control (0-100%) and color temperature adjustment (2200K-6500K), smooth transitions and scene support"
```

### ❌ Poor Descriptions

Avoid vague or useless descriptions:

```python
description="Light"                    # Too vague
description="Device template"          # Not informative
description="Template"                 # Useless
description="My template"              # Doesn't explain functionality
```

## Vendor-Specific Templates

For `vendorType` templates, include vendor information:

```python
template_path = device.save_as_template(
    template_name="philips_hue_white_ambiance",
    template_type="vendorType",
    description="Philips Hue White Ambiance bulb with brightness control (0-100%) and color temperature adjustment (2200K-6500K), smooth transitions and scene support",
    vendor="Philips",                  # Add vendor name
    vendor_model_id="8718696548738",   # Add model/part number
)
```

This creates:
```yaml
template_metadata:
  template_name: "philips_hue_white_ambiance"
  description: "Philips Hue White Ambiance bulb with brightness control (0-100%) and color temperature adjustment (2200K-6500K), smooth transitions and scene support"
  vendor: "Philips"
  vendor_model_id: "8718696548738"
  created_from_model: "Philips Hue White Ambiance"
```

## Reading Template Descriptions

When loading a template, you can access the description:

```python
from pyvdcapi.templates import TemplateManager, TemplateType

manager = TemplateManager()

# Load template
template_data = manager.load_template(
    template_name="rgb_color_light",
    template_type=TemplateType.DEVICE_TYPE,
)

# Access description
description = template_data["template_metadata"]["description"]
print(f"Template: {description}")

# Output:
# Template: RGB color light with brightness (0-100%), hue (0-360°), and saturation (0-100%) control, supports smooth color transitions
```

## Template Metadata Fields

All fields in `template_metadata`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `template_name` | string | ✅ Yes | Template identifier |
| `description` | string | ✅ Yes | Detailed feature description |
| `vendor` | string | ❌ No | Manufacturer name (for vendorType) |
| `vendor_model_id` | string | ❌ No | Model/part number (for vendorType) |
| `created_from_model` | string | ✅ Yes | Original device model name |

## Example Templates

The project includes comprehensive example templates with detailed descriptions:

### deviceType Templates

1. **ExampleTemplateAllFeaturesOutputPushed**
   ```yaml
   description: "Complete example device with bidirectional output (pushChanges=True)"
   ```

2. **ExampleTemplateAllFeaturesOutputControlOnly**
   ```yaml
   description: "Complete example device with control-only output (pushChanges=False)"
   ```

### Running the Example

Create templates with descriptions:

```bash
python examples/template_descriptions_example.py
```

This creates 5 example templates demonstrating:
- Simple on/off light (basic description)
- Dimmable light (detailed description)
- RGB color light (comprehensive description)
- Vendor-specific template (with vendor info)
- Multi-sensor device (complex description)

## Summary

The `description` field is **essential** for creating useful, shareable templates. It helps users:
- Understand what the template does
- Choose the right template for their needs
- Know what features are included
- Identify vendor-specific models

Always provide a **detailed, informative description** when creating templates!
