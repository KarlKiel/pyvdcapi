# Device Templates

This directory contains reusable device configuration templates for pyvdcapi. Templates enable quick deployment of common device configurations and facilitate community sharing of device configs.

## 🔗 Hardware Binding Layer

**IMPORTANT**: Templates create device components (channels, sensors, buttons, binary inputs) that act as the **binding layer between your native hardware and the virtual vDC device**. These components are NOT static values - they are live, bidirectional variables that:

- **Map hardware state to vDC API**: Your hardware updates → component → vdSM
- **Map vDC commands to hardware**: vdSM commands → component → your hardware
- **Support callbacks**: Subscribe to changes in both directions
- **Remain mutable**: Can be updated throughout device lifetime

### Bidirectional Flow Example

```
Native Hardware     ←→     Component (Binding)     ←→     vdSM/digitalSTROM
─────────────────         ─────────────────────         ──────────────────
Physical dimmer           OutputChannel                 vDC API
  brightness=75%          .update_value(75)   →         Push notification
                          .subscribe(callback) ←        SET_OUTPUT request
  set_pwm(50%)      ←     callback(50.0)

Temperature sensor        Sensor                        vDC API
  temp=23.5°C             .update_value(23.5) →         Push notification
                          .subscribe(callback)          GET_PROPERTY request

Motion detector           BinaryInput                   vDC API
  motion=true             .set_state(True)    →         State notification
                          .subscribe(callback)          Automation trigger

Physical button           ButtonInput                   vDC API
  pressed                 .set_click_type(0)  →         Button event
                          .on_click(callback)           Scene trigger
```

### Why This Matters

When you create a device from a template, you're creating **binding objects** that:
1. ✅ Receive updates FROM your hardware (sensors reading, button presses)
2. ✅ Send commands TO your hardware (brightness changes, state changes)
3. ✅ Synchronize with vdSM automatically
4. ✅ Trigger your callbacks for hardware integration

This is the **integration point** between your physical devices and the digitalSTROM ecosystem.

### ✅ Single-Step Binding Helpers

The device now provides **one-call binding methods** for all component types.
These map components to your native variables in a single step:

```python
# Output channels (bidirectional)
device.bind_output_channel(
  DSChannelType.BRIGHTNESS,
  getter=lambda: native_state["brightness"],
  setter=lambda value: native_state.__setitem__("brightness", value),
  poll_interval=0.5,  # optional polling from hardware
  epsilon=0.1,
)

# Sensors (hardware → vdSM)
device.bind_sensor(
  sensor_index=0,
  getter=lambda: native_state["temperature"],
  poll_interval=5.0,
  epsilon=0.1,
)

# Binary inputs (hardware → vdSM)
device.bind_binary_input(
  input_index=0,
  getter=lambda: native_state["motion"],
  poll_interval=0.2,
)

# Button inputs (hardware → vdSM)
# event_getter returns next clickType or None
device.bind_button_input(
  button_index=0,
  event_getter=lambda: native_events.pop(0) if native_events else None,
  poll_interval=0.05,
)
```

### ✅ Event-Driven Binding (No Polling)

If your hardware can **push events**, use the event-driven helpers:

```python
# Output hardware feedback (native → vdSM)
device.bind_output_channel_events(
  DSChannelType.BRIGHTNESS,
  register=lambda cb: hardware.on_brightness_changed(cb),
)

# Sensor events (native → vdSM)
device.bind_sensor_events(
  sensor_index=0,
  register=lambda cb: hardware.on_temperature_changed(cb),
)

# Binary input events (native → vdSM)
device.bind_binary_input_events(
  input_index=0,
  register=lambda cb: hardware.on_motion_changed(cb),
)

# Button events (native → vdSM)
device.bind_button_input_events(
  button_index=0,
  register=lambda cb: hardware.on_button_event(cb),
)
```

**Use polling or events depending on your hardware.** Both are supported.

### ✅ Automatic Input Binding (Config-Driven)

The library automatically determines the correct binding approach based on the **vDC API properties** already defined in your device template. You don't need to specify a separate binding configuration - the component properties tell the system how to bind.

#### Binding Behavior by Component Type

**Buttons** - Always Event-Driven (Push Only)
- Buttons NEVER need polling
- Button behavior mode MUST be defined at creation (cannot be changed later)
- Report EITHER clickType/value (standard mode) OR actionId/actionMode (action mode), never both
- Both are discrete events, not continuous values
- Always bind using `register` callback

Example:
```python
# Standard mode button (clickType/value)
button = device.add_button_input(
    name="Wall Button",
    button_type=1,
    use_action_mode=False  # REQUIRED: Standard mode
)

# Action mode button (actionId/actionMode)  
scene_button = device.add_button_input(
    name="Scene Button",
    button_type=1,
    use_action_mode=True  # REQUIRED: Action mode
)
```

