# Project Setup and Library Integration

## Overview

This guide explains how to integrate pyvdcapi into a Home Assistant custom integration, covering project structure, dependency management, and staying up-to-date with library changes.

## 🚨 Current Status: pyvdcapi Not on PyPI

**Important**: pyvdcapi is not yet published to PyPI or other package repositories. This means you cannot simply add it to `requirements.txt` and have it automatically installed.

## Integration Approaches

### Approach 1: Git Submodule (Recommended for Development)

Use git submodules to include pyvdcapi directly in your integration.

#### Advantages
✅ Always get latest updates with `git submodule update`
✅ Pin to specific commits for stability
✅ Easy to contribute changes back to pyvdcapi
✅ Works well with development workflow

#### Setup Steps

1. **Add pyvdcapi as submodule**:

```bash
cd custom_components/vdc_integration/
git submodule add https://github.com/user/pyvdcapi.git lib/pyvdcapi
git submodule update --init --recursive
```

2. **Update submodule** (get latest changes):

```bash
git submodule update --remote lib/pyvdcapi
```

3. **Pin to specific version** (for stability):

```bash
cd lib/pyvdcapi
git checkout v1.2.3  # or specific commit hash
cd ../..
git add lib/pyvdcapi
git commit -m "Pin pyvdcapi to v1.2.3"
```

#### Project Structure

```
custom_components/
└── vdc_integration/
    ├── __init__.py
    ├── manifest.json
    ├── config_flow.py
    ├── const.py
    ├── coordinator.py
    ├── entity.py
    ├── light.py
    ├── sensor.py
    ├── switch.py
    ├── services.yaml
    ├── strings.json
    ├── translations/
    │   └── en.json
    └── lib/
        └── pyvdcapi/          # ← Git submodule
            ├── pyvdcapi/
            │   ├── __init__.py
            │   ├── entities/
            │   ├── components/
            │   ├── core/
            │   └── ...
            ├── README.md
            └── requirements.txt
```

#### Import in Python

```python
# In your integration files
import sys
from pathlib import Path

# Add pyvdcapi to Python path
PYVDCAPI_PATH = Path(__file__).parent / "lib" / "pyvdcapi"
if str(PYVDCAPI_PATH) not in sys.path:
    sys.path.insert(0, str(PYVDCAPI_PATH))

# Now import pyvdcapi
from pyvdcapi.entities.vdc_host import VdcHost
from pyvdcapi.core.constants import DSGroup, DSChannelType
```

### Approach 2: Local Copy

Copy pyvdcapi source directly into your integration.

#### Advantages
✅ Simple, no git submodule complexity
✅ Complete control over included code
✅ No external dependencies during installation

#### Disadvantages
❌ Manual updates required
❌ Harder to track upstream changes
❌ Potentially stale code

#### Setup Steps

```bash
# Copy pyvdcapi into your integration
cp -r /path/to/pyvdcapi custom_components/vdc_integration/lib/
```

#### Project Structure

```
custom_components/
└── vdc_integration/
    ├── __init__.py
    ├── manifest.json
    └── lib/
        └── pyvdcapi/          # ← Direct copy
            ├── __init__.py
            ├── entities/
            ├── components/
            └── ...
```

### Approach 3: Development Mode (Testing Only)

For local testing and development, install pyvdcapi in development mode.

```bash
# In your Home Assistant venv
cd /path/to/pyvdcapi
pip install -e .
```

**⚠️ Not suitable for distribution** - users would need to manually install pyvdcapi.

## Home Assistant Integration Structure

### Complete Project Layout

```
custom_components/vdc_integration/
├── __init__.py                 # Integration initialization
├── manifest.json              # Integration metadata
├── config_flow.py             # Configuration UI
├── const.py                   # Constants
├── coordinator.py             # Data update coordinator
├── entity.py                  # Base entity classes
├── vdc_manager.py             # VDC host/device manager
├── device_creation.py         # Device creation flows
├── entity_binding.py          # HA entity ↔ vDC binding
├── light.py                   # Light platform
├── sensor.py                  # Sensor platform
├── binary_sensor.py           # Binary sensor platform
├── switch.py                  # Switch platform
├── services.yaml              # Service definitions
├── strings.json               # UI strings
├── translations/
│   ├── en.json               # English translations
│   └── de.json               # German translations (optional)
└── lib/
    └── pyvdcapi/             # pyvdcapi library (submodule or copy)
```

### manifest.json

```json
{
  "domain": "vdc_integration",
  "name": "virtualDC Integration",
  "codeowners": ["@yourusername"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/yourusername/ha-vdc-integration",
  "iot_class": "local_push",
  "issue_tracker": "https://github.com/yourusername/ha-vdc-integration/issues",
  "requirements": [
    "protobuf>=4.21.0",
    "PyYAML>=6.0",
    "zeroconf>=0.131.0"
  ],
  "version": "0.1.0"
}
```

**Key Points**:
- `requirements`: Lists pyvdcapi's dependencies (since pyvdcapi itself isn't on PyPI)
- `config_flow`: true enables UI-based configuration
- `iot_class`: "local_push" indicates local network device with push updates

### const.py

```python
"""Constants for the virtualDC integration."""
from typing import Final

# Integration domain
DOMAIN: Final = "vdc_integration"

# Configuration keys
CONF_VDC_PORT: Final = "vdc_port"
CONF_VDC_NAME: Final = "vdc_name"
CONF_VENDOR_ID: Final = "vendor_id"
CONF_MAC_ADDRESS: Final = "mac_address"

# Defaults
DEFAULT_VDC_PORT: Final = 8440
DEFAULT_VDC_NAME: Final = "Home Assistant vDC"
DEFAULT_VENDOR_ID: Final = "HomeAssistant"

# Data storage keys
DATA_VDC_MANAGER: Final = "vdc_manager"
DATA_COORDINATOR: Final = "coordinator"

# Services
SERVICE_CREATE_DEVICE: Final = "create_device"
SERVICE_DELETE_DEVICE: Final = "delete_device"
SERVICE_CREATE_FROM_TEMPLATE: Final = "create_from_template"

# Platforms
PLATFORMS: Final = ["light", "sensor", "binary_sensor", "switch"]
```

