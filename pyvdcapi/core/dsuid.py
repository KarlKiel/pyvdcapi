"""
dSUID generation utilities.

The dSUID format is 34 hex characters (2*17 bytes):
- Bytes 0-5: Namespace/class identifier
- Bytes 6-15: Device identifier (MAC address, UUID, etc.)
- Byte 16: Subdevice enumeration (0 for single device, 1-255 for multi-output)
"""

import uuid
import hashlib
from typing import Optional


class DSUIDGenerator:
    """Generates dSUIDs according to digitalSTROM specifications."""
    
    # Namespace identifiers for different entity types
    NAMESPACE_VDC_HOST = "00000000"
    NAMESPACE_VDC = "00000001"
    NAMESPACE_VDSD = "00000002"
    
    @staticmethod
    def generate_vdc_host_dsuid(mac_address: str, vendor_id: str = "KarlKiel") -> str:
        """
        Generate a dSUID for a vDC host.
        
        Args:
            mac_address: MAC address in format "AA:BB:CC:DD:EE:FF"
            vendor_id: Vendor identifier string
            
        Returns:
            34 character hex string (17 bytes)
        """
        return DSUIDGenerator._generate_dsuid(
            DSUIDGenerator.NAMESPACE_VDC_HOST,
            mac_address,
            vendor_id,
            0
        )
    
    @staticmethod
    def generate_vdc_dsuid(mac_address: str, vdc_index: int, vendor_id: str = "KarlKiel") -> str:
        """
        Generate a dSUID for a vDC.
        
        Args:
            mac_address: MAC address of the host
            vdc_index: Index of this vDC on the host (0-255)
            vendor_id: Vendor identifier string
            
        Returns:
            34 character hex string (17 bytes)
        """
        # Use vdc_index as part of the identifier
        identifier = f"{mac_address}:{vdc_index}"
        return DSUIDGenerator._generate_dsuid(
            DSUIDGenerator.NAMESPACE_VDC,
            identifier,
            vendor_id,
            vdc_index
        )
    
    @staticmethod
    def generate_vdsd_dsuid(
        hardware_guid: str,
        vendor_id: str = "KarlKiel",
        subdevice_index: int = 0
    ) -> str:
        """
        Generate a dSUID for a vdSD (virtual device).
        
        Args:
            hardware_guid: Unique hardware identifier (MAC, serial, etc.)
            vendor_id: Vendor identifier string
            subdevice_index: Subdevice enumeration (0 for single, 1-255 for multi-output)
            
        Returns:
            34 character hex string (17 bytes)
        """
        return DSUIDGenerator._generate_dsuid(
            DSUIDGenerator.NAMESPACE_VDSD,
            hardware_guid,
            vendor_id,
            subdevice_index
        )
    
    @staticmethod
    def _generate_dsuid(
        namespace: str,
        identifier: str,
        vendor_id: str,
        subdevice_index: int
    ) -> str:
        """
        Internal method to generate a dSUID.
        
        Format: NNNNNNNN-IIIIIIIIIIII-EE
        Where:
        - N = Namespace (4 bytes)
        - I = Identifier hash (10 bytes)
        - E = Enumeration/subdevice (1 byte)
        """
        # Ensure subdevice index is in valid range
        if not 0 <= subdevice_index <= 255:
            raise ValueError(f"Subdevice index must be 0-255, got {subdevice_index}")
        
        # Create a deterministic identifier by hashing vendor_id + identifier
        combined = f"{vendor_id}:{identifier}".encode('utf-8')
        hash_obj = hashlib.sha256(combined)
        hash_bytes = hash_obj.digest()
        
        # Build the 17-byte dSUID
        # Bytes 0-3: Namespace (4 bytes)
        namespace_bytes = bytes.fromhex(namespace.zfill(8))
        
        # Bytes 4-13: First 10 bytes of hash (device identifier)
        identifier_bytes = hash_bytes[:10]
        
        # Bytes 14-15: Reserved (set to 0x00)
        reserved_bytes = b'\x00\x00'
        
        # Byte 16: Subdevice enumeration
        enum_byte = bytes([subdevice_index])
        
        # Combine all parts
        dsuid_bytes = namespace_bytes + identifier_bytes + reserved_bytes + enum_byte
        
        # Convert to 34 hex characters
        return dsuid_bytes.hex().upper()
    
    @staticmethod
    def validate_dsuid(dsuid: str) -> bool:
        """
        Validate a dSUID format.
        
        Args:
            dsuid: String to validate
            
        Returns:
            True if valid dSUID format
        """
        if not isinstance(dsuid, str):
            return False
        
        # Remove any separators
        clean_dsuid = dsuid.replace('-', '').replace(':', '')
        
        # Must be exactly 34 hex characters
        if len(clean_dsuid) != 34:
            return False
        
        # Must be valid hex
        try:
            int(clean_dsuid, 16)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def format_dsuid(dsuid: str) -> str:
        """
        Format a dSUID for display (removes any existing formatting and ensures uppercase).
        
        Args:
            dsuid: Raw dSUID string
            
        Returns:
            Formatted dSUID (34 uppercase hex chars)
        """
        clean = dsuid.replace('-', '').replace(':', '').upper()
        if len(clean) != 34:
            raise ValueError(f"Invalid dSUID length: {len(clean)}, expected 34")
        return clean
