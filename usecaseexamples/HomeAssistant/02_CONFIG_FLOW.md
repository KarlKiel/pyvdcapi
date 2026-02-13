# Configuration Flow Implementation

## Overview

This guide explains how to implement the Home Assistant configuration flow for the vDC integration, including user parameter collection, validation, and VdcHost initialization.

## Configuration Parameters

### User-Configurable Parameters

These should be requested during setup:

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `vdc_port` | int | ✅ Yes | 8440 | TCP port for vDC host |
| `vdc_name` | string | ✅ Yes | "Home Assistant vDC" | Human-readable vDC name |
| `announce_service` | bool | ❌ No | true | Enable Zeroconf announcement |

### Hard-Coded/Calculated Parameters

These should NOT be user-configurable:

| Parameter | Value | Reason |
|-----------|-------|--------|
| `mac_address` | Auto-generated | Must be unique and stable per instance |
| `vendor_id` | "HomeAssistant" | Identifies integration vendor |
| `model` | "HA-vDC-Bridge" | Fixed model identifier |
| `model_uid` | "ha-vdc-v1" | Fixed model UID |

### Why This Split?

**User-Configurable**:
- Port: May conflict with other services
- Name: User preference for identification
- Announcement: Some networks don't support mDNS

**Hard-Coded**:
- MAC address: Must be stable across restarts for device identity
- Vendor/Model: Consistency in vDSM identification
- Technical identifiers: Should not be changed by users

## config_flow.py Implementation

```python
"""Config flow for virtualDC integration."""
from __future__ import annotations

import logging
from typing import Any
import uuid

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    DEFAULT_VDC_PORT,
    DEFAULT_VDC_NAME,
    DEFAULT_VENDOR_ID,
    CONF_VDC_PORT,
    CONF_VDC_NAME,
    CONF_VENDOR_ID,
    CONF_MAC_ADDRESS,
    CONF_ANNOUNCE_SERVICE,
)

_LOGGER = logging.getLogger(__name__)


def _generate_stable_mac(hass: HomeAssistant) -> str:
    """
    Generate a stable MAC address for this HA instance.
    
    The MAC is based on the HA instance UUID to ensure:
    - Uniqueness across different HA instances
    - Stability across restarts (same HA = same MAC)
    - Proper formatting for vDC API
    
    Returns:
        MAC address string in format "XX:XX:XX:XX:XX:XX"
    """
    # Use HA instance ID as seed for stable generation
    instance_id = hass.data.get("core.uuid")
    if not instance_id:
        # Fallback: generate and store
        instance_id = str(uuid.uuid4())
        
    # Create stable 6-byte MAC from UUID
    # Use first 12 hex chars from UUID
    hex_str = instance_id.replace("-", "")[:12]
    
    # Format as MAC address
    mac = ":".join(hex_str[i:i+2] for i in range(0, 12, 2))
    
    _LOGGER.debug("Generated stable MAC address: %s", mac)
    return mac.upper()


async def validate_port(hass: HomeAssistant, port: int) -> None:
    """
    Validate that the port is available.
    
    Raises:
        ValueError: If port is invalid or already in use
    """
    if not (1024 <= port <= 65535):
        raise ValueError("Port must be between 1024 and 65535")
    
    # Check if port is already used by another vDC integration instance
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get(CONF_VDC_PORT) == port:
            raise ValueError(f"Port {port} is already used by another vDC integration")


class VdcConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for virtualDC."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate port
                await validate_port(self.hass, user_input[CONF_VDC_PORT])
                
                # Generate stable MAC address (not user-configurable)
                mac_address = _generate_stable_mac(self.hass)
                
                # Create config entry data
                data = {
                    CONF_VDC_PORT: user_input[CONF_VDC_PORT],
                    CONF_VDC_NAME: user_input[CONF_VDC_NAME],
                    CONF_ANNOUNCE_SERVICE: user_input.get(CONF_ANNOUNCE_SERVICE, True),
                    # Hard-coded/calculated values
                    CONF_MAC_ADDRESS: mac_address,
                    CONF_VENDOR_ID: DEFAULT_VENDOR_ID,
                }
                
                # Create unique ID based on MAC to prevent duplicates
                await self.async_set_unique_id(mac_address)
                self._abort_if_unique_id_configured()
                
                # Create the config entry
                return self.async_create_entry(
                    title=user_input[CONF_VDC_NAME],
                    data=data,
                )
                
            except ValueError as err:
                _LOGGER.error("Validation error: %s", err)
                errors["base"] = "invalid_port"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"

        # Show form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_VDC_NAME,
                        default=DEFAULT_VDC_NAME
                    ): cv.string,
                    vol.Required(
                        CONF_VDC_PORT,
                        default=DEFAULT_VDC_PORT
                    ): cv.port,
                    vol.Optional(
                        CONF_ANNOUNCE_SERVICE,
                        default=True
                    ): cv.boolean,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> VdcOptionsFlowHandler:
        """Get the options flow for this handler."""
        return VdcOptionsFlowHandler(config_entry)


class VdcOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for virtualDC integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # Update config entry
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    CONF_VDC_NAME: user_input[CONF_VDC_NAME],
                    CONF_ANNOUNCE_SERVICE: user_input[CONF_ANNOUNCE_SERVICE],
                    # Port cannot be changed after setup (would break connections)
                },
            )
            return self.async_create_entry(title="", data={})

        # Show options form
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_VDC_NAME,
                        default=self.config_entry.data[CONF_VDC_NAME],
                    ): cv.string,
                    vol.Optional(
                        CONF_ANNOUNCE_SERVICE,
                        default=self.config_entry.data.get(CONF_ANNOUNCE_SERVICE, True),
                    ): cv.boolean,
                }
            ),
        )
```

