# Installing the vDC Integration in Home Assistant

## Overview

This guide covers installing the vDC integration into your Home Assistant instance, from downloading the files to verifying successful installation.

## Installation Methods

### Method 1: Manual Installation (Recommended for Development)
### Method 2: HACS Installation (When Available)
### Method 3: Docker/Add-on Installation

---

## Method 1: Manual Installation

### Prerequisites

- Home Assistant installed and running (2023.1 or newer)
- SSH or terminal access to your Home Assistant instance
- Git installed (for submodule support)
- Basic command-line knowledge

### Step 1: Access Home Assistant File System

#### Home Assistant OS (via SSH Add-on)

1. Install the **Terminal & SSH** add-on:
   - Go to **Settings** → **Add-ons** → **Add-on Store**
   - Search for "Terminal & SSH"
   - Click **Install**
   - Start the add-on

2. Access terminal via web UI or SSH

#### Home Assistant Container/Core

```bash
# SSH directly to your host machine
ssh user@your-ha-host

# Navigate to Home Assistant config directory
cd /config  # or /home/homeassistant/.homeassistant
```

### Step 2: Create Custom Components Directory

```bash
# Create custom_components if it doesn't exist
mkdir -p custom_components
cd custom_components
```

### Step 3: Download the Integration

#### Option A: Clone from Repository (Recommended)

```bash
# Clone the integration repository
git clone https://github.com/yourusername/ha-vdc-integration.git vdc_integration

cd vdc_integration

# Initialize and update the pyvdcapi submodule
git submodule update --init --recursive
```

#### Option B: Manual Download (Without Git)

```bash
# Create directory
mkdir -p vdc_integration
cd vdc_integration

# Download files manually
# (Download all files from the repository and extract here)

# Download pyvdcapi separately
cd ..
wget https://github.com/yourusername/pyvdcapi/archive/main.zip
unzip main.zip
mv pyvdcapi-main vdc_integration/pyvdcapi
```

### Step 4: Verify File Structure

```bash
# Check structure
ls -la vdc_integration/

# Should show:
# __init__.py
# manifest.json
# config_flow.py
# const.py
# vdc_manager.py
# service_announcer.py
# device_services.py
# entity_binding.py
# template_browser.py
# strings.json
# services.yaml
# pyvdcapi/  (directory with git submodule)
```

### Step 5: Check pyvdcapi Submodule

```bash
cd vdc_integration
ls -la pyvdcapi/

# Should show pyvdcapi library contents:
# pyvdcapi/
# ├── __init__.py
# ├── core/
# ├── components/
# ├── entities/
# ├── templates/
# └── ...
```

### Step 6: Set Correct Permissions

```bash
# Ensure Home Assistant can read the files
cd /config/custom_components
chmod -R 755 vdc_integration
chown -R homeassistant:homeassistant vdc_integration  # If needed
```

### Step 7: Restart Home Assistant

#### Home Assistant OS (UI)

1. Go to **Settings** → **System**
2. Click **Restart** (top right)
3. Confirm restart

#### Home Assistant Container

```bash
docker restart homeassistant
```

#### Home Assistant Core

```bash
sudo systemctl restart home-assistant@homeassistant
```

### Step 8: Verify Installation

#### Check Logs for Errors

```bash
# View logs
tail -f /config/home-assistant.log | grep vdc

# Or via UI: Settings → System → Logs
```

Look for:
```
✅ GOOD: "Setting up vdc_integration component"
❌ BAD: "Error loading custom_components.vdc_integration"
```

#### Check Integration Availability

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration** (bottom right)
3. Search for "vdc" or "Virtual Device Connector"

If you see it, installation successful! ✅

---

## Method 2: HACS Installation (Future)

> **Note**: This method will be available once the integration is published to HACS.

### Prerequisites

- HACS installed in Home Assistant
- GitHub account

### Installation Steps

1. Open HACS:
   - Go to **HACS** in sidebar

2. Add Custom Repository (if not in default HACS):
   - Click **⋮** (three dots) → **Custom repositories**
   - Repository: `https://github.com/yourusername/ha-vdc-integration`
   - Category: **Integration**
   - Click **Add**

3. Install Integration:
   - Search for "Virtual Device Connector"
   - Click **Download**
   - Click **Download** again to confirm
   - Restart Home Assistant

