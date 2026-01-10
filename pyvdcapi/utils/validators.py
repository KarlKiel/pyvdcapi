"""
Property type validators for vDC API.

Ensures strict validation of property types according to the specification.
"""

from typing import Any, Union, List, Dict, Optional
import re


class PropertyValidator:
    """Validates property values according to vDC API specifications."""
    
    # dSUID format: 34 hex characters (17 bytes)
    DSUID_PATTERN = re.compile(r'^[0-9A-Fa-f]{34}$')
    
    @staticmethod
    def validate_dsuid(value: Any) -> bool:
        """
        Validate dSUID format.
        
        Args:
            value: Value to validate
            
        Returns:
            True if valid dSUID
        """
        if not isinstance(value, str):
            return False
        # Remove common separators
        clean = value.replace('-', '').replace(':', '')
        return bool(PropertyValidator.DSUID_PATTERN.match(clean))
    
    @staticmethod
    def validate_boolean(value: Any) -> bool:
        """Validate boolean type."""
        return isinstance(value, bool)
    
    @staticmethod
    def validate_integer(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None) -> bool:
        """
        Validate integer type with optional range.
        
        Args:
            value: Value to validate
            min_val: Minimum allowed value (inclusive)
            max_val: Maximum allowed value (inclusive)
            
        Returns:
            True if valid
        """
        if not isinstance(value, int) or isinstance(value, bool):
            return False
        if min_val is not None and value < min_val:
            return False
        if max_val is not None and value > max_val:
            return False
        return True
    
    @staticmethod
    def validate_double(value: Any) -> bool:
        """Validate double/float type."""
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    
    @staticmethod
    def validate_string(value: Any, max_length: Optional[int] = None) -> bool:
        """
        Validate string type.
        
        Args:
            value: Value to validate
            max_length: Maximum string length
            
        Returns:
            True if valid
        """
        if not isinstance(value, str):
            return False
        if max_length is not None and len(value) > max_length:
            return False
        return True
    
    @staticmethod
    def validate_bytes(value: Any) -> bool:
        """Validate bytes type."""
        return isinstance(value, (bytes, bytearray))
    
    @staticmethod
    def validate_zone_id(value: Any) -> bool:
        """
        Validate zone ID (integer, global dS Zone ID).
        
        Args:
            value: Value to validate
            
        Returns:
            True if valid zone ID
        """
        return PropertyValidator.validate_integer(value, min_val=0, max_val=65535)
    
    @staticmethod
    def validate_primary_group(value: Any) -> bool:
        """
        Validate primary group (dS class number).
        
        Args:
            value: Value to validate
            
        Returns:
            True if valid primary group
        """
        # dS group numbers are typically 0-255
        return PropertyValidator.validate_integer(value, min_val=0, max_val=255)
    
    @staticmethod
    def validate_scene_number(value: Any) -> bool:
        """
        Validate scene number.
        
        Args:
            value: Value to validate
            
        Returns:
            True if valid scene number
        """
        # Scene numbers are typically 0-255
        return PropertyValidator.validate_integer(value, min_val=0, max_val=255)
    
    @staticmethod
    def validate_channel_id(value: Any) -> bool:
        """
        Validate channel ID.
        
        Args:
            value: Value to validate
            
        Returns:
            True if valid channel ID
        """
        # Channel IDs: 0 = default, 1-239 = specific channels
        return PropertyValidator.validate_integer(value, min_val=0, max_val=239)
    
    @staticmethod
    def validate_property_name(value: Any) -> bool:
        """
        Validate property name.
        
        Custom properties must start with "x-".
        
        Args:
            value: Value to validate
            
        Returns:
            True if valid property name
        """
        if not isinstance(value, str):
            return False
        # Property names should be reasonable length
        if len(value) == 0 or len(value) > 256:
            return False
        return True
    
    @staticmethod
    def validate_entity_type(value: Any) -> bool:
        """
        Validate entity type.
        
        Args:
            value: Value to validate
            
        Returns:
            True if valid entity type
        """
        valid_types = ["vdSD", "vDC", "vDChost", "vdSM"]
        return value in valid_types
    
    @staticmethod
    def coerce_to_type(value: Any, target_type: str) -> Any:
        """
        Coerce a value to the target type if possible.
        
        Args:
            value: Value to coerce
            target_type: Target type ('bool', 'int', 'double', 'string', 'bytes')
            
        Returns:
            Coerced value
            
        Raises:
            ValueError: If coercion is not possible
        """
        if target_type == 'bool':
            if isinstance(value, bool):
                return value
            if isinstance(value, int):
                return bool(value)
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            raise ValueError(f"Cannot coerce {type(value)} to bool")
        
        elif target_type == 'int':
            if isinstance(value, bool):
                raise ValueError("Cannot coerce bool to int")
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                return int(value)
            raise ValueError(f"Cannot coerce {type(value)} to int")
        
        elif target_type == 'double':
            if isinstance(value, bool):
                raise ValueError("Cannot coerce bool to double")
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                return float(value)
            raise ValueError(f"Cannot coerce {type(value)} to double")
        
        elif target_type == 'string':
            if isinstance(value, str):
                return value
            if isinstance(value, bytes):
                return value.decode('utf-8')
            return str(value)
        
        elif target_type == 'bytes':
            if isinstance(value, bytes):
                return value
            if isinstance(value, bytearray):
                return bytes(value)
            if isinstance(value, str):
                return value.encode('utf-8')
            raise ValueError(f"Cannot coerce {type(value)} to bytes")
        
        else:
            raise ValueError(f"Unknown target type: {target_type}")
