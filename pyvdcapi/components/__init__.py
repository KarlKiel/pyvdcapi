"""
Device components for vDC API devices.

This module provides the building blocks for virtual devices (vdSDs):

Inputs (Device → vdSM):
- Button: User interaction events (press, release, long press, double press)
- BinaryInput: Contact closure, motion detection, presence sensors
- Sensor: Continuous value readings (temperature, humidity, power, etc.)

Outputs (vdSM → Device):
- Output: Container for output channels with configuration
- OutputChannel: Individual controllable aspects (brightness, hue, saturation, etc.)

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
│ │ Button 1 │  │BinaryIn 1│  │ Output 0              │ │
│ │ (Toggle) │  │ (Motion) │  │  ├─ Brightness Ch.    │ │
│ └──────────┘  └──────────┘  │  ├─ Hue Ch.           │ │
│ ┌──────────┐  ┌──────────┐  │  └─ Saturation Ch.   │ │
│ │ Button 2 │  │ Sensor 1 │  └───────────────────────┘ │
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
from .button import Button
from .binary_input import BinaryInput
from .sensor import Sensor
from .actions import ActionManager, StateManager, DevicePropertyManager, ActionParameter

__all__ = [
    "Output",
    "OutputChannel",
    "Button",
    "BinaryInput",
    "Sensor",
    "ActionManager",
    "StateManager",
    "DevicePropertyManager",
    "ActionParameter",
]
