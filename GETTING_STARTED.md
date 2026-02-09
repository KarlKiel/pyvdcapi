# Getting Started with pyvdcapi Development

**Welcome to the team!** 🎉

This guide will get you up and running as a pyvdcapi developer in 30 minutes.

---

## Quick Links

📖 **Documentation You Need:**
- [SUMMARY.md](SUMMARY.md) - Start here! Executive overview
- [API_REFERENCE.md](API_REFERENCE.md) - Your coding reference
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design details
- [ISSUES.md](ISSUES.md) - Known issues and tasks

🔧 **Important Files:**
- `examples/` - Working code examples (study these!)
- `Documentation/vdc-API/` - Official specification
- `pyvdcapi/entities/` - Core classes (VdcHost, Vdc, VdSD)
- `pyvdcapi/components/` - Device components

---

## Prerequisites

```bash
# Python 3.7 or higher
python --version

# Git
git --version

# Text editor (VS Code recommended)
code --version
```

---

## Setup (5 minutes)

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/KarlKiel/pyvdcapi.git
cd pyvdcapi

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install protobuf pyyaml zeroconf

# Verify installation
python -c "from pyvdcapi import VdcHost; print('✅ pyvdcapi installed!')"
```

### 2. Run First Example

```bash
cd examples/
python 01_create_clean_vdc_host.py
```

Follow the prompts:
- Name: Press Enter (uses default "vDC Test Server")
- Port: Press Enter (uses 8444)
- Persistence file: Press Enter (example_announced_config.yaml)
- Use Avahi: Type `N` and press Enter

You should see:
```
Created vDC host: vDC Test Server
  dSUID: [your unique ID]
  Port: 8444
Starting host and announcing service...
Host is running and discoverable via mDNS/DNS-SD.
Press Ctrl+C to stop.
```

Press Ctrl+C to stop. ✅ **Success!** Your setup works.

---

## Core Concepts (10 minutes)

### The Three Entities

Think of it like a filing system:

```
VdcHost (The Cabinet)
  └── Vdc (A Drawer for similar devices)
       └── VdSD (Individual Device File)
```

**VdcHost** = Server that vdSM connects to  
**Vdc** = Collection of related devices (e.g., "All Hue Lights")  
**VdSD** = Individual device (e.g., "Living Room Light")

### The Essential Pattern

Every pyvdcapi program follows this pattern:

```python
import asyncio
from pyvdcapi.entities import VdcHost
from pyvdcapi.core.constants import DSGroup, DSChannelType

async def main():
    # 1. Create host (the server)
    host = VdcHost(
        name="My Smart Home",
        port=8444,
        mac_address="AA:BB:CC:DD:EE:FF",
        persistence_file="config.yaml"
    )
    
    # 2. Create vDC (device collection)
    lights = host.create_vdc(
        name="Light Controller",
        model="LightVDC v1.0"
    )
    
    # 3. Create device
    living_room = lights.create_vdsd(
        name="Living Room Light",
        model="Dimmer",
        primary_group=DSGroup.YELLOW  # Yellow = Lights!
    )
    
    # 4. Add output channel
    brightness = living_room.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0
    )
    
    # 5. Register hardware callback
    # IMPORTANT: Callback receives TWO parameters!
    def control_hardware(channel_type, value):
        print(f"Set hardware channel {channel_type} to {value}%")
        # your_hardware.set_brightness(value)
    
    brightness.subscribe(control_hardware)
    
    # 6. Start the server
    await host.start()
    
    # Keep running
    print("Server running... Press Ctrl+C to stop")
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await host.stop()

# Run it!
if __name__ == "__main__":
    asyncio.run(main())