## strings.json

UI strings for the configuration flow:

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Configure virtualDC Integration",
        "description": "Set up a virtual digitalSTROM Controller (vDC) that exposes Home Assistant entities as digitalSTROM devices.",
        "data": {
          "vdc_name": "vDC Name",
          "vdc_port": "TCP Port",
          "announce_service": "Announce via Zeroconf"
        },
        "data_description": {
          "vdc_name": "Human-readable name for this vDC (shown in digitalSTROM Server)",
          "vdc_port": "TCP port for vDC host to listen on (1024-65535)",
          "announce_service": "Enable automatic discovery via mDNS/Zeroconf"
        }
      }
    },
    "error": {
      "invalid_port": "Port is invalid or already in use",
      "cannot_connect": "Failed to start vDC host on specified port",
      "unknown": "Unexpected error occurred"
    },
    "abort": {
      "already_configured": "vDC integration is already configured with this MAC address"
    }
  },
  "options": {
    "step": {
      "init": {
        "title": "virtualDC Options",
        "description": "Update configuration options for the vDC integration.",
        "data": {
          "vdc_name": "vDC Name",
          "announce_service": "Announce via Zeroconf"
        }
      }
    }
  }
}
```

## VDC Manager Initialization

After config flow completes, initialize the VdcHost and Vdc:

### vdc_manager.py

```python
"""VDC Manager for Home Assistant integration."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

# pyvdcapi imports (ensure path is set in __init__.py)
from pyvdcapi.entities.vdc_host import VdcHost
from pyvdcapi.entities.vdc import Vdc
from pyvdcapi.core.constants import DSGroup

_LOGGER = logging.getLogger(__name__)


class VdcManager:
    """Manages VdcHost and devices for Home Assistant integration."""

    def __init__(
        self,
        hass: HomeAssistant,
        port: int,
        name: str,
        vendor_id: str,
        mac_address: str | None = None,
    ) -> None:
        """
        Initialize VDC manager.
        
        Args:
            hass: Home Assistant instance
            port: TCP port for vDC host
            name: Human-readable vDC name
            vendor_id: Vendor identifier
            mac_address: MAC address for vDC host (generated if None)
        """
        self.hass = hass
        self._port = port
        self._name = name
        self._vendor_id = vendor_id
        self._mac_address = mac_address
        
        # pyvdcapi objects
        self._host: VdcHost | None = None
        self._vdc: Vdc | None = None
        
        # Devices
        self._devices: dict[str, any] = {}  # dsuid -> VdSD
        
        _LOGGER.debug(
            "VdcManager initialized: port=%s, name=%s, vendor=%s, mac=%s",
            port, name, vendor_id, mac_address
        )

    async def async_initialize(self) -> None:
        """
        Initialize VdcHost and create default Vdc.
        
        This must be called after __init__ to set up the vDC infrastructure.
        Creates:
        1. VdcHost - The main vDC host listening on TCP port
        2. Vdc - A single vDC container for all devices
        
        Raises:
            Exception: If initialization fails
        """
        try:
            # Create VdcHost
            _LOGGER.info("Creating VdcHost on port %s", self._port)
            
            self._host = VdcHost(
                name=f"{self._name} Host",
                port=self._port,
                mac_address=self._mac_address,
                vendor_id=self._vendor_id,
                persistence_file=None,  # HA manages persistence
            )
            
            # Create a single Vdc for all HA devices
            _LOGGER.info("Creating Vdc: %s", self._name)
            
            self._vdc = self._host.create_vdc(
                name=self._name,
                model="HA-vDC-Bridge",
                vendor="HomeAssistant",
            )
            
            _LOGGER.info(
                "VdC initialized successfully: host_dsuid=%s, vdc_dsuid=%s",
                self._host.dsuid,
                self._vdc.dsuid,
            )
            
        except Exception as err:
            _LOGGER.error("Failed to initialize VdC: %s", err)
            raise

    async def async_shutdown(self) -> None:
        """Shutdown VdcHost and cleanup."""
        if self._host:
            _LOGGER.info("Shutting down VdcHost")
            # Cleanup if needed
            self._host = None
            self._vdc = None
            self._devices.clear()

    @property
    def host(self) -> VdcHost:
        """Get VdcHost instance."""
        if not self._host:
            raise RuntimeError("VdcHost not initialized")
        return self._host

    @property
    def vdc(self) -> Vdc:
        """Get Vdc instance."""
        if not self._vdc:
            raise RuntimeError("Vdc not initialized")
        return self._vdc

    def get_device(self, dsuid: str):
        """Get device by dSUID."""
        return self._devices.get(dsuid)

    def add_device(self, device) -> None:
        """Register a device."""
        self._devices[device.dsuid] = device
        _LOGGER.debug("Device registered: %s (%s)", device.name, device.dsuid)

    def remove_device(self, dsuid: str) -> None:
        """Unregister a device."""
        if dsuid in self._devices:
            device = self._devices.pop(dsuid)
            _LOGGER.debug("Device removed: %s (%s)", device.name, dsuid)
```

## Integration Initialization with VdcManager

Update `__init__.py` to use VdcManager:

```python
"""The virtualDC integration."""
import asyncio
import logging
import sys
from pathlib import Path

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
from .vdc_manager import VdcManager

_LOGGER = logging.getLogger(__name__)

# Add pyvdcapi to path (do this ONCE at module level)
PYVDCAPI_PATH = Path(__file__).parent / "lib" / "pyvdcapi"
if str(PYVDCAPI_PATH) not in sys.path:
    sys.path.insert(0, str(PYVDCAPI_PATH))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up virtualDC from a config entry."""
    _LOGGER.info("Setting up vDC integration: %s", entry.title)
    
    hass.data.setdefault(DOMAIN, {})

    # Create and initialize VDC manager
    try:
        vdc_manager = VdcManager(
            hass=hass,
            port=entry.data[CONF_VDC_PORT],
            name=entry.data[CONF_VDC_NAME],
            vendor_id=entry.data[CONF_VENDOR_ID],
            mac_address=entry.data.get(CONF_MAC_ADDRESS),
        )
        
        # Initialize VdcHost and Vdc
        await vdc_manager.async_initialize()
        
    except Exception as err:
        _LOGGER.error("Failed to initialize VDC manager: %s", err)
        raise ConfigEntryNotReady from err

    # Store manager
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_VDC_MANAGER: vdc_manager,
    }

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("vDC integration setup complete")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading vDC integration: %s", entry.title)
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Cleanup VDC manager
        vdc_manager = hass.data[DOMAIN][entry.entry_id][DATA_VDC_MANAGER]
        await vdc_manager.async_shutdown()
        
        # Remove entry data
        hass.data[DOMAIN].pop(entry.entry_id)
        
        _LOGGER.info("vDC integration unloaded successfully")

    return unload_ok
