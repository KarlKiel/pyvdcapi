"""
Service announcement module for vDC host discovery.

This module provides mDNS/DNS-SD service announcement using either:
- zeroconf (cross-platform Python implementation)
- Avahi (Linux native daemon)

The vDC host announces itself as _ds-vdc._tcp to allow vdSMs to discover it automatically.
"""

import logging
import socket
from typing import Optional

logger = logging.getLogger(__name__)


class ServiceAnnouncer:
    """
    Announces vDC host service via mDNS/DNS-SD for automatic discovery.
    
    The vDC host is announced as:
    - Service Type: _ds-vdc._tcp
    - Service Name: "digitalSTROM vDC host on <hostname>"
    - Port: The port the TCP server is listening on
    
    Usage:
        announcer = ServiceAnnouncer(port=8444, host_name="my-vdc-host")
        announcer.start()
        # ... run vDC host ...
        announcer.stop()
    """
    
    def __init__(
        self,
        port: int,
        host_name: Optional[str] = None,
        use_avahi: bool = False
    ):
        """
        Initialize service announcer.
        
        Args:
            port: TCP port the vDC host is listening on
            host_name: Optional custom host name (defaults to system hostname)
            use_avahi: If True, use Avahi daemon (Linux). If False, use zeroconf library
        """
        self.port = port
        self.host_name = host_name or socket.gethostname()
        self.use_avahi = use_avahi
        
        self._service_type = "_ds-vdc._tcp.local."
        self._service_name = f"digitalSTROM vDC host on {self.host_name}"
        
        # For zeroconf implementation
        self._zeroconf = None
        self._service_info = None
        
        # For Avahi implementation
        self._avahi_service_file = None
        
        self._running = False
        
    async def start(self) -> bool:
        """
        Start announcing the vDC host service.
        
        Returns:
            True if announcement started successfully, False otherwise
        """
        if self._running:
            logger.warning("Service announcement already running")
            return True
            
        try:
            if self.use_avahi:
                return self._start_avahi()
            else:
                return await self._start_zeroconf_async()
        except Exception as e:
            logger.error(f"Failed to start service announcement: {e}", exc_info=True)
            return False
    
    async def stop(self):
        """Stop announcing the vDC host service."""
        if not self._running:
            return
            
        try:
            if self.use_avahi:
                self._stop_avahi()
            else:
                await self._stop_zeroconf_async()
        except Exception as e:
            logger.error(f"Error stopping service announcement: {e}")
        finally:
            self._running = False
    
    async def _start_zeroconf_async(self) -> bool:
        """Start announcement using zeroconf library (async version)."""
        try:
            from zeroconf import ServiceInfo
            from zeroconf.asyncio import AsyncZeroconf
        except ImportError:
            logger.error(
                "zeroconf library not installed. "
                "Install with: pip install zeroconf"
            )
            return False
        
        try:
            # Get local IP address
            addresses = self._get_local_addresses()
            if not addresses:
                logger.error("No network addresses found for service announcement")
                return False
            
            # Create service info
            self._service_info = ServiceInfo(
                type_=self._service_type,
                name=f"{self._service_name}.{self._service_type}",
                port=self.port,
                addresses=addresses,
                properties={},  # No TXT records needed for vDC host
                server=f"{self.host_name}.local."
            )
            
            # Start AsyncZeroconf and register service
            self._zeroconf = AsyncZeroconf()
            await self._zeroconf.async_register_service(self._service_info)
            logger.debug("Registered service with AsyncZeroconf")
            
            self._running = True
            logger.info(
                f"Started mDNS service announcement: {self._service_name} "
                f"on port {self.port}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to start zeroconf announcement: {e}", exc_info=True)
            if self._zeroconf:
                try:
                    await self._zeroconf.async_close()
                except Exception:
                    pass
                self._zeroconf = None
            return False
    
    async def _stop_zeroconf_async(self):
        """Stop zeroconf announcement (async version)."""
        if self._zeroconf and self._service_info:
            try:
                await self._zeroconf.async_unregister_service(self._service_info)
                await self._zeroconf.async_close()
                logger.info("Unregistered mDNS service")
            except Exception as e:
                logger.error(f"Error unregistering service: {e}")
            finally:
                self._zeroconf = None
                self._service_info = None
    
    def _start_avahi(self) -> bool:
        """Start announcement using Avahi daemon."""
        import os
        import tempfile
        
        # Check if Avahi daemon is available
        if not os.path.exists('/etc/avahi/services'):
            logger.error(
                "Avahi daemon not found. /etc/avahi/services does not exist. "
                "Install avahi-daemon or use zeroconf mode instead."
            )
            return False
        
        # Create Avahi service file
        service_xml = f"""<?xml version="1.0" standalone="no"?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">{self._service_name}</name>
  <service protocol="ipv4">
    <type>_ds-vdc._tcp</type>
    <port>{self.port}</port>
  </service>
</service-group>
"""
        
        # Write to /etc/avahi/services (requires root)
        service_file = f'/etc/avahi/services/ds-vdc-{self.port}.service'
        
        try:
            with open(service_file, 'w') as f:
                f.write(service_xml)
            
            self._avahi_service_file = service_file
            self._running = True
            
            logger.info(
                f"Created Avahi service file: {service_file}. "
                f"Avahi daemon will announce the service automatically."
            )
            return True
            
        except PermissionError:
            logger.error(
                f"Permission denied writing to {service_file}. "
                "Avahi service announcement requires root privileges. "
                "Consider using zeroconf mode instead (use_avahi=False)."
            )
            return False
        except Exception as e:
            logger.error(f"Failed to create Avahi service file: {e}")
            return False
    
    def _stop_avahi(self):
        """Stop Avahi announcement by removing service file."""
        import os
        
        if self._avahi_service_file and os.path.exists(self._avahi_service_file):
            try:
                os.remove(self._avahi_service_file)
                logger.info(f"Removed Avahi service file: {self._avahi_service_file}")
            except Exception as e:
                logger.error(f"Error removing Avahi service file: {e}")
            finally:
                self._avahi_service_file = None
    
    def _get_local_addresses(self) -> list:
        """
        Get local network addresses for service announcement.
        
        Returns:
            List of IP addresses as bytes
        """
        import ipaddress
        
        addresses = []
        
        # Get hostname and resolve to IP
        try:
            hostname = socket.gethostname()
            # Get all addresses for this host
            addr_info = socket.getaddrinfo(
                hostname, None, socket.AF_INET, socket.SOCK_STREAM
            )
            
            for info in addr_info:
                ip_str = info[4][0]
                # Skip localhost
                if ip_str.startswith('127.'):
                    continue
                try:
                    ip_obj = ipaddress.IPv4Address(ip_str)
                    addresses.append(ip_obj.packed)
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"Error getting network addresses: {e}")
        
        # Fallback: try to get default route interface address
        if not addresses:
            try:
                # Connect to external address to determine local IP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                
                if not local_ip.startswith('127.'):
                    ip_obj = ipaddress.IPv4Address(local_ip)
                    addresses.append(ip_obj.packed)
            except Exception:
                pass
        
        return addresses
    
    def is_running(self) -> bool:
        """Check if service announcement is active."""
        return self._running
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False
