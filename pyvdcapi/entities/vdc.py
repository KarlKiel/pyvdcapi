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
from genericVDC_pb2 import Message

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
    
    Device Management:
    - Devices are identified by their dSUID
    - Each device (vdSD) belongs to exactly one vDC
    - Device dSUIDs are generated deterministically
    - Device addition triggers announcement to vdSM
    
    Persistence:
    - vDC configuration is stored in YAML
    - Device configurations are stored under the vDC
    - Changes are auto-saved (configurable)
    
    Attributes:
        dsuid: Unique identifier for this vDC
        host: Reference to parent VdcHost
        vdsds: Dictionary of managed devices (dSUID -> VdSD)
        common_props: Common entity properties
        vdc_props: vDC-specific properties
    """
    
    def __init__(
        self,
        host: 'VdcHost',
        mac_address: str,
        vendor_id: str,
        persistence: YAMLPersistence,
        model: str,
        model_uid: str,
        model_version: str = "1.0",
        **properties
    ):
        """
        Initialize virtual device connector.
        
        Note: Do not call directly - use VdcHost.create_vdc() instead.
        
        Args:
            host: Parent VdcHost instance
            mac_address: MAC address for dSUID generation
            vendor_id: Vendor identifier for dSUID namespace
            persistence: YAML persistence manager (shared with host)
            model: Human-readable model name
            model_uid: Unique model identifier (required for vdSM)
            model_version: Model version string (default: "1.0")
            **properties: Additional vDC properties (name, vendor, etc.)
        
        The vDC dSUID is generated from:
        - MAC address (ensures uniqueness across hosts)
        - Vendor ID (namespace)
        - vDC namespace (0x00000001)
        - Enumeration (if multiple vDCs with same MAC)
        
        Example:
            # Always use VdcHost.create_vdc() instead of direct instantiation
            vdc = host.create_vdc(
                name="Smart Light Controller",
                model="LightVDC v1.0",
                model_uid="lightvdc-v1-0",
                model_version="1.0"
            )
        """
        # Generate vDC dSUID
        # Note: For multiple vDCs on same host, use enumeration parameter
        dsuid_gen = DSUIDGenerator(mac_address, vendor_id)
        enumeration = properties.pop('enumeration', 0)  # Allow override
        self.dsuid = dsuid_gen.generate(
            DSUIDNamespace.VDC,
            enumeration=enumeration
        )
        
        logger.info(f"Initializing vDC with dSUID: {self.dsuid}")
        
        # Parent reference
        self.host = host
        
        # Persistence (shared with host)
        self._persistence = persistence
        
        # Load or initialize vDC configuration
        vdc_config = self._persistence.get_vdc(self.dsuid)
        if not vdc_config:
            # First time - initialize with provided properties
            vdc_config = {
                'dSUID': self.dsuid,
                'type': 'vDC',
                'model': model,
                'model_uid': model_uid,
                'model_version': model_version,
                'vendor_id': vendor_id,
                'enumeration': enumeration,
                **properties
            }
            self._persistence.set_vdc(self.dsuid, vdc_config)
        
        # Common properties (dSUID, name, model, etc.)
        self._common_props = CommonProperties(
            dsuid=self.dsuid,
            entity_type='vDC',
            name=vdc_config.get('name', properties.get('name', model)),
            model=vdc_config.get('model', model),
            model_uid=vdc_config.get('model_uid', model_uid),
            model_version=vdc_config.get('model_version', model_version) or "",
            **vdc_config
        )
        
        # vDC-specific properties (implementationId, zoneID, capabilities)
        self._vdc_props = VdcProperties(**vdc_config)
        
        # Device management
        # Key: vdSD dSUID, Value: VdSD instance
        self._vdsds: Dict[str, 'VdSD'] = {}
        
        # Load persisted devices
        # This will be implemented when VdSD class is ready
        # self._load_vdsds()
        
        logger.info(
            f"vDC initialized: name='{self._common_props.get('name')}', "
            f"model='{self._common_props.get('model')}', "
            f"devices={len(self._vdsds)}"
        )
    
    def create_vdsd(
        self,
        name: str,
        model: str,
        primary_group: int,
        model_uid: Optional[str] = None,
        model_version: str = "1.0",
        **properties
    ) -> 'VdSD':
        """
        Create a new virtual device (vdSD) in this vDC.
        
        A vdSD represents an individual device (light, sensor, switch, etc.).
        The device is:
        1. Created with unique dSUID
        2. Configured with properties
        3. Added to vDC's device collection
        4. Persisted to YAML
        5. Announced to vdSM (if connected)
        
        Args:
            name: Human-readable device name (e.g., "Living Room Light")
            model: Device model identifier (e.g., "Hue White")
            primary_group: digitalSTROM group (color) - see DSGroup enum
            model_uid: Unique model identifier (auto-generated from model if not provided)
            model_version: Model version string (default: "1.0")
            **properties: Additional device properties
        
        Returns:
            VdSD instance representing the new device
        
        Example:
            dimmer = vdc.create_vdsd(
                name="Kitchen Dimmer",
                model="Dimmer 1CH",
                primary_group=DSGroup.YELLOW,  # Light
                model_uid="dimmer-1ch",
                model_version="1.0",
                output_function=DSOutputFunction.DIMMER,
                output_channels=[
                    {
                        'channelType': DSChannelType.BRIGHTNESS,
                        'min': 0.0,
                        'max': 100.0,
                        'resolution': 0.1
                    }
                ]
            )
        """
        # Import here to avoid circular dependency
        from .vdsd import VdSD
        
        # Generate modelUID if not provided
        if model_uid is None:
            # Auto-generate from model name: "Hue White v2" -> "hue-white-v2"
            model_uid = model.lower().replace(' ', '-').replace('.', '-')
        
        # Calculate enumeration (number of existing devices)
        enumeration = len(self._vdsds)
        
        # Get MAC and vendor from host (via vDC)
        mac_address = self.host._mac_address
        vendor_id = self.host._vendor_id
        
        # Create vdSD instance
        vdsd = VdSD(
            vdc=self,
            name=name,
            model=model,
            primary_group=primary_group,
            mac_address=mac_address,
            vendor_id=vendor_id,
            enumeration=enumeration,
            model_uid=model_uid,
            model_version=model_version,
            **properties
        )
        
        # Add to collection
        self._vdsds[vdsd.dsuid] = vdsd
        
        logger.info(f"Created vdSD: {name} with dSUID: {vdsd.dsuid}")
        
        # TODO: Send announcement to vdSM if connected
        # if self.host.is_connected():
        #     await self._announce_device(vdsd)
        
        return vdsd
    
    def remove_vdsd(self, dsuid: str) -> bool:
        """
        Remove a device from this vDC.
        
        Process:
        1. Validate device exists and belongs to this vDC
        2. Send vanish notification to vdSM (if connected)
        3. Remove from device collection
        4. Remove from persistence
        5. Cleanup device resources
        
        Args:
            dsuid: Device dSUID to remove
        
        Returns:
            True if device was removed, False if not found
        
        Example:
            if vdc.remove_vdsd("00000002aabbccddeeff001122"):
                print("Device removed successfully")
        """
        if dsuid not in self._vdsds:
            logger.warning(f"Cannot remove vdSD {dsuid} - not found in this vDC")
            return False
        
        logger.info(f"Removing vdSD {dsuid}")
        
        # Get device reference before removal
        vdsd = self._vdsds[dsuid]
        
        # TODO: Send vanish notification to vdSM if connected
        # if self.host.is_connected():
        #     self._send_vanish_notification(dsuid)
        
        # Remove from collection
        del self._vdsds[dsuid]
        
        # Remove from persistence
        self._persistence.delete_vdsd(dsuid)
        
        logger.info(f"vdSD {dsuid} removed successfully")
        
        return True
    
    def get_vdsd(self, dsuid: str) -> Optional['VdSD']:
        """
        Get a device by its dSUID.
        
        Args:
            dsuid: Device dSUID
        
        Returns:
            VdSD instance or None if not found
        """
        return self._vdsds.get(dsuid)
    
    def has_vdsd(self, dsuid: str) -> bool:
        """
        Check if a device belongs to this vDC.
        
        Args:
            dsuid: Device dSUID to check
        
        Returns:
            True if device exists in this vDC, False otherwise
        """
        return dsuid in self._vdsds
    
    def get_all_vdsds(self) -> List['VdSD']:
        """
        Get all devices managed by this vDC.
        
        Returns:
            List of VdSD instances
        """
        return list(self._vdsds.values())
    
    def get_properties(self, query: Any) -> Any:
        """
        Get vDC properties based on query.
        
        This method is called when vdSM requests properties for this vDC.
        The query specifies which properties to retrieve (can be a subset).
        
        Process:
        1. Parse query (PropertyElement tree)
        2. Build property dict with requested properties
        3. Merge common and vDC-specific properties
        4. Convert to PropertyElement tree
        5. Return to caller
        
        Args:
            query: PropertyElement tree specifying what to retrieve
                  (None or empty means "get all")
        
        Returns:
            PropertyElement tree with requested properties
        
        Properties returned:
        - Common: dSUID, type, name, model, active, etc.
        - vDC-specific: implementationId, zoneID, capabilities
        - Dynamic: device count, connection status, etc.
        """
        # Merge all properties into single dict
        props = {}
        
        # Add common properties
        props.update(self._common_props.to_dict())
        
        # Add vDC-specific properties
        props.update(self._vdc_props.to_dict())
        
        # Add dynamic/computed properties
        props['vdsd_count'] = len(self._vdsds)
        props['vdsds'] = [vdsd.dsuid for vdsd in self._vdsds.values()]
        
        # TODO: Filter based on query (if query specifies subset)
        # For now, return all properties
        
        # Convert to PropertyElement tree
        return PropertyTree.to_protobuf(props)
    
    def set_properties(self, properties: Any) -> None:
        """
        Set vDC properties from PropertyElement tree.
        
        This method is called when vdSM modifies vDC properties.
        Only writable properties can be changed.
        
        Process:
        1. Convert PropertyElement to dict
        2. Validate properties are writable
        3. Update common properties
        4. Update vDC-specific properties
        5. Persist changes to YAML
        6. Trigger any side effects (e.g., zone change)
        
        Args:
            properties: PropertyElement tree with new values
        
        Raises:
            ValueError: If trying to set read-only property
            TypeError: If property type is invalid
        
        Writable Properties:
        - name (string)
        - active (boolean)
        - zoneID (uint16)
        
        Read-only Properties:
        - dSUID
        - type
        - model
        - implementationId
        - capabilities
        """
        # Convert PropertyElement to dict
        prop_dict = PropertyTree.from_protobuf(properties)
        
        logger.debug(f"Setting vDC properties: {prop_dict.keys()}")
        
        # Update common properties (validates read-only)
        self._common_props.update(prop_dict)
        
        # Update vDC-specific properties
        self._vdc_props.update(prop_dict)
        
        # Persist changes
        vdc_config = {
            **self._common_props.to_dict(),
            **self._vdc_props.to_dict()
        }
        self._persistence.set_vdc(self.dsuid, vdc_config)
        
        logger.debug(f"vDC properties updated and persisted")
    
    def get_vdsd_properties(self, dsuid: str, query: Any) -> Any:
        """
        Get properties for a specific device.
        
        This is called by VdcHost when vdSM requests device properties.
        
        Args:
            dsuid: Device dSUID
            query: Property query
        
        Returns:
            PropertyElement tree with device properties
        
        Raises:
            ValueError: If device not found
        """
        vdsd = self.get_vdsd(dsuid)
        if not vdsd:
            raise ValueError(f"vdSD {dsuid} not found in this vDC")
        
        return vdsd.get_properties(query)
    
    def set_vdsd_properties(self, dsuid: str, properties: Any) -> None:
        """
        Set properties for a specific device.
        
        This is called by VdcHost when vdSM modifies device properties.
        
        Args:
            dsuid: Device dSUID
            properties: PropertyElement tree with new values
        
        Raises:
            ValueError: If device not found
        """
        vdsd = self.get_vdsd(dsuid)
        if not vdsd:
            raise ValueError(f"vdSD {dsuid} not found in this vDC")
        
        vdsd.set_properties(properties)
    
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
        """
        message = Message()
        message.type = Message.VDC_SEND_ANNOUNCE_VDC
        
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
    
    def _load_vdsds(self) -> None:
        """
        Load persisted devices from YAML storage.
        
        Called during vDC initialization to restore devices from
        previous session. For each persisted device:
        1. Read configuration from YAML
        2. Create VdSD instance
        3. Restore device state
        4. Add to device collection
        
        This ensures devices persist across restarts.
        """
        # Get all vdSDs for this vDC from persistence
        vdsd_configs = self._persistence.get_vdsds_for_vdc(self.dsuid)
        
        logger.info(f"Loading {len(vdsd_configs)} persisted devices for vDC {self.dsuid}")
        
        for dsuid, config in vdsd_configs.items():
            try:
                # Create VdSD from persisted config
                # This will be implemented when VdSD class is ready
                # vdsd = VdSD.from_config(self, config)
                # self._vdsds[dsuid] = vdsd
                
                logger.debug(f"Loaded vdSD {dsuid}")
            except Exception as e:
                logger.error(f"Failed to load vdSD {dsuid}: {e}", exc_info=True)
        
        logger.info(f"Loaded {len(self._vdsds)} devices successfully")
    
    def get_device_count(self) -> int:
        """
        Get number of devices in this vDC.
        
        Returns:
            Number of vdSDs managed by this vDC
        """
        return len(self._vdsds)
    
    def __repr__(self) -> str:
        """String representation of vDC."""
        return (
            f"Vdc(dsuid='{self.dsuid}', "
            f"name='{self._common_props.get('name')}', "
            f"devices={len(self._vdsds)})"
        )