**Binary Inputs** - Property-Driven
- The `inputType` property defines push vs poll behavior  
- Bind to `value` (boolean) or `extendedValue` (integer)
- Use `register` for event-driven, `getter` for polling

**Sensors** - Throttled Push
- Use existing `min_push_interval` and `changes_only_interval` properties
- These control throttling for push updates
- Bind to `value` property
- Can use both `getter` (polling) and `register` (events) simultaneously

**Output Channels** - Always Bidirectional
- The output's `push_changes` setting (always True) defines behavior
- Changes MUST be pushed back to vdSM
- Bind to channel `value` property
- Requires both `getter` and `setter`

#### Usage Example

```python
# 1. Create device from template (vDC properties restored automatically)
device = vdc.create_vdsd_from_template(
    template_name="multi_sensor",
    template_type="deviceType",
    instance_name="Sensor_1",
)

# 2. Bind to native hardware - binding behavior determined by vDC API properties
device.bind_inputs_auto({
    # Buttons: Always event-driven
    "buttons": [
        {"register": hardware.on_button_event},  # register required
    ],
    
    # Binary inputs: Event-driven or polling based on hardware
    "binary_inputs": [
        {"register": hardware.on_motion_change},  # Event-driven (preferred)
        # OR {"getter": hardware.get_door_state, "poll_interval": 0.2},
    ],
    
    # Sensors: Can use both polling and events
    "sensors": [
        {"getter": hardware.get_temperature},  # Uses sensor.min_push_interval
        # OR {"register": hardware.on_temp_change},
        # OR BOTH for reliability
    ],
})
```

No separate "binding" configuration is needed - the vDC API properties already contain all the information!

### ✅ Output Channels Always Push

Per vDC documentation (and this implementation), **output channels always push
value changes**. The `pushChanges` setting is forced to `True` internally and
ignored if the vdSM tries to disable it. This guarantees that output value
updates are always notified.

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
  description: "Simple on/off light with brightness control (0-100%)"  # Detailed description
  vendor: "ACME"  # Optional, for vendorType templates
  vendor_model_id: "12345"  # Optional, vendor's model number
  created_from_model: "OnOff Light"  # Model name from original device
```

**Field Descriptions**:
- **template_name**: Template identifier (used when creating devices from template)
- **description**: Detailed human-readable description of the template's functionality, features, and capabilities. This helps users understand what the template does and when to use it.
- **vendor**: (Optional) Manufacturer name for vendor-specific templates
- **vendor_model_id**: (Optional) Manufacturer's model/part number
- **created_from_model**: Original device model name this template was created from

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
        value_param: CONFIGURABLE
  
  button_inputs: [...]  # Optional
  sensors: [...]        # Optional
  binary_inputs: [...]  # Optional
  scenes: {...}         # Optional
  actions: {...}        # Optional (see Actions section)
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

# Save as template with detailed description
template_path = device.save_as_template(
    template_name="my_custom_light",
    template_type="deviceType",  # or "vendorType"
    description="Custom dimmable light with temperature sensor and manual override button",
)

# For vendor-specific templates, add vendor information
template_path = device.save_as_template(
    template_name="philips_hue_white_ambiance",
    template_type="vendorType",
    description="Philips Hue White Ambiance bulb with color temperature control (2200K-6500K)",
    vendor="Philips",
    vendor_model_id="8718696548738",
)
```

### Creating Devices from Templates

```python
# Create a single device from template
device = vdc.create_vdsd_from_template(
    template_name="simple_onoff_light",
    instance_name="Living Room Light",
    template_type="deviceType",
    brightness=0.0,  # Starting value for the brightness channel
)

# ═══════════════════════════════════════════════════════════════
# CRITICAL: Set up hardware binding after creation!
# ═══════════════════════════════════════════════════════════════
# Components are the BINDING LAYER between hardware and vDC API
# You MUST connect them to your native hardware for bidirectional flow

# 1. OUTPUT BINDING (vdSM ←→ Hardware)
output = device.get_output()
brightness_channel = output.get_channel(DSChannelType.BRIGHTNESS)

async def apply_to_hardware(channel_type: int, value: float):
    """Called when vdSM changes the brightness value"""
    print(f"Setting native hardware brightness to {value}%")
    await my_hardware_driver.set_brightness(value)

brightness_channel.subscribe(apply_to_hardware)  # vdSM → Hardware

# Update from hardware (e.g., manual dimmer knob turned)
brightness_channel.update_value(75.0)  # Hardware → vdSM

# 2. SENSOR BINDING (Hardware → vdSM)
if device._sensors:
    temp_sensor = device._sensors[0]
    
    # Your hardware polling loop
    async def poll_temperature():
        while True:
            temp = await my_hardware_driver.read_temperature()
            temp_sensor.update_value(temp)  # Native value → vdSM
            await asyncio.sleep(60)
    
    # Optional: React to sensor changes
    def on_temp_change(sensor_type: int, value: float):
        if value > 30.0:
            print("Temperature alert!")
    temp_sensor.subscribe(on_temp_change)

# 3. BUTTON BINDING (Hardware → vdSM)
if device._button_inputs:
    button = device._button_inputs[0]
    
    # Your hardware interrupt handler
    def on_physical_button_press():
        # Detect click type from your hardware
        click_type = detect_click_pattern()  # Your logic
        button.set_click_type(click_type)  # Native event → vdSM
    
    my_hardware.register_interrupt(on_physical_button_press)

# 4. BINARY INPUT BINDING (Hardware → vdSM)
if device._binary_inputs:
    motion = device._binary_inputs[0]
    
    # Your hardware state change handler
    def on_motion_detected(active: bool):
        motion.set_state(active)  # Native state → vdSM
    
    my_hardware.on_motion_change(on_motion_detected)
    
    # Optional: React to motion
    def on_motion_callback(input_type: int, state: bool):
        if state:
            print("Motion detected!")
    motion.subscribe(on_motion_callback)
```

