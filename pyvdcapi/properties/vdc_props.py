"""
vDC-specific properties.

Implements properties defined in section 3 of the vDC API properties specification.
"""

from typing import Dict, Any, Optional


class VdcProperties:
    """
    Properties specific to vDC entities.

    vDCs must also support common properties via CommonProperties class.
    """

    def __init__(
        self,
        implementation_id: str = "x-KarlKiel-generic vDC",
        zone_id: Optional[int] = None,
        capabilities: Optional[Dict[str, bool]] = None,
    ):
        """
        Initialize vDC-specific properties.

        Args:
            implementation_id: Unique ID for vDC implementation
            zone_id: Default zone for this vDC (set by vdSM)
            capabilities: vDC capabilities
        """
        self._properties: Dict[str, Any] = {
            "implementationId": implementation_id,
        }

        if zone_id is not None:
            self._properties["zoneID"] = zone_id

        # Default capabilities
        default_capabilities = {
            "metering": False,
            "identification": False,
            "dynamicDefinitions": True,  # We support dynamic definitions
        }

        if capabilities:
            default_capabilities.update(capabilities)

        self._properties["capabilities"] = default_capabilities

    def get_property(self, name: str, default: Any = None) -> Any:
        """Get vDC property value."""
        return self._properties.get(name, default)

    def set_property(self, name: str, value: Any) -> bool:
        """
        Set vDC property value.

        Args:
            name: Property name
            value: New value

        Returns:
            True if successful
        """
        # zoneID is read-write (updated by vdSM)
        if name == "zoneID":
            if not isinstance(value, int):
                return False
            self._properties["zoneID"] = value
            return True

        # Other properties are read-only
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self._properties.copy()

    def get_zone_id(self) -> Optional[int]:
        """Get zone ID."""
        return self._properties.get("zoneID")

    def set_zone_id(self, zone_id: int) -> None:
        """Set zone ID (typically set by vdSM)."""
        self.set_property("zoneID", zone_id)
