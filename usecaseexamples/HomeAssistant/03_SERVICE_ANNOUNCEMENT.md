# Service Announcement with Zeroconf

## Overview

This guide explains how to implement Zeroconf (mDNS) service announcement for automatic discovery by digitalSTROM Server (vdSM).

## Why Zeroconf?

**Zeroconf (not Avahi)** provides:
- ✅ Automatic service discovery on local network
- ✅ Cross-platform support (Windows, macOS, Linux)
- ✅ Python library available (`zeroconf`)
- ✅ Already used by Home Assistant core

**Avahi** is Linux-specific and requires D-Bus, making it unsuitable for cross-platform HA integration.

## Service Announcement Specification

Per vDC API specification (SERVICE_ANNOUNCEMENT.md), vDC hosts announce via mDNS:

```
Service Type: _ds-vdc._tcp.local.
Service Name: <vdcHostDsuid>._ds-vdc._tcp.local.
Port: <TCP port>
TXT Records:
  - vdchost=<vdcHostDsuid>
  - vdcid=<implementationId>
  - vdcmodel=<model>
```

## Implementation

### Dependencies

Add to `manifest.json`:
```json
{
  "requirements": [
    "zeroconf>=0.131.0"
  ]
}
```

### Service Announcer Module

Create `service_announcer.py`:

```python
"""Zeroconf service announcement for vDC host."""
from __future__ import annotations

import logging
import socket
from typing import TYPE_CHECKING

from zeroconf import IPVersion, ServiceInfo, Zeroconf
from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pyvdcapi.entities.vdc_host import VdcHost

_LOGGER = logging.getLogger(__name__)

# vDC service type per specification
SERVICE_TYPE = "_ds-vdc._tcp.local."


class VdcServiceAnnouncer:
    """Announces vDC host via Zeroconf/mDNS."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: VdcHost,
        port: int,
    ) -> None:
        """
        Initialize service announcer.
        
        Args:
            hass: Home Assistant instance
            host: VdcHost to announce
            port: TCP port vDC host listens on
        """
        self.hass = hass
        self._host = host
        self._port = port
        
        self._aiozc: AsyncZeroconf | None = None
        self._service_info: AsyncServiceInfo | None = None
        
        _LOGGER.debug(
            "Service announcer initialized for %s on port %s",
            host.dsuid,
            port,
        )

    async def async_start(self) -> None:
        """Start announcing the vDC service."""
        try:
            # Create AsyncZeroconf instance
            self._aiozc = AsyncZeroconf(ip_version=IPVersion.V4Only)
            
            # Get local IP address
            local_ip = self._get_local_ip()
            
            # Build service name: <vdcHostDsuid>._ds-vdc._tcp.local.
            service_name = f"{self._host.dsuid}.{SERVICE_TYPE}"
            
            # Create TXT records per vDC API specification
            txt_records = {
                "vdchost": self._host.dsuid,
                "vdcid": self._host._vendor_id,  # implementationId
                "vdcmodel": "HA-vDC-Bridge",
            }
            
            _LOGGER.info(
                "Announcing vDC service: %s at %s:%s",
                service_name,
                local_ip,
                self._port,
            )
            
            # Create service info
            self._service_info = AsyncServiceInfo(
                type_=SERVICE_TYPE,
                name=service_name,
                addresses=[socket.inet_aton(local_ip)],
                port=self._port,
                properties=txt_records,
                server=f"{socket.gethostname()}.local.",
            )
            
            # Register service
            await self._aiozc.async_register_service(self._service_info)
            
            _LOGGER.info("vDC service announced successfully")
            
        except Exception as err:
            _LOGGER.error("Failed to announce vDC service: %s", err)
            raise

    async def async_stop(self) -> None:
        """Stop announcing the vDC service."""
        if self._service_info and self._aiozc:
            _LOGGER.info("Unregistering vDC service")
            
            try:
                await self._aiozc.async_unregister_service(self._service_info)
            except Exception as err:
                _LOGGER.error("Error unregistering service: %s", err)
            
            await self._aiozc.async_close()
            
            self._service_info = None
            self._aiozc = None

    def _get_local_ip(self) -> str:
        """
        Get the local IP address to announce.
        
        Returns:
            Local IP address as string
        """
        # Try to get from Home Assistant network info
        try:
            from homeassistant.components import network
            
            adapters = network.async_get_adapters(self.hass)
            if adapters:
                # Get first non-loopback IPv4 address
                for adapter in adapters:
                    for addr in adapter.get("ipv4", []):
                        ip = addr.get("address")
                        if ip and not ip.startswith("127."):
                            return ip
        except Exception as err:
            _LOGGER.debug("Could not get IP from HA network component: %s", err)
        
        # Fallback: detect via socket connection
        try:
            # Create socket to determine which interface would be used
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # Google DNS as reference
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception as err:
            _LOGGER.warning("Could not detect local IP: %s", err)
            return "127.0.0.1"  # Fallback to localhost
```