4. Add Integration:
   - **Settings** → **Devices & Services** → **Add Integration**
   - Search for "vdc"

---

## Method 3: Docker/Add-on Installation

### Using Docker Compose

If running Home Assistant via Docker Compose, add volume mount:

```yaml
version: '3'
services:
  homeassistant:
    image: homeassistant/home-assistant:stable
    volumes:
      - /path/to/config:/config
      # Mount the custom component
      - /path/to/ha-vdc-integration:/config/custom_components/vdc_integration:ro
    restart: unless-stopped
```

Then initialize submodules:

```bash
cd /path/to/ha-vdc-integration
git submodule update --init --recursive
docker-compose restart homeassistant
```

---

## Post-Installation Configuration

### Step 1: Add Integration Instance

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Virtual Device Connector" or "vdc"
4. Click on it

### Step 2: Configure Integration

You'll be prompted for:

| Field | Description | Default | Required |
|-------|-------------|---------|----------|
| **vDC Name** | Name for this vDC instance | Home Assistant vDC | Yes |
| **TCP Port** | Port for vDC API server | 8440 | Yes |

**Example Configuration**:
```
vDC Name: Living Room vDC
TCP Port: 8440
```

Click **Submit**.

### Step 3: Verify Service Announcement

Check that the vDC is announcing itself via mDNS:

```bash
# From terminal (Linux/macOS)
avahi-browse -r _ds-vdc._tcp

# Should show:
# + eth0 IPv4 Living Room vDC._ds-vdc._tcp local
#    hostname = [homeassistant.local]
#    address = [192.168.1.100]
#    port = [8440]
#    txt = ["vdchost=Living Room vDC" "vdcid=..." "vdcmodel=..."]
```

### Step 4: Check Integration Status

1. Go to **Settings** → **Devices & Services**
2. Find "Virtual Device Connector"
3. Status should show: **Configured** ✅

---

## Verification Steps

### 1. Check Integration Loaded

**Settings** → **Devices & Services** → Look for "Virtual Device Connector"

### 2. Check Services Available

**Developer Tools** → **Services** → Search for `vdc_integration`

You should see:
- `vdc_integration.create_device_from_template`
- `vdc_integration.create_device_manual`
- `vdc_integration.add_sensor_to_device`

### 3. Test Device Creation

```yaml
# In Developer Tools → Services
service: vdc_integration.create_device_from_template
data:
  template_name: simple_onoff_light
  template_type: deviceType
  device_name: Test Light
```

Click **Call Service**. Check logs for success message.

### 4. Check Network Port

```bash
# Verify port is listening
netstat -tuln | grep 8440

# Or
ss -tuln | grep 8440

# Should show:
# tcp  LISTEN  0.0.0.0:8440
```

### 5. Test from vdSM/DSS

From your digitalSTROM Server:
1. Enable vDC discovery
2. Look for "Living Room vDC" in device list
3. Connection should show as active

---

## Troubleshooting Installation

### Issue: Integration Not Found

**Symptom**: Cannot find "Virtual Device Connector" in Add Integration

**Solutions**:

1. **Check file location**:
   ```bash
   ls -la /config/custom_components/vdc_integration/
   ```
   Must have `manifest.json` and `__init__.py`

2. **Check manifest.json**:
   ```bash
   cat /config/custom_components/vdc_integration/manifest.json
   ```
   Must be valid JSON with `"domain": "vdc_integration"`

3. **Check logs**:
   ```bash
   grep -i "vdc" /config/home-assistant.log
   ```
   Look for import errors

4. **Restart Home Assistant**:
   Full restart, not just quick reload

### Issue: Import Errors

**Symptom**: Log shows `ModuleNotFoundError: No module named 'pyvdcapi'`

**Solutions**:

1. **Verify submodule initialized**:
   ```bash
   cd /config/custom_components/vdc_integration
   ls -la pyvdcapi/
   # Should show library files, not empty
   ```

2. **Initialize submodule**:
   ```bash
   cd /config/custom_components/vdc_integration
   git submodule update --init --recursive
   ```

3. **Check Python path**:
   Verify `__init__.py` has:
   ```python
   pyvdcapi_path = Path(__file__).parent / "pyvdcapi"
   if pyvdcapi_path.exists() and str(pyvdcapi_path) not in sys.path:
       sys.path.insert(0, str(pyvdcapi_path))
   ```