```

### Critical Rules

❌ **DON'T:**
- Use `DSGroup.LIGHT` (doesn't exist)
- Write callbacks with 1 parameter: `def callback(value)`
- Call methods that don't exist (check docs!)
- Forget `await` on async functions

✅ **DO:**
- Use `DSGroup.YELLOW` (value=1) for lights
- Write callbacks with 2 parameters: `def callback(channel_type, value)`
- Check [API_REFERENCE.md](API_REFERENCE.md) for method signatures
- Use `await` with `start()`, `stop()`, etc.

---

## Study These Examples (10 minutes)

### Example 1: Simple Host (Minimal)

```bash
cd examples/
python 01_create_clean_vdc_host.py
```

**What it shows:** Creating and starting a basic vDC host

### Example 2: Service Announcement (Discovery)

```bash
python service_announcement_demo.py
```

**What it shows:** How mDNS/DNS-SD auto-discovery works

### Example 3: Real Device (Motion Light)

```bash
python motion_light_device.py
```

**What it shows:** Complete device with sensor, button, and output

### Example 4: Protocol Testing

```bash
# Terminal 1: Start simulator
python vdsm_simulator.py

# Terminal 2: Run demo
python demo_with_simulator.py
```

**What it shows:** Full message exchange simulation

---

## Your First Code Change (5 minutes)

Let's create a simple RGB light device:

```python
# File: my_rgb_light.py

import asyncio
from pyvdcapi.entities import VdcHost
from pyvdcapi.core.constants import DSGroup, DSChannelType

async def main():
    # Create host
    host = VdcHost(
        name="RGB Light Demo",
        port=8444,
        persistence_file="rgb_config.yaml"
    )
    
    # Create vDC
    vdc = host.create_vdc(
        name="Smart Lights",
        model="RGB Controller"
    )
    
    # Create RGB device
    rgb = vdc.create_vdsd(
        name="Desk Lamp",
        model="RGB LED Strip",
        primary_group=DSGroup.YELLOW
    )
    
    # Add THREE channels for full color
    brightness = rgb.add_output_channel(
        channel_type=DSChannelType.BRIGHTNESS,
        min_value=0.0,
        max_value=100.0
    )
    
    hue = rgb.add_output_channel(
        channel_type=DSChannelType.HUE,
        min_value=0.0,
        max_value=360.0
    )
    
    saturation = rgb.add_output_channel(
        channel_type=DSChannelType.SATURATION,
        min_value=0.0,
        max_value=100.0
    )
    
    # Hardware callback
    def control_rgb(channel_type, value):
        if channel_type == DSChannelType.BRIGHTNESS:
            print(f"🔆 Brightness: {value}%")
        elif channel_type == DSChannelType.HUE:
            print(f"🎨 Hue: {value}°")
        elif channel_type == DSChannelType.SATURATION:
            print(f"💧 Saturation: {value}%")
    
    # Subscribe all channels to same callback
    brightness.subscribe(control_rgb)
    hue.subscribe(control_rgb)
    saturation.subscribe(control_rgb)
    
    # Test it!
    print("Testing RGB light...")
    brightness.set_value(100.0)  # Full brightness
    hue.set_value(0.0)           # Red
    saturation.set_value(100.0)  # Full saturation
    
    # Start server
    await host.start()
    print("RGB light server running!")
    print("Press Ctrl+C to stop")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await host.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

Save and run:
```bash
python my_rgb_light.py
```

You should see:
```
Testing RGB light...
🔆 Brightness: 100.0%
🎨 Hue: 0.0°
💧 Saturation: 100.0%
RGB light server running!
Press Ctrl+C to stop
```

**Congratulations! You just created your first device!** 🎉

---

## Common Tasks

### Adding a Button

```python
button = device.add_button(
    name="Power Button",
    button_type=0,  # Single press
    element=0       # First button
)

# Simulate button press
button.press()
```

### Adding a Sensor

```python
temp_sensor = device.add_sensor(
    name="Room Temperature",
    sensor_type="temperature",
    unit="°C",
    min_value=-40.0,
    max_value=125.0
)

# Update sensor value
temp_sensor.update_value(22.5)
```

### Configuring a Scene

```python
# Save scene 5 with specific values
device.set_scene(
    scene_number=5,
    channel_values={
        DSChannelType.BRIGHTNESS: 75.0,
        DSChannelType.HUE: 180.0,
        DSChannelType.SATURATION: 100.0
    },
    effect=DSSceneEffect.SMOOTH
)

# Later, recall the scene
await device.call_scene(5)
```

