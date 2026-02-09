"""
Test Sensor settings and push throttling.

This test verifies the implementation of API section 4.4.2:
- group: dS group assignment
- minPushInterval: Minimum time between any pushes
- changesOnlyInterval: Minimum time between same-value pushes
"""

import time
from pyvdcapi.components.sensor import Sensor


def test_sensor_settings_from_dss():
    """Test that DSS can update sensor settings."""
    
    class MockVdSD:
        def push_sensor_value(self, sensor_id, value):
            pass
    
    sensor = Sensor(
        vdsd=MockVdSD(),
        name="Temp",
        sensor_type="temperature",
        unit="°C",
        sensor_id=1,
        min_value=-40.0,
        max_value=125.0,
        resolution=0.1
    )
    
    # Check defaults
    assert sensor.group == 0
    assert sensor.min_push_interval == 2.0
    assert sensor.changes_only_interval == 0.0
    
    # DSS updates settings
    sensor.from_dict({
        "settings": {
            "group": 1,  # Assign to heating group
            "minPushInterval": 5.0,  # Push max every 5 seconds
            "changesOnlyInterval": 60.0  # Same-value updates only every 60s
        }
    })
    
    assert sensor.group == 1
    assert sensor.min_push_interval == 5.0
    assert sensor.changes_only_interval == 60.0
    
    # to_dict includes settings
    data = sensor.to_dict()
    assert "settings" in data
    assert data["settings"]["group"] == 1
    assert data["settings"]["minPushInterval"] == 5.0
    assert data["settings"]["changesOnlyInterval"] == 60.0


def test_min_push_interval_throttling():
    """Test minPushInterval prevents rapid pushes."""
    
    class MockVdSD:
        def __init__(self):
            self.push_calls = []
        
        def push_sensor_value(self, sensor_id, value):
            self.push_calls.append((time.time(), value))
    
    mock_vdsd = MockVdSD()
    
    sensor = Sensor(
        vdsd=mock_vdsd,
        name="Temp",
        sensor_type="temperature",
        unit="°C",
        sensor_id=1,
        min_value=-40.0,
        max_value=125.0,
        resolution=0.1
    )
    
    # Set minPushInterval to 1.0 second
    sensor.min_push_interval = 1.0
    sensor.changes_only_interval = 0.0
    
    # Clear initial state
    mock_vdsd.push_calls.clear()
    sensor._last_push_time = 0.0
    
    # First update - should push immediately
    sensor.update_value(20.0)
    assert len(mock_vdsd.push_calls) == 1
    
    # Second update immediately - should be throttled
    sensor.update_value(21.0)
    assert len(mock_vdsd.push_calls) == 1, "Should be throttled by minPushInterval"
    
    # Wait for throttle interval to pass
    time.sleep(1.1)
    
    # Third update - should push now
    sensor.update_value(22.0)
    assert len(mock_vdsd.push_calls) == 2


def test_changes_only_interval_throttling():
    """Test changesOnlyInterval filters same-value updates."""
    
    class MockVdSD:
        def __init__(self):
            self.push_calls = []
        
        def push_sensor_value(self, sensor_id, value):
            self.push_calls.append(value)
    
    mock_vdsd = MockVdSD()
    
    sensor = Sensor(
        vdsd=mock_vdsd,
        name="Temp",
        sensor_type="temperature",
        unit="°C",
        sensor_id=1,
        min_value=-40.0,
        max_value=125.0,
        resolution=0.1
    )
    
    # Disable minPushInterval, enable changesOnlyInterval
    sensor.min_push_interval = 0.0
    sensor.changes_only_interval = 2.0  # 2 seconds for same-value pushes
    
    # Clear state
    mock_vdsd.push_calls.clear()
    sensor._last_push_time = 0.0
    
    # First update to 20.0 - should push
    sensor.update_value(20.0)
    assert len(mock_vdsd.push_calls) == 1
    time.sleep(0.1)
    
    # Change to 21.0 immediately - should push (value changed)
    sensor.update_value(21.0)
    assert len(mock_vdsd.push_calls) == 2, "Value change should bypass changesOnlyInterval"
    time.sleep(0.1)
    
    # Same value (21.0) again immediately - should be throttled
    sensor.update_value(21.0)
    assert len(mock_vdsd.push_calls) == 2, "Same value should be throttled"
    
    # Wait for changesOnlyInterval
    time.sleep(2.0)
    
    # Same value again - should push now (age update)
    sensor.update_value(21.0)
    assert len(mock_vdsd.push_calls) == 3


def test_hysteresis_and_throttling_interaction():
    """Test that hysteresis and throttling work together."""
    
    class MockVdSD:
        def __init__(self):
            self.push_calls = []
        
        def push_sensor_value(self, sensor_id, value):
            self.push_calls.append(value)
    
    mock_vdsd = MockVdSD()
    
    sensor = Sensor(
        vdsd=mock_vdsd,
        name="Temp",
        sensor_type="temperature",
        unit="°C",
        sensor_id=1,
        min_value=-40.0,
        max_value=125.0,
        resolution=0.1,
        initial_value=20.0
    )
    
    # Set hysteresis to 1.0°C
    sensor.on_change(lambda sid, val: None, hysteresis=1.0)
    
    # Set throttling
    sensor.min_push_interval = 0.5
    sensor.changes_only_interval = 0.0
    
    # Clear state
    mock_vdsd.push_calls.clear()
    sensor._last_push_time = 0.0
    
    # Small change (0.5°C) - blocked by hysteresis, no push
    sensor.update_value(20.5)
    assert len(mock_vdsd.push_calls) == 0, "Hysteresis should block small changes"
    
    # Large change (1.5°C total) - passes hysteresis, should push
    sensor.update_value(21.5)
    assert len(mock_vdsd.push_calls) == 1
    
    # Another large change immediately - blocked by throttling
    sensor.update_value(23.0)
    assert len(mock_vdsd.push_calls) == 1, "minPushInterval should throttle"
    
    # Wait for throttle
    time.sleep(0.6)
    
    # Now should push
    sensor.update_value(24.0)
    assert len(mock_vdsd.push_calls) == 2


def test_settings_persistence():
    """Test that settings are included in to_dict/from_dict."""
    
    class MockVdSD:
        def push_sensor_value(self, sensor_id, value):
            pass
    
    sensor1 = Sensor(
        vdsd=MockVdSD(),
        name="Power",
        sensor_type="power",
        unit="W",
        sensor_id=5
    )
    
    # Configure settings
    sensor1.group = 3
    sensor1.min_push_interval = 10.0
    sensor1.changes_only_interval = 120.0
    sensor1.update_value(1500.0)
    
    # Serialize
    data = sensor1.to_dict()
    
    # Create new sensor from data
    sensor2 = Sensor(
        vdsd=MockVdSD(),
        name="",
        sensor_type="",
        unit="",
        sensor_id=0
    )
    sensor2.from_dict(data)
    
    # Verify settings restored
    assert sensor2.group == 3
    assert sensor2.min_push_interval == 10.0
    assert sensor2.changes_only_interval == 120.0


if __name__ == "__main__":
    test_sensor_settings_from_dss()
    test_min_push_interval_throttling()
    test_changes_only_interval_throttling()
    test_hysteresis_and_throttling_interaction()
    test_settings_persistence()
    print("✓ All sensor settings tests passed!")
