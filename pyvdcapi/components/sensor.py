"""
Sensor - Continuous value input for vDC devices.

A Sensor represents an input that provides continuous or periodic
numerical readings:
- Temperature sensors (°C, °F)
- Humidity sensors (% relative humidity)
- Illuminance sensors (lux)
- Power meters (W, kWh)
- Air quality sensors (ppm CO2, VOC)
- Pressure sensors (hPa, bar)
- Any other analog/numeric measurement

Sensor Types:
┌──────────────────────────────────────────────────────────┐
│ Common Sensor Types                                      │
├──────────────────────────────────────────────────────────┤
│ temperature:   Temperature (°C, °F, K)                   │
│ humidity:      Relative humidity (%)                     │
│ illuminance:   Light level (lux)                         │
│ power:         Electrical power (W)                      │
│ energy:        Energy consumption (kWh)                  │
│ voltage:       Voltage (V)                               │
│ current:       Current (A)                               │
│ co2:           CO₂ concentration (ppm)                   │
│ voc:           Volatile organic compounds (ppb)          │
│ pressure:      Atmospheric pressure (hPa)                │
│ sound:         Sound level (dB)                          │
│ distance:      Distance measurement (m, cm)              │
│ custom:        Application-specific measurement          │
└──────────────────────────────────────────────────────────┘

Sensor Value Flow:
┌─────────────────────────────────────────────────────────┐
│ 1. Hardware measures physical quantity                 │
│    ↓                                                    │
│ 2. Driver reads sensor value                           │
│    ↓                                                    │
│ 3. Application calls sensor.update_value(23.5)         │
│    ↓                                                    │
│ 4. Sensor validates and stores value                   │
│    ↓                                                    │
│ 5. Sensor triggers callbacks (if changed significantly)│
│    ↓                                                    │
│ 6. Application logic (e.g., trigger alert if too hot)  │
│    ↓                                                    │
│ 7. Sensor sends notification to vdSM (periodic)        │
│    ↓                                                    │
│ 8. vdSM displays value, triggers automation            │
└─────────────────────────────────────────────────────────┘

Sensor Features:
- Value validation (min/max bounds)
- Change detection (hysteresis to reduce noise)
- Age tracking (freshness of reading)
- Unit conversion support
- Error state handling (sensor offline, out of range)
- Periodic vs event-based reporting

Usage:
```python
# Create temperature sensor
temp_sensor = Sensor(
    vdsd=device,
    name="Room Temperature",
    sensor_type="temperature",
    unit="°C",
    min_value=-40.0,
    max_value=125.0,
    resolution=0.1
)

# Set up callback for significant changes
def on_temp_change(sensor_id, value):
    print(f"Temperature changed to {value}°C")
    if value > 28.0:
        print("Too hot! Turning on AC")
        ac.set_target_temperature(24.0)
    elif value < 18.0:
        print("Too cold! Turning on heating")
        heater.set_target_temperature(22.0)

temp_sensor.on_change(on_temp_change, hysteresis=0.5)  # Report if changes by 0.5°C

# Update sensor from hardware reading
current_temp = hardware.read_temperature()
temp_sensor.update_value(current_temp)

# Create power meter
power_meter = Sensor(
    vdsd=device,
    name="Total Power",
    sensor_type="power",
    unit="W",
    min_value=0.0,
    max_value=10000.0,
    resolution=1.0
)

# Periodic update
import asyncio

async def poll_power():
    while True:
        power = hardware.read_power()
        power_meter.update_value(power)
        await asyncio.sleep(5.0)  # Every 5 seconds

asyncio.create_task(poll_power())
```
"""

import logging
import time
import asyncio
from typing import Optional, Callable, Dict, Any
from typing import TYPE_CHECKING
from ..utils.callbacks import Observable
from ..utils.validators import PropertyValidator

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..entities.vdsd import VdSD


