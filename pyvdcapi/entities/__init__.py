"""
Core entity classes for vDC API.

This module contains the main entity classes that form the vDC architecture:

- VdcHost: The top-level container managing the TCP server and all vDCs
- Vdc: Virtual Device Connector managing a collection of related devices
- VdSD: Virtual Device (Smart Device) representing individual devices

Entity Hierarchy:
┌─────────────────────────────────────────────┐
│ VdcHost                                     │
│ - TCP Server (port 8444)                    │
│ - Session Management                        │
│ - YAML Persistence                          │
│ - Common Properties                         │
├─────────────────────────────────────────────┤
│ ┌─────────┐  ┌─────────┐  ┌─────────┐     │
│ │  Vdc 1  │  │  Vdc 2  │  │  Vdc N  │     │
│ │ (Light) │  │(Heating)│  │ (Audio) │     │
│ └─────────┘  └─────────┘  └─────────┘     │
└─────────────────────────────────────────────┘
      │              │              │
      ▼              ▼              ▼
  ┌────────┐    ┌────────┐    ┌────────┐
  │ VdSD 1 │    │ VdSD 3 │    │ VdSD 5 │
  │ VdSD 2 │    │ VdSD 4 │    │ VdSD 6 │
  └────────┘    └────────┘    └────────┘
"""
