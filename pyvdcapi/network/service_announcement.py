"""
Service announcement module for vDC host discovery.

This module provides mDNS/DNS-SD service announcement using either:
- zeroconf (cross-platform Python implementation)
- Avahi (Linux native daemon)

The vDC host announces itself as _ds-vdc._tcp to allow vdSMs to discover it automatically.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from typing import List, Optional

logger = logging.getLogger(__name__)


class ServiceAnnouncer:
    """
    Announces vDC host service via mDNS/DNS-SD for automatic discovery.

    The vDC host is announced as:
    - Service Type: _ds-vdc._tcp
    - Service Name: "digitalSTROM vDC host on <hostname>"
    - Port: The port the TCP server is listening on

    Usage (async):
        announcer = ServiceAnnouncer(port=8444, dsuid="my-dsuid", host_name="my-vdc-host")
        await announcer.start()
        ...
        await announcer.stop()

    Usage (sync convenience):
        with ServiceAnnouncer(port=8444, dsuid="my-dsuid") as announcer:
            ...
    Note: If using sync context manager from inside an already-running asyncio event loop,
    an exception will be raised: prefer "async with" in that case.
    """

    def __init__(
        self,
        port: int,
        dsuid: str,
        host_name: Optional[str] = None,
        use_avahi: bool = False,
    ):
        """
        Initialize service announcer.

        Args:
            port: TCP port the vDC host is listening on
            dsuid: The dSUID of the vDC host (required for TXT records)
            host_name: Optional custom host name (defaults to system hostname)
            use_avahi: If True, use Avahi daemon (Linux). If False, use zeroconf library
        """
        self.port = port
        self.dsuid = dsuid
        self.host_name = host_name or socket.gethostname()
        self.use_avahi = use_avahi

        self._service_type = "_ds-vdc._tcp"
        self._service_name = f"digitalSTROM vDC host on {self.host_name}"

        # For zeroconf implementation
        self._zeroconf = None
        self._service_info = None

        # For Avahi implementation
        self._avahi_service_file: Optional[str] = None

        self._running = False

    # -----------------------
    # Public start/stop API
    # -----------------------
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
                # Avahi implementation is synchronous by nature
                result = self._start_avahi()
                return result
            else:
                return await self._start_zeroconf_async()
        except Exception as e:
            logger.error("Failed to start service announcement: %s", e, exc_info=True)
            return False

    async def stop(self) -> None:
        """Stop announcing the vDC host service."""
        if not self._running:
            return

        try:
            if self.use_avahi:
                self._stop_avahi()
            else:
                await self._stop_zeroconf_async()
        except Exception as e:
            logger.error("Error stopping service announcement: %s", e)
        finally:
            self._running = False

    # Synchronous convenience wrappers
    def start_sync(self) -> bool:
        """
        Synchronous wrapper for start(). Useful when not running inside an event loop.

        If an event loop is already running, raises RuntimeError and the user should use
        the async API instead (await start()) or use "async with".
        """
        try:
            loop = asyncio.get_running_loop()
            # If we reach here, an event loop is running
            raise RuntimeError(
                "An asyncio event loop is already running. Use await start() or use the async context manager."
            )
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            return asyncio.run(self.start())

    def stop_sync(self) -> None:
        """
        Synchronous wrapper for stop(). Useful when not running inside an event loop.
        """
        try:
            loop = asyncio.get_running_loop()
            # If we reach here, an event loop is running
            raise RuntimeError(
                "An asyncio event loop is already running. Use await stop() or use the async context manager."
            )
        except RuntimeError:
            asyncio.run(self.stop())

    # -----------------------
    # Async zeroconf methods
    # -----------------------
    async def _start_zeroconf_async(self) -> bool:
        """Start announcement using zeroconf library (async version)."""
        try:
            from zeroconf import ServiceInfo
            from zeroconf.asyncio import AsyncZeroconf
        except ImportError:
            logger.error(
                "zeroconf library not installed. Install with: pip install zeroconf"
            )
            return False

        try:
            addresses = self._get_local_addresses()
            if not addresses:
                logger.error("No network addresses found for service announcement")
                return False

            # Type must include .local. suffix for mDNS
            service_type = f"{self._service_type}.local."

            # Create fully-qualified service name: "<instance>.<service_type>"
            service_name = f"{self._service_name}.{service_type}"

            # Server name must be a valid DNS name ending with .local. Use lowercase for Avahi compatibility.
            server_name = f"{self.host_name.lower()}.local."

            logger.info("Creating mDNS service: type=%s, name=%s, server=%s, port=%d",
                        service_type, service_name, server_name, self.port)
            logger.debug("Addresses: %s", [".".join(str(b) for b in addr) for addr in addresses])

            # Prepare TXT records.
            # Ensure the TXT record contains the requested keys:
            # - "service protocol": "ipv4"
            # - "dSUID": <dsuid>
            # Keep lowercase 'dsuid' too for compatibility with some resolvers.
            txt_records = {
                "service protocol": "ipv4",
                "dSUID": self.dsuid,
                "dsuid": self.dsuid,
            }
            logger.info("Prepared TXT records for service announcement: %s", txt_records)

            self._service_info = ServiceInfo(
                type_=service_type,
                name=service_name,
                port=self.port,
                addresses=addresses,
                properties=txt_records,
                server=server_name,
            )

            logger.debug("Creating AsyncZeroconf instance")
            self._zeroconf = AsyncZeroconf()

            logger.debug("Registering service with AsyncZeroconf: %s", self._service_info)
            await self._zeroconf.async_register_service(self._service_info)
            logger.info("Started mDNS service announcement: %s on port %d", self._service_name, self.port)

            self._running = True
            return True

        except Exception as e:
            logger.error("Failed to start zeroconf announcement: %s: %s", type(e).__name__, e, exc_info=True)
            if self._zeroconf:
                try:
                    await self._zeroconf.async_close()
                except Exception:
                    pass
                self._zeroconf = None
            return False

    async def _stop_zeroconf_async(self) -> None:
        """Stop zeroconf announcement (async version)."""
        if self._zeroconf and self._service_info:
            try:
                await self._zeroconf.async_unregister_service(self._service_info)
                await self._zeroconf.async_close()
                logger.info("Unregistered mDNS service")
            except Exception as e:
                logger.error("Error unregistering service: %s", e)
            finally:
                self._zeroconf = None
                self._service_info = None

    # -----------------------
    # Avahi methods
    # -----------------------
    def _start_avahi(self) -> bool:
        """Start announcement using Avahi daemon."""
        import os

        # Check if Avahi daemon is available
        if not os.path.exists("/etc/avahi/services"):
            logger.error(
                "Avahi daemon not found. /etc/avahi/services does not exist. "
                "Install avahi-daemon or use zeroconf mode instead."
            )
            return False

        # Create Avahi service file with a single TXT record for dSUID.
        # Follow the exact XML structure used in Documentation/service.txt
        # Use escaped wildcard '\%h' in the name to match the documented example.
        service_xml = (
            "<?xml version=\"1.0\" standalone='no'?>\n"
            "<!DOCTYPE service-group SYSTEM \"avahi-service.dtd\">\n"
            "<service-group>\n"
            f"<name replace-wildcards=\"yes\">{self._service_name} on \\%h</name>\n"
            "<service protocol=\"ipv4\">\n"
            f"<type>{self._service_type}</type>\n"
            f"<port>{self.port}</port>\n"
            f"<txt-record>dSUID={self.dsuid}</txt-record>\n"
            "</service>\n"
            "</service-group>\n"
        )

        service_file = f"/etc/avahi/services/ds-vdc-{self.port}.service"

        try:
            with open(service_file, "w") as f:
                f.write(service_xml)

            self._avahi_service_file = service_file
            self._running = True

            logger.info(
                "Created Avahi service file: %s. Avahi daemon will announce the service automatically.",
                service_file,
            )
            return True

        except PermissionError:
            logger.error(
                "Permission denied writing to %s. Avahi service announcement requires root privileges. Consider using zeroconf mode instead (use_avahi=False).",
                service_file,
            )
            return False
        except Exception as e:
            logger.error("Failed to create Avahi service file: %s", e)
            return False

    def _stop_avahi(self) -> None:
        """Stop Avahi announcement by removing service file."""
        import os

        if self._avahi_service_file and os.path.exists(self._avahi_service_file):
            try:
                os.remove(self._avahi_service_file)
                logger.info("Removed Avahi service file: %s", self._avahi_service_file)
            except Exception as e:
                logger.error("Error removing Avahi service file: %s", e)
            finally:
                self._avahi_service_file = None

    # -----------------------
    # Utilities
    # -----------------------
    def _get_local_addresses(self) -> List[bytes]:
        """
        Get local network addresses for service announcement.

        Returns:
            List of IP addresses as bytes (packed)
        """
        addresses: List[bytes] = []

        try:
            hostname = socket.gethostname()
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)

            for info in addr_info:
                ip_str = info[4][0]
                # Skip localhost
                if ip_str.startswith("127."):
                    continue
                try:
                    ip_obj = ipaddress.IPv4Address(ip_str)
                    addresses.append(ip_obj.packed)
                except Exception:
                    continue

        except Exception as e:
            logger.warning("Error getting network addresses by hostname lookup: %s", e)

        # Fallback: determine the default interface IP used to reach the Internet
        if not addresses:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                # doesn't need to be reachable; used only to determine outbound IP address
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()

                if not local_ip.startswith("127."):
                    ip_obj = ipaddress.IPv4Address(local_ip)
                    addresses.append(ip_obj.packed)
            except Exception:
                logger.debug("Fallback method to discover local address failed", exc_info=True)

        return addresses

    def is_running(self) -> bool:
        """Check if service announcement is active."""
        return self._running

    # -----------------------
    # Context managers
    # -----------------------
    def __enter__(self):
        """
        Synchronous context manager entry. Calls start_sync().

        If an asyncio event loop is already running, this will raise a RuntimeError.
        Use "async with" in that case.
        """
        self.start_sync()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Synchronous context manager exit. Calls stop_sync()."""
        self.stop_sync()
        return False

    async def __aenter__(self):
        """Async context manager entry: await start()."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit: await stop()."""
        await self.stop()
        return False
