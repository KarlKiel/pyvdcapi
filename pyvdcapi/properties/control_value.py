from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import time


@dataclass
class ControlValue:
    name: str
    value: float
    group: Optional[int] = None
    zone_id: Optional[int] = None
    last_updated: float = 0.0

    def __post_init__(self):
        if not self.last_updated:
            self.last_updated = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'value': self.value,
            'group': self.group,
            'zone_id': self.zone_id,
            'last_updated': self.last_updated,
        }


class ControlValues:
    """Container for ControlValue instances keyed by control name."""

    def __init__(self, initial: Optional[Dict[str, Any]] = None):
        self._values: Dict[str, ControlValue] = {}
        if initial:
            for k, v in initial.items():
                if isinstance(v, dict):
                    try:
                        cv = ControlValue(
                            name=k,
                            value=v.get('value', 0.0),
                            group=v.get('group'),
                            zone_id=v.get('zone_id', v.get('zoneId')),
                            last_updated=v.get('last_updated', 0.0),
                        )
                    except Exception:
                        # fallback to simple value
                        cv = ControlValue(name=k, value=float(v))
                else:
                    cv = ControlValue(name=k, value=float(v))
                self._values[k] = cv

    def get(self, name: str) -> Optional[ControlValue]:
        return self._values.get(name)

    def set(self, name: str, value: float, group: Optional[int] = None, zone_id: Optional[int] = None) -> ControlValue:
        cv = self._values.get(name)
        if cv is None:
            cv = ControlValue(name=name, value=float(value), group=group, zone_id=zone_id)
            self._values[name] = cv
        else:
            cv.value = float(value)
            if group is not None:
                cv.group = group
            if zone_id is not None:
                cv.zone_id = zone_id
            cv.last_updated = time.time()
        return cv

    def to_persistence(self) -> Dict[str, Any]:
        return {k: v.to_dict() for k, v in self._values.items()}

    def to_simple_dict(self) -> Dict[str, float]:
        return {k: v.value for k, v in self._values.items()}
