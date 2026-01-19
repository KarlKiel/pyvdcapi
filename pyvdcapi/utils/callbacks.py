"""
Observer/callback pattern for value change notifications.

Provides immediate propagation of value changes between vdSD inputs/outputs
and external implementations.
"""

from typing import Callable, Any, Dict, List
from threading import Lock
import logging

logger = logging.getLogger(__name__)


CallbackFunction = Callable[[Any], None]


class Observable:
    """
    Observable value that notifies callbacks when changed.

    Used for device inputs/outputs to propagate changes immediately.
    """

    def __init__(self, initial_value: Any = None, name: str = ""):
        """
        Initialize observable value.

        Args:
            initial_value: Initial value
            name: Name for logging purposes
        """
        self._value = initial_value
        self._callbacks: List[CallbackFunction] = []
        self._lock = Lock()
        self._name = name

    def get(self) -> Any:
        """Get current value."""
        with self._lock:
            return self._value

    def set(self, value: Any, notify: bool = True) -> None:
        """
        Set value and optionally notify callbacks.

        Args:
            value: New value
            notify: If True, notify all registered callbacks
        """
        with self._lock:
            old_value = self._value
            self._value = value

            if notify and value != old_value:
                logger.debug(f"Observable '{self._name}' changed: {old_value} -> {value}")
                # Notify outside the lock to prevent deadlocks
                callbacks = self._callbacks.copy()

        if notify and value != old_value:
            for callback in callbacks:
                try:
                    callback(value)
                except Exception as e:
                    logger.error(f"Error in callback for '{self._name}': {e}", exc_info=True)

    def notify(self, *args, **kwargs) -> None:
        """
        Call all callbacks with arbitrary arguments.

        This complements the `set` API by allowing components to notify
        subscribers with multiple parameters (e.g., id and value).
        """
        with self._lock:
            callbacks = self._callbacks.copy()

        for callback in callbacks:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in callback for '{self._name}': {e}", exc_info=True)

    def subscribe(self, callback: CallbackFunction) -> None:
        """
        Subscribe to value changes.

        Args:
            callback: Function to call when value changes, receives new value as argument
        """
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)
                logger.debug(f"Added callback to observable '{self._name}'")

    def unsubscribe(self, callback: CallbackFunction) -> None:
        """
        Unsubscribe from value changes.

        Args:
            callback: Callback function to remove
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
                logger.debug(f"Removed callback from observable '{self._name}'")

    def clear_callbacks(self) -> None:
        """Remove all callbacks."""
        with self._lock:
            self._callbacks.clear()


class ObservableDict:
    """
    Dictionary with observable values.

    Useful for managing multiple observable properties.
    """

    def __init__(self):
        """Initialize observable dictionary."""
        self._observables: Dict[str, Observable] = {}
        self._lock = Lock()

    def get_observable(self, key: str, default: Any = None) -> Observable:
        """
        Get or create an observable for a key.

        Args:
            key: Dictionary key
            default: Default value if key doesn't exist

        Returns:
            Observable instance
        """
        with self._lock:
            if key not in self._observables:
                self._observables[key] = Observable(default, name=key)
            return self._observables[key]

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value for a key.

        Args:
            key: Dictionary key
            default: Default value if key doesn't exist

        Returns:
            Current value
        """
        with self._lock:
            if key in self._observables:
                return self._observables[key].get()
            return default

    def set(self, key: str, value: Any, notify: bool = True) -> None:
        """
        Set value for a key.

        Args:
            key: Dictionary key
            value: New value
            notify: If True, notify callbacks
        """
        observable = self.get_observable(key, value)
        observable.set(value, notify)

    def subscribe(self, key: str, callback: CallbackFunction) -> None:
        """
        Subscribe to changes for a specific key.

        Args:
            key: Dictionary key
            callback: Callback function
        """
        observable = self.get_observable(key)
        observable.subscribe(callback)

    def unsubscribe(self, key: str, callback: CallbackFunction) -> None:
        """
        Unsubscribe from changes for a specific key.

        Args:
            key: Dictionary key
            callback: Callback function
        """
        if key in self._observables:
            self._observables[key].unsubscribe(callback)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to regular dictionary.

        Returns:
            Dictionary with current values
        """
        with self._lock:
            return {key: obs.get() for key, obs in self._observables.items()}
