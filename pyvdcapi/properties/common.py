"""
Common properties for all addressable entities (vDC host, vDC, vdSD).

Implements properties defined in section 2 of the vDC API properties specification.
"""

from typing import Dict, Any, Optional
from ..utils.validators import PropertyValidator
import logging

logger = logging.getLogger(__name__)


class CommonProperties:
    """
    Common properties that must be supported by all addressable entities.
    
    These properties apply to vDC hosts, vDCs, and vdSDs.
    """
    
    # Required properties
    REQUIRED_PROPS = ['dSUID', 'type', 'model', 'modelUID', 'name']
    
    # Read-only properties
    READONLY_PROPS = [
        'dSUID', 'displayId', 'type', 'model', 'modelVersion', 'modelUID',
        'hardwareVersion', 'hardwareGuid', 'hardwareModelGuid', 'vendorName',
        'vendorGuid', 'oemGuid', 'oemModelGuid', 'configURL', 'deviceIcon16',
        'deviceIconName', 'deviceClass', 'deviceClassVersion'
    ]
    
    # Read-write properties
    READWRITE_PROPS = ['name', 'active']
    
    def __init__(
        self,
        dsuid: str,
        entity_type: str,
        name: str,
        model: str,
        model_uid: str,
        model_version: str = "",
        vendor_name: str = "KarlKiel",
        **kwargs
    ):
        """
        Initialize common properties.
        
        Args:
            dsuid: dSUID of the entity (34 hex characters)
            entity_type: Type of entity ("vDChost", "vDC", "vdSD")
            name: User-specified name (required)
            model: Human-readable model string
            model_uid: digitalSTROM system unique ID for functional model
            model_version: Model version string (optional, empty if not provided)
            vendor_name: Vendor name
            **kwargs: Additional optional properties
        """
        # Validate required properties
        if not PropertyValidator.validate_dsuid(dsuid):
            raise ValueError(f"Invalid dSUID: {dsuid}")
        if not PropertyValidator.validate_entity_type(entity_type):
            raise ValueError(f"Invalid entity type: {entity_type}")
        
        # Core properties
        self._properties: Dict[str, Any] = {
            'dSUID': dsuid.upper().replace('-', '').replace(':', ''),
            'type': entity_type,
            'model': model,
            'modelUID': model_uid,
            'vendorName': vendor_name,
            'name': name or f"{model}",
            'active': kwargs.get('active', True),
            'displayId': kwargs.get('displayId', '')  # Always present, empty string if not set
        }
        
        # modelVersion is optional - only set if provided
        if model_version:
            self._properties['modelVersion'] = model_version
        if 'model_version' in kwargs and kwargs['model_version']:
            self._properties['modelVersion'] = kwargs['model_version']
        
        # Optional read-only properties (excluding displayId which is always present)
        optional_ro = [
            'modelVersion', 'hardwareVersion', 'hardwareGuid',
            'hardwareModelGuid', 'vendorGuid', 'oemGuid', 'oemModelGuid',
            'configURL', 'deviceIcon16', 'deviceIconName', 'deviceClass',
            'deviceClassVersion'
        ]
        
        for prop in optional_ro:
            if prop in kwargs and kwargs[prop] is not None:
                self._properties[prop] = kwargs[prop]
    
    def get_property(self, name: str, default: Any = None) -> Any:
        """
        Get property value.
        
        Args:
            name: Property name
            default: Default value if property doesn't exist
            
        Returns:
            Property value or default
        """
        return self._properties.get(name, default)
    
    def set_property(self, name: str, value: Any) -> bool:
        """
        Set property value.
        
        Args:
            name: Property name
            value: New value
            
        Returns:
            True if successful, False if property is read-only or doesn't exist
        """
        if name in self.READONLY_PROPS:
            logger.warning(f"Cannot set read-only property: {name}")
            return False
        
        if name not in self.READWRITE_PROPS:
            logger.warning(f"Unknown property: {name}")
            return False
        
        # Validate name property
        if name == 'name':
            if not isinstance(value, str) or not value:
                logger.error("Name must be a non-empty string")
                return False
        
        # Validate active property
        if name == 'active':
            if not isinstance(value, bool):
                logger.error("Active must be boolean")
                return False
        
        self._properties[name] = value
        logger.debug(f"Set property {name} = {value}")
        return True
    
    def has_property(self, name: str) -> bool:
        """
        Check if property exists.
        
        Args:
            name: Property name
            
        Returns:
            True if property exists
        """
        return name in self._properties
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert properties to dictionary.
        
        Returns:
            Dictionary with all properties
        """
        return self._properties.copy()
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update properties from dictionary.
        
        Only updates read-write properties.
        
        Args:
            data: Dictionary with property updates
        """
        for key, value in data.items():
            if key in self.READWRITE_PROPS:
                self.set_property(key, value)
    
    def get_dsuid(self) -> str:
        """Get dSUID of this entity."""
        return self._properties['dSUID']
    
    def get_type(self) -> str:
        """Get entity type."""
        return self._properties['type']
    
    def get_name(self) -> str:
        """Get entity name."""
        return self._properties.get('name', '')
    
    def set_name(self, name: str) -> None:
        """Set entity name."""
        self.set_property('name', name)
    
    def is_active(self) -> bool:
        """Check if entity is active."""
        return self._properties.get('active', True)
    
    def set_active(self, active: bool) -> None:
        """Set entity active state."""
        self.set_property('active', active)
    
    def validate(self) -> bool:
        """
        Validate that all required properties are present.
        
        Returns:
            True if valid
        """
        for prop in self.REQUIRED_PROPS:
            if prop not in self._properties:
                logger.error(f"Missing required property: {prop}")
                return False
        return True