---

## Debugging Tips

### Enable Debug Logging

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,  # Change to INFO or ERROR to reduce noise
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
```

### Check What's Persisted

```bash
# Your config is saved in YAML
cat config.yaml

# Backup is in .bak file
cat config.yaml.bak
```

### Test Protocol Messages

```python
# See raw protobuf messages
import logging
logging.getLogger('pyvdcapi.network').setLevel(logging.DEBUG)

# Run your code - you'll see all messages logged
```

---

## Next Steps

### Learn More

1. **Read the API Reference**
   - Open [API_REFERENCE.md](API_REFERENCE.md)
   - Follow the examples
   - Try modifying them

2. **Study Real Examples**
   - `examples/motion_light_device.py` - Good pattern
   - `examples/device_configuration.py` - Configuration patterns
   - `examples/vdsm_simulator.py` - Protocol details

3. **Read the Spec**
   - `Documentation/vdc-API/01-Basics.md` - Start here
   - `Documentation/vdc-API/04-vdc-host-session.md` - Session management
   - `Documentation/vdc-API/07-Device-and_vDC_Operation_Methods_and_Notifications.md` - Operations

### Contribute

Check [ISSUES.md](ISSUES.md) for tasks:

**Good First Issues:**
- Add docstrings to internal methods
- Create more examples
- Write pytest tests
- Document VdSD.configure() method

**Your First PR:**
1. Pick an issue from ISSUES.md
2. Create a branch: `git checkout -b fix-issue-xyz`
3. Make your changes
4. Test thoroughly
5. Submit PR with clear description

---

## Need Help?

### Documentation
- **Quick question?** Check [SUMMARY.md](SUMMARY.md)
- **API question?** Check [API_REFERENCE.md](API_REFERENCE.md)
- **Design question?** Check [ARCHITECTURE.md](ARCHITECTURE.md)
- **Bug or issue?** Check [ISSUES.md](ISSUES.md)

### Code Examples
- **Basic usage:** examples/01_create_clean_vdc_host.py
- **Real device:** examples/motion_light_device.py
- **Protocol test:** examples/vdsm_simulator.py

### Specification
- **vDC API spec:** Documentation/vdc-API/
- **digitalSTROM basics:** Documentation/ds-basics.pdf

---

## Cheat Sheet

### Essential Constants

```python
# Device Groups (Colors)
DSGroup.YELLOW = 1   # Lights (NOT .LIGHT!)
DSGroup.GRAY = 2     # Blinds/Shades
DSGroup.BLUE = 3     # Heating
DSGroup.CYAN = 4     # Audio

# Channel Types
DSChannelType.BRIGHTNESS = 1
DSChannelType.HUE = 2
DSChannelType.SATURATION = 3
DSChannelType.COLOR_TEMP = 4
DSChannelType.POSITION = 11
DSChannelType.ANGLE = 12

# Scene Effects
DSSceneEffect.NONE = 0
DSSceneEffect.SMOOTH = 1
DSSceneEffect.SLOW = 2
DSSceneEffect.VERY_SLOW = 3
DSSceneEffect.ALERT = 4
```

### Quick Commands

```bash
# Run examples
cd examples/
python 01_create_clean_vdc_host.py

# Install dependencies
pip install protobuf pyyaml zeroconf

# Check config file
cat config.yaml

# Enable debug logging
export LOG_LEVEL=DEBUG  # Linux/Mac
set LOG_LEVEL=DEBUG     # Windows
```

---

## You're Ready! 🚀

You now know enough to:
- ✅ Create a vDC host
- ✅ Add devices with outputs
- ✅ Register hardware callbacks
- ✅ Use buttons and sensors
- ✅ Configure scenes
- ✅ Debug issues

**Next:** Pick an example, modify it, and make it your own!

**Remember:**
- Study the examples folder
- Check ISSUES.md for contribution ideas
- Read docstrings in the code
- Test your changes

**Welcome to the team!** Happy coding! 💻

---

*Last Updated: 2026-02-09*  
*Questions? Check SUMMARY.md or DOCUMENTATION_REVIEW.md*