### __init__.py (Basic Structure)

```python
"""The virtualDC integration."""
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    DOMAIN,
    DATA_VDC_MANAGER,
    PLATFORMS,
    CONF_VDC_PORT,
    CONF_VDC_NAME,
    CONF_VENDOR_ID,
    CONF_MAC_ADDRESS,
)

# Add pyvdcapi to path
PYVDCAPI_PATH = Path(__file__).parent / "lib" / "pyvdcapi"
if str(PYVDCAPI_PATH) not in sys.path:
    sys.path.insert(0, str(PYVDCAPI_PATH))

# Import pyvdcapi after adding to path
from pyvdcapi.entities.vdc_host import VdcHost
from pyvdcapi.core.constants import DSGroup

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up virtualDC from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Create VDC manager
    try:
        vdc_manager = await _create_vdc_manager(hass, entry)
    except Exception as err:
        _LOGGER.error("Failed to create VDC manager: %s", err)
        raise ConfigEntryNotReady from err

    # Store manager
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_VDC_MANAGER: vdc_manager,
    }

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_register_services(hass, vdc_manager)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Cleanup VDC manager
        vdc_manager = hass.data[DOMAIN][entry.entry_id][DATA_VDC_MANAGER]
        await vdc_manager.async_shutdown()
        
        # Remove entry data
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _create_vdc_manager(hass: HomeAssistant, entry: ConfigEntry):
    """Create and initialize VDC manager."""
    from .vdc_manager import VdcManager
    
    manager = VdcManager(
        hass=hass,
        port=entry.data[CONF_VDC_PORT],
        name=entry.data[CONF_VDC_NAME],
        vendor_id=entry.data[CONF_VENDOR_ID],
        mac_address=entry.data.get(CONF_MAC_ADDRESS),
    )
    
    await manager.async_initialize()
    
    return manager


async def _async_register_services(hass: HomeAssistant, vdc_manager) -> None:
    """Register integration services."""
    # Services will be registered here
    # See device creation guide for details
    pass
```

## Managing pyvdcapi Updates

### With Git Submodule

```bash
# Update to latest
cd custom_components/vdc_integration
git submodule update --remote lib/pyvdcapi

# Update to specific version
cd lib/pyvdcapi
git fetch --tags
git checkout v1.3.0
cd ../..
git add lib/pyvdcapi
git commit -m "Update pyvdcapi to v1.3.0"
```

### With Local Copy

```bash
# Manually update from source
rm -rf custom_components/vdc_integration/lib/pyvdcapi
cp -r /path/to/pyvdcapi custom_components/vdc_integration/lib/
```

### Testing After Updates

```python
# test_integration.py
"""Test integration after pyvdcapi update."""
import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent / "lib" / "pyvdcapi"))

import pyvdcapi
print(f"pyvdcapi version: {pyvdcapi.__version__}")

# Test basic imports
from pyvdcapi.entities.vdc_host import VdcHost
from pyvdcapi.core.constants import DSGroup, DSChannelType
from pyvdcapi.templates import TemplateManager

print("✓ All imports successful")
```

## Best Practices

### 1. Version Pinning
Always pin pyvdcapi to a specific commit or tag for production:
```bash
cd lib/pyvdcapi
git checkout v1.2.3  # or commit hash
```

### 2. Dependency Isolation
List pyvdcapi's dependencies in your manifest.json to ensure they're installed.

### 3. Update Testing
Before deploying updates:
1. Test in development environment
2. Run integration tests
3. Verify all platforms still work
4. Check for API changes

### 4. Documentation
Document which pyvdcapi version you're using:
```python
# In your integration
PYVDCAPI_VERSION = "1.2.3"  # Update when updating submodule
```

### 5. Path Management
Always add pyvdcapi to path before importing:
```python
# Do this once in __init__.py
PYVDCAPI_PATH = Path(__file__).parent / "lib" / "pyvdcapi"
if str(PYVDCAPI_PATH) not in sys.path:
    sys.path.insert(0, str(PYVDCAPI_PATH))
```

## Future: When pyvdcapi is on PyPI

Once pyvdcapi is published to PyPI, you can simplify:

### manifest.json
```json
{
  "requirements": [
    "pyvdcapi>=1.0.0,<2.0.0"
  ]
}
```

### Python imports
```python
# No path manipulation needed
from pyvdcapi.entities.vdc_host import VdcHost
```

## Next Steps

Now that your project is set up, proceed to:
- **[02_CONFIG_FLOW.md](02_CONFIG_FLOW.md)** - Set up configuration UI
- **[03_SERVICE_ANNOUNCEMENT.md](03_SERVICE_ANNOUNCEMENT.md)** - Add service discovery

## Troubleshooting

### Import Errors
```python
ModuleNotFoundError: No module named 'pyvdcapi'
```
**Solution**: Ensure path is added before import:
```python
sys.path.insert(0, str(Path(__file__).parent / "lib" / "pyvdcapi"))
```

### Submodule Not Found
```bash
fatal: No url found for submodule path 'lib/pyvdcapi'
```
**Solution**: Initialize submodules:
```bash
git submodule update --init --recursive
```

### Stale Library Version
**Solution**: Update submodule:
```bash
git submodule update --remote lib/pyvdcapi
```
