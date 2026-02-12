# Service Announcement for vDC Host Auto-Discovery

The pyvdcapi library supports automatic service discovery using mDNS/DNS-SD (also known as Avahi or Bonjour). This allows vdSMs to automatically find and connect to vDC hosts on the local network without manual configuration.

**Related Documentation:**
- [README.md](README.md) - Complete feature overview
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [TESTING.md](TESTING.md) - Test examples

## Overview

When service announcement is enabled, the vDC host broadcasts its presence on the local network using the mDNS protocol. vdSMs can then discover the host automatically without needing to know its IP address or hostname.

**Service Details:**
- Service Type: `_ds-vdc._tcp`
- Service Name: `digitalSTROM vDC host on <hostname>`
- Port: Configured vDC host port (default: 8444)
- Protocol: IPv4 (IPv6 support planned for future)

## Installation

### Option 1: Zeroconf (Recommended - Cross-Platform)

Install the Python zeroconf library:

```bash
pip install zeroconf
```

This works on all platforms (Linux, macOS, Windows) and requires no system-level configuration.

### Option 2: Avahi (Linux Only)

Install the Avahi daemon:

```bash
# Debian/Ubuntu
sudo apt-get install avahi-daemon

# Fedora/RHEL
sudo dnf install avahi

# Start the service
sudo systemctl start avahi-daemon
sudo systemctl enable avahi-daemon
```

**Note:** Avahi mode requires root privileges to write to `/etc/avahi/services/`.

## Usage

### Enable Service Announcement

When creating a VdcHost, set `announce_service=True`:

```python
from pyvdcapi.entities import VdcHost

# Using zeroconf (recommended)
host = VdcHost(
    name="My Smart Home Hub",
    port=8444,
    announce_service=True  # Enable auto-discovery
)

await host.start()
```

### Use Avahi (Linux Only)

```python
host = VdcHost(
    name="My Smart Home Hub",
    port=8444,
    announce_service=True,
    use_avahi=True  # Use native Avahi daemon
)

await host.start()
```

### Complete Example

```python
import asyncio
from pyvdcapi.entities import VdcHost
from pyvdcapi.core.constants import DSGroup

async def main():
    # Create host with service announcement
    host = VdcHost(
        name="Demo Hub",
        port=8444,
        announce_service=True,
        use_avahi=False  # Use zeroconf
    )
    
    # Create a vDC and add devices
    vdc = host.create_vdc(name="Light Controller", model="Generic vDC")
    device = vdc.create_vdsd(
        name="Living Room Light",
        model="Dimmer",
        primary_group=DSGroup.LIGHT
    )
    
    # Start the host
    await host.start()
    
    print("vDC Host is now discoverable on the network!")
    print("vdSMs can automatically find and connect.")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        await host.stop()

asyncio.run(main())
```

## Discovering vDC Hosts

### From Command Line

**Linux (Avahi):**
```bash
# Browse for vDC hosts
avahi-browse -r _ds-vdc._tcp

# Example output:
# + eth0 IPv4 digitalSTROM vDC host on myhub      _ds-vdc._tcp         local
#    hostname = [myhub.local]
#    address = [192.168.1.100]
#    port = [8444]
```

**macOS/Windows (dns-sd):**
```bash
dns-sd -B _ds-vdc._tcp
```

### From Python (vdSM Implementation)

```python
from zeroconf import Zeroconf, ServiceBrowser, ServiceListener

class VdcHostListener(ServiceListener):
    def add_service(self, zc, type, name):
        info = zc.get_service_info(type, name)
        if info:
            address = info.parsed_addresses()[0]
            port = info.port
            print(f"Found vDC host: {name}")
            print(f"  Address: {address}:{port}")
            # Connect to the host
            # await connect_to_vdc_host(address, port)

zeroconf = Zeroconf()
listener = VdcHostListener()
browser = ServiceBrowser(zeroconf, "_ds-vdc._tcp.local.", listener)

# Keep browser running
try:
    input("Press enter to exit...\n")
finally:
    zeroconf.close()
```

## Implementation Details

### Zeroconf Mode (Default)

When `announce_service=True` and `use_avahi=False`:

1. Creates a `ServiceInfo` object with:
   - Type: `_ds-vdc._tcp.local.`
   - Name: Based on hostname
   - Port: vDC host port
   - Addresses: Local network IP addresses

2. Registers the service with the zeroconf library
3. Service is announced via mDNS
4. Automatically unregistered when host stops

**Advantages:**
- Cross-platform (works on Linux, macOS, Windows)
- No system configuration required
- No root privileges needed
- Pure Python implementation

**Disadvantages:**
- Requires `zeroconf` package installation
- Slightly higher memory usage

### Avahi Mode (Linux Only)

