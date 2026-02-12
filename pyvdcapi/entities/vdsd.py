"""
VdSD - Virtual Device (Smart Device).

A vdSD represents an individual device in the digitalSTROM ecosystem.
It's the leaf node in the hierarchy:

VdcHost → Vdc → VdSD

Each vdSD represents a single controllable/monitorable device:
- Light (dimmer, color, on/off)
- Blind/shade
- Thermostat
- Sensor (temperature, humidity, motion)
- Button/switch
- Any other addressable device

Device Architecture:
┌──────────────────────────────────────────────────────────┐
│ VdSD (e.g., "Living Room Dimmer")                       │
├──────────────────────────────────────────────────────────┤
│ Properties:                                              │
│ - Common: dSUID, name, model, type                       │
│ - vdSD-specific: primaryGroup, modelFeatures, zoneID     │
│                                                          │
│ Components:                                              │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│ │   Inputs     │  │   Outputs    │  │    Scenes    │   │
│ ├──────────────┤  ├──────────────┤  ├──────────────┤   │
│ │ - Buttons    │  │ - Channels   │  │ - Scene 0-63 │   │
│ │ - BinaryIn   │  │ - Brightness │  │ - Effects    │   │
│ │ - Sensors    │  │ - Color      │  │ - DontCare   │   │
│ └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                          │
│ Callbacks:                                               │
│ - on_output_change: Device → vdSM notification          │
│ - on_scene_call: vdSM → Device scene activation         │
│ - on_button_press: Device → vdSM button event           │
└──────────────────────────────────────────────────────────┘

Device Types (by primary group):
- Yellow (1): Light - has output channels (brightness, color, etc.)
- Gray (2): Blinds - has position/angle outputs
- Blue (3): Heating - has temperature/valve outputs
- Cyan (4): Audio - has volume/bass/treble
- Others: Various specialized device types

Bidirectional Value Flow:
┌─────────┐                              ┌─────────┐
│  vdSM   │                              │ Hardware│
└────┬────┘                              └────┬────┘
     │                                        │
     │ setProperty(output.value=50%)          │
     ├───────────────────────────────────────>│
     │                                        │
     │                     (apply to hardware)│
     │                                        │
     │ notification(output.value=50%)         │
     │<───────────────────────────────────────┤
     │                                        │
     │                       (state confirmed)│
     │                                        │

Value Propagation:
1. vdSM sets output value via property
2. VdSD applies to hardware callback
3. Hardware confirms new state
4. VdSD updates internal state
5. VdSD sends notification to vdSM
6. State is synchronized bidirectionally

Scene Handling:
When scene is called:
1. vdSM sends callScene notification
2. VdSD looks up scene configuration
3. Scene values applied to outputs
4. Effect (smooth/slow/alert) determines transition
5. Output notifications sent to vdSM

Usage Example:
```python
# Create a dimmer device
dimmer = vdc.create_vdsd(
    name="Living Room Dimmer",
    model="Dimmer 1CH",
    primary_group=DSGroup.YELLOW  # Yellow group = Light (value 1)
)

# Add output channel
dimmer.add_output_channel(
    channel_type=DSChannelType.BRIGHTNESS,
    min_value=0.0,
    max_value=100.0,
    resolution=0.1,
    initial_value=0.0
)

# Add button input
dimmer.add_button_input(
    name="Toggle Button",
    button_type=1,  # Single pushbutton
    button_element_id=0
)

# Configure scenes
dimmer.set_scene(DSScene.PRESENT, {
    DSChannelType.BRIGHTNESS: 75.0
}, effect=DSSceneEffect.SMOOTH)

# Set up hardware callback (receives channel_type and value)
def apply_to_hardware(channel_type, value):
    # Send to actual hardware
    hardware.set_brightness(value)
    print(f"Applied channel {channel_type} brightness: {value}%")

dimmer.on_output_change(apply_to_hardware)
```
"""

from __future__ import annotations

import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from pyvdcapi.network import genericVDC_pb2
from ..core.dsuid import DSUIDGenerator, DSUIDNamespace
from ..core.constants import DSChannelType, DSSceneEffect
from ..properties.common import CommonProperties
from ..properties.vdsd_props import VdSDProperties
from ..properties.property_tree import PropertyTree
from ..utils.callbacks import Observable
from ..properties.control_value import ControlValues
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..entities.vdc import Vdc
    from ..components.output import Output
    from ..components.output_channel import OutputChannel
    from ..components.button_input import ButtonInput
    from ..components.binary_input import BinaryInput
    from ..components.sensor import Sensor

logger = logging.getLogger(__name__)


