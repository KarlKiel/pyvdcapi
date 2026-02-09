"""
Device components for vDC API devices.

This module provides the building blocks for virtual devices (vdSDs):

Inputs (Device → vdSM):
- ButtonInput: User interaction events with API-compliant clickType values
- BinaryInput: Contact closure, motion detection, presence sensors
- Sensor: Continuous value readings (temperature, humidity, power, etc.)

Outputs (vdSM → Device):
- Output: Container for output channels with configuration
- OutputChannel: Individual controllable aspects (brightness, hue, saturation, etc.)

Helpers:
- DSButtonStateMachine: Optional timing-based clickType detection for simple buttons

These components attach to vdSDs and provide:
- State tracking and persistence
- Value change notifications
- Hardware abstraction callbacks
- vDC API property integration

Component Architecture:
┌─────────────────────────────────────────────────────────┐
│ VdSD                                                    │
├─────────────────────────────────────────────────────────┤
│ Inputs:                      Outputs:                   │
│ ┌──────────┐  ┌──────────┐  ┌───────────────────────┐ │
│ │ButtonInp1│  │BinaryIn 1│  │ Output 0              │ │
│ │ (Toggle) │  │ (Motion) │  │  ├─ Brightness Ch.    │ │
│ └──────────┘  └──────────┘  │  ├─ Hue Ch.           │ │
│ ┌──────────┐  ┌──────────┐  │  └─ Saturation Ch.   │ │
│ │ButtonInp2│  │ Sensor 1 │  └───────────────────────┘ │
│ │ (Dimmer) │  │  (Temp)  │                            │
│ └──────────┘  └──────────┘                            │
└─────────────────────────────────────────────────────────┘

Value Flow:
Input Events:    Hardware → Component → VdSD → VdSM
Output Control:  VdSM → VdSD → Output → OutputChannel → Hardware

Each component:
- Manages its own state and configuration
- Provides Observable callbacks for value changes
- Serializes to/from property trees
- Integrates with YAML persistence
"""

from .output import Output
from .output_channel import OutputChannel
from .button_input import ButtonInput
from .button_state_machine import DSButtonStateMachine
from .binary_input import BinaryInput
from .sensor import Sensor
from .actions import ActionManager, StateManager, DevicePropertyManager, ActionParameter

__all__ = [
    "Output",
    "OutputChannel",
    "ButtonInput",
    "DSButtonStateMachine",
    "BinaryInput",
    "Sensor",
    "ActionManager",
    "StateManager",
    "DevicePropertyManager",
    "ActionParameter",
]