### Issue: Dependency Errors

**Symptom**: `No module named 'zeroconf'` or `No module named 'yaml'`

**Solutions**:

1. **Check manifest requirements**:
   ```json
   "requirements": [
     "pyyaml>=6.0",
     "zeroconf>=0.131.0"
   ]
   ```

2. **Install manually (last resort)**:
   ```bash
   # In Home Assistant venv
   source /srv/homeassistant/bin/activate
   pip install pyyaml zeroconf
   ```

3. **Restart Home Assistant** after installing

### Issue: Port Already in Use

**Symptom**: Log shows `Address already in use` for port 8440

**Solutions**:

1. **Check what's using the port**:
   ```bash
   sudo lsof -i :8440
   ```

2. **Change port in configuration**:
   - Go to integration options
   - Change port to different value (e.g., 8441)
   - Save and reload

3. **Kill conflicting process**:
   ```bash
   # Only if you know what's using it
   sudo kill -9 <PID>
   ```

### Issue: Service Not Announced

**Symptom**: `avahi-browse` doesn't show vDC service

**Solutions**:

1. **Check Zeroconf running**:
   ```bash
   systemctl status avahi-daemon
   # Or
   ps aux | grep avahi
   ```

2. **Check firewall**:
   ```bash
   # Allow mDNS (port 5353 UDP)
   sudo ufw allow 5353/udp
   ```

3. **Check network interface**:
   Service announces on all interfaces. Verify network connectivity.

4. **Check logs**:
   ```bash
   grep -i "zeroconf\|service.*announc" /config/home-assistant.log
   ```

### Issue: Permission Denied

**Symptom**: Log shows permission errors accessing files

**Solutions**:

1. **Fix ownership**:
   ```bash
   sudo chown -R homeassistant:homeassistant /config/custom_components/vdc_integration
   ```

2. **Fix permissions**:
   ```bash
   sudo chmod -R 755 /config/custom_components/vdc_integration
   ```

---

## Updating the Integration

### Update from Git

```bash
cd /config/custom_components/vdc_integration

# Pull latest changes
git pull

# Update submodule
git submodule update --remote --recursive

# Restart Home Assistant
# (via UI or command line)
```

### Update via HACS (Future)

1. **HACS** → **Integrations**
2. Find "Virtual Device Connector"
3. Click **Update** if available
4. Restart Home Assistant

---

## Uninstalling the Integration

### Step 1: Remove Integration Instance

1. **Settings** → **Devices & Services**
2. Find "Virtual Device Connector"
3. Click **⋮** (three dots) → **Delete**
4. Confirm deletion

### Step 2: Remove Files

```bash
# Remove integration directory
rm -rf /config/custom_components/vdc_integration
```

### Step 3: Restart Home Assistant

Full restart to clear all cached modules.

### Step 4: Verify Removal

1. Check **Settings** → **Devices & Services** (should be gone)
2. Check **Developer Tools** → **Services** (vdc_integration services should be gone)
3. Check logs (no vdc-related messages)

---

## Advanced Installation Options

### Install to Custom Path

If you need a custom installation path:

1. **Create symbolic link**:
   ```bash
   ln -s /path/to/ha-vdc-integration /config/custom_components/vdc_integration
   ```

2. **Update configuration.yaml** (if needed):
   ```yaml
   # Usually not needed for custom components
   ```

### Multiple vDC Instances

To run multiple independent vDC instances:

1. Install integration once (files in custom_components)
2. Add integration multiple times via UI with different names/ports:
   - Instance 1: "Kitchen vDC" on port 8440
   - Instance 2: "Bedroom vDC" on port 8441
   - Instance 3: "Garage vDC" on port 8442

Each instance gets unique MAC address and runs independently.

### Docker Volume Mounts

For development with instant file updates:

```yaml
services:
  homeassistant:
    volumes:
      # Development mount (read-write)
      - /path/to/dev/ha-vdc-integration:/config/custom_components/vdc_integration
      # Or production mount (read-only)
      - /path/to/prod/ha-vdc-integration:/config/custom_components/vdc_integration:ro
```

---

## Installation Checklist

Use this checklist to verify complete installation:

