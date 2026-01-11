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
    primary_group=DSGroup.YELLOW,
    output_function=DSOutputFunction.DIMMER
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
dimmer.add_button(
    name="Toggle Button",
    button_type=0,  # Single press
    on_press=lambda: dimmer.toggle_output()
)

# Configure scenes
dimmer.set_scene(DSScene.PRESENT, {
    DSChannelType.BRIGHTNESS: 75.0
}, effect=DSSceneEffect.SMOOTH)

# Set up hardware callback
def apply_to_hardware(channel_type, value):
    # Send to actual hardware
    hardware.set_brightness(value)
    print(f"Applied brightness: {value}%")

dimmer.on_output_change(apply_to_hardware)
```
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from genericVDC_pb2 import Message

from ..core.dsuid import DSUIDGenerator, DSUIDNamespace
from ..core.constants import DSScene, DSChannelType, DSSceneEffect
from ..properties.common import CommonProperties
from ..properties.vdsd_props import VdSDProperties
from ..properties.property_tree import PropertyTree
from ..utils.callbacks import Observable

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
        vdc: 'Vdc',
        name: str,
        model: str,
        primary_group: int,
        mac_address: str,
        vendor_id: str,
        enumeration: int = 0,
        model_uid: Optional[str] = None,
        model_version: str = "1.0",
        **properties
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
        self.dsuid = dsuid_gen.generate(
            DSUIDNamespace.VDSD,
            enumeration=enumeration
        )
        
        logger.info(f"Initializing vdSD with dSUID: {self.dsuid}")
        
        # Parent reference
        self.vdc = vdc
        
        # Persistence (shared with vDC)
        self._persistence = vdc._persistence
        
        # Load or initialize device configuration
        vdsd_config = self._persistence.get_vdsd(self.dsuid)
        if not vdsd_config:
            # First time - initialize with provided properties
            vdsd_config = {
                'dSUID': self.dsuid,
                'type': 'vDSD',
                'vdc_dSUID': vdc.dsuid,  # Link to parent vDC
                'name': name,
                'model': model,
                'primaryGroup': primary_group,
                'enumeration': enumeration,
                **properties
            }
            self._persistence.set_vdsd(self.dsuid, vdsd_config)
        
        # Common properties (dSUID, name, model, etc.)
        # Extract explicitly handled properties to avoid duplicates
        extra_props = {k: v for k, v in vdsd_config.items() 
                      if k not in ['name', 'model', 'model_uid', 'model_version', 'primary_group', 'enumeration', 'type', 'dSUID']}
        
        self._common_props = CommonProperties(
            dsuid=self.dsuid,
            entity_type='vDSD',
            name=name,
            model=model,
            model_uid=model_uid,
            model_version=model_version if model_version else "",
            **extra_props
        )
        
        # vdSD-specific properties (primaryGroup, modelFeatures, etc.)
        self._vdsd_props = VdSDProperties(
            primary_group=primary_group,
            **vdsd_config
        )
        
        # Device components
        # These will hold the actual input/output/scene components
        self._outputs: Dict[int, 'Output'] = {}  # outputID -> Output (contains OutputChannels)
        self._buttons: List['Button'] = []
        self._binary_inputs: List['BinaryInput'] = []
        self._sensors: List['Sensor'] = []
        self._scenes: Dict[int, Dict] = {}  # sceneNo -> scene config
        
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
        self._active = vdsd_config.get('active', True)
        
        logger.info(
            f"vdSD initialized: name='{name}', "
            f"model='{model}', "
            f"group={primary_group}"
        )
    
    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure device with all capabilities from a configuration dictionary.
        
        This method allows bulk configuration of a device after creation,
        useful for:
        - Loading from persistence/YAML
        - Applying device templates
        - Cloning device configurations
        - API-driven device setup
        
        Args:
            config: Configuration dictionary containing:
                - outputs: List of output configurations
                - buttons: List of button configurations
                - binary_inputs: List of binary input configurations
                - sensors: List of sensor configurations
                - scenes: Dictionary of scene configurations
                - actions: Custom/dynamic actions
                - states: Initial state values
                - properties: Device properties
        
        Example:
            # Configure a complete RGB light
            device.configure({
                'outputs': [{
                    'outputID': 0,
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
        from ..components import Output, OutputChannel, Button, BinaryInput, Sensor
        
        logger.info(f"Configuring vdSD {self.dsuid} from config")
        
        # Configure outputs
        if 'outputs' in config:
            for output_config in config['outputs']:
                output = Output(
                    vdsd=self,
                    output_id=output_config.get('outputID', 0),
                    output_function=output_config.get('outputFunction', 'dimmer'),
                    output_mode=output_config.get('outputMode', 'gradual'),
                    push_changes=output_config.get('pushChanges', True)
                )
                
                # Add channels to output
                if 'channels' in output_config:
                    for channel_config in output_config['channels']:
                        channel = OutputChannel(
                            vdsd=self,
                            channel_type=channel_config.get('channelType'),
                            name=channel_config.get('name', ''),
                            min_value=channel_config.get('min', 0.0),
                            max_value=channel_config.get('max', 100.0),
                            resolution=channel_config.get('resolution', 0.1),
                            default_value=channel_config.get('default', 0.0)
                        )
                        output.add_channel(channel)
                
                self.add_output(output)
                logger.debug(f"Added output {output.output_id} with {len(output.channels)} channels")
        
        # Configure buttons
        if 'buttons' in config:
            for button_config in config['buttons']:
                button = Button(
                    vdsd=self,
                    name=button_config.get('name', ''),
                    button_type=button_config.get('buttonType', 'toggle'),
                    element=button_config.get('element', 0)
                )
                self._buttons.append(button)
                logger.debug(f"Added button: {button.name}")
        
        # Configure binary inputs
        if 'binary_inputs' in config:
            for input_config in config['binary_inputs']:
                binary_input = BinaryInput(
                    vdsd=self,
                    name=input_config.get('name', ''),
                    input_type=input_config.get('inputType', 'contact'),
                    input_id=input_config.get('inputID'),
                    invert=input_config.get('invert', False),
                    initial_state=input_config.get('initialState', False)
                )
                self._binary_inputs.append(binary_input)
                logger.debug(f"Added binary input: {binary_input.name}")
        
        # Configure sensors
        if 'sensors' in config:
            for sensor_config in config['sensors']:
                sensor = Sensor(
                    vdsd=self,
                    name=sensor_config.get('name', ''),
                    sensor_type=sensor_config.get('sensorType', 'custom'),
                    unit=sensor_config.get('unit', ''),
                    min_value=sensor_config.get('min'),
                    max_value=sensor_config.get('max'),
                    resolution=sensor_config.get('resolution', 0.1),
                    initial_value=sensor_config.get('initialValue')
                )
                self._sensors.append(sensor)
                logger.debug(f"Added sensor: {sensor.name}")
        
        # Configure scenes
        if 'scenes' in config:
            for scene_number, scene_config in config['scenes'].items():
                self.set_scene(
                    scene_number=int(scene_number) if isinstance(scene_number, str) else scene_number,
                    channel_values=scene_config.get('channels', {}),
                    effect=scene_config.get('effect', DSSceneEffect.SMOOTH),
                    dont_care=scene_config.get('dontCare', False)
                )
                logger.debug(f"Configured scene {scene_number}")
        
        # Configure custom actions
        if 'customActions' in config:
            for action in config['customActions']:
                self.actions.add_custom_action(
                    name=action.get('name', ''),
                    title=action.get('title', ''),
                    action_template=action.get('action', ''),
                    params=action.get('params', {})
                )
        
        # Set initial states
        if 'states' in config:
            for state_name, state_value in config['states'].items():
                self.states.set_state(state_name, state_value)
        
        # Set device properties
        if 'deviceProperties' in config:
            for prop in config['deviceProperties']:
                self.device_properties.set_property(
                    prop.get('name'),
                    prop.get('value')
                )
        
        # Persist the configuration
        self._save_config()
        
        logger.info(
            f"vdSD {self.dsuid} configured: "
            f"{len(self._outputs)} outputs, "
            f"{len(self._buttons)} buttons, "
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
        config = {
            'outputs': [
                output.to_dict()
                for output in self._outputs.values()
            ],
            'buttons': [
                button.to_dict()
                for button in self._buttons
            ],
            'binary_inputs': [
                binary_input.to_dict()
                for binary_input in self._binary_inputs
            ],
            'sensors': [
                sensor.to_dict()
                for sensor in self._sensors
            ],
            'scenes': self._scenes.copy(),
            'customActions': self.actions.get_custom_actions().get('customActions', []),
            'states': self.states.get_values().get('deviceStates', []),
            'deviceProperties': self.device_properties.to_dict().get('deviceProperties', [])
        }
        
        return config
    
    def clone(self, new_name: str, enumeration: Optional[int] = None) -> 'VdSD':
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
        model = self._common_props.get('model')
        primary_group = self._vdsd_props.get('primaryGroup')
        
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
            enumeration=enumeration
        )
        
        # Apply configuration to clone
        clone_device.configure(config)
        
        logger.info(
            f"Cloned vdSD {self.dsuid} ('{self._common_props.get('name')}') "
            f"to {clone_device.dsuid} ('{new_name}')"
        )
        
        return clone_device
    
    def add_output_channel(
        self,
        channel_type: int,
        min_value: float = 0.0,
        max_value: float = 100.0,
        resolution: float = 0.1,
        initial_value: Optional[float] = None,
        **properties
    ) -> 'OutputChannel':
        """
        Add an output channel to this device.
        
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
        # Implementation depends on OutputChannel class
        # This is a placeholder
        logger.info(
            f"Adding output channel type {channel_type} to vdSD {self.dsuid}"
        )
        raise NotImplementedError("OutputChannel class not yet implemented")
    
    def add_button(
        self,
        name: str,
        button_type: int,
        on_press: Optional[Callable] = None,
        on_release: Optional[Callable] = None,
        **properties
    ) -> 'Button':
        """
        Add a button input to this device.
        
        Buttons generate events when pressed/released. Common uses:
        - Wall switches
        - Remote control buttons
        - Touch sensors
        - Gesture inputs
        
        Button types:
        - 0: Single press (on press)
        - 1: Double press
        - 2: Long press
        - 3: Release
        
        Args:
            name: Button name (e.g., "Toggle Button", "Brightness Up")
            button_type: Type of button interaction
            on_press: Callback when button is pressed
            on_release: Callback when button is released
            **properties: Additional button properties
        
        Returns:
            Button instance
        
        Example:
            # Simple toggle button
            toggle = device.add_button(
                name="Power Toggle",
                button_type=0,
                on_press=lambda: device.toggle_output()
            )
            
            # Brightness control buttons
            device.add_button(
                name="Brightness Up",
                button_type=2,  # Long press
                on_press=lambda: device.increase_brightness()
            )
        """
        # Implementation depends on Button class
        logger.info(f"Adding button '{name}' to vdSD {self.dsuid}")
        raise NotImplementedError("Button class not yet implemented")
    
    def add_sensor(
        self,
        sensor_type: str,
        unit: str,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        **properties
    ) -> 'Sensor':
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
        # Implementation depends on Sensor class
        logger.info(f"Adding sensor type '{sensor_type}' to vdSD {self.dsuid}")
        raise NotImplementedError("Sensor class not yet implemented")
    
    def set_scene(
        self,
        scene_number: int,
        channel_values: Dict[int, float],
        effect: int = DSSceneEffect.SMOOTH,
        dont_care: bool = False,
        **properties
    ) -> None:
        """
        Configure a scene for this device.
        
        Scenes store preset configurations that can be recalled later.
        Each scene defines:
        - Values for each output channel
        - Transition effect (how to reach values)
        - Don't care flag (whether device participates)
        
        Args:
            scene_number: Scene number (0-127, see DSScene enum)
            channel_values: Dict mapping channel type to target value
            effect: Transition effect (DSSceneEffect enum)
            dont_care: If True, device ignores this scene
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
            'channels': channel_values,
            'effect': effect,
            'dontCare': dont_care,
            **properties
        }
        
        self._scenes[scene_number] = scene_config
        
        # Persist scene configuration
        self._save_scenes()
        
        logger.debug(
            f"Configured scene {scene_number} for vdSD {self.dsuid}: "
            f"channels={list(channel_values.keys())}, effect={effect}"
        )
    
    def call_scene(
        self,
        scene_number: int,
        force: bool = False
    ) -> None:
        """
        Activate a scene on this device.
        
        This applies the scene's configured values to the device outputs.
        The scene's effect determines how values transition.
        
        Process:
        1. Look up scene configuration
        2. Check don't care flag (skip if True and not forced)
        3. Apply each channel value with effect
        4. Send notifications to vdSM
        
        Args:
            scene_number: Scene to activate (DSScene enum value)
            force: If True, ignore don't care flag
        
        Example:
            # Call standard scene
            device.call_scene(DSScene.PRESENT)
            
            # Force scene even if device marked as don't care
            device.call_scene(DSScene.DEEP_OFF, force=True)
        """
        scene = self._scenes.get(scene_number)
        
        if not scene:
            logger.warning(
                f"Scene {scene_number} not configured for vdSD {self.dsuid}"
            )
            return
        
        # Check don't care flag
        if scene.get('dontCare', False) and not force:
            logger.debug(
                f"Skipping scene {scene_number} for vdSD {self.dsuid} "
                f"(don't care flag set)"
            )
            return
        
        logger.info(
            f"Calling scene {scene_number} on vdSD {self.dsuid}, "
            f"effect={scene.get('effect', 0)}"
        )
        
        # Apply each channel value
        channel_values = scene.get('channels', {})
        effect = scene.get('effect', DSSceneEffect.SMOOTH)
        
        for channel_type, value in channel_values.items():
            if channel_type in self._output_channels:
                # Apply value with effect
                self._output_channels[channel_type].set_value(
                    value,
                    effect=effect
                )
        
        logger.debug(
            f"Applied scene {scene_number} to {len(channel_values)} channels"
        )
    
    def save_scene(self, scene_number: int) -> None:
        """
        Save current output values as a scene.
        
        Captures the current state of all output channels and stores
        them as the specified scene configuration.
        
        Args:
            scene_number: Scene number to save to (0-127)
        
        Example:
            # Manually adjust device
            device.set_output(DSChannelType.BRIGHTNESS, 65.0)
            device.set_output(DSChannelType.COLOR_TEMP, 4000)
            
            # Save current state as preset
            device.save_scene(DSScene.PRESET_0)
            
            # Later, recall this configuration
            device.call_scene(DSScene.PRESET_0)
        """
        # Capture current channel values from all outputs
        channel_values = {}
        for output in self._outputs.values():
            values = output.get_all_channel_values()
            channel_values.update(values)
        
        # Save as scene with smooth effect (default)
        self.set_scene(
            scene_number=scene_number,
            channel_values=channel_values,
            effect=DSSceneEffect.SMOOTH
        )
        
        logger.info(
            f"Saved current state as scene {scene_number} for vdSD {self.dsuid}"
        )
    
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
        
        # Add output information (outputs contain channels)
        if self._outputs:
            props['outputs'] = [
                output.to_dict()
                for output in self._outputs.values()
            ]
        
        # Add input information
        inputs = []
        inputs.extend([btn.to_dict() for btn in self._buttons])
        inputs.extend([bi.to_dict() for bi in self._binary_inputs])
        inputs.extend([sensor.to_dict() for sensor in self._sensors])
        if inputs:
            props['inputs'] = inputs
        
        # Add scene information (if queried)
        if self._scenes:
            props['scenes'] = {
                str(scene_no): scene_config
                for scene_no, scene_config in self._scenes.items()
            }
        
        # Add actions (templates, standard, custom, dynamic)
        props.update(self.actions.to_dict())
        
        # Add states (descriptions and current values)
        props.update(self.states.to_dict())
        
        # Add device properties
        props.update(self.device_properties.to_dict())
        
        # TODO: Filter based on query (if query specifies subset)
        
        # Convert to PropertyElement tree
        return PropertyTree.to_protobuf(props)
    
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
        self._common_props.update(prop_dict)
        
        # Update vdSD-specific properties
        self._vdsd_props.update(prop_dict)
        
        # Handle output value changes from vdSM
        if 'outputs' in prop_dict:
            self._apply_output_changes(prop_dict['outputs'])
        
        # Persist changes
        self._save_config()
    
    def announce_to_vdsm(self) -> Message:
        """
        Create device announcement message for vdSM.
        
        Returns:
            Message with vdc_SendAnnounceDevice
        """
        message = Message()
        message.type = Message.VDC_SEND_ANNOUNCE_DEVICE
        
        announce = message.vdc_send_announce_device
        announce.dSUID = self.dsuid
        
        # Add device properties to announcement
        # announce.properties.CopyFrom(self.get_properties(None))
        
        logger.debug(f"Created device announcement for {self.dsuid}")
        
        return message
    
    def _save_config(self) -> None:
        """Save device configuration to persistence."""
        config = {
            **self._common_props.to_dict(),
            **self._vdsd_props.to_dict(),
            'vdc_dSUID': self.vdc.dsuid
        }
        
        # Add outputs configuration
        if self._outputs:
            config['outputs'] = [
                output.to_dict()
                for output in self._outputs.values()
            ]
        
        self._persistence.set_vdsd(self.dsuid, config)
    
    def _apply_output_changes(self, outputs_data: List[Dict[str, Any]]) -> None:
        """
        Apply output value changes from vdSM.
        
        This is called when vdSM sends property changes for outputs.
        Values are applied to the Output/OutputChannel objects and
        hardware callbacks are triggered.
        
        Args:
            outputs_data: List of output property dictionaries from vdSM
        """
        for output_data in outputs_data:
            output_id = output_data.get('outputID')
            if output_id is None:
                continue
            
            output = self._outputs.get(output_id)
            if not output:
                logger.warning(
                    f"vdSD {self.dsuid} has no output {output_id}"
                )
                continue
            
            # Update output configuration
            output.from_dict(output_data)
            
            # Apply channel value changes
            if 'channels' in output_data:
                for channel_type_str, channel_data in output_data['channels'].items():
                    try:
                        channel_type = DSChannelType(int(channel_type_str))
                        if 'value' in channel_data:
                            # Apply the value change (triggers hardware callback)
                            output.set_channel_value(
                                channel_type,
                                channel_data['value'],
                                transition_time=channel_data.get('transitionTime')
                            )
                            logger.info(
                                f"vdSD {self.dsuid}: Set output {output_id} "
                                f"channel {channel_type} to {channel_data['value']}"
                            )
                    except (ValueError, KeyError) as e:
                        logger.error(f"Error applying channel value: {e}")
    
    def _save_scenes(self) -> None:
        """Save scene configurations to persistence."""
        # Update scenes in config
        self._persistence.update_vdsd_property(
            self.dsuid,
            'scenes',
            self._scenes
        )
    
    def _initialize_common_states(self) -> None:
        """Initialize common device states."""
        # Operational state
        self.states.add_state_description(
            name="operational",
            options={
                0: "off",
                1: "initializing",
                2: "running",
                3: "error",
                4: "shutdown"
            },
            description="Device operational state"
        )
        
        # Reachable state (network connectivity)
        self.states.add_state_description(
            name="reachable",
            options={
                0: "unreachable",
                1: "reachable"
            },
            description="Network connectivity status"
        )
        
        # Service mode
        self.states.add_state_description(
            name="service",
            options={
                0: "normal",
                1: "service"
            },
            description="Service mode indicator"
        )
        
        # Set initial state to running and reachable
        self.states.set_state("operational", "running")
        self.states.set_state("reachable", "reachable")
        self.states.set_state("service", "normal")
    
    def _initialize_common_actions(self) -> None:
        """Initialize common device actions."""
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
                    param_type="numeric",
                    min_value=1.0,
                    max_value=60.0,
                    default=3.0,
                    siunit="s"
                )
            },
            handler=identify_handler
        )
    
    def __repr__(self) -> str:
        """String representation of device."""
        return (
            f"VdSD(dsuid='{self.dsuid}', "
            f"name='{self._common_props.get('name')}', "
            f"group={self._vdsd_props.get('primaryGroup')}, "
            f"outputs={len(self._outputs)})"
        )
    
    # ===================================================================
    # Scene Operations (Protocol Integration)
    # ===================================================================
    
    async def call_scene(self, scene: int, force: bool = False, mode: str = 'normal') -> None:
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
        
        # Get scene configuration
        scene_config = self._scenes.get(scene, {})
        
        if not scene_config and not force:
            logger.warning(f"Scene {scene} not configured on device {self.dsuid}")
            return
        
        # Save current state to undo stack (before applying scene)
        self._save_undo_state()
        
        # Get output containers
        for output_id, output in self._outputs.items():
            # Extract scene values for this output
            scene_values = scene_config.get('outputs', {}).get(output_id, {})
            
            if not scene_values:
                continue
            
            # Get effect for transition
            effect = scene_config.get('effect', DSSceneEffect.SMOOTH)
            
            # Apply scene values to output
            if mode == 'min':
                # Only apply if scene values are higher
                output.apply_scene_values(scene_values, effect=effect, mode='min')
            else:
                # Normal: apply unconditionally
                output.apply_scene_values(scene_values, effect=effect)
        
        # Notify vdSM of changes (if outputs changed)
        await self._send_push_notification()
    
    async def save_scene(self, scene: int) -> None:
        """
        Save current output values to a scene number.
        
        Captures a "snapshot" of current device state for later recall.
        This allows users to create custom scenes with their preferred settings.
        
        Args:
            scene: Scene number to save to (0-127)
        
        Scene Storage:
            - Scene configurations stored in YAML persistence
            - Includes all output channel values
            - Optionally includes effect settings
        
        Example:
            # Set brightness to 75%
            await device.get_output().set_channel_value(DSChannelType.BRIGHTNESS, 75.0)
            
            # Save current state as scene 17 ("Preset 1")
            await device.save_scene(17)
            
            # Later, recall this exact state
            await device.call_scene(17)
        """
        logger.info(f"Save scene {scene} on device {self.dsuid}")
        
        # Capture current output values
        scene_config = {
            'outputs': {}
        }
        
        for output_id, output in self._outputs.items():
            # Get all channel values
            channel_values = output.get_all_channel_values()
            
            if channel_values:
                scene_config['outputs'][output_id] = {
                    'channels': channel_values
                }
        
        # Store in scenes dictionary
        self._scenes[scene] = scene_config
        
        # Persist to YAML
        self._save_scenes()
        
        # Notify vdSM that scenes changed
        await self._send_push_notification({'scenes': {scene: scene_config}})
    
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
        
        if not hasattr(self, '_undo_stack'):
            self._undo_stack = []
        
        if not self._undo_stack:
            logger.warning(f"No undo state available for device {self.dsuid}")
            return
        
        # Pop last state from stack
        previous_state = self._undo_stack.pop()
        
        # Restore output values
        for output_id, channel_values in previous_state.items():
            output = self._outputs.get(output_id)
            if output:
                for channel_type, value in channel_values.items():
                    output.set_channel_value(channel_type, value, apply_now=True)
        
        # Notify vdSM
        await self._send_push_notification()
    
    def _save_undo_state(self) -> None:
        """
        Save current output state to undo stack.
        
        Called before applying a scene to enable undo functionality.
        """
        if not hasattr(self, '_undo_stack'):
            self._undo_stack = []
        
        # Capture current state
        current_state = {}
        for output_id, output in self._outputs.items():
            current_state[output_id] = output.get_all_channel_values()
        
        # Add to stack (limit depth to 5)
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
        if self.actions.has_action('identify'):
            await self.actions.call_action('identify', duration=duration)
        else:
            # Default implementation: blink output if available
            output = self.get_output()
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
        Set local priority for device/scene.
        
        Local priority determines which device takes precedence when
        multiple devices control the same resource.
        
        Args:
            scene: Scene number to prioritize (None = global priority)
        
        Priority Levels:
            - Local priority overrides group scenes
            - Used in multi-device zones
            - Allows individual device control
        
        Example:
            # Give device priority for scene 5
            device.set_local_priority(scene=5)
        """
        logger.info(f"Set local priority on device {self.dsuid} for scene {scene}")
        
        # Store priority setting
        if not hasattr(self, '_local_priorities'):
            self._local_priorities = {}
        
        if scene is not None:
            self._local_priorities[scene] = True
        else:
            # Global priority
            self._local_priorities['*'] = True
        
        # Persist priority settings
        self._persistence.update_vdsd_property(
            self.dsuid,
            'local_priorities',
            self._local_priorities
        )
    
    def set_control_value(self, control_name: str, value: float) -> None:
        """
        Set a control value (distinct from output channels).
        
        Control values represent actuator positions, valve states, etc.
        They are different from output channels (brightness, color).
        
        Args:
            control_name: Name of control (e.g., "valve_position")
            value: Control value (0-100 typically)
        
        Use Cases:
            - Heating: Valve position (0-100%)
            - Blinds: Slat angle (-90 to +90 degrees)
            - HVAC: Fan speed, damper position
        
        Example:
            # Set heating valve to 75%
            device.set_control_value("valve_position", 75.0)
        """
        logger.info(f"Set control '{control_name}' to {value} on device {self.dsuid}")
        
        # Store control value
        if not hasattr(self, '_control_values'):
            self._control_values = {}
        
        self._control_values[control_name] = value
        
        # Trigger hardware callback if registered
        if self._hardware_callbacks.get('on_control_change'):
            self._hardware_callbacks['on_control_change'](control_name, value)
    
    async def _send_push_notification(self, properties: Optional[dict] = None) -> None:
        """
        Send push notification to vdSM via host.
        
        Args:
            properties: Optional specific properties to push
        """
        # Get host reference
        if hasattr(self, '_vdc') and self._vdc:
            host = self._vdc._host
            if host:
                await host.send_push_notification(self.dsuid, properties)
    
    def _on_output_change(self, output_id: int, channel_type: DSChannelType, value: float) -> None:
        """
        Callback when output channel value changes.
        
        Triggered by Output when a channel value is set.
        This sends a push notification to vdSM.
        
        Args:
            output_id: Output that changed
            channel_type: Channel that changed
            value: New value
        """
        logger.debug(f"Output {output_id} channel {channel_type} changed to {value}")
        
        # Create push notification with channel values
        properties = {
            'outputs': {
                output_id: {
                    'channels': {
                        str(channel_type.value): {
                            'value': value
                        }
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
            logger.warning("No event loop available for push notification")
