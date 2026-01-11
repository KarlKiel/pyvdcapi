"""
vdSD-specific properties.

Implements properties defined in section 4 of the vDC API properties specification.
"""

from typing import Dict, Any, Optional, List, Set


# Valid model feature keys according to vDC API specification
VALID_MODEL_FEATURES: Set[str] = {
    'dontcare',
    'blink',
    'ledauto',
    'leddark',
    'transt',
    'outmode',
    'outmodeswitch',
    'outvalue8',
    'pushbutton',
    'pushbdevice',
    'pushbsensor',
    'pushbarea',
    'pushbadvanced',
    'pushbcombined',
    'shadeprops',
    'shadeposition',
    'motiontimefins',
    'optypeconfig',
    'shadebladeang',
    'highlevel',
    'consumption',
    'jokerconfig',
    'akmsensor',
    'akminput',
    'akmdelay',
    'twowayconfig',
    'outputchannels',
    'heatinggroup',
    'heatingoutmode',
    'heatingprops',
    'pwmvalue',
    'valvetype',
    'extradimmer',
    'umvrelay',
    'blinkconfig',
    'umroutmode',
    'locationconfig',
    'windprotectionconfig',
    'impulseconfig',
    'outmodegeneric',
    'outconfigswitch',
    'temperatureoffset',
    'apartmentapplication',
    'ftwtempcontrolventilationselect',
    'ftwdisplaysettings',
    'ftwbacklighttimeout',
    'ventconfig',
    'fcu',
    'pushbdisabled',
    'consumptioneventled',
    'consumptiontimer',
    'jokertempcontrol',
    'dimtimeconfig',
    'outmodeauto',
    'dimmodeconfig',
    'identification',
}


class VdSDProperties:
    """
    Properties specific to vdSD (virtual device) entities.
    
    vdSDs must also support common properties via CommonProperties class.
    """
    
    def __init__(
        self,
        primary_group: int,
        zone_id: Optional[int] = None,
        model_features: Optional[Dict[str, bool]] = None,
        **kwargs
    ):
        """
        Initialize vdSD-specific properties.
        
        Args:
            primary_group: Basic class (color) of the device (0-255)
            zone_id: Zone the device is in (set by vdSM)
            model_features: Device model features for visibility matrix (required - defaults to empty dict if not provided)
            **kwargs: Additional optional properties
        """
        self._properties: Dict[str, Any] = {
            'primaryGroup': primary_group,
        }
        
        if zone_id is not None:
            self._properties['zoneID'] = zone_id
        
        # Model features determine UI capabilities - REQUIRED property
        # Default to empty dict if not explicitly provided
        self._properties['modelFeatures'] = model_features if model_features is not None else {}
        
        # Optional properties
        if 'progMode' in kwargs:
            self._properties['progMode'] = kwargs['progMode']
        
        if 'currentConfigId' in kwargs:
            self._properties['currentConfigId'] = kwargs['currentConfigId']
        
        if 'configurations' in kwargs:
            self._properties['configurations'] = kwargs['configurations']
    
    def get_property(self, name: str, default: Any = None) -> Any:
        """Get vdSD property value."""
        return self._properties.get(name, default)
    
    def set_property(self, name: str, value: Any) -> bool:
        """
        Set vdSD property value.
        
        Args:
            name: Property name
            value: New value
            
        Returns:
            True if successful
        """
        # Read-write properties
        if name == 'zoneID':
            if not isinstance(value, int):
                return False
            self._properties['zoneID'] = value
            return True
        
        if name == 'progMode':
            if not isinstance(value, bool):
                return False
            self._properties['progMode'] = value
            return True
        
        # Other properties are read-only
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Converts all enum values to their underlying types for serialization.
        """
        result = {}
        for key, value in self._properties.items():
            # Convert enum values to their underlying int/str type
            if hasattr(value, 'value'):
                result[key] = value.value
            else:
                result[key] = value
        return result
    
    def get_primary_group(self) -> int:
        """Get primary group (dS class/color)."""
        return self._properties['primaryGroup']
    
    def get_zone_id(self) -> Optional[int]:
        """Get zone ID."""
        return self._properties.get('zoneID')
    
    def set_zone_id(self, zone_id: int) -> None:
        """Set zone ID (typically set by vdSM)."""
        self.set_property('zoneID', zone_id)
    
    def get_model_features(self) -> Dict[str, bool]:
        """Get model features."""
        return self._properties.get('modelFeatures', {}).copy()
    
    def add_model_feature(self, feature: str, enabled: bool = True) -> None:
        """
        Add a model feature.
        
        Args:
            feature: Feature name (must be a valid model feature)
            enabled: Whether feature is enabled
            
        Raises:
            ValueError: If feature is not a valid model feature
        """
        if feature not in VALID_MODEL_FEATURES:
            raise ValueError(
                f"Invalid model feature '{feature}'. Must be one of: {sorted(VALID_MODEL_FEATURES)}"
            )
        
        if 'modelFeatures' not in self._properties:
            self._properties['modelFeatures'] = {}
        self._properties['modelFeatures'][feature] = enabled