**Summary**: Templates create the components, YOU create the hardware binding by:
- Subscribing to component callbacks (for vdSM → Hardware direction)
- Calling `.update_value()`, `.set_state()`, `.set_click_type()` (for Hardware → vdSM direction)

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
  
- **CONFIGURABLE**: User can optionally override the starting value
  - Example: `value_param: CONFIGURABLE`

**Important**: Parameters marked as CONFIGURABLE set the **starting value** for the channel, but the channel remains **fully mutable and bidirectional** after creation. Channels created from templates support:
- `.subscribe(callback)` - Register hardware update callbacks
- `.set_value(value)` - vdSM → Hardware direction  
- `.update_value(value)` - Hardware → vdSM direction
- `.get_value()` - Read current state

When creating a device from a template:
```python
device = vdc.create_vdsd_from_template(
    template_name="simple_onoff_light",
    instance_name="My Light",      # REQUIRED parameter
    # enumeration auto-calculated if not provided
    brightness=50.0,                # CONFIGURABLE - sets starting value
)

# After creation, get the channel for bidirectional binding
output = device.get_output()
brightness_channel = output.get_channel(DSChannelType.BRIGHTNESS)

# Channel is now a live, mutable variable with callbacks
brightness_channel.subscribe(my_hardware_callback)
```

## Actions in Templates

Templates can include **actions** (identify, reset, calibrate, etc.).
The action definitions are saved with the template, but **handlers must be bound**
when creating a new device from the template.

### How It Works

1. The original device registers actions via `device.actions.add_standard_action()`
   or `device.actions.add_custom_action()`.
2. When saving as template, **action definitions** are stored.
3. When creating from template, **pass handler mappings** to bind behavior.

### Example

```python
# 1) Original device defines actions
device.actions.add_standard_action(
  name="identify",
  description="Identify device",
  handler=lambda duration=3.0: hardware.blink(duration),
)

device.actions.add_custom_action(
  name="calibrate",
  title="Calibrate device",
  action_template="calibration",
  handler=lambda: hardware.calibrate(),
)

# 2) Save template (actions are stored automatically)
device.save_as_template("my_device_with_actions")

# 3) Create from template and bind handlers
action_handlers = {
  "std.identify": lambda duration=3.0: hardware.blink(duration),
  "custom.calibrate": lambda: hardware.calibrate(),
  # You can also use short names: "identify", "calibrate"
}

new_device = vdc.create_vdsd_from_template(
  template_name="my_device_with_actions",
  instance_name="Kitchen Device",
  action_handlers=action_handlers,
)

# Alternatively, bind after creation:
# new_device.bind_action_handlers(action_handlers)
```

This ensures templates preserve **what actions exist**, and your device code
binds **how actions are executed** on the native hardware.

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
2. **Write detailed descriptions**: Explain device functionality, features, and capabilities
   - ✅ Good: "RGB color light with brightness (0-100%), hue (0-360°), saturation (0-100%), and color temperature (2200K-6500K)"
   - ❌ Poor: "Light template"
3. **Set sensible defaults**: Choose default values that work for most cases
4. **Document special features**: Note any unique capabilities in metadata
5. **Test thoroughly**: Create multiple instances to verify template works
6. **Include vendor details** (for vendorType): Add vendor name and model ID for easy identification

#### Writing Good Template Descriptions

The `description` field in `template_metadata` should help users understand:
- **What** the device is (type and purpose)
- **What it can do** (channels, inputs, sensors)
- **How it works** (ranges, special features)
- **When to use it** (vendor-specific models, use cases)

**Examples**:
```python
# deviceType template
description="Dimmable light with brightness control (0-100%), supports smooth transitions and scene recall"

# vendorType template  
description="Philips Hue White Ambiance bulb with color temperature control (2200K-6500K), smooth dimming, and scene support"

# Complex device
description="Multi-sensor device with temperature (-20°C to 60°C), humidity (0-100%), and motion detection, configurable push intervals"
```

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
