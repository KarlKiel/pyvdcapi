# (full file with announce_to_vdsm signature and body updated)
"""
Vdc - Virtual Device Connector.

A vDC (virtual device connector) represents a collection of virtual devices
(vdSDs) that share common characteristics, typically from the same:
- Technology (e.g., Zigbee, Z-Wave, KNX)
- Manufacturer (e.g., Philips Hue, IKEA TRÅDFRI)
- Physical gateway/bridge (e.g., one Hue bridge = one vDC)

Architecture Context:
┌─────────────────────────────────────────────────────────┐
│ VdcHost                                                 │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Vdc (e.g., "Philips Hue vDC")                       │ │
│ │ ┌─────────┐  ┌─────────┐  ┌─────────┐             │ │
│ │ │ VdSD 1  │  │ VdSD 2  │  │ VdSD N  │             │ │
│ │ │ (Light) │  │ (Light) │  │ (Sensor)│             │ │
│ │ └─────────┘  └─────────┘  └─────────┘             │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘

Responsibilities:
1. Device Management:
   - Create/remove virtual devices (vdSDs)
   - Maintain device inventory
   - Handle device announcements to vdSM

2. Property Management:
   - vDC-specific properties (implementationId, zoneID, capabilities)
   - Route property queries to child vdSDs
   - Persist vDC configuration

3. Device Discovery:
   - Implement device scanning/discovery
   - Announce new devices to vdSM
   - Handle device removal notifications

4. Communication Bridge:
   - Forward vdSM commands to devices
   - Forward device events to vdSM
   - Manage device state synchronization

Lifecycle:
1. Creation: Host creates vDC with initial properties
2. Device Addition: vdSDs are created and announced
3. Operation: Routes messages, manages devices
4. Removal: Cleanup and persist final state

Example Use Cases:
- Philips Hue vDC: Manages all lights from one Hue bridge
- Thermostat vDC: Manages heating devices from one manufacturer
- GPIO vDC: Manages all GPIO-connected devices on one board

Usage:
```python
# Create vDC for a Hue bridge
hue_vdc = host.create_vdc(
    name="Philips Hue Bridge",
    model="vDC Hue v1.0",
    vendor="Philips"
)

# Add devices to the vDC
living_room_light = hue_vdc.create_vdsd(
    name="Living Room Light",
    model="Hue White",
    primary_group=DSGroup.YELLOW,
    output_function=DSOutputFunction.DIMMER
)

bedroom_light = hue_vdc.create_vdsd(
    name="Bedroom Light",
    model="Hue White and Color",
    primary_group=DSGroup.YELLOW,
    output_function=DSOutputFunction.FULL_COLOR
)

# vDC now manages these devices and handles their communication
``` 
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from pyvdcapi.network.genericVDC_pb2 import Message, VDC_SEND_ANNOUNCE_VDC

from ..core.dsuid import DSUIDGenerator, DSUIDNamespace
from ..properties.common import CommonProperties
from ..properties.vdc_props import VdcProperties
from ..properties.property_tree import PropertyTree
from ..persistence.yaml_store import YAMLPersistence

logger = logging.getLogger(__name__)


class Vdc:
    """
    Virtual Device Connector - manages a collection of related devices.
    
    A Vdc acts as a bridge between the vDC API (vdSM side) and
    actual devices (physical or virtual). It:
    
    - Maintains a collection of vdSDs (virtual devices)
    - Routes property queries between vdSM and devices
    - Handles device announcements and removal
    - Persists vDC and device configuration
    - Manages vDC-specific capabilities
    
    Properties:
    The vDC has two sets of properties:
    1. Common properties (inherited from CommonProperties)
       - dSUID, name, model, type, etc.
    2. vDC-specific properties (from VdcProperties)
       - implementationId, zoneID, capabilities
    ...
    (rest of file unchanged up to announce_to_vdsm)
    """

    ...
    def announce_to_vdsm(self) -> Message:
        """
        Create vDC announcement message for vdSM.

        When vdSM connects or requests device discovery, the vDC must
        announce itself. The announcement includes:
        - vDC dSUID (identification)
        - vDC properties (name, model, capabilities)

        Returns:
            Message with vdc_SendAnnounceVdc

        This is typically followed by device announcements (announce_devices).

        NOTE: Announcements are notifications and MUST NOT contain any
        message_id information in the envelope. The announce_to_vdsm
        method's signature intentionally does not accept or set a
        message_id.
        """
        message = Message()
        message.type = VDC_SEND_ANNOUNCE_VDC

        # Intentionally do NOT set message.message_id. Announce messages
        # are notifications and must never include message_id information.

        # Create announcement with vDC properties
        announce = message.vdc_send_announce_vdc
        announce.dSUID = self.dsuid

        # Add vDC properties to announcement
        # Note: Actual field structure depends on protobuf definition
        # announce.properties.CopyFrom(self.get_properties(None))

        logger.debug(f"Created vDC announcement for {self.dsuid}")

        return message

    def announce_devices(self) -> List[Message]:
        """
        Create device announcement messages for all vdSDs.

        After announcing the vDC, we must announce each device.
        Returns a list of announcement messages (one per device).

        Returns:
            List of Messages with vdc_SendAnnounceDevice

        The vdSM processes these to build its device inventory.
        """
        announcements = []

        for vdsd in self._vdsds.values():
            message = vdsd.announce_to_vdsm()
            announcements.append(message)

        logger.debug(
            f"Created {len(announcements)} device announcements for vDC {self.dsuid}"
        )

        return announcements

    # rest of file unchanged
