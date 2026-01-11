# vdSM Simulator

Mock virtualSTROM Manager for testing vDC implementations.

## Environment Setup

Before running the simulator or demos, you need to set up a Python environment with the required dependencies.

### 1. Create a Virtual Environment

It's recommended to use a virtual environment to isolate dependencies:

```bash
# Navigate to the repository root
cd pyvdcapi

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### 2. Install Dependencies

The repository requires the following Python packages:

```bash
pip install protobuf pyyaml
```

### 3. Verify Installation

Verify that the packages are installed correctly:

```bash
python3 -c "import google.protobuf; import yaml; print('Dependencies installed successfully!')"
```

If you see "Dependencies installed successfully!", you're ready to proceed.

## Testing the Repository

The easiest way to test the repository is to run the complete demo which creates a vDC host with sample devices and demonstrates the full protocol interaction.

### Running the Complete Demo

```bash
# Make sure you're in the repository root and the virtual environment is activated
python examples/demo_with_simulator.py
```

This demo will:
1. Create a vDC host with 2 vDCs (lights and sensors)
2. Create 3 devices (2 lights and 1 multi-sensor)
3. Start the vDC host server on port 8444
4. Connect the vdSM simulator to the host
5. Perform full discovery of vDCs and devices
6. Execute interactive test commands (set brightness, call scenes, save scenes)
7. Display all protocol communication in real-time

**Expected Output:**

You should see output sections including:
- ✅ `CREATING vDC HOST WITH DEMO DEVICES` - Device creation
- ✅ `STARTING vDC HOST SERVER` - Server startup
- ✅ `STARTING vdSM SIMULATOR` - Simulator connection
- ✅ `RUNNING INTERACTIVE TEST COMMANDS` - Command execution
- ✅ All protocol messages (Hello, Discovery, Commands, Responses)

The demo runs for approximately 15 seconds and then stops automatically.

### Troubleshooting

**Problem:** `ModuleNotFoundError: No module named 'google'`
```bash
# Solution: Install protobuf
pip install protobuf
```

**Problem:** `ModuleNotFoundError: No module named 'yaml'`
```bash
# Solution: Install pyyaml
pip install pyyaml
```

**Problem:** Port 8444 already in use
```bash
# Solution: Stop any process using port 8444 or modify the port in demo_with_simulator.py
lsof -i :8444  # Find process using the port
```

**Problem:** Connection refused
```bash
# Solution: Ensure the vDC host started successfully and you're connecting to the right host/port
# Check the logs for "vDC host is running on port 8444"
```

## Overview

The vdSM simulator acts as a vdSM (virtual digitalSTROM Manager) client that can:
- Connect to a vDC host via TCP
- Perform Hello handshake and session management
- Discover vDCs and devices (vdSDs)
- Query properties from all entity types
- Send commands (scene calls, output control, etc.)
- Display all protocol communication in real-time

This is useful for:
- **Testing** vDC implementations without a real vdSM
- **Development** and debugging of vDC protocol handlers
- **Learning** how the vDC API protocol works
- **Automation** of integration tests

## Quick Start

### 1. Run the Complete Demo

The easiest way to see everything in action:

```bash
python examples/demo_with_simulator.py
```

This will:
1. Create a vDC host with sample devices (lights and sensors)
2. Start the vDC host server
3. Connect the vdSM simulator
4. Perform full discovery
5. Run interactive test commands

### 2. Standalone Simulator Usage

If you already have a vDC host running:

```bash
# Basic discovery
python examples/vdsm_simulator.py

# Full test scenario with commands
python examples/vdsm_simulator.py --scenario full_test

# Interactive mode
python examples/vdsm_simulator.py --interactive

# Connect to remote host
python examples/vdsm_simulator.py --host 192.168.1.100 --port 8444
```

## Features

### Automated Discovery

```python
from examples.vdsm_simulator import VdsmSimulator

simulator = VdsmSimulator(host='localhost', port=8444)
await simulator.connect()
await simulator.send_hello()

# Discover everything
await simulator.full_discovery()

# Access discovered entities
print(f"Found {len(simulator.vdcs)} vDCs")
print(f"Found {len(simulator.devices)} devices")
```

### Send Commands

```python
# Call a scene
await simulator.call_scene(device_dsuid, scene_number=5)

