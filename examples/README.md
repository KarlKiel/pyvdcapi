# Examples

This folder contains runnable examples that demonstrate how to use the `pyvdcapi` library.

## Core Examples

### Basic Setup
- **`01_create_clean_vdc_host.py`** — Minimal VdcHost setup
- **`02_create_clean_vdc.py`** — Create VdC and devices
- **`03_create_clean_vdsd.py`** — Complete device setup
- **`04_example_operations.py`** — Device operations (scenes, channels, etc.)
- **`05_vdc_utility_methods.py`** — Utility methods demonstration

### Device Components
- **`button_input_example.py`** — Button with state machine and click detection
- **`motion_light_device.py`** — Motion-activated light with sensor integration
- **`control_values_heating_demo.py`** — Heating control values and setpoints

### Template System
- **`06_template_system.py`** — **Complete template system demonstration**
  - Save devices as templates (deviceType and vendorType)
  - Create multiple devices from templates
  - List, inspect, and manage templates
  - Community sharing workflow

### Network & Discovery
- **`service_announcement_demo.py`** — Full demo with mDNS/DNS-SD auto-discovery
- **`demo_with_simulator.py`** — Complete demo with vdSM protocol simulator
- **`vdsm_simulator.py`** — vdSM protocol simulator for testing

### Validation & Testing
- **`e2e_validation.py`** — End-to-end validation
- **`device_configuration.py`** — Configuration management

Requirements:

Create a virtual environment and install the minimal requirements:

```bash
python3 -m venv /path/to/venv
. /path/to/venv/bin/activate
pip install --upgrade pip
pip install -r examples/requirements.txt
```

Running `example_clean_start.py`:

```bash
python3 examples/example_clean_start.py
```

The script will prompt for host details, start the `VdcHost` with service announcement enabled, and run until you press Ctrl+C.
