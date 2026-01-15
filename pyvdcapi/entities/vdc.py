[entire file contents with the announce_to_vdsm change applied]
1| """
2| Vdc - Virtual Device Connector.
3| 
4| A vDC (virtual device connector) represents a collection of virtual devices
5| (vdSDs) that share common characteristics, typically from the same:
6| - Technology (e.g., Zigbee, Z-Wave, KNX)
7| - Manufacturer (e.g., Philips Hue, IKEA TRÅDFRI)
8| - Physical gateway/bridge (e.g., one Hue bridge = one vDC)
9| 
10| Architecture Context:
11| ┌─────────────────────────────────────────────────────────┐
12| │ VdcHost                                                 │
13| │ ┌─────────────────────────────────────────────────────┐ │
14| │ │ Vdc (e.g., "Philips Hue vDC")                       │ │
15| │ │ ┌─────────┐  ┌─────────┐  ┌─────────┐             │ │
16| │ │ │ VdSD 1  │  │ VdSD 2  │  │ VdSD N  │             │ │
17| │ │ │ (Light) │  │ (Light) │  │ (Sensor)│             │ │
18| │ │ └─────────┘  └─────────┘  └─────────┘             │ │
19| │ └─────────────────────────────────────────────────────┘ │
20| └─────────────────────────────────────────────────────────┘
21| 
22| Responsibilities:
23| 1. Device Management:
24|    - Create/remove virtual devices (vdSDs)
25|    - Maintain device inventory
26|    - Handle device announcements to vdSM
27| 
28| 2. Property Management:
29|    - vDC-specific properties (implementationId, zoneID, capabilities)
30|    - Route property queries to child vdSDs
31|    - Persist vDC configuration
32| 
33| 3. Device Discovery:
34|    - Implement device scanning/discovery
35|    - Announce new devices to vdSM
36|    - Handle device removal notifications
37| 
38| 4. Communication Bridge:
39|    - Forward vdSM commands to devices
40|    - Forward device events to vdSM
41|    - Manage device state synchronization
42| 
43| Lifecycle:
44| 1. Creation: Host creates vDC with initial properties
45| 2. Device Addition: vdSDs are created and announced
46| 3. Operation: Routes messages, manages devices
47| 4. Removal: Cleanup and persist final state
48| 
49| Example Use Cases:
50| - Philips Hue vDC: Manages all lights from one Hue bridge
51| - Thermostat vDC: Manages heating devices from one manufacturer
52| - GPIO vDC: Manages all GPIO-connected devices on one board
53| 
54| Usage:
55| ```python
56| # Create vDC for a Hue bridge
57| hue_vdc = host.create_vdc(
58|     name="Philips Hue Bridge",
59|     model="vDC Hue v1.0",
60|     vendor="Philips"
61| )
62| 
63| # Add devices to the vDC
64| living_room_light = hue_vdc.create_vdsd(
65|     name="Living Room Light",
66|     model="Hue White",
67|     primary_group=DSGroup.YELLOW,
68|     output_function=DSOutputFunction.DIMMER
69| )
70| 
71| bedroom_light = hue_vdc.create_vdsd(
72|     name="Bedroom Light",
73|     model="Hue White and Color",
74|     primary_group=DSGroup.YELLOW,
75|     output_function=DSOutputFunction.FULL_COLOR
76| )
77| 
78| # vDC now manages these devices and handles their communication
79| ``` 
80| """
81| 
82| import logging
83| from typing import Dict, List, Optional, Any, Callable
84| from pyvdcapi.network.genericVDC_pb2 import Message, VDC_SEND_ANNOUNCE_VDC
85| 
86| from ..core.dsuid import DSUIDGenerator, DSUIDNamespace
87| from ..properties.common import CommonProperties
88| from ..properties.vdc_props import VdcProperties
89| from ..properties.property_tree import PropertyTree
90| from ..persistence.yaml_store import YAMLPersistence
91| 
92| logger = logging.getLogger(__name__)
93| 
94| 
95| class Vdc:
96|     """
97|     Virtual Device Connector - manages a collection of related devices.
98|     
99|     A Vdc acts as a bridge between the vDC API (vdSM side) and
100|     actual devices (physical or virtual). It:
101|     
102|     - Maintains a collection of vdSDs (virtual devices)
103|     - Routes property queries between vdSM and devices
104|     - Handles device announcements and removal
105|     - Persists vDC and device configuration
106|     - Manages vDC-specific capabilities
107|     
108|     Properties:
109|     The vDC has two sets of properties:
110|     1. Common properties (inherited from CommonProperties)
111|        - dSUID, name, model, type, etc.
112|     2. vDC-specific properties (from VdcProperties)
113|        - implementationId, zoneID, capabilities
114|     
115|     Device Management:
116|     - Devices are identified by their dSUID
117|     - Each device (vdSD) belongs to exactly one vDC
118|     - Device dSUIDs are generated deterministically
119|     - Device addition triggers announcement to vdSM
120|     
121|     Persistence:
122|     - vDC configuration is stored in YAML
123|     - Device configurations are stored under the vDC
124|     - Changes are auto-saved (configurable)
125|     
126|     Attributes:
127|         dsuid: Unique identifier for this vDC
128|         host: Reference to parent VdcHost
129|         vdsds: Dictionary of managed devices (dSUID -> VdSD)
130|         common_props: Common entity properties
131|         vdc_props: vDC-specific properties
132|     """
133|     
134|     def __init__(
135|         self,
136|         host: 'VdcHost',
137|         mac_address: str,
138|         vendor_id: str,
139|         persistence: YAMLPersistence,
140|         model: str,
141|         model_uid: str,
142|         model_version: str = "1.0",
143|         **properties
144|     ):
145|         """
146|         Initialize virtual device connector.
147|         
148|         Note: Do not call directly - use VdcHost.create_vdc() instead.
149|         
150|         Args:
151|             host: Parent VdcHost instance
152|             mac_address: MAC address for dSUID generation
153|             vendor_id: Vendor identifier for dSUID namespace
154|             persistence: YAML persistence manager (shared with host)
155|             model: Human-readable model name
156|             model_uid: Unique model identifier (required for vdSM)
157|             model_version: Model version string (default: "1.0")
158|             **properties: Additional vDC properties (name, vendor, etc.)
159|         
160|         The vDC dSUID is generated from:
161|         - MAC address (ensures uniqueness across hosts)
162|         - Vendor ID (namespace)
163|         - vDC namespace (0x00000001)
164|         - Enumeration (if multiple vDCs with same MAC)
165|         
166|         Example:
167|             # Always use VdcHost.create_vdc() instead of direct instantiation
168|             vdc = host.create_vdc(
169|                 name="Smart Light Controller",
170|                 model="LightVDC v1.0",
171|                 model_uid="lightvdc-v1-0",
172|                 model_version="1.0"
173|             )
174|         """
175|         # Generate vDC dSUID
176|         # Note: For multiple vDCs on same host, use enumeration parameter
177|         dsuid_gen = DSUIDGenerator(mac_address, vendor_id)
178|         enumeration = properties.pop('enumeration', 0)  # Allow override
179|         self.dsuid = dsuid_gen.generate(
180|             DSUIDNamespace.VDC,
181|             enumeration=enumeration
182|         )
183|         
184|         logger.info(f"Initializing vDC with dSUID: {self.dsuid}")
185|         
186|         # Parent reference
187|         self.host = host
188|         
189|         # Persistence (shared with host)
190|         self._persistence = persistence
191|         
192|         # Load or initialize vDC configuration
193|         vdc_config = self._persistence.get_vdc(self.dsuid)
194|         if not vdc_config:
195|             # First time - initialize with provided properties
196|             vdc_config = {
197|                 'dSUID': self.dsuid,
198|                 'type': 'vDC',
199|                 'model': model,
200|                 'model_uid': model_uid,
201|                 'model_version': model_version,
202|                 'vendor_id': vendor_id,
203|                 'enumeration': enumeration,
204|                 **properties
205|             }
206|             self._persistence.set_vdc(self.dsuid, vdc_config)
207|         
208|         # Common properties (dSUID, name, model, etc.)
209|         # Extract explicitly handled properties to avoid duplicates
210|         extra_props = {k: v for k, v in vdc_config.items() 
211|                       if k not in ['name', 'model', 'model_uid', 'model_version', 'vendor_id', 'enumeration', 'type', 'dSUID']}
212|         
213|         self._common_props = CommonProperties(
214|             dsuid=self.dsuid,
215|             entity_type='vDC',
216|             name=vdc_config.get('name', properties.get('name', model)),
217|             model=vdc_config.get('model', model),
218|             model_uid=vdc_config.get('model_uid', model_uid),
219|             model_version=vdc_config.get('model_version', model_version) or "",
220|             **extra_props
221|         )
222|         
223|         # vDC-specific properties (implementationId, zoneID, capabilities)
224|         # Extract only vDC-specific properties and convert camelCase to snake_case
225|         vdc_specific_props = {}
226|         if 'implementationId' in vdc_config:
227|             vdc_specific_props['implementation_id'] = vdc_config['implementationId']
228|         if 'implementation_id' in vdc_config:
229|             vdc_specific_props['implementation_id'] = vdc_config['implementation_id']
230|         if 'zoneID' in vdc_config:
231|             vdc_specific_props['zone_id'] = vdc_config['zoneID']
232|         if 'zone_id' in vdc_config:
233|             vdc_specific_props['zone_id'] = vdc_config['zone_id']
234|         if 'capabilities' in vdc_config:
235|             vdc_specific_props['capabilities'] = vdc_config['capabilities']
236|         
237|         self._vdc_props = VdcProperties(**vdc_specific_props)
238|         
239|         # Device management
240|         # Key: vdSD dSUID, Value: VdSD instance
241|         self._vdsds: Dict[str, 'VdSD'] = {}
242|         
243|         # Load persisted devices
244|         # This will be implemented when VdSD class is ready
245|         # self._load_vdsds()
246|         
247|         logger.info(
248|             f"vDC initialized: name='{self._common_props.get_property('name')}', "
249|             f"model='{self._common_props.get_property('model')}', "
250|             f"devices={len(self._vdsds)}"
251|         )
252|     
253|     def create_vdsd(
254|         self,
255|         name: str,
256|         model: str,
257|         primary_group: int,
258|         model_uid: Optional[str] = None,
259|         model_version: str = "1.0",
260|         **properties
261|     ) -> 'VdSD':
262|         """
263|         Create a new virtual device (vdSD) in this vDC.
264|         
265|         A vdSD represents an individual device (light, sensor, switch, etc.). ...
[... lines omitted here for brevity in this view, file continues unchanged until announce_to_vdsm ...]
568|         vdsd.set_properties(properties)
569|     
570|     def announce_to_vdsm(self, message_id: int = 0) -> Message:
571|         """
572|         Create vDC announcement message for vdSM.
573|         
574|         When vdSM connects or requests device discovery, the vDC must
575|         announce itself. The announcement includes:
576|         - vDC dSUID (identification)
577|         - vDC properties (name, model, capabilities)
578|         
579|         Returns:
580|             Message with vdc_SendAnnounceVdc
581|         
582|         This is typically followed by device announcements (announce_devices).
583|         
584|         NOTE: Announcements are notifications and MUST NOT contain any
585|         message_id information in the envelope. The message_id parameter
586|         is accepted for backward compatibility but is ignored; the
587|         generated message will never include a message_id field.
588|         """
589|         message = Message()
590|         message.type = VDC_SEND_ANNOUNCE_VDC
591|         # NOTE: Do not set message.message_id. Announce messages are
592|         # notifications and must never include message_id information.
593|         
594|         # Create announcement with vDC properties
595|         announce = message.vdc_send_announce_vdc
596|         announce.dSUID = self.dsuid
597|         
598|         # Add vDC properties to announcement
599|         # Note: Actual field structure depends on protobuf definition
600|         # announce.properties.CopyFrom(self.get_properties(None))
601|         
602|         logger.debug(f"Created vDC announcement for {self.dsuid}")
603|         
604|         return message
605|     
606|     def announce_devices(self) -> List[Message]:
607|         """
608|         Create device announcement messages for all vdSDs.
609|         
610|         After announcing the vDC, we must announce each device.
611|         Returns a list of announcement messages (one per device).
612|         
613|         Returns:
614|             List of Messages with vdc_SendAnnounceDevice
615|         
616|         The vdSM processes these to build its device inventory.
617|         """
618|         announcements = []
619|         
620|         for vdsd in self._vdsds.values():
621|             message = vdsd.announce_to_vdsm()
622|             announcements.append(message)
623|         
624|         logger.debug(
625|             f"Created {len(announcements)} device announcements for vDC {self.dsuid}"
626|         )
627|         
628|         return announcements
629|     
630|     def _load_vdsds(self) -> None:
631|         """
632|         Load persisted devices from YAML storage.
633|         
634| Called during vDC initialization to restore devices from
635| previous session. For each persisted device:
636| 1. Read configuration from YAML
637| 2. Create VdSD instance
638| 3. Restore device state
639| 4. Add to device collection
640|         
641| This ensures devices persist across restarts.
642|         """
643|         # Get all vdSDs for this vDC from persistence
644|         vdsd_configs = self._persistence.get_vdsds_for_vdc(self.dsuid)
645|         
646|         logger.info(f"Loading {len(vdsd_configs)} persisted devices for vDC {self.dsuid}")
647|         
648|         for dsuid, config in vdsd_configs.items():
649|             try:
650|                 # Create VdSD from persisted config
651|                 # This will be implemented when VdSD class is ready
652|                 # vdsd = VdSD.from_config(self, config)
653|                 # self._vdsds[dsuid] = vdsd
654|                 
655|                 logger.debug(f"Loaded vdSD {dsuid}")
656|             except Exception as e:
657|                 logger.error(f"Failed to load vdSD {dsuid}: {e}", exc_info=True)
658|         
659|         logger.info(f"Loaded {len(self._vdsds)} devices successfully")
660|     
661|     def get_device_count(self) -> int:
662|         """
663|         Get number of devices in this vDC.
664|         
665|         Returns:
666|             Number of vdSDs managed by this vDC
667|         """
668|         return len(self._vdsds)
669|     
670|     def __repr__(self) -> str:
671|         """String representation of vDC."""
672|         return (
673|             f"Vdc(dsuid='{self.dsuid}', "
674|             f"name='{self._common_props.get_property('name')}', "
675|             f"devices={len(self._vdsds)})"
676|         )
677| 
678| 
679| 