When `announce_service=True` and `use_avahi=True`:

1. Creates an Avahi service file at `/etc/avahi/services/ds-vdc-<port>.service`
2. Avahi daemon automatically picks up the file and announces the service
3. Service file removed when host stops

**Service File Format:**
```xml
<?xml version="1.0" standalone="no"?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">digitalSTROM vDC host on %h</name>
  <service protocol="ipv4">
    <type>_ds-vdc._tcp</type>
    <port>8444</port>
  </service>
</service-group>
```

**Advantages:**
- Native Linux integration
- Lower overhead (uses system daemon)
- Standard Avahi configuration

**Disadvantages:**
- Linux only
- Requires root privileges
- Requires Avahi daemon installed and running
- More complex error handling

## Troubleshooting

### "zeroconf library not installed"

Install the package:
```bash
pip install zeroconf
```

### "Permission denied writing to /etc/avahi/services"

Avahi mode requires root privileges. Either:
1. Run as root: `sudo python my_vdc_host.py`
2. Use zeroconf mode instead: `use_avahi=False`

### "Avahi daemon not found"

Install and start the Avahi daemon:
```bash
sudo apt-get install avahi-daemon
sudo systemctl start avahi-daemon
```

Or use zeroconf mode instead.

### "No network addresses found"

The host cannot determine its local IP address. Check:
1. Network interface is up
2. IP address is assigned
3. Not in airplane/offline mode

### Service Not Discoverable

**Check firewall:**
- mDNS uses UDP port 5353
- Ensure UDP 5353 is allowed in firewall

**Verify announcement:**
```bash
# Linux
avahi-browse -r _ds-vdc._tcp

# macOS/Windows
dns-sd -B _ds-vdc._tcp
```

**Check logs:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

### Network Exposure

Service announcement broadcasts the vDC host presence on the local network. This means:
- Any device on the network can discover the host
- The host IP and port are publicly visible (on local network)
- Authentication is still required for actual connection

### Whitelist Protection

As per vDC specification, vdSMs should support whitelists to avoid connecting to wrong hosts in multi-host environments (e.g., showrooms, development labs).

### Recommendations

1. **Small/Home Installations**: Service announcement is safe and convenient
2. **Large/Multi-Host Environments**: Consider disabling auto-discovery and using manual configuration with whitelists
3. **Production Deployments**: Ensure proper network segmentation and firewall rules

## Performance

### Resource Usage

**Zeroconf mode:**
- Memory: ~2-5 MB additional
- CPU: Minimal (only during startup/shutdown)
- Network: Periodic mDNS announcements (~200 bytes every few seconds)

**Avahi mode:**
- Memory: Negligible (handled by system daemon)
- CPU: None (handled by system daemon)
- Network: Same as zeroconf

### Scalability

Service announcement scales well:
- Supports hundreds of vDC hosts on same network
- mDNS protocol handles collisions automatically
- Name conflicts resolved with automatic renaming

## API Reference

### ServiceAnnouncer Class

```python
class ServiceAnnouncer:
    """Announces vDC host service via mDNS/DNS-SD."""
    
    def __init__(
        self,
        port: int,
        host_name: Optional[str] = None,
        use_avahi: bool = False
    ):
        """
        Args:
            port: TCP port the vDC host is listening on
            host_name: Optional custom host name (defaults to system hostname)
            use_avahi: If True, use Avahi daemon (Linux). If False, use zeroconf
        """
    
    def start(self) -> bool:
        """
        Start announcing the vDC host service.
        
        Returns:
            True if announcement started successfully, False otherwise
        """
    
    def stop(self):
        """Stop announcing the vDC host service."""
    
    def is_running(self) -> bool:
        """Check if service announcement is active."""
```

### VdcHost Parameters

```python
VdcHost(
    name: str,
    port: int = 8444,
    # ... other parameters ...
    announce_service: bool = False,  # Enable service announcement
    use_avahi: bool = False  # Use Avahi instead of zeroconf
)
```

## Examples

See the following example files:
- `examples/service_announcement_demo.py` - Basic service announcement demo
- `examples/demo_with_simulator.py` - Full vDC host with simulator

## Future Enhancements

Planned improvements:
- IPv6 support
- TXT record support for additional metadata
- Service browsing helper utilities
- Automatic reconnection on network changes
- Integration with systemd (Linux)

## References

- [RFC 6762 - Multicast DNS](https://tools.ietf.org/html/rfc6762)
- [RFC 6763 - DNS-Based Service Discovery](https://tools.ietf.org/html/rfc6763)
- [Avahi Documentation](https://www.avahi.org/)
- [Python zeroconf](https://github.com/python-zeroconf/python-zeroconf)
- [vDC API Discovery Documentation](../Documentation/vdc-API/03-Discovery.md)