# Set output value
await simulator.set_output_value(
    device_dsuid, 
    channel_type=0,  # Brightness
    value=75.0,
    transition_time=2.0
)

# Save scene
await simulator.save_scene(device_dsuid, scene_number=1)
```

### Query Properties

```python
# Get device properties
props = await simulator.get_property(device_dsuid, {
    "dSUID": None,
    "name": None,
    "model": None,
    "primaryGroup": None,
    "outputDescription": None
})

print(f"Device: {props['name']}")
print(f"Group: {props['primaryGroup']}")
```

### Interactive Mode

```bash
$ python examples/vdsm_simulator.py --interactive

vdSM SIMULATOR - Interactive Mode
================================================================================

Commands:
  discover        - Discover all vDCs and devices
  list            - Show discovered entities
  scene <dsuid> <num>  - Call scene on device
  set <dsuid> <ch> <val>  - Set output value
  quit            - Exit

vdSM> discover
... [discovery output] ...

vdSM> scene 00000002... 5
→ Calling scene 5 on device 00000002...
✓ Scene call sent

vdSM> set 00000002... 0 75.0
→ Setting output channel 0 to 75.0% on 00000002...
✓ Output value set

vdSM> quit
```

## Protocol Messages Supported

### Session Management
- ✅ VDSM_REQUEST_HELLO / VDC_RESPONSE_HELLO
- ✅ VDC_SEND_BYE
- ✅ VDSM_SEND_PING / VDC_SEND_PONG

### Discovery
- ✅ VDC_SEND_ANNOUNCE_VDC
- ✅ VDC_SEND_ANNOUNCE_DEVICE

### Properties
- ✅ VDSM_REQUEST_GET_PROPERTY / VDC_RESPONSE_GET_PROPERTY
- ✅ VDSM_REQUEST_GENERIC_REQUEST / VDC_RESPONSE_GENERIC_REQUEST

### Device Control
- ✅ VDSM_NOTIFICATION_CALL_SCENE
- ✅ VDSM_NOTIFICATION_SAVE_SCENE
- ✅ VDSM_NOTIFICATION_SET_OUTPUT_CHANNEL_VALUE
- ✅ VDSM_NOTIFICATION_DIM_CHANNEL
- ✅ VDSM_NOTIFICATION_IDENTIFY

## Architecture

```
┌─────────────────┐          TCP/IP           ┌──────────────────┐
│                 │◄────────────────────────►  │                  │
│  vdSM Simulator │     Port 8444             │   vDC Host       │
│                 │                            │                  │
│  - Discovery    │   Protobuf Messages        │  - VdcHost       │
│  - Commands     │◄────────────────────────►  │  - Vdc(s)        │
│  - Monitoring   │                            │  - VdSD(s)       │
│                 │                            │                  │
└─────────────────┘                            └──────────────────┘
```

## Extending the Simulator

Add custom test scenarios:

```python
async def custom_test_scenario(simulator: VdsmSimulator):
    """Custom test scenario."""
    # Discover all devices
    await simulator.full_discovery()
    
    # Find specific device type
    light_devices = [
        d for d in simulator.devices.values() 
        if d.primary_group == 1  # Light group
    ]
    
    # Run custom test sequence
    for device in light_devices:
        await simulator.set_output_value(device.dsuid, 0, 100.0)
        await asyncio.sleep(1)
        await simulator.call_scene(device.dsuid, 0)  # Off scene
        await asyncio.sleep(1)

# Use in main
if args.scenario == 'custom':
    await custom_test_scenario(sim)
```

## Logging

Control log verbosity:

```python
import logging

# Show all protocol messages
logging.getLogger('vdsm_simulator').setLevel(logging.DEBUG)

# Show only important events
logging.getLogger('vdsm_simulator').setLevel(logging.INFO)
```

## See Also

- [e2e_validation.py](e2e_validation.py) - End-to-end validation tests
- [demo_with_simulator.py](demo_with_simulator.py) - Complete demo with vDC host
- [complete_protocol_demo.py](complete_protocol_demo.py) - Protocol demonstration
- [../API_REFERENCE.md](../API_REFERENCE.md) - Full API documentation
- [../Documentation/vdc-API/](../Documentation/vdc-API/) - vDC API specification