class Sensor:
    """
    Represents a continuous value sensor input on a device.

    A Sensor provides numerical readings from physical measurements.
    The sensor:

    - Tracks current value and history
    - Validates readings against min/max bounds
    - Detects significant changes (hysteresis)
    - Triggers callbacks on meaningful updates
    - Sends periodic notifications to vdSM
    - Handles error states (sensor offline, invalid reading)

    Sensor Configuration:
    - sensor_id: Unique identifier within device
    - sensor_type: Type of measurement (temperature, humidity, etc.)
    - unit: Unit of measurement (°C, %, lux, W, etc.)
    - min/max: Valid range for readings
    - resolution: Precision of measurements

    Value Tracking:
    - value: Current reading
    - last_update: Timestamp of last update
    - age: Time since last reading
    - error: Error state (None if OK)

    Attributes:
        vdsd: Parent device
        sensor_id: Sensor identifier
        sensor_type: Type of sensor
        name: Sensor name
        unit: Unit of measurement
        value: Current reading
    """

    def __init__(
        self,
        vdsd: "VdSD",
        name: str,
        sensor_type: str,
        unit: str,
        sensor_id: Optional[int] = None,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        resolution: float = 0.1,
        initial_value: Optional[float] = None,
    ):
        """
        Initialize sensor input.

        Args:
            vdsd: Parent VdSD device
            name: Human-readable sensor name (e.g., "Living Room Temperature")
            sensor_type: Type of sensor (temperature, humidity, power, etc.)
            unit: Unit of measurement (°C, %, lux, W, ppm, etc.)
            sensor_id: Unique sensor identifier (auto-assigned if None)
            min_value: Minimum valid reading (for validation)
            max_value: Maximum valid reading (for validation)
            resolution: Precision/granularity of readings
            initial_value: Starting value (if known)

        Example:
            # Temperature sensor
            temp = Sensor(
                vdsd=device,
                name="Outdoor Temperature",
                sensor_type="temperature",
                unit="°C",
                min_value=-40.0,
                max_value=125.0,
                resolution=0.1,
                initial_value=20.0
            )

            # Humidity sensor
            humidity = Sensor(
                vdsd=device,
                name="Room Humidity",
                sensor_type="humidity",
                unit="%",
                min_value=0.0,
                max_value=100.0,
                resolution=0.1
            )

            # Power meter
            power = Sensor(
                vdsd=device,
                name="Total Power",
                sensor_type="power",
                unit="W",
                min_value=0.0,
                max_value=10000.0,
                resolution=1.0
            )
        """
        self.vdsd = vdsd
        self.name = name
        self.sensor_type = sensor_type
        self.unit = unit

        # Auto-assign sensor ID if not provided
        if sensor_id is None:
            self.sensor_id = 0  # Would be set by VdSD when added
        else:
            self.sensor_id = sensor_id

        # Description properties (API section 4.4.1) - read-only
        self.ds_index = self.sensor_id  # Device sensor index (0..N-1)
        self.sensor_usage = 0  # 0=undefined, 1=room, 2=outdoors, 3=user

        # Value range and precision
        self.min_value = min_value
        self.max_value = max_value
        self.resolution = resolution

        # Settings properties (API section 4.4.2) - configurable from DSS
        self.group = 0  # dS group number (0=undefined)
        self.min_push_interval = 2.0  # Minimum seconds between push notifications
        self.changes_only_interval = 0.0  # Minimum seconds between same-value pushes (0=push all)

        # Current state
        self._value: Optional[float] = initial_value
        self._last_update_time = time.time() if initial_value is not None else None
        self._error: Optional[str] = None

        # Change detection
        # Store last notified value to implement hysteresis
        self._last_notified_value: Optional[float] = initial_value
        self._hysteresis = 0.0  # Default: notify on any change
        
        # Push throttling state
        self._last_push_time = 0.0  # When we last pushed to vdSM
        self._last_pushed_value: Optional[float] = initial_value  # Last value we pushed

        # Observable for value changes
        # Subscribers receive: callback(sensor_id, value)
        self._change_observable = Observable()

        # Validator
        self._validator = PropertyValidator()

        logger.debug(
            f"Created sensor: id={self.sensor_id}, "
            f"name='{name}', type={sensor_type}, "
            f"unit={unit}, range=[{min_value}, {max_value}]"
        )

    def update_value(self, value: float) -> None:
        """
        Update sensor value from hardware reading.

        This should be called when a new measurement is available.
        The value is validated, stored, and callbacks triggered if
        the change is significant (exceeds hysteresis threshold).

        Args:
            value: New sensor reading

        Example:
            # Periodic polling
            while True:
                temp = hardware.read_temperature()
                temp_sensor.update_value(temp)
                time.sleep(60)  # Every minute

            # Event-driven (interrupt on significant change)
            def on_sensor_interrupt():
                reading = hardware.read_sensor()
                sensor.update_value(reading)
        """
        # Validate value against bounds
        if self.min_value is not None and value < self.min_value:
            logger.warning(f"Sensor {self.sensor_id} value {value} below minimum {self.min_value}")
            self._error = f"Below minimum ({self.min_value})"
            return

        if self.max_value is not None and value > self.max_value:
            logger.warning(f"Sensor {self.sensor_id} value {value} above maximum {self.max_value}")
            self._error = f"Above maximum ({self.max_value})"
            return

        # Clear any previous error
        self._error = None

        # Round to resolution
        rounded_value = round(value / self.resolution) * self.resolution

        # Update state
        old_value = self._value
        self._value = rounded_value
        self._last_update_time = time.time()

        logger.debug(f"Sensor {self.sensor_id} ('{self.name}') updated: " f"{old_value} → {rounded_value} {self.unit}")

        # Check if change is significant (hysteresis)
        # Only trigger callbacks if value changed by more than hysteresis
        should_notify = False

        if self._last_notified_value is None:
            # First reading
            should_notify = True
        elif abs(rounded_value - self._last_notified_value) >= self._hysteresis:
            # Change exceeds hysteresis threshold
            should_notify = True

        if should_notify:
            self._last_notified_value = rounded_value

            # Trigger callbacks
            self._change_observable.notify(self.sensor_id, rounded_value)

            # Send sensor value notification to vdSM with throttling
            # Pattern A: Device → DSS (push notification on significant change)
            # Implements API section 4.4.2 throttling settings
            self._push_value_with_throttling(rounded_value)

    def _push_value_with_throttling(self, value: float) -> None:
        """
        Push sensor value to vdSM with throttling per API settings.
        
        Implements API section 4.4.2 throttling:
        - minPushInterval: Minimum time between any pushes
        - changesOnlyInterval: Minimum time between pushes of same value
        
        Args:
            value: Sensor value to push
        """
        current_time = time.time()
        time_since_last_push = current_time - self._last_push_time
        value_changed = (self._last_pushed_value is None or 
                        abs(value - self._last_pushed_value) >= self.resolution)
        
        # Check minPushInterval throttling (applies to all pushes)
        if time_since_last_push < self.min_push_interval:
            logger.debug(
                f"Sensor {self.sensor_id} push throttled by minPushInterval: "
                f"{time_since_last_push:.2f}s < {self.min_push_interval}s"
            )
            return
        
        # Check changesOnlyInterval throttling (only for same-value pushes)
        if not value_changed and self.changes_only_interval > 0:
            if time_since_last_push < self.changes_only_interval:
                logger.debug(
                    f"Sensor {self.sensor_id} same-value push throttled: "
                    f"{time_since_last_push:.2f}s < {self.changes_only_interval}s"
                )
                return
        
        # Throttling passed - send push notification
        self.vdsd.push_sensor_value(self.sensor_id, value)
        self._last_push_time = current_time
        self._last_pushed_value = value
        
        logger.debug(
            f"Sensor {self.sensor_id} pushed value {value} {self.unit} "
            f"(changed={value_changed})"
        )

    def set_error(self, error_message: str) -> None:
        """
        Set sensor error state.

        Call this when sensor reading fails (sensor offline, communication
        error, out of range, etc.).

        Args:
            error_message: Description of error

        Example:
            try:
                value = hardware.read_temperature()
                sensor.update_value(value)
            except IOError:
                sensor.set_error("Sensor communication failed")
        """
        self._error = error_message
        self._last_update_time = time.time()

        logger.error(f"Sensor {self.sensor_id} error: {error_message}")

        # Notify of error condition
        self._change_observable.notify(self.sensor_id, None)

    def clear_error(self) -> None:
        """Clear sensor error state."""
        self._error = None

    def get_value(self) -> Optional[float]:
        """
        Get current sensor value.

        Returns:
            Current value, or None if no reading available or error
        """
        return self._value if self._error is None else None

    def get_age(self) -> Optional[float]:
        """
        Get age of current reading in seconds.

        Indicates how fresh the data is. Stale data (high age) might
        indicate sensor is offline or not being polled.
        Per vDC API spec section 4.4.3, age is returned in seconds.

        Returns:
            Seconds since last update, or None if no reading
        """
        if self._last_update_time is None:
            return None
        return time.time() - self._last_update_time

    def has_error(self) -> bool:
        """
        Check if sensor is in error state.

        Returns:
            True if sensor has error, False if OK
        """
        return self._error is not None

    def get_error(self) -> Optional[str]:
        """
        Get error message if sensor has error.

        Returns:
            Error message string, or None if no error
        """
        return self._error

    def on_change(self, callback: Callable[[int, Optional[float]], None], hysteresis: float = 0.0) -> None:
        """
        Register callback for value changes.

        The callback will be invoked when the sensor value changes
        significantly (exceeds hysteresis threshold).

        Callback signature: callback(sensor_id: int, value: Optional[float])
        - value is None if sensor has error

        Args:
            callback: Function to call on significant changes
            hysteresis: Minimum change to trigger callback (reduces noise)

        Example:
            def handle_temperature(sensor_id, value):
                if value is None:
                    print("Temperature sensor error!")
                    return

                print(f"Temperature: {value}°C")

                if value > 30.0:
                    print("Too hot!")
                elif value < 15.0:
                    print("Too cold!")

            # Trigger callback only if temperature changes by ≥0.5°C
            temp_sensor.on_change(handle_temperature, hysteresis=0.5)

            def handle_power(sensor_id, value):
                if value is not None:
                    print(f"Power consumption: {value} W")
                    if value > 5000:
                        print("WARNING: High power usage!")

            # Trigger on any power change ≥10W
            power_meter.on_change(handle_power, hysteresis=10.0)
        """
        self._hysteresis = hysteresis
        self._change_observable.subscribe(callback)

    def remove_callback(self, callback: Callable[[int, Optional[float]], None]) -> None:
        """
        Remove a value change callback.

        Args:
            callback: Function to remove from subscribers
        """
        self._change_observable.unsubscribe(callback)

    def bind_to(
        self,
        getter: Callable[[], Optional[float]],
        poll_interval: float,
        epsilon: float = 0.0,
    ) -> asyncio.Task:
        """
        Bind this sensor to a native hardware value (Hardware → vdSM).

        Args:
            getter: Function returning current native sensor value (or None if unavailable)
            poll_interval: Poll interval in seconds
            epsilon: Minimum change required to publish updates

        Returns:
            asyncio.Task for the polling loop
        """
        async def _poll() -> None:
            last_value = getter()
            if last_value is not None:
                self.update_value(last_value)

            while True:
                await asyncio.sleep(poll_interval)
                current = getter()
                if current is None:
                    continue
                if last_value is None or abs(current - last_value) > epsilon:
                    self.update_value(current)
                    last_value = current

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError as exc:
            raise RuntimeError("bind_to() requires a running event loop") from exc

        return loop.create_task(_poll())

    def bind_to_events(
        self,
        register: Callable[[Callable[[float], None]], None],
    ) -> None:
        """
        Bind this sensor to native hardware events (Hardware → vdSM).

        Args:
            register: Function that accepts a callback(value) and registers it
                      with the native hardware event source.
        """
        def _on_event(value: float) -> None:
            self.update_value(value)

        register(_on_event)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert sensor to dictionary for property tree.

        Returns API-compliant structure per section 4.4.

        Returns:
            Dictionary representation of sensor
        """
        result = {
            # Description properties (section 4.4.1) - read-only, invariable
            "name": self.name,
            "dsIndex": self.ds_index,
            "sensorType": self.sensor_type,
            "sensorUsage": self.sensor_usage,
            "unit": self.unit,
            "resolution": self.resolution,
            # Legacy compatibility
            "inputType": "sensor",
            "sensorID": self.sensor_id,
            # Settings properties (section 4.4.2) - configurable
            "settings": {
                "group": self.group,
                "minPushInterval": self.min_push_interval,
                "changesOnlyInterval": self.changes_only_interval,
            },
        }

        # Add value range if specified
        if self.min_value is not None:
            result["min"] = self.min_value
        if self.max_value is not None:
            result["max"] = self.max_value

        # Add current state (section 4.4.3)
        if self._error:
            result["error"] = self._error
        elif self._value is not None:
            result["value"] = self._value
            result["age"] = self.get_age()

        return result

    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        Update sensor configuration from dictionary.
        
        Handles settings updates from DSS (API section 4.4.2).

        Args:
            data: Dictionary with sensor properties
        """
        # Description properties (mostly read-only, but allow updates)
        if "name" in data:
            self.name = data["name"]
        if "unit" in data:
            self.unit = data["unit"]
        if "resolution" in data:
            self.resolution = data["resolution"]
        if "min" in data:
            self.min_value = data["min"]
        if "max" in data:
            self.max_value = data["max"]
        
        # Settings properties (section 4.4.2) - DSS → Device (Pattern B)
        # Accept settings either nested or top-level
        settings = data.get("settings", data)
        
        if "group" in settings:
            old_group = self.group
            self.group = settings["group"]
            logger.info(
                f"Sensor {self.sensor_id} group changed: {old_group} → {self.group}"
            )
        
        if "minPushInterval" in settings:
            old_interval = self.min_push_interval
            self.min_push_interval = settings["minPushInterval"]
            logger.info(
                f"Sensor {self.sensor_id} minPushInterval changed: "
                f"{old_interval}s → {self.min_push_interval}s"
            )
        
        if "changesOnlyInterval" in settings:
            old_interval = self.changes_only_interval
            self.changes_only_interval = settings["changesOnlyInterval"]
            logger.info(
                f"Sensor {self.sensor_id} changesOnlyInterval changed: "
                f"{old_interval}s → {self.changes_only_interval}s"
            )

    def __repr__(self) -> str:
        """String representation of sensor."""
        value_str = f"{self._value} {self.unit}" if self._value is not None else "N/A"
        if self._error:
            value_str = f"ERROR: {self._error}"

        return (
            f"Sensor(id={self.sensor_id}, " f"name='{self.name}', " f"type={self.sensor_type}, " f"value={value_str})"
        )