- [ ] Files copied to `/config/custom_components/vdc_integration/`
- [ ] `manifest.json` present and valid
- [ ] pyvdcapi submodule initialized (`pyvdcapi/` directory has files)
- [ ] Home Assistant restarted
- [ ] No errors in logs related to vdc_integration
- [ ] Integration appears in **Add Integration** list
- [ ] Integration instance configured (name + port)
- [ ] Service announcement working (avahi-browse shows service)
- [ ] Services available in **Developer Tools** → **Services**
- [ ] Port accessible (netstat/ss shows listening)
- [ ] Test device creation successful

---

## Platform-Specific Notes

### Home Assistant OS (HassOS)

- Use **Terminal & SSH** add-on for file access
- Files go in `/config/custom_components/`
- Git available via add-on store
- Restart via UI: **Settings** → **System** → **Restart**

### Home Assistant Container (Docker)

- Mount custom_components directory as volume
- Restart container: `docker restart homeassistant`
- Access files from host filesystem
- May need to restart container after submodule init

### Home Assistant Core (Python venv)

- Direct filesystem access
- Files in `~/.homeassistant/custom_components/`
- Restart: `systemctl restart home-assistant@homeassistant`
- Can use local Python for testing

### Home Assistant Supervised

- Similar to HassOS but with more host access
- Files in `/usr/share/hassio/homeassistant/custom_components/`
- Can access via SSH directly to host
- Restart via supervisor

---

## Next Steps

After successful installation:

1. **Create your first device**: [04_DEVICE_CREATION_UI.md](04_DEVICE_CREATION_UI.md)
2. **Bind entities**: [06_ENTITY_BINDING.md](06_ENTITY_BINDING.md)
3. **Review complete examples**: [COMPLETE_EXAMPLE.md](COMPLETE_EXAMPLE.md)

---

## Getting Help

### Check Logs

Always start with logs:
```bash
# Real-time log monitoring
tail -f /config/home-assistant.log | grep -i vdc

# Or via UI
Settings → System → Logs → Search "vdc"
```

### Enable Debug Logging

Add to `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.vdc_integration: debug
    pyvdcapi: debug
```

Restart Home Assistant, reproduce issue, check logs.

### Common Log Messages

| Message | Meaning | Action |
|---------|---------|--------|
| "Setting up vdc_integration component" | Setup starting | ✅ Good |
| "vDC integration setup complete" | Setup successful | ✅ Good |
| "ModuleNotFoundError: pyvdcapi" | Submodule missing | Init submodule |
| "Address already in use" | Port conflict | Change port |
| "vDC service registered" | mDNS working | ✅ Good |

### Support Resources

- GitHub Issues: Report bugs and request features
- Documentation: This guide series
- Home Assistant Community: Ask in forums
- pyvdcapi Documentation: Library reference

---

## Security Considerations

### Network Security

- **Firewall**: Open only required ports (8440, 5353)
- **VLANs**: Consider isolating vDC traffic
- **Authentication**: Add if exposing externally (future feature)

### File Permissions

- **Read-only**: Set integration files read-only after installation
- **Ownership**: Ensure `homeassistant` user owns files
- **No world-write**: `chmod 755` maximum, never `777`

### Updates

- **Stay updated**: Regularly pull latest changes
- **Review changes**: Check changelog before updating
- **Backup first**: Always backup before major updates

---

## Performance Tips

### Resource Usage

- **Each integration instance** uses:
  - 1 TCP port
  - Minimal CPU (event-driven)
  - ~10-50MB RAM depending on device count
  - Minimal network (only when devices change)

### Optimization

- **Limit device count**: Start with 10-20 devices
- **Batch operations**: Create multiple devices in one automation
- **Debounce updates**: Avoid rapid state changes
- **Monitor logs**: Watch for excessive updates

---

## Key Takeaways

✅ **Installation is straightforward** - Custom component + git submodule
✅ **Multiple methods available** - Manual, HACS (future), Docker
✅ **Verification is important** - Check logs, services, network
✅ **Troubleshooting is documented** - Common issues have solutions
✅ **Updates are simple** - Git pull + submodule update + restart

**Installation complete? Start creating devices!** → [04_DEVICE_CREATION_UI.md](04_DEVICE_CREATION_UI.md)