```

## Configuration Flow Behavior

### First-Time Setup

1. User adds integration via UI
2. Configuration dialog appears
3. User fills in:
   - **vDC Name**: "Living Room vDC"
   - **TCP Port**: 8440
   - **Announce Service**: ✓ (checked)
4. System automatically:
   - Generates stable MAC based on HA instance UUID
   - Sets vendor_id to "HomeAssistant"
5. VdcHost and Vdc are created
6. Integration is ready

### Reconfiguration (Options)

Users can change:
- ✅ vDC Name
- ✅ Announce Service setting

Users CANNOT change:
- ❌ TCP Port (would break connections)
- ❌ MAC Address (would change device identity)
- ❌ Vendor ID (should remain consistent)

## Testing the Config Flow

```python
"""Test config flow."""
import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_PORT

from custom_components.vdc_integration.const import DOMAIN


async def test_config_flow(hass):
    """Test the config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    
    # Submit form
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "vdc_name": "Test vDC",
            "vdc_port": 8440,
            "announce_service": True,
        },
    )
    
    assert result["type"] == "create_entry"
    assert result["title"] == "Test vDC"
    assert result["data"]["vdc_port"] == 8440
    assert "mac_address" in result["data"]
```

## Next Steps

Now that the config flow is set up:
- **[03_SERVICE_ANNOUNCEMENT.md](03_SERVICE_ANNOUNCEMENT.md)** - Add Zeroconf discovery
- **[04_DEVICE_CREATION_UI.md](04_DEVICE_CREATION_UI.md)** - Implement device creation

## Key Takeaways

✅ **User-Configurable**: Port, Name, Announcement setting
✅ **Auto-Generated**: MAC address (stable per HA instance)
✅ **Hard-Coded**: Vendor ID, Model identifiers
✅ **Validation**: Port availability, uniqueness checks
✅ **VdcHost/Vdc**: Created automatically during setup