class VdSD:
    """
    Virtual Device (Smart Device) - represents a single controllable device.

    The VdSD is the leaf entity in the vDC API hierarchy. It represents
    an individual device that can:
    - Have inputs (buttons, binary inputs, sensors)
    - Have outputs (channels for brightness, color, position, etc.)
    - Store and recall scenes
    - Generate notifications (button press, value change, etc.)
    - Accept commands from vdSM (set output, call scene, etc.)

    Components:
    1. Inputs: Device → vdSM notifications
       - Buttons: User interaction events
       - Binary Inputs: Contact closure, motion detection
       - Sensors: Temperature, humidity, illuminance readings

    2. Outputs: vdSM → Device control
       - Channels: Brightness, color, position, etc.
       - State tracking: Current value, age, transition
       - Hardware callbacks: Apply values to real devices

    3. Scenes: Preset configurations
       - Store: Remember current state as scene
       - Recall: Restore scene configuration
       - Effects: Transition style (smooth, slow, alert)

    Properties:
    The device has three property sets:
    1. Common: dSUID, name, model, type (from CommonProperties)
    2. vdSD-specific: primaryGroup, modelFeatures, zoneID (from VdSDProperties)
    3. Dynamic: outputs, inputs, scenes (generated on request)

    Callbacks:
    The VdSD uses Observable pattern for bidirectional communication:
    - Application sets callbacks to handle vdSM commands
    - VdSD notifies application of hardware changes
    - All communication is asynchronous-capable

    Attributes:
        dsuid: Unique identifier for this device
        vdc: Reference to parent vDC
        primary_group: digitalSTROM group (color) determining device type
        outputs: Output channels (brightness, color, etc.)
        inputs: Input components (buttons, sensors, etc.)
        scenes: Scene configurations (0-63)
    """

    def __init__(
        self,
        vdc: "Vdc",
        name: str,
        model: str,
        primary_group: int,
        mac_address: str,
        vendor_id: str,
        enumeration: int = 0,
        model_uid: Optional[str] = None,
        model_version: str = "1.0",
        **properties,
    ):
        """
        Initialize virtual device.

        Args:
            vdc: Parent Vdc instance
            name: Human-readable device name
            model: Device model identifier
            primary_group: digitalSTROM group (DSGroup enum value)
            mac_address: MAC address for dSUID generation
            vendor_id: Vendor ID for dSUID namespace
            enumeration: Device enumeration number (for multiple devices)
            model_uid: Unique model identifier (auto-generated from model if not provided)
            model_version: Model version string (default: "1.0")
            **properties: Additional device properties

        The device dSUID is generated from:
        - MAC address (base identifier)
        - Vendor ID (namespace)
        - vdSD namespace (0x00000002)
        - Enumeration (to differentiate multiple devices)

        Example:
            vdsd = VdSD(
                vdc=my_vdc,
                name="Kitchen Light",
                model="Dimmer 1CH",
                primary_group=DSGroup.YELLOW,
                mac_address="00:11:22:33:44:55",
                vendor_id="MyCompany",
                enumeration=5,  # 5th device
                output_function=DSOutputFunction.DIMMER
            )
        """
        # Generate device dSUID
        # Enumeration allows multiple devices from same MAC address
        dsuid_gen = DSUIDGenerator(mac_address, vendor_id)
        self.dsuid = dsuid_gen.generate(DSUIDNamespace.VDSD, enumeration=enumeration)

        logger.info(f"Initializing vdSD with dSUID: {self.dsuid}")

        # Parent reference
        self.vdc = vdc

        # Persistence (shared with vDC)
        self._persistence = vdc._persistence

        # Load or initialize device configuration
        vdsd_config = self._persistence.get_vdsd(self.dsuid)
        if not vdsd_config:
            # First time - initialize with provided properties
            # Convert enum to value for YAML serialization
            primary_group_value = primary_group if isinstance(primary_group, int) else primary_group.value
            vdsd_config = {
                "dSUID": self.dsuid,
                "type": "vDSD",
                "vdc_dSUID": vdc.dsuid,  # Link to parent vDC
                "name": name,
                "model": model,
                "primaryGroup": primary_group_value,
                "enumeration": enumeration,
                **properties,
            }
            self._persistence.set_vdsd(self.dsuid, vdsd_config)

        # Common properties (dSUID, name, model, etc.)
        # Extract explicitly handled properties to avoid duplicates
        extra_props = {
            k: v
            for k, v in vdsd_config.items()
            if k not in ["name", "model", "model_uid", "model_version", "primary_group", "enumeration", "type", "dSUID"]
        }

        self._common_props = CommonProperties(
            dsuid=self.dsuid,
            entity_type="vdSD",
            name=name,
            model=model,
            model_uid=model_uid if model_uid else "",
            model_version=model_version if model_version else "",
            **extra_props,
        )

        # vdSD-specific properties (primaryGroup, modelFeatures, etc.)
        self._vdsd_props = VdSDProperties(primary_group=primary_group, **vdsd_config)

        # Control values container (in-memory representation)
        # Load persisted controlValues if present
        try:
            persisted_cvs = vdsd_config.get("controlValues", {}) if isinstance(vdsd_config, dict) else {}
        except Exception:
            persisted_cvs = {}
        self.controlValues = ControlValues(persisted_cvs)

        # Device components
        # These will hold the actual input/output/scene components
        # Per vDC API: Device has maximum ONE output (but can have multiple channels)
        self._output: Optional["Output"] = None  # Single output (not a dict)
        self._button_inputs: List["ButtonInput"] = []  # API-compliant button inputs
        self._binary_inputs: List["BinaryInput"] = []
        self._sensors: List["Sensor"] = []
        self._scenes: Dict[int, Dict] = {}  # sceneNo -> scene config
        self._local_priority_scene: Optional[int] = None  # Local priority scene lock

        # Actions and States managers
        from ..components.actions import ActionManager, StateManager, DevicePropertyManager

        self.actions = ActionManager(self)
        self.states = StateManager(self)
        self.device_properties = DevicePropertyManager(self)

        # Initialize common states
        self._initialize_common_states()

        # Initialize common actions
        self._initialize_common_actions()

        # Callbacks for hardware integration
        # These are Observable objects that can have multiple subscribers
        self._output_callbacks: Dict[int, Observable] = {}  # channelType -> Observable

        # State tracking
        self._active = vdsd_config.get("active", True)
        self._announced = False  # Track if device has been announced to vdSM

        logger.info(f"vdSD initialized: name='{name}', " f"model='{model}', " f"group={primary_group}")

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure device with all capabilities from a configuration dictionary.

        IMPORTANT: Per vDC API specification, device structure is immutable after
        announcement to vdSM. This method will raise RuntimeError if called after
        the device has been announced. Always configure devices before announcement.

        This method allows bulk configuration of a device after creation,
        useful for:
        - Loading from persistence/YAML
        - Applying device templates
        - Cloning device configurations
        - API-driven device setup

        Args:
            config: Configuration dictionary containing:
                - output: Output configuration (single, not list - per API spec)
                - button_inputs: List of button input configurations
                - binary_inputs: List of binary input configurations
                - sensors: List of sensor configurations
                - scenes: Dictionary of scene configurations
                - actions: Custom/dynamic actions
                - states: Initial state values
                - properties: Device properties

        Example:
            # Configure a complete RGB light
            device.configure({
                'output': {
                    'outputFunction': 'colordimmer',
                    'outputMode': 'gradual',
                    'channels': [
                        {
                            'channelType': DSChannelType.BRIGHTNESS,
                            'name': 'Brightness',
                            'min': 0.0,
                            'max': 100.0,
                            'default': 0.0
                        },
                        {
                            'channelType': DSChannelType.HUE,
                            'name': 'Hue',
                            'min': 0.0,
                            'max': 360.0,
                            'default': 0.0
                        },
                        {
                            'channelType': DSChannelType.SATURATION,
                            'name': 'Saturation',
                            'min': 0.0,
                            'max': 100.0,
                            'default': 0.0
                        }
                    ]
                }],
                'buttons': [{
                    'name': 'Power Button',
                    'buttonType': 'toggle',
                    'element': 0
                }],
                'sensors': [{
                    'sensorType': 'temperature',
                    'name': 'Internal Temperature',
                    'unit': '°C',
                    'min': -40.0,
                    'max': 125.0
                }],
                'scenes': {
                    DSScene.PRESENT: {
                        'channels': {
                            DSChannelType.BRIGHTNESS: 75.0,
                            DSChannelType.HUE: 0.0,
                            DSChannelType.SATURATION: 0.0
                        },
                        'effect': DSSceneEffect.SMOOTH
                    }
                }
            })
        """
        if self._announced:
            raise RuntimeError(
                f"Cannot configure device {self.dsuid} after announcement to vdSM. "
                f"Device structure is immutable once announced per vDC API specification."
            )
        
        from ..components import Output, OutputChannel, BinaryInput, Sensor

        logger.info(f"Configuring vdSD {self.dsuid} from config")

        # Configure output (singular - per API spec: max ONE output per device)
        if "output" in config:
            output_config = config["output"]
            output = Output(
                vdsd=self,
                output_function=output_config.get("outputFunction", "dimmer"),
                output_mode=output_config.get("outputMode", "gradual"),
                push_changes=output_config.get("pushChanges", True),
            )

            # Add channels to output
            if "channels" in output_config:
                for channel_config in output_config["channels"]:
                    channel = OutputChannel(
                        vdsd=self,
                        channel_type=channel_config.get("channelType"),
                        name=channel_config.get("name", ""),
                        min_value=channel_config.get("min", 0.0),
                        max_value=channel_config.get("max", 100.0),
                        resolution=channel_config.get("resolution", 0.1),
                        initial_value=channel_config.get("default", 0.0),
                    )
                    output.add_channel(channel)

            self._output = output
            logger.debug(f"Added output with {len(output.channels)} channels")

        # Configure button inputs
        if "button_inputs" in config:
            for button_config in config["button_inputs"]:
                button_input = self.add_button_input(
                    name=button_config.get("name", ""),
                    button_type=button_config.get("buttonType", 1),
                    button_id=button_config.get("buttonID"),
                    button_element_id=button_config.get("buttonElementID", 0),
                    **button_config.get("settings", {})
                )
                logger.debug(f"Added button input: {button_input.name}")

        # Configure binary inputs
        if "binary_inputs" in config:
            for input_config in config["binary_inputs"]:
                binary_input = self.add_binary_input(
                    name=input_config.get("name", ""),
                    input_type=input_config.get("inputType", "contact"),
                    input_id=input_config.get("inputID"),
                    invert=input_config.get("invert", False),
                    initial_state=input_config.get("initialState", False),
                    **input_config.get("settings", {})
                )
                logger.debug(f"Added binary input: {binary_input.name}")

        # Configure sensors
        if "sensors" in config:
            for sensor_config in config["sensors"]:
                sensor = self.add_sensor(
                    sensor_type=sensor_config.get("sensorType", "custom"),
                    unit=sensor_config.get("unit", ""),
                    min_value=sensor_config.get("min"),
                    max_value=sensor_config.get("max"),
                    name=sensor_config.get("name", ""),
                    resolution=sensor_config.get("resolution", 0.1),
                    initial_value=sensor_config.get("initialValue"),
                    sensor_id=sensor_config.get("sensorID")
                )
                logger.debug(f"Added sensor: {sensor.name}")

        # Configure scenes
        if "scenes" in config:
            for scene_number, scene_config in config["scenes"].items():
                self.set_scene(
                    scene_number=int(scene_number) if isinstance(scene_number, str) else scene_number,
                    channel_values=scene_config.get("channels", {}),
                    effect=scene_config.get("effect", DSSceneEffect.SMOOTH),
                    dont_care=scene_config.get("dontCare", False),
                )
                logger.debug(f"Configured scene {scene_number}")

        # Configure custom actions
        if "customActions" in config:
            for action in config["customActions"]:
                self.actions.add_custom_action(
                    name=action.get("name", ""),
                    title=action.get("title", ""),
                    action_template=action.get("action", ""),
                    params=action.get("params", {}),
                )

        # Set initial states
        if "states" in config:
            for state_name, state_value in config["states"].items():
                self.states.set_state(state_name, state_value)

        # Set device properties
        if "deviceProperties" in config:
            for prop in config["deviceProperties"]:
                self.device_properties.set_property(prop.get("name"), prop.get("value"))

        # Persist the configuration
        self._save_config()

        logger.info(
            f"vdSD {self.dsuid} configured: "
            f"{1 if self._output else 0} output, "
            f"{len(self._button_inputs)} buttons, "
            f"{len(self._binary_inputs)} binary inputs, "
            f"{len(self._sensors)} sensors, "
            f"{len(self._scenes)} scenes"
        )

    def export_configuration(self) -> Dict[str, Any]:
        """
        Export device configuration (without identity fields).

        This method exports all device capabilities to a dictionary
        that can be:
        - Saved to file (YAML/JSON)
        - Used as device template
        - Sent via API
        - Applied to new devices

        Note: Identity fields (dSUID, serial, name) are NOT included
        to allow configuration reuse across multiple devices.

        Returns:
            Configuration dictionary with all device capabilities

        Example:
            # Export device configuration
            config = device.export_configuration()

            # Save to JSON
            import json
            with open('device_config.json', 'w') as f:
                json.dump(config, f, indent=2)

            # Apply to another device
            new_device.configure(config)
        """
        config = {}
        
        # Export output (singular) if it exists
        if self._output:
            config["output"] = self._output.to_dict()
        
        # Export other components
        config["button_inputs"] = [button_input.to_dict() for button_input in self._button_inputs]
        config["binary_inputs"] = [binary_input.to_dict() for binary_input in self._binary_inputs]
        config["sensors"] = [sensor.to_dict() for sensor in self._sensors]
        config["scenes"] = self._scenes.copy()
        config["customActions"] = self.actions.get_custom_actions().get("customActions", [])
        config["states"] = self.states.get_values().get("deviceStates", [])
        config["deviceProperties"] = self.device_properties.to_dict().get("deviceProperties", [])

        return config

    def clone(self, new_name: str, enumeration: Optional[int] = None) -> "VdSD":
        """
        Clone this device with a new name and unique dSUID.

        Creates a new device with identical configuration but different
        identity (name, dSUID, enumeration). The clone will have:
        - Same model, vendor, group
        - Same outputs, inputs, sensors
        - Same scene configurations
        - Same actions and states
        - NEW dSUID (unique identifier)
        - NEW name
        - NEW enumeration number

        Args:
            new_name: Name for the cloned device
            enumeration: Enumeration number (auto-assigned if None)

        Returns:
            New VdSD instance with cloned configuration

        Example:
            # Clone living room light to bedroom
            living_room = vdc.create_vdsd(
                name="Living Room Light",
                model="RGB-100",
                primary_group=DSGroup.LIGHT,
                mac_address="00:11:22:33:44:55",
                vendor_id="MyCompany"
            )
            living_room.configure(RGB_LIGHT_TEMPLATE)

            # Clone to bedroom (gets new dSUID automatically)
            bedroom = living_room.clone("Bedroom Light")

            # Devices have same capabilities but different identities
            assert living_room.dsuid != bedroom.dsuid
            assert living_room._common_props.get('name') != bedroom._common_props.get('name')
        """
        # Export configuration (without identity)
        config = self.export_configuration()

        # Get original device properties
        model = self._common_props.get_property("model")
        primary_group = self._vdsd_props.get_property("primaryGroup")

        # Auto-assign enumeration if not provided
        if enumeration is None:
            # Count existing devices to get next enumeration
            enumeration = len(self.vdc._vdsds)

        # Create new device with same base properties but new identity
        # Note: We use the parent vDC to create the new device
        clone_device = self.vdc.create_vdsd(
            name=new_name,
            model=model,
            primary_group=primary_group,
            # Use same MAC base but different enumeration for unique dSUID
            enumeration=enumeration,
        )

        # Apply configuration to clone
        clone_device.configure(config)

        original_name = self._common_props.get_property("name")
        logger.info(
            f"Cloned vdSD {self.dsuid} ('{original_name}') " f"to {clone_device.dsuid} ('{new_name}')"
        )

        return clone_device

    def add_output_channel(
        self,
        channel_type: int,
        min_value: float = 0.0,
        max_value: float = 100.0,
        resolution: float = 0.1,
        initial_value: Optional[float] = None,
        **properties,
    ) -> "OutputChannel":
        """
        Add an output channel to this device.

        IMPORTANT: Per vDC API specification, device structure is immutable after
        announcement to vdSM. This method will raise RuntimeError if called after
        the device has been announced.

        Output channels represent controllable aspects of the device:
        - Brightness (for lights)
        - Hue, Saturation (for color lights)
        - Position, Angle (for blinds)
        - Temperature (for thermostats)
        - Volume (for audio devices)

        Each channel has:
        - Type: What it controls (brightness, hue, etc.)
        - Range: Min/max values
        - Resolution: Smallest change increment
        - Value: Current state

        Args:
            channel_type: DSChannelType enum value
            min_value: Minimum value for this channel
            max_value: Maximum value for this channel
            resolution: Smallest increment (for UI granularity)
            initial_value: Starting value (defaults to min_value)
            **properties: Additional channel properties

        Returns:
            OutputChannel instance

        Example:
            # Add brightness channel for dimmer
            brightness = device.add_output_channel(
                channel_type=DSChannelType.BRIGHTNESS,
                min_value=0.0,
                max_value=100.0,
                resolution=0.1,
                initial_value=0.0
            )

            # Add color channels for RGB light
            device.add_output_channel(
                channel_type=DSChannelType.HUE,
                min_value=0.0,
                max_value=360.0,
                resolution=1.0
            )
            device.add_output_channel(
                channel_type=DSChannelType.SATURATION,
                min_value=0.0,
                max_value=100.0,
                resolution=1.0
            )
        """
        if self._announced:
            raise RuntimeError(
                f"Cannot add output channel to device {self.dsuid} after announcement to vdSM. "
                f"Per vDC API specification, device structure is immutable once announced.\n"
                f"To modify device capabilities:\n"
                f"  1. Send vanish notification: await vdc.vanish_device('{self.dsuid}')\n"
                f"  2. Delete device: vdc.delete_vdsd('{self.dsuid}')\n"
                f"  3. Create new device with desired configuration\n"
                f"  4. New device will be announced automatically"
            )
        
        from ..components.output_channel import OutputChannel

        # Create the output channel
        channel = OutputChannel(
            vdsd=self,
            channel_type=channel_type,
            min_value=min_value,
            max_value=max_value,
            resolution=resolution,
            initial_value=initial_value,
            **properties,
        )

        # Create single output if it doesn't exist yet
        # (Per API: max ONE output per device)
        if self._output is None:
            from ..components.output import Output

            self._output = Output(
                vdsd=self,
                output_function=properties.get("output_function", "dimmer"),
                output_mode=properties.get("output_mode", "gradual"),
            )

        # Add channel to THE output (singular)
        self._output.add_channel(channel)

        logger.info(f"Added output channel type {channel_type} to vdSD {self.dsuid}")

        return channel

    def bind_output_channel(
        self,
        channel_type: int,
        getter: Callable[[], Optional[float]],
        setter: Optional[Callable[..., Any]] = None,
        poll_interval: Optional[float] = None,
        epsilon: float = 0.0,
    ):
        """
        Bind an output channel to a native hardware value (single-step).

        Args:
            channel_type: DSChannelType enum value
            getter: Function returning native hardware value
            setter: Function applying vdSM value to hardware (optional)
            poll_interval: If set, poll native value every N seconds
            epsilon: Minimum change required to publish updates
        """
        if self._output is None:
            raise RuntimeError("Device has no output to bind")

        from ..core.constants import DSChannelType

        try:
            ch_type = DSChannelType(channel_type)
        except ValueError:
            ch_type = channel_type

        channel = self._output.get_channel(ch_type)
        if channel is None:
            raise RuntimeError(f"Output channel {channel_type} not found")

        return channel.bind_to(
            getter=getter,
            setter=setter,
            poll_interval=poll_interval,
            epsilon=epsilon,
        )

    def bind_output_channel_events(
        self,
        channel_type: int,
        register: Callable[[Callable[[float], None]], None],
    ) -> None:
        """
        Bind output channel to native hardware events (Hardware → vdSM).
        """
        if self._output is None:
            raise RuntimeError("Device has no output to bind")

        from ..core.constants import DSChannelType

        try:
            ch_type = DSChannelType(channel_type)
        except ValueError:
            ch_type = channel_type

        channel = self._output.get_channel(ch_type)
        if channel is None:
            raise RuntimeError(f"Output channel {channel_type} not found")

        channel.bind_to_events(register)

    def bind_sensor(
        self,
        sensor_index: int,
        getter: Callable[[], Optional[float]],
        poll_interval: float,
        epsilon: float = 0.0,
    ):
        """
        Bind a sensor to a native hardware value (Hardware → vdSM).

        Args:
            sensor_index: Index of sensor in device
            getter: Function returning native sensor value
            poll_interval: Poll interval in seconds
            epsilon: Minimum change required to publish updates
        """
        if sensor_index >= len(self._sensors):
            raise RuntimeError("Sensor index out of range")

        return self._sensors[sensor_index].bind_to(
            getter=getter,
            poll_interval=poll_interval,
            epsilon=epsilon,
        )

    def bind_sensor_events(
        self,
        sensor_index: int,
        register: Callable[[Callable[[float], None]], None],
    ) -> None:
        """
        Bind sensor to native hardware events (Hardware → vdSM).
        """
        if sensor_index >= len(self._sensors):
            raise RuntimeError("Sensor index out of range")

        self._sensors[sensor_index].bind_to_events(register)

    def bind_binary_input(
        self,
        input_index: int,
        getter: Callable[[], Optional[bool]],
        poll_interval: float,
    ):
        """
        Bind a binary input to a native hardware state (Hardware → vdSM).

        Args:
            input_index: Index of binary input in device
            getter: Function returning native state
            poll_interval: Poll interval in seconds
        """
        if input_index >= len(self._binary_inputs):
            raise RuntimeError("Binary input index out of range")

        return self._binary_inputs[input_index].bind_to(
            getter=getter,
            poll_interval=poll_interval,
        )

    def bind_binary_input_events(
        self,
        input_index: int,
        register: Callable[[Callable[[bool], None]], None],
    ) -> None:
        """
        Bind binary input to native hardware events (Hardware → vdSM).
        """
        if input_index >= len(self._binary_inputs):
            raise RuntimeError("Binary input index out of range")

        self._binary_inputs[input_index].bind_to_events(register)

    def bind_button_input(
        self,
        button_index: int,
        event_getter: Callable[[], Optional[Any]],
        poll_interval: float = 0.1,
    ):
        """
        Bind a button input to native hardware events (Hardware → vdSM).

        Args:
            button_index: Index of button input in device
            event_getter: Function returning the next button event
            poll_interval: Poll interval in seconds
        """
        if button_index >= len(self._button_inputs):
            raise RuntimeError("Button input index out of range")

        return self._button_inputs[button_index].bind_to(
            event_getter=event_getter,
            poll_interval=poll_interval,
        )

    def bind_button_input_events(
        self,
        button_index: int,
        register: Callable[[Callable[[Any], None]], None],
    ) -> None:
        """
        Bind button input to native hardware events (Hardware → vdSM).
        """
        if button_index >= len(self._button_inputs):
            raise RuntimeError("Button input index out of range")

        self._button_inputs[button_index].bind_to_events(register)

    def bind_action_handlers(self, handlers: Dict[str, Callable]) -> None:
        """
        Bind action handlers for this device.

        Supports both full action IDs ("std.identify", "custom.foo") and short names.
        """
        self.actions.bind_handlers(handlers)

    def add_button_input(
        self,
        name: str,
        button_type: int = 0,
        button_id: Optional[int] = None,
        button_element_id: int = 0,
        **properties
    ) -> "ButtonInput":
        """
        Add an API-compliant button input to this device.
        
        ButtonInput accepts clickType values directly, as specified in vDC API
        section 4.2. This is the RECOMMENDED approach for new implementations.
        
        Unlike the legacy Button class (which calculates clickType from timing),
        ButtonInput receives clickType as an integer input from hardware or
        external logic. This matches the vDC API specification.
        
        **IMPORTANT**: This method cannot be called after the device has been
        announced to vdSM. Device structure is immutable after announcement.
        
        Args:
            name: Human-readable button name (e.g., "Light Switch")
            button_type: Physical button type per API
                0 - undefined
                1 - single pushbutton
                2 - 2-way pushbutton
                3 - 4-way navigation button
                4 - 4-way navigation with center button
                5 - 8-way navigation with center button
                6 - on-off switch
            button_id: Physical button ID (optional, for multi-function buttons)
            button_element_id: Element of multi-contact button
                0 - center
                1 - down
                2 - up
                3 - left
                4 - right
                5 - upper left
                6 - lower left
                7 - upper right
                8 - lower right
            **properties: Additional settings (group, function, mode, channel, etc.)
        
        Returns:
            ButtonInput instance
        
        Raises:
            RuntimeError: If device has already been announced to vdSM
        
        Example:
            # Simple button (hardware provides clickType directly)
            button = device.add_button_input(
                name="Power Button",
                button_type=1  # Single pushbutton
            )
            
            # Hardware reports click events
            button.set_click_type(0)  # tip_1x (single tap)
            button.set_click_type(1)  # tip_2x (double tap)
            button.set_click_type(4)  # hold_start (long press)
            
            # Multi-element navigation button (up element)
            nav_up = device.add_button_input(
                name="Navigation Up",
                button_type=4,  # 4-way with center
                button_id=0,
                button_element_id=2,  # Up
                group=1,
                function=0
            )
            
            # With state machine for timing-based detection
            from pyvdcapi.components.button_state_machine import DSButtonStateMachine
            
            button = device.add_button_input(name="Dimmer", button_type=1)
            sm = DSButtonStateMachine(button, enable_hold_repeat=True)
            
            # Hardware calls state machine
            gpio.on_press(sm.on_press)
            gpio.on_release(sm.on_release)
        """
        if self._announced:
            raise RuntimeError(
                f"Cannot add button input to device {self.dsuid} after announcement to vdSM. "
                f"Device structure is immutable once announced per vDC API specification."
            )
        
        from ..components.button_input import ButtonInput

        # Auto-assign button ID based on existing button inputs
        if button_id is None:
            button_id = properties.get("button_id", len(self._button_inputs))

        # Create the button input
        button_input = ButtonInput(
            vdsd=self,
            name=name,
            button_type=button_type,
            button_id=button_id,
            button_element_id=button_element_id,
            **properties
        )

        # Add to device collection
        self._button_inputs.append(button_input)

        logger.info(
            f"Added button input '{name}' (id={button_id}, type={button_type}, "
            f"element={button_element_id}) to vdSD {self.dsuid}"
        )

        return button_input

    def push_button_state(self, button_id: int, click_type: int) -> None:
        """
        Push button state change notification to vdSM.
        
        This method is called by ButtonInput.set_click_type() to notify vdSM
        of button events. It sends a property push notification via the
        protocol.
        
        Args:
            button_id: Button identifier
            click_type: Button click type (0-14, 255)
        
        Note:
            This method will be enhanced to actually send protocol messages
            once the push notification infrastructure is in place.
        """
        logger.debug(
            f"Button {button_id} state push: clickType={click_type} "
            f"(device {self.dsuid})"
        )
        
        # TODO: Implement actual protocol message sending
        # This should create and send a vdc_SendPushNotification message
        # with the button state change.
        #
        # For now, just log the event. The actual implementation will
        # integrate with the VdcHost message sending infrastructure.
        pass

    def push_binary_input_state(self, input_id: int, state: bool) -> None:
        """
        Push binary input state change notification to vdSM.
        
        This method is called by BinaryInput.set_state() when the input state
        changes (e.g., motion detected, door opened). It sends a property push
        notification via the protocol.
        
        Pattern: Device → DSS (Pattern A)
        The device detects a state change and immediately notifies vdSM.
        
        Args:
            input_id: Binary input identifier (0..N-1)
            state: New state (True=active, False=inactive)
        
        Example:
            # Motion sensor detects movement
            binary_input.set_state(True)  # Triggers this push notification
        """
        logger.debug(
            f"Binary input {input_id} state push: state={state} "
            f"(device {self.dsuid})"
        )
        
        # Create push notification with binary input state
        # Per API section 4.3.3, push includes value and age
        properties = {
            "binaryInputs": {
                str(input_id): {
                    "state": {
                        "value": state,
                        "age": 0.0  # Age is 0 at moment of change
                    }
                }
            }
        }
        
        # Send push notification asynchronously
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._send_push_notification(properties))
            else:
                loop.run_until_complete(self._send_push_notification(properties))
        except RuntimeError:
            # No event loop, can't send notification
            logger.warning("No event loop available for binary input push notification")

    def push_sensor_value(self, sensor_id: int, value: float) -> None:
        """
        Push sensor value change notification to vdSM.
        
        This method is called by Sensor.update_value() when a significant sensor
        value change is detected (exceeding hysteresis threshold). It sends a
        property push notification via the protocol.
        
        Pattern: Device → DSS (Pattern A)
        The device measures a sensor value change and notifies vdSM.
        
        Note:
            Per vDC API convention, sensors are typically polled by vdSM rather
            than pushing every change. Push notifications are sent only for
            significant changes (beyond hysteresis) to reduce network traffic.
        
        Args:
            sensor_id: Sensor identifier (0..N-1)
            value: New sensor value
        
        Example:
            # Temperature sensor detects 2°C change (exceeds hysteresis)
            sensor.update_value(22.5)  # Triggers this push notification
        """
        logger.debug(
            f"Sensor {sensor_id} value push: value={value} "
            f"(device {self.dsuid})"
        )
        
        # Create push notification with sensor value
        # Per API section 4.4.3, push includes value and age
        properties = {
            "sensors": {
                str(sensor_id): {
                    "value": value,
                    "age": 0.0  # Age is 0 at moment of change
                }
            }
        }
        
        # Send push notification asynchronously
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._send_push_notification(properties))
            else:
                loop.run_until_complete(self._send_push_notification(properties))
        except RuntimeError:
            # No event loop, can't send notification
            logger.warning("No event loop available for sensor push notification")

    def push_output_channel_value(self, channel_index: int, value: float) -> None:
        """
        Push output channel value change notification to vdSM.
        
        This method is called by OutputChannel.update_value() when the hardware
        changes an output value independently (not in response to DSS command).
        
        Pattern: Device → DSS (Pattern C - Bidirectional, Device→DSS direction)
        
        CRITICAL DISTINCTION:
        - OutputChannel.set_value() - DSS → Device: Does NOT call this (no echo back)
        - OutputChannel.update_value() - Device → DSS: DOES call this (notify DSS)
        
        This bidirectional pattern is unique to output channels:
        - DSS can set values via set_value() → hardware callback → no push
        - Hardware can change values → update_value() → push to DSS
        
        Args:
            channel_index: Output channel index (brightness=0, hue=1, saturation=2, etc.)
            value: New channel value
        
        Example:
            # User manually adjusts dimmer on wall switch
            # Hardware detects change and updates local state
            channel.update_value(75.0)  # Triggers this push to inform DSS
        """
        logger.debug(
            f"Output channel {channel_index} value push: value={value} "
            f"(device {self.dsuid})"
        )
        
        # Create push notification with output channel value
        # Per API section 4.9.2, push includes value and age
        properties = {
            "outputChannels": {
                str(channel_index): {
                    "value": value,
                    "age": 0.0  # Age is 0 at moment of change
                }
            }
        }
        
        # Send push notification asynchronously
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._send_push_notification(properties))
            else:
                loop.run_until_complete(self._send_push_notification(properties))
        except RuntimeError:
            # No event loop, can't send notification
            logger.warning("No event loop available for output channel push notification")

    def add_binary_input(
        self,
        name: str,
        input_type: str,
        **properties,
    ) -> "BinaryInput":
        """
        Add a binary input to this device.

        Binary inputs represent two-state conditions:
        - Motion detector (motion detected / no motion)
        - Door/window contact (open / closed)
        - Presence sensor (present / absent)
        - Water leak detector (leak / no leak)

        Args:
            name: Human-readable name for the binary input
            input_type: Type of binary input (motion, contact, presence, etc.)
            **properties: Additional binary input properties

        Returns:
            BinaryInput instance

        Raises:
            RuntimeError: If device has already been announced to vdSM

        Example:
            # Motion sensor
            motion = device.add_binary_input(
                name="Living Room Motion",
                input_type="motion"
            )

            # Update state from hardware
            motion.update_state(True)  # Motion detected

        Note:
            This method cannot be called after the device has been announced
            to vdSM. Device structure becomes immutable at announcement per
            vDC API specification. To modify a device, you must:
            1. Call vanish() on the old device
            2. Create a new device with desired structure
            3. Announce the new device
        """
        if self._announced:
            raise RuntimeError(
                f"Cannot add binary input to device {self.dsuid} after announcement to vdSM. "
                f"Device structure is immutable once announced per vDC API specification. "
                f"To modify device structure: 1) call vanish() on this device, "
                f"2) create new device with desired structure, 3) announce new device."
            )

        from pyvdcapi.components.binary_input import BinaryInput

        binary_input = BinaryInput(
            vdsd=self,
            name=name,
            input_type=input_type,
            **properties
        )
        self._binary_inputs.append(binary_input)

        logger.info(
            f"Added binary input '{name}' (type: {input_type}) to device {self.dsuid}"
        )

        return binary_input

    def add_sensor(
        self,
        sensor_type: str,
        unit: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        **properties,
    ) -> "Sensor":
        """
        Add a sensor input to this device.

        Sensors provide continuous or periodic value readings:
        - Temperature
        - Humidity
        - Illuminance (light level)
        - Power consumption
        - Air quality

        Args:
            sensor_type: Type of sensor (temperature, humidity, etc.)
            unit: Unit of measurement (°C, %, lux, W, ppm, etc.)
            min_value: Minimum possible value (for validation/scaling)
            max_value: Maximum possible value
            **properties: Additional sensor properties

        Returns:
            Sensor instance

        Example:
            # Temperature sensor
            temp_sensor = device.add_sensor(
                sensor_type="temperature",
                unit="°C",
                min_value=-40.0,
                max_value=125.0
            )

            # Update sensor value from hardware
            temp_sensor.update_value(22.5)  # Room temperature
        """
        if self._announced:
            raise RuntimeError(
                f"Cannot add sensor to device {self.dsuid} after announcement to vdSM. "
                f"Device structure is immutable once announced per vDC API specification."
            )
        
        from ..components.sensor import Sensor

        # Auto-assign sensor ID based on existing sensors
        sensor_id = properties.get("sensor_id", len(self._sensors))

        # Get sensor name from properties or generate from type
        sensor_name = properties.get("name", f"{sensor_type.capitalize()} Sensor")

        # Create the sensor
        sensor = Sensor(
            vdsd=self,
            name=sensor_name,
            sensor_type=sensor_type,
            unit=unit,
            sensor_id=sensor_id,
            min_value=min_value,
            max_value=max_value,
            resolution=properties.get("resolution", 0.1),
            initial_value=properties.get("initial_value"),
        )

        # Add to device's sensor list
        self._sensors.append(sensor)

        logger.info(f"Added sensor '{sensor_name}' (type={sensor_type}, unit={unit}) " f"to vdSD {self.dsuid}")

        return sensor

    def set_scene(
        self,
        scene_number: int,
        channel_values: Dict[int, float],
        effect: int = DSSceneEffect.SMOOTH,
        dont_care: bool = False,
        ignore_local_priority: bool = False,
        **properties,
    ) -> None:
        """
        Configure a scene for this device.

        Scenes store preset configurations that can be recalled later.
        Each scene defines:
        - Values for each output channel
        - Transition effect (how to reach values)
        - Don't care flag (whether device participates)
        - Ignore local priority flag (whether scene bypasses priority lock)

        Args:
            scene_number: Scene number (0-127, see DSScene enum)
            channel_values: Dict mapping channel type to target value
            effect: Transition effect (DSSceneEffect enum)
            dont_care: If True, device ignores this scene
            ignore_local_priority: If True, scene can bypass localPriority lock
            **properties: Additional scene properties

        Example:
            # Configure "Present" scene for a dimmer
            device.set_scene(
                scene_number=DSScene.PRESENT,
                channel_values={
                    DSChannelType.BRIGHTNESS: 75.0
                },
                effect=DSSceneEffect.SMOOTH
            )

            # Configure "Deep Off" scene
            device.set_scene(
                scene_number=DSScene.DEEP_OFF,
                channel_values={
                    DSChannelType.BRIGHTNESS: 0.0
                },
                effect=DSSceneEffect.SMOOTH
            )

            # Configure color scene for RGB light
            device.set_scene(
                scene_number=DSScene.PRESET_0,
                channel_values={
                    DSChannelType.BRIGHTNESS: 100.0,
                    DSChannelType.HUE: 120.0,  # Green
                    DSChannelType.SATURATION: 100.0
                },
                effect=DSSceneEffect.SMOOTH
            )
        """
        scene_config = {
            "channels": channel_values,
            "effect": effect,
            "dontCare": dont_care,
            "ignoreLocalPriority": ignore_local_priority,
            **properties
        }

        self._scenes[scene_number] = scene_config

        # Persist scene configuration
        self._save_scenes()

        logger.debug(
            f"Configured scene {scene_number} for vdSD {self.dsuid}: "
            f"channels={list(channel_values.keys())}, effect={effect}"
        )

    # Duplicate synchronous scene helpers were removed in favor of
    # the async protocol-aware implementations defined later in this file.

    def get_properties(self, query: Any) -> Any:
        """
        Get device properties based on query.

        Builds a property tree containing:
        - Common properties (dSUID, name, model, etc.)
        - vdSD-specific properties (primaryGroup, zoneID, etc.)
        - Output channel descriptions and states
        - Input configurations
        - Scene configurations

        Args:
            query: PropertyElement tree specifying what to retrieve

        Returns:
            PropertyElement tree with requested properties
        """
        # Merge all properties
        props = {}

        # Add common properties
        props.update(self._common_props.to_dict())

        # Add vdSD-specific properties
        props.update(self._vdsd_props.to_dict())

        # Add output information (output can have multiple channels)
        if self._output:
            props["output"] = self._output.to_dict()

        # Add input information
        inputs = []
        # All button inputs are now API-compliant ButtonInput instances
        inputs.extend([bi.to_dict() for bi in self._binary_inputs])
        inputs.extend([sensor.to_dict() for sensor in self._sensors])
        if inputs:
            props["inputs"] = inputs

        # Add scene information (if queried)
        if self._scenes:
            props["scenes"] = {str(scene_no): scene_config for scene_no, scene_config in self._scenes.items()}

        # Add actions (templates, standard, custom, dynamic)
        props.update(self.actions.to_dict())

        # Add states (descriptions and current values)
        props.update(self.states.to_dict())

        # Add device properties
        props.update(self.device_properties.to_dict())

        # If a query is provided, filter the properties accordingly
        try:
            if query and len(query) > 0:
                filtered = PropertyTree.filter_dict_by_query(props, query)
            else:
                filtered = props
        except Exception:
            filtered = props

        # Convert to PropertyElement tree
        return PropertyTree.to_protobuf(filtered)

    def set_properties(self, properties: Any) -> None:
        """
        Set device properties from PropertyElement tree.

        Args:
            properties: PropertyElement tree with new values
        """
        # Convert PropertyElement to dict
        prop_dict = PropertyTree.from_protobuf(properties)

        logger.debug(f"Setting vdSD properties: {prop_dict.keys()}")

        # Update common properties
        try:
            self._common_props.update_from_dict(prop_dict)
        except Exception:
            # Fallback if object doesn't provide update_from_dict
            for k, v in prop_dict.items():
                try:
                    self._common_props.set_property(k, v)
                except Exception:
                    pass

        # Update vdSD-specific properties
        try:
            # Use dedicated update method when available
            self._vdsd_props.update_from_dict(prop_dict)
        except Exception:
            # Fallback: attempt to set writable properties via set_property
            for k, v in prop_dict.items():
                try:
                    self._vdsd_props.set_property(k, v)
                except Exception:
                    pass

        # Handle output value changes from vdSM
        if "outputs" in prop_dict:
            self._apply_output_changes(prop_dict["outputs"])

        # Persist changes
        self._save_config()

    def announce_to_vdsm(self) -> Any:
        """
        Create device announcement message for vdSM.

        Returns:
            Message with vdc_SendAnnounceDevice
        """
        message = genericVDC_pb2.Message()  # type: ignore[attr-defined]
        message.type = genericVDC_pb2.VDC_SEND_ANNOUNCE_DEVICE  # type: ignore[attr-defined]
        # Optionally set message_id when host/session has previously
        # received a non-zero id (use last_received + 1). Otherwise leave
        # the envelope id absent on the wire.
        try:
            next_id = None
            if hasattr(self, "vdc") and getattr(self.vdc, "host", None):
                next_id = self.vdc.host._next_message_id_if_have_received()
            if next_id:
                message.message_id = int(next_id)
        except Exception:
            pass

        announce = message.vdc_send_announce_device
        announce.dSUID = self.dsuid
        # vdc_SendAnnounceDevice requires the owning vDC dSUID as well
        try:
            announce.vdc_dSUID = self.vdc.dsuid
        except Exception:
            # Ensure message remains conformant: set empty string if unavailable
            try:
                announce.vdc_dSUID = ""
            except Exception:
                pass

        logger.debug(f"Created device announcement for {self.dsuid}")

        return message

    def mark_announced(self) -> None:
        """
        Mark this device as announced to vdSM.
        
        After announcement, device structure becomes immutable per vDC API spec.
        Features (outputs, buttons, sensors) cannot be added after announcement.
        
        To modify device capabilities after announcement:
        1. Send vanish notification: vdc.vanish_device(dsuid)
        2. Delete device: vdc.delete_vdsd(dsuid)
        3. Create new device with desired configuration
        4. New device will be announced on next vdSM connection
        """
        self._announced = True
        logger.info(f"Device {self.dsuid} marked as announced - structure now immutable")

    def _save_config(self) -> None:
        """Save device configuration to persistence."""
        config = {**self._common_props.to_dict(), **self._vdsd_props.to_dict(), "vdc_dSUID": self.vdc.dsuid}

        # Add output configuration
        if self._output:
            config["output"] = self._output.to_dict()

        self._persistence.set_vdsd(self.dsuid, config)

    def _apply_output_changes(self, output_data: Dict[str, Any]) -> None:
        """
        Apply output value changes from vdSM.

        This is called when vdSM sends property changes for the output.
        Values are applied to the Output/OutputChannel objects and
        hardware callbacks are triggered.

        Args:
            output_data: Output property dictionary from vdSM
        """
        if not self._output:
            logger.warning(f"vdSD {self.dsuid} has no output")
            return

        # Update output configuration
        self._output.from_dict(output_data)

        # Apply channel value changes
        if "channels" in output_data:
            channels = output_data["channels"]
            # If channels is a mapping from channelType->data
            if isinstance(channels, dict):
                items = channels.items()
            else:
                # List of channel entries
                # Convert to (channelTypeStr, channel_data) pairs
                def _iter_list(lst):
                    for ch in lst:
                        key = ch.get("channelType") or ch.get("channelType", None)
                        yield (str(int(key)) if key is not None else None, ch)

                items = _iter_list(channels)

                for channel_type_str, channel_data in items:
                    try:
                        if channel_type_str is None:
                            continue
                        channel_type = DSChannelType(int(channel_type_str))
                        if "value" in channel_data:
                            # Apply the value change (triggers hardware callback)
                            self._output.set_channel_value(
                                channel_type, channel_data["value"], transition_time=channel_data.get("transitionTime")
                            )
                            logger.info(
                                f"vdSD {self.dsuid}: Set output "
                                f"channel {channel_type} to {channel_data['value']}"
                            )
                    except (ValueError, KeyError) as e:
                        logger.error(f"Error applying channel value: {e}")

    def _save_scenes(self) -> None:
        """Save scene configurations to persistence."""
        # Update scenes in config
        self._persistence.update_vdsd_property(self.dsuid, "scenes", self._scenes)

    def _initialize_common_states(self) -> None:
        """
        Initialize common device states required by vDC API specification.

        Adds three standard states to all devices:
        1. operational: Device operational status (off, initializing, running, error, shutdown)
        2. reachable: Network connectivity status (unreachable, reachable)
        3. service: Service mode indicator (normal, service)

        Initial values: operational=running, reachable=reachable, service=normal
        """
        # Operational state
        self.states.add_state_description(
            name="operational",
            options={0: "off", 1: "initializing", 2: "running", 3: "error", 4: "shutdown"},
            description="Device operational state",
        )

        # Reachable state (network connectivity)
        self.states.add_state_description(
            name="reachable", options={0: "unreachable", 1: "reachable"}, description="Network connectivity status"
        )

        # Service mode
        self.states.add_state_description(
            name="service", options={0: "normal", 1: "service"}, description="Service mode indicator"
        )

        # Set initial state to running and reachable
        self.states.set_state("operational", "running")
        self.states.set_state("reachable", "reachable")
        self.states.set_state("service", "normal")

    def _initialize_common_actions(self) -> None:
        """
        Initialize common device actions required by vDC API specification.

        Adds standard action:
        - identify: Make device identifiable by blinking LED or audible signal
          Parameter: duration (1.0-60.0 seconds, default 3.0s)

        This action allows users to physically locate devices during setup.
        """
        from ..components.actions import ActionParameter

        # Identify action (make device identifiable)
        def identify_handler(duration: float = 3.0) -> Dict[str, Any]:
            """
            Identify device by blinking or making audible signal.

            Args:
                duration: Duration in seconds

            Returns:
                Result dictionary
            """
            logger.info(f"Identify device {self.dsuid} for {duration}s")
            # TODO: Trigger hardware identification (blink LED, beep, etc.)
            # This would typically call a hardware callback
            return {"success": True, "duration": duration}

        self.actions.add_standard_action(
            name="identify",
            description="Identify device by blinking or audible signal",
            params={
                "duration": ActionParameter(
                    param_type="numeric", min_value=1.0, max_value=60.0, default=3.0, siunit="s"
                )
            },
            handler=identify_handler,
        )

    def __repr__(self) -> str:
        """String representation of device."""
        name = self._common_props.get_property("name")
        primary_group = self._vdsd_props.get_property("primaryGroup")
        return (
            f"VdSD(dsuid='{self.dsuid}', "
            f"name='{name}', "
            f"group={primary_group}, "
            f"output={'yes' if self._output else 'no'})"
        )

    # ===================================================================
    # Scene Operations (Protocol Integration)
    # ===================================================================

    async def call_scene(self, scene: int, force: bool = False, mode: str = "normal") -> None:
        """
        Call/activate a scene on this device.

        Scenes represent predefined configurations that set output values
        to specific states (e.g., "Full On", "Preset 1", "Deep Off").

        Args:
            scene: Scene number (0-127)
                   - 0-63: Device scenes
                   - 64-127: Group/area scenes
            force: Force execution even if scene is already active
            mode: Scene call mode:
                  - 'normal': Apply scene unconditionally
                  - 'min': Apply only if scene values are higher than current

        Scene Execution Flow:
            1. Look up scene configuration
            2. Apply output values (with effects/transitions)
            3. Save current state to undo stack
            4. Trigger hardware callbacks
            5. Send push notifications to vdSM

        Effects:
            - Smooth (default): Fade transition
            - Slow: Slower fade (e.g., sunset simulation)
            - Alert: Blink/flash effect

        Example:
            # Call "Full On" scene (scene 5)
            await device.call_scene(5)

            # Call "Preset 1" with forced execution
            await device.call_scene(17, force=True)

            # Call scene only if it increases brightness
            await device.call_scene(5, mode='min')
        """
        logger.info(f"Call scene {scene} on device {self.dsuid} (force={force}, mode={mode})")

        # Check local priority enforcement
        if self._local_priority_scene is not None and not force:
            scene_config_check = self._scenes.get(scene, {})
            ignore_priority = scene_config_check.get("ignoreLocalPriority", False)
            
            if not ignore_priority and scene != self._local_priority_scene:
                logger.info(
                    f"Scene {scene} blocked by local priority "
                    f"(active priority: {self._local_priority_scene}). "
                    f"Use force=True to override."
                )
                return

        # Get scene configuration
        scene_config = self._scenes.get(scene, {})

        if not scene_config and not force:
            logger.warning(f"Scene {scene} not configured on device {self.dsuid}")
            return

        # Save current state to undo stack (before applying scene)
        self._save_undo_state()

        # Get scene values for the output
        if self._output:
            scene_output = scene_config.get("output", {})
            scene_values = scene_output.get("channels", {})

            if scene_values:
                # Get effect for transition
                effect = scene_config.get("effect", DSSceneEffect.SMOOTH)

                # Apply scene values to output
                if mode == "min":
                    # Only apply if scene values are higher
                    self._output.apply_scene_values(scene_values, effect=effect, mode="min")
                else:
                    # Normal: apply unconditionally
                    self._output.apply_scene_values(scene_values, effect=effect)

        # Notify vdSM of changes (if outputs changed)
        await self._send_push_notification()

    async def save_scene(self, scene: int, ignore_local_priority: bool = False) -> None:
        """
        Save current output values to a scene number.

        Captures a "snapshot" of current device state for later recall.
        This allows users to create custom scenes with their preferred settings.

        Args:
            scene: Scene number to save to (0-127)
            ignore_local_priority: If True, scene can bypass localPriority lock

        Scene Storage:
            - Scene configurations stored in YAML persistence
            - Includes all output channel values
            - Optionally includes effect settings
            - ignoreLocalPriority flag for priority bypass

        Example:
            # Set brightness to 75%
            await device.get_output().set_channel_value(DSChannelType.BRIGHTNESS, 75.0)

            # Save current state as scene 17 ("Preset 1")
            await device.save_scene(17)
            
            # Save scene that can bypass local priority
            await device.save_scene(5, ignore_local_priority=True)

            # Later, recall this exact state
            await device.call_scene(17)
        """
        logger.info(f"Save scene {scene} on device {self.dsuid}")

        # Capture current output values
        scene_config: Dict[str, Any] = {"ignoreLocalPriority": ignore_local_priority}

        if self._output:
            # Get all channel values
            channel_values = self._output.get_all_channel_values()

            if channel_values:
                scene_config["output"] = {"channels": channel_values}

        # Store in scenes dictionary
        self._scenes[scene] = scene_config

        logger.info(
            f"Saved scene {scene} on device {self.dsuid} "
            f"(ignoreLocalPriority={ignore_local_priority})"
        )

        # Persist to YAML
        self._save_scenes()

        # Notify vdSM that scenes changed
        await self._send_push_notification({"scenes": {scene: scene_config}})

    async def undo_scene(self) -> None:
        """
        Undo the last scene call and restore previous state.

        Pops the most recent state from the undo stack and restores
        all output values to their previous configuration.

        Undo Stack:
            - Limited depth (typically 1-5 levels)
            - LIFO (Last In, First Out)
            - Contains full output snapshots

        Use Cases:
            - "Oops, didn't mean to turn everything off"
            - "Go back to previous brightness"
            - Experimentation without losing state

        Example:
            await device.call_scene(0)  # Turn off
            # User: "Wait, I didn't want that!"
            await device.undo_scene()   # Restore previous state
        """
        logger.info(f"Undo scene on device {self.dsuid}")

        if not hasattr(self, "_undo_stack"):
            self._undo_stack = []

        if not self._undo_stack:
            logger.warning(f"No undo state available for device {self.dsuid}")
            return

        # Pop last state from stack
        previous_state = self._undo_stack.pop()

        # Restore output values
        if self._output and previous_state:
            for channel_type, value in previous_state.items():
                self._output.set_channel_value(channel_type, value, apply_now=True)

        # Notify vdSM
        await self._send_push_notification()

    def _save_undo_state(self) -> None:
        """
        Save current output state to undo stack.

        Called before applying a scene to enable undo functionality.
        """
        if not hasattr(self, "_undo_stack"):
            self._undo_stack = []

        # Capture current state
        current_state = None
        if self._output:
            current_state = self._output.get_all_channel_values()

        # Add to stack (limit depth to 5)
        if current_state:
            self._undo_stack.append(current_state)
            if len(self._undo_stack) > 5:
                self._undo_stack.pop(0)

    async def identify(self, duration: float = 3.0) -> None:
        """
        Identify device by blinking, beeping, or other visual/audible signal.

        Used during commissioning to find physical devices.
        Implementation is hardware-specific.

        Args:
            duration: Duration in seconds (default: 3.0)

        Common Implementations:
            - Lights: Blink rapidly
            - Speakers: Play tone
            - Motors: Move back and forth
            - LEDs: Flash identification pattern

        Example:
            # Identify device for 5 seconds
            await device.identify(duration=5.0)
        """
        logger.info(f"Identify device {self.dsuid} for {duration}s")

        # Try to call the action if it exists
        if self.actions.has_action("identify"):
            await self.actions.call_action("identify", duration=duration)
        else:
            # Default implementation: blink output if available
            output = self._output
            if output:
                # Save current state
                original_values = output.get_all_channel_values()

                # Blink pattern (on-off-on-off)
                blink_count = int(duration * 2)  # 2 blinks per second
                for _ in range(blink_count):
                    # Turn on
                    output.set_channel_value(DSChannelType.BRIGHTNESS, 100.0, apply_now=True)
                    await asyncio.sleep(0.25)

                    # Turn off
                    output.set_channel_value(DSChannelType.BRIGHTNESS, 0.0, apply_now=True)
                    await asyncio.sleep(0.25)

                # Restore original state
                for channel_type, value in original_values.items():
                    output.set_channel_value(channel_type, value, apply_now=True)

    def set_local_priority(self, scene: Optional[int] = None) -> None:
        """
        Set local priority scene lock.
        
        When a local priority scene is set, only that scene (or scenes with
        ignoreLocalPriority=True) can be called. Other scene calls are blocked
        unless force=True is used.
        
        This is a dS 1.0 compatibility feature for local device control priority.
        
        Args:
            scene: Scene number to lock (0-127), or None to clear priority
            
        Example:
            # Lock to scene 10 (local control)
            device.set_local_priority(10)
            
            await device.call_scene(5)  # Blocked (not priority scene)
            await device.call_scene(10)  # Allowed (matches priority)
            await device.call_scene(5, force=True)  # Allowed (force override)
            
            # Clear priority
            device.set_local_priority(None)
            await device.call_scene(5)  # Now allowed
        """
        self._local_priority_scene = scene
        
        if scene is not None:
            logger.info(f"Local priority set to scene {scene} on device {self.dsuid}")
        else:
            logger.info(f"Local priority cleared on device {self.dsuid}")
        
        # Persist priority settings
        if self._persistence:
            self._persistence.update_vdsd_property(self.dsuid, "local_priority_scene", scene)

    def get_control_value(self, control_name: str) -> Optional[float]:
        """
        Get a control value (device-side read-only access).

        This is the RECOMMENDED way for device hardware to read control values
        that were set by DSS. Control values are write-only from DSS perspective
        (acc="w"), but read-only from device perspective.

        Args:
            control_name: Name of control (e.g., "heatingLevel")

        Returns:
            Current value or None if not set

        Example:
            # Device reads heatingLevel to control radiator
            heating = device.get_control_value("heatingLevel")
            if heating is not None:
                adjust_radiator_valve(heating)
        """
        cv = self.controlValues.get(control_name)
        return cv.value if cv else None

    def set_control_value(self, control_name: str, value: float) -> None:
        """
        Set a control value (INTERNAL - called by vDC host when DSS sends update).

        ⚠️  WARNING: This method should ONLY be called by the vDC host when processing
        SetControlValue notifications from DSS. Device code should NOT call this method
        directly - devices should only READ control values via get_control_value() or
        controlValues.get().

        Control values are:
        - Write-only from DSS perspective (DSS writes, never reads)
        - Read-only from device perspective (device reads, should not write)

        This ensures proper data flow: DSS → vDC → Device Hardware

        Args:
            control_name: Name of control (e.g., "heatingLevel")
            value: Control value (-100 to +100 for heatingLevel)

        Proper Usage:
            # ❌ INCORRECT (device arbitrarily writing):
            # device.set_control_value("heatingLevel", 50.0)

            # ✅ CORRECT (device reading):
            # heating = device.get_control_value("heatingLevel")

        Internal Flow:
            1. DSS sends SetControlValue notification
            2. VdcHost routes to this method
            3. Control value updated and persisted
            4. Hardware callback triggered
            5. Push notification sent to vdSM
        """
        logger.info(f"Set control '{control_name}' to {value} on device {self.dsuid}")

        # Update or create ControlValue instance in container
        try:
            self.controlValues.set(control_name, value)
        except Exception:
            # Fallback: ensure a dict container exists
            if not hasattr(self, "_control_values"):
                self._control_values = {}
            self._control_values[control_name] = value

        # Trigger hardware callback if registered
        # Note: _hardware_callbacks removed in favor of Observable pattern
        pass

        # Persist control values mapping so it is available via persistence for vdSM queries
        try:
            if hasattr(self, "_persistence") and self._persistence:
                # Persist full controlValues dict under 'controlValues'
                self._persistence.update_vdsd_property(self.dsuid, "controlValues", self.controlValues.to_persistence())
        except Exception as e:
            logger.warning(f"Unable to persist control value for {self.dsuid}: {e}")

        # Notify vdSM about the updated control value (async)
        try:
            host = getattr(self.vdc, "host", None)
            if host and hasattr(host, "send_push_notification"):
                try:
                    asyncio.get_event_loop().create_task(
                        host.send_push_notification(self.dsuid, {"controlValues": {control_name: float(value)}})
                    )
                except RuntimeError:
                    # No running event loop; ignore push
                    pass
        except Exception:
            pass

    async def _send_push_notification(self, properties: Optional[dict] = None) -> None:
        """
        Send push notification to vdSM via host.

        Args:
            properties: Optional specific properties to push
        """
        # Get host reference
        if hasattr(self.vdc, "host"):
            host = self.vdc.host
            if host:
                await host.send_push_notification(self.dsuid, properties)

    def _on_output_change(self, channel_type: DSChannelType, value: float) -> None:
        """
        Callback when output channel value changes.

        Triggered by Output when a channel value is set.
        This sends a push notification to vdSM.

        Args:
            channel_type: Channel that changed
            value: New value
        """
        logger.debug(f"Output channel {channel_type} changed to {value}")

        # Create push notification with channel values
        properties = {"output": {"channels": {str(channel_type.value): {"value": value}}}}

        # Send push notification asynchronously
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._send_push_notification(properties))
            else:
                loop.run_until_complete(self._send_push_notification(properties))
        except RuntimeError:
            # No event loop, can't send notification
            logger.warning("No event loop available for push notification")

    def save(self) -> None:
        """
        Save device configuration to persistence layer.

        Persists current device state including:
        - Common properties (name, model, etc.)
        - Device-specific properties (primaryGroup, etc.)
        - Component configurations (outputs, buttons, sensors)
        - Scene configurations

        The configuration is saved to YAML via the persistence layer
        and will be automatically reloaded on next initialization.

        Example:
            # Modify device properties
            device._common_props.set('name', 'Updated Name')

            # Save changes
            device.save()
        """
        # Build configuration dict from current state
        config = {
            "dSUID": self.dsuid,
            "type": "vdSD",
            "vdc_dSUID": self.vdc.dsuid,
            **self._common_props.to_dict(),
            **self._vdsd_props.to_dict(),
        }

        # Save to persistence
        self._persistence.set_vdsd(self.dsuid, config)

        logger.info(f"Saved configuration for vdSD {self.dsuid}")

    def save_as_template(
        self,
        template_name: str,
        template_type: str = "deviceType",
        description: Optional[str] = None,
        vendor: Optional[str] = None,
        vendor_model_id: Optional[str] = None,
    ) -> str:
        """
        Save this device configuration as a reusable template.

        Templates allow creating new device instances with the same configuration
        but minimal instance-specific information (name, enumeration).

        Args:
            template_name: Unique name for the template
            template_type: "deviceType" (standard hardware) or "vendorType" (vendor-specific)
            description: Optional human-readable description
            vendor: Optional vendor name (recommended for vendorType)
            vendor_model_id: Optional vendor model identifier

        Returns:
            Path to the created template file

        Example:
            # Save as standard device type
            light.save_as_template(
                template_name="simple_onoff_light",
                template_type="deviceType",
                description="Simple on/off light with 50% threshold"
            )

            # Save as vendor-specific type
            hue_light.save_as_template(
                template_name="philips_hue_lily_spot",
                template_type="vendorType",
                description="Philips HUE Lily Garden Spot",
                vendor="Philips",
                vendor_model_id="915005730801"
            )
        """
        from pyvdcapi.templates import TemplateManager, TemplateType

        template_mgr = TemplateManager()
        ttype = TemplateType.VENDOR_TYPE if template_type == "vendorType" else TemplateType.DEVICE_TYPE

        return template_mgr.save_device_as_template(
            vdsd=self,
            template_name=template_name,
            template_type=ttype,
            description=description,
            vendor=vendor,
            vendor_model_id=vendor_model_id,
        )

