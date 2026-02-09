"""
pyvdcapi - Python implementation of digitalSTROM vDC API

A complete, spec-compliant implementation of the digitalSTROM vDC API that enables
custom devices and gateways to integrate with the digitalSTROM ecosystem.

Core Concepts:
  VdcHost: Top-level container, manages TCP server and vDCs
  Vdc: Virtual Device Connector, manages a collection of related devices
  VdSD: Virtual Smart Device, individual controllable/monitorable device
  
Example:
  from pyvdcapi import VdcHost
  
  host = VdcHost(name="My vDC", port=8444)
  vdc = host.create_vdc(name="Lights")
  light = vdc.create_vdsd(name="Living Room", primary_group=1)
  
  await host.start()
"""

__version__ = "1.0.0"
__author__ = "KarlKiel"

from .entities.vdc_host import VdcHost
from .entities.vdc import Vdc
from .entities.vdsd import VdSD

__all__ = ["VdcHost", "Vdc", "VdSD"]
