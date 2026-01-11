"""
Property tree conversion between protobuf PropertyElement and Python dicts.

Provides bidirectional conversion for property trees matching the vDC API structure.
"""

from typing import Any, Dict, List, Optional, Union
import sys
import os

# Add parent directory to path to import genericVDC_pb2
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
import genericVDC_pb2 as pb

import logging

logger = logging.getLogger(__name__)


class PropertyTree:
    """
    Converts between protobuf PropertyElement messages and Python dictionaries.
    
    The property tree structure mirrors the vDC API property hierarchy.
    """
    
    @staticmethod
    def from_protobuf(elements: List[pb.PropertyElement]) -> Dict[str, Any]:
        """
        Convert protobuf PropertyElement list to Python dict.
        
        Args:
            elements: List of PropertyElement messages
            
        Returns:
            Dictionary representation of the property tree
        """
        result = {}
        
        for element in elements:
            name = element.name
            
            # Check if this element has nested elements
            if len(element.elements) > 0:
                # Recursive conversion for nested properties
                result[name] = PropertyTree.from_protobuf(element.elements)
            elif element.HasField('value'):
                # Extract the actual value
                result[name] = PropertyTree._extract_value(element.value)
            else:
                # Element with name but no value (used in queries)
                result[name] = None
        
        return result
    
    @staticmethod
    def to_protobuf(data: Dict[str, Any]) -> List[pb.PropertyElement]:
        """
        Convert Python dict to protobuf PropertyElement list.
        
        Args:
            data: Dictionary to convert
            
        Returns:
            List of PropertyElement messages
        """
        elements = []
        
        for key, value in data.items():
            element = pb.PropertyElement()
            # Ensure key is always a string (protobuf requirement)
            element.name = str(key) if not isinstance(key, str) else key
            
            if isinstance(value, dict):
                # Nested dictionary - recurse
                element.elements.extend(PropertyTree.to_protobuf(value))
            elif isinstance(value, list):
                # List - handle as repeated elements
                if len(value) == 0:
                    # Empty list - create element with no value/children
                    pass
                elif isinstance(value[0], dict):
                    # List of dictionaries (e.g., multiple inputs/outputs)
                    for item in value:
                        element.elements.extend(PropertyTree.to_protobuf(item))
                else:
                    # List of primitive values - create child elements
                    for idx, item in enumerate(value):
                        child = pb.PropertyElement()
                        child.name = str(idx)
                        PropertyTree._set_value(child.value, item)
                        element.elements.append(child)
            else:
                # Leaf value
                PropertyTree._set_value(element.value, value)
            
            elements.append(element)
        
        return elements
    
    @staticmethod
    def _extract_value(prop_value: pb.PropertyValue) -> Any:
        """
        Extract actual value from PropertyValue message.
        
        Args:
            prop_value: PropertyValue message
            
        Returns:
            Python value
        """
        # Check which field is set
        if prop_value.HasField('v_bool'):
            return prop_value.v_bool
        elif prop_value.HasField('v_uint64'):
            return prop_value.v_uint64
        elif prop_value.HasField('v_int64'):
            return prop_value.v_int64
        elif prop_value.HasField('v_double'):
            return prop_value.v_double
        elif prop_value.HasField('v_string'):
            return prop_value.v_string
        elif prop_value.HasField('v_bytes'):
            return prop_value.v_bytes
        else:
            return None
    
    @staticmethod
    def _set_value(prop_value: pb.PropertyValue, value: Any) -> None:
        """
        Set PropertyValue message from Python value.
        
        Args:
            prop_value: PropertyValue message to set
            value: Python value
        """
        if value is None:
            # Don't set any field for None
            pass
        elif isinstance(value, bool):
            prop_value.v_bool = value
        elif isinstance(value, int):
            # Use int64 for signed integers
            if value < 0:
                prop_value.v_int64 = value
            else:
                # Use uint64 for positive integers
                prop_value.v_uint64 = value
        elif isinstance(value, float):
            prop_value.v_double = value
        elif isinstance(value, str):
            prop_value.v_string = value
        elif isinstance(value, (bytes, bytearray)):
            prop_value.v_bytes = bytes(value)
        else:
            # Try to convert to string as fallback
            logger.warning(f"Unknown value type {type(value)}, converting to string")
            prop_value.v_string = str(value)
    
    @staticmethod
    def create_query(property_path: str) -> List[pb.PropertyElement]:
        """
        Create a property query for getProperty requests.
        
        Args:
            property_path: Dot-separated property path (e.g., "inputs.0.value")
                          Use "*" for wildcard
            
        Returns:
            List of PropertyElement messages forming the query
        """
        parts = property_path.split('.')
        
        def build_query_recursive(parts: List[str]) -> List[pb.PropertyElement]:
            if not parts:
                return []
            
            element = pb.PropertyElement()
            element.name = parts[0] if parts[0] != '*' else ''
            
            if len(parts) > 1:
                # More levels to go
                element.elements.extend(build_query_recursive(parts[1:]))
            
            return [element]
        
        return build_query_recursive(parts)
    
    @staticmethod
    def merge_dicts(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries.
        
        Args:
            base: Base dictionary
            update: Dictionary with updates
            
        Returns:
            Merged dictionary
        """
        result = base.copy()
        
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = PropertyTree.merge_dicts(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def get_nested_value(data: Dict[str, Any], path: str, default: Any = None) -> Any:
        """
        Get a value from nested dictionary using dot notation.
        
        Args:
            data: Dictionary to search
            path: Dot-separated path (e.g., "inputs.0.value")
            default: Default value if path not found
            
        Returns:
            Value at path or default
        """
        parts = path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError):
                    return default
            else:
                return default
        
        return current
    
    @staticmethod
    def set_nested_value(data: Dict[str, Any], path: str, value: Any) -> None:
        """
        Set a value in nested dictionary using dot notation.
        
        Args:
            data: Dictionary to modify
            path: Dot-separated path (e.g., "inputs.0.value")
            value: Value to set
        """
        parts = path.split('.')
        current = data
        
        for i, part in enumerate(parts[:-1]):
            if part not in current:
                # Create intermediate dict or list
                next_part = parts[i + 1]
                if next_part.isdigit():
                    current[part] = []
                else:
                    current[part] = {}
            
            if isinstance(current[part], list):
                try:
                    index = int(parts[i + 1])
                    # Extend list if needed
                    while len(current[part]) <= index:
                        current[part].append({})
                    current = current[part][index]
                    # Skip the index in next iteration
                    parts = parts[:i+1] + parts[i+2:]
                except (ValueError, IndexError):
                    pass
            else:
                current = current[part]
        
        # Set the final value
        current[parts[-1]] = value