### Integration with VdcManager

Update `vdc_manager.py` to include service announcement:

```python
"""VDC Manager with service announcement."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from .service_announcer import VdcServiceAnnouncer

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from pyvdcapi.entities.vdc_host import VdcHost
from pyvdcapi.entities.vdc import Vdc

_LOGGER = logging.getLogger(__name__)


class VdcManager:
    """Manages VdcHost and devices with service announcement."""

    def __init__(
        self,
        hass: HomeAssistant,
        port: int,
        name: str,
        vendor_id: str,
        mac_address: str | None = None,
        announce_service: bool = True,
    ) -> None:
        """Initialize VDC manager."""
        self.hass = hass
        self._port = port
        self._name = name
        self._vendor_id = vendor_id
        self._mac_address = mac_address
        self._announce_service = announce_service
        
        # pyvdcapi objects
        self._host: VdcHost | None = None
        self._vdc: Vdc | None = None
        
        # Service announcer
        self._announcer: VdcServiceAnnouncer | None = None
        
        # Devices
        self._devices: dict[str, any] = {}

    async def async_initialize(self) -> None:
        """Initialize VdcHost, Vdc, and start service announcement."""
        try:
            # Create VdcHost
            _LOGGER.info("Creating VdcHost on port %s", self._port)
            
            self._host = VdcHost(
                name=f"{self._name} Host",
                port=self._port,
                mac_address=self._mac_address,
                vendor_id=self._vendor_id,
                persistence_file=None,
            )
            
            # Create Vdc
            _LOGGER.info("Creating Vdc: %s", self._name)
            
            self._vdc = self._host.create_vdc(
                name=self._name,
                model="HA-vDC-Bridge",
                vendor="HomeAssistant",
            )
            
            # Announce vDC via Zeroconf (if enabled)
            if self._announce_service:
                _LOGGER.info("Starting Zeroconf service announcement")
                self._announcer = VdcServiceAnnouncer(
                    hass=self.hass,
                    host=self._host,
                    port=self._port,
                )
                await self._announcer.async_start()
            
            # Announce Vdc to vdSM (when vdSM connects)
            # This happens automatically when vdSM connects via TCP
            # The library handles the announcement protocol
            
            _LOGGER.info("VdC initialized and announced successfully")
            
        except Exception as err:
            _LOGGER.error("Failed to initialize VdC: %s", err)
            raise

    async def async_shutdown(self) -> None:
        """Shutdown VdcHost and stop service announcement."""
        # Stop service announcement
        if self._announcer:
            _LOGGER.info("Stopping service announcement")
            await self._announcer.async_stop()
            self._announcer = None
        
        # Cleanup
        if self._host:
            _LOGGER.info("Shutting down VdcHost")
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

    # ... rest of methods from previous example
```

### Update __init__.py

Pass `announce_service` to VdcManager:

```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up virtualDC from a config entry."""
    # ... previous code ...
    
    try:
        vdc_manager = VdcManager(
            hass=hass,
            port=entry.data[CONF_VDC_PORT],
            name=entry.data[CONF_VDC_NAME],
            vendor_id=entry.data[CONF_VENDOR_ID],
            mac_address=entry.data.get(CONF_MAC_ADDRESS),
            announce_service=entry.data.get(CONF_ANNOUNCE_SERVICE, True),  # ← Add this
        )
        
        await vdc_manager.async_initialize()
        
    # ... rest of setup ...
```

## How Service Discovery Works

### 1. Integration Starts

```
┌─────────────────────────────────────────────┐
│ Home Assistant                              │
│                                             │
│  1. VdcHost created on port 8440           │
│  2. AsyncZeroconf starts                    │
│  3. Service registered:                     │
│     Name: <dsuid>._ds-vdc._tcp.local.      │
│     Port: 8440                              │
│     TXT: vdchost=<dsuid>                   │
│          vdcid=HomeAssistant                │
│          vdcmodel=HA-vDC-Bridge            │
└─────────────────────────────────────────────┘
              ↓
        mDNS Broadcast
              ↓
┌─────────────────────────────────────────────┐
│ Network                                     │
│                                             │
│  • Service advertised on .local domain     │
│  • Discoverable by mDNS clients            │
└─────────────────────────────────────────────┘
```

