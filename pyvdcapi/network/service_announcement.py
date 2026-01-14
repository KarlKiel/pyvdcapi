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
        the async API instead (await start()) or use the async context manager.
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