### 2. vdSM Discovery

```
┌─────────────────────────────────────────────┐
│ digitalSTROM Server (vdSM)                  │
│                                             │
│  1. Scans network for _ds-vdc._tcp         │
│  2. Finds: <dsuid>._ds-vdc._tcp.local.     │
│  3. Reads TXT records                       │
│  4. Connects to port 8440                   │
└─────────────────────────────────────────────┘
              ↓
        TCP Connection
              ↓
┌─────────────────────────────────────────────┐
│ pyvdcapi VdcHost                            │
│                                             │
│  1. Accepts connection                      │
│  2. Sends vDC_SEND_ANNOUNCE_VDC            │
│  3. vdSM learns about Vdc                   │
│  4. Devices can now be announced            │
└─────────────────────────────────────────────┘
```

### 3. Vdc Announcement

The Vdc announcement happens automatically when vdSM connects:

```python
# In pyvdcapi library (automatic):
# When vdSM connects to VdcHost:
# 1. VdcHost accepts connection
# 2. For each Vdc in host:
#    - Send vdc_SendAnnounceVdc message
#    - Include vDC dSUID and properties
# 3. vdSM registers the Vdc
```

## Testing Service Announcement

### Check Service Registration

Use `avahi-browse` (Linux/macOS) or DNS-SD browser:

```bash
# Linux/macOS
avahi-browse -rt _ds-vdc._tcp

# Output should show:
# +   eth0 IPv4 <vdcHostDsuid>           _ds-vdc._tcp         local
#    hostname = [homeassistant.local]
#    address = [192.168.1.100]
#    port = [8440]
#    txt = ["vdchost=..." "vdcid=HomeAssistant" "vdcmodel=HA-vDC-Bridge"]
```

### Test from Python

```python
"""Test service discovery."""
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf


class VdcListener(ServiceListener):
    """Listen for vDC services."""
    
    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        print(f"Found vDC service: {name}")
        print(f"  Address: {info.parsed_addresses()}")
        print(f"  Port: {info.port}")
        print(f"  Properties: {info.properties}")


zc = Zeroconf()
browser = ServiceBrowser(zc, "_ds-vdc._tcp.local.", VdcListener())
input("Press enter to exit...\n")
zc.close()
```

## Troubleshooting

### Service Not Appearing

**Check Zeroconf is running**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Your service announcement code
# Should see debug logs about registration
```

**Firewall issues**:
- Ensure UDP port 5353 (mDNS) is open
- Ensure TCP port 8440 (vDC) is open

**Network interface selection**:
```python
# Force specific interface
from zeroconf import Zeroconf
zc = Zeroconf(interfaces=["192.168.1.100"])
```

### vdSM Not Connecting

1. **Check service is visible**: Use `avahi-browse`
2. **Verify TXT records**: Ensure `vdchost` matches VdcHost dSUID
3. **Test TCP port**: `telnet <ip> 8440`
4. **Check logs**: Look for connection attempts in HA logs

### Multiple Instances

If running multiple HA instances:
- Each must use unique MAC address (auto-generated from HA UUID)
- Each must use different TCP port
- Each will have unique dSUID

## Options Flow Integration

Allow disabling service announcement in options:

```python
class VdcOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for service announcement."""

    async def async_step_init(self, user_input=None):
        """Manage options including service announcement."""
        if user_input is not None:
            # Check if announcement setting changed
            old_announce = self.config_entry.data.get(CONF_ANNOUNCE_SERVICE, True)
            new_announce = user_input[CONF_ANNOUNCE_SERVICE]
            
            if old_announce != new_announce:
                # Restart integration to apply change
                self.hass.config_entries.async_schedule_reload(
                    self.config_entry.entry_id
                )
            
            # ... update config entry ...
```

## Next Steps

Now that service announcement is set up:
- **[04_DEVICE_CREATION_UI.md](04_DEVICE_CREATION_UI.md)** - Implement device creation
- **[06_ENTITY_BINDING.md](06_ENTITY_BINDING.md)** - Bind HA entities to devices

## Key Takeaways

✅ **Use Zeroconf, not Avahi** (cross-platform)
✅ **Service type**: `_ds-vdc._tcp.local.`
✅ **TXT records**: `vdchost`, `vdcid`, `vdcmodel`
✅ **Automatic discovery**: vdSM finds and connects
✅ **Vdc announcement**: Handled by pyvdcapi on connection
✅ **User control**: Can disable via integration options
