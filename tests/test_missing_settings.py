"""
Test missing settings properties for BinaryInput and Output.

This test verifies implementation of API section 4.3.2 (BinaryInput Settings)
and section 4.8.2 (Output Settings) that were previously missing.
"""

from pyvdcapi.components.binary_input import BinaryInput
from pyvdcapi.components.output import Output
from pyvdcapi.core.constants import DSChannelType


def test_binary_input_settings():
    """Test BinaryInput settings (group, sensorFunction) per API section 4.3.2."""
    
    class MockVdSD:
        name = "Test Device"
        def push_binary_input_state(self, input_id, state):
            pass
    
    bi = BinaryInput(
        vdsd=MockVdSD(),
        name="Motion Sensor",
        input_type="motion",
        input_id=1
    )
    
    # Check defaults
    assert bi.group == 0, "Default group should be 0 (undefined)"
    assert bi.sensor_function == 0, "Default sensorFunction should be 0"
    
    # DSS updates settings
    bi.from_dict({
        "settings": {
            "group": 1,  # Light group
            "sensorFunction": 5  # Motion detector
        }
    })
    
    assert bi.group == 1
    assert bi.sensor_function == 5
    
    # to_dict includes settings
    data = bi.to_dict()
    assert "settings" in data
    assert data["settings"]["group"] == 1
    assert data["settings"]["sensorFunction"] == 5
    assert data["settings"]["invert"] == False


def test_binary_input_settings_persistence():
    """Test that BinaryInput settings persist through serialization."""
    
    class MockVdSD:
        name = "Device"
        def push_binary_input_state(self, input_id, state):
            pass
    
    bi1 = BinaryInput(
        vdsd=MockVdSD(),
        name="Door",
        input_type="contact",
        input_id=2
    )
    
    # Configure
    bi1.group = 9  # Security
    bi1.sensor_function = 14  # Door contact
    
    # Serialize
    data = bi1.to_dict()
    
    # Create new instance from data
    bi2 = BinaryInput(
        vdsd=MockVdSD(),
        name="",
        input_type="",
        input_id=0
    )
    bi2.from_dict(data)
    
    # Verify settings restored
    assert bi2.group == 9
    assert bi2.sensor_function == 14


def test_output_settings_all_properties():
    """Test Output settings (all 14 properties) per API section 4.8.2."""
    
    class MockVdSD:
        name = "Light Device"
    
    output = Output(
        vdsd=MockVdSD(),
        output_function="dimmer",
        output_mode="gradual"
    )
    
    # Check defaults
    assert output.active_group == 1  # Light group
    assert output.groups == {1: True}
    assert output.output_mode == "gradual"
    assert output.push_changes == True
    assert output.on_threshold == 50.0
    assert output.min_brightness == 0.0
    assert output.dim_time_up == 0
    assert output.dim_time_down == 0
    assert output.heating_system_capability == 0
    assert output.heating_system_type == 0
    
    # DSS updates settings
    output.from_dict({
        "settings": {
            "activeGroup": 3,  # Shading group
            "groups": {1: True, 3: True},  # Multi-group
            "mode": 2,  # Gradual (enum)
            "pushChanges": False,
            "onThreshold": 25.0,
            "minBrightness": 5.0,
            "dimTimeUp": 10,
            "dimTimeDown": 20,
            "dimTimeUpAlt1": 15,
            "dimTimeDownAlt1": 25,
            "dimTimeUpAlt2": 30,
            "dimTimeDownAlt2": 40,
            "heatingSystemCapability": 3,  # Heating and cooling
            "heatingSystemType": 2  # Radiator
        }
    })
    
    # Verify all updated
    assert output.active_group == 3
    assert output.groups == {1: True, 3: True}
    assert output.push_changes == False
    assert output.on_threshold == 25.0
    assert output.min_brightness == 5.0
    assert output.dim_time_up == 10
    assert output.dim_time_down == 20
    assert output.dim_time_up_alt1 == 15
    assert output.dim_time_down_alt1 == 25
    assert output.dim_time_up_alt2 == 30
    assert output.dim_time_down_alt2 == 40
    assert output.heating_system_capability == 3
    assert output.heating_system_type == 2


def test_output_settings_persistence():
    """Test that Output settings persist through serialization."""
    
    class MockVdSD:
        name = "Climate Device"
    
    output1 = Output(
        vdsd=MockVdSD(),
        output_function="heating",
        output_mode="gradual"
    )
    
    # Configure
    output1.active_group = 8  # Climate
    output1.groups = {8: True, 9: True}
    output1.on_threshold = 30.0
    output1.min_brightness = 10.0
    output1.heating_system_capability = 1  # Heating only
    output1.heating_system_type = 1  # Floor heating
    
    # Serialize
    data = output1.to_dict()
    
    # Create new instance from data
    output2 = Output(
        vdsd=MockVdSD(),
        output_function="dimmer"
    )
    output2.from_dict(data)
    
    # Verify settings restored
    assert output2.active_group == 8
    assert output2.groups == {8: True, 9: True}
    assert output2.on_threshold == 30.0
    assert output2.min_brightness == 10.0
    assert output2.heating_system_capability == 1
    assert output2.heating_system_type == 1


def test_output_mode_enum_conversion():
    """Test Output mode can be updated via integer enum from DSS."""
    
    class MockVdSD:
        name = "Device"
    
    output = Output(vdsd=MockVdSD())
    
    # DSS sends mode as integer enum (API section 4.8.2)
    output.from_dict({"settings": {"mode": 0}})  # Disabled
    assert output.output_mode == "disabled"
    
    output.from_dict({"settings": {"mode": 1}})  # Binary
    assert output.output_mode == "binary"
    
    output.from_dict({"settings": {"mode": 2}})  # Gradual
    assert output.output_mode == "gradual"
    
    output.from_dict({"settings": {"mode": 127}})  # Default
    assert output.output_mode == "gradual"


def test_output_to_dict_includes_all_settings():
    """Test that to_dict() exports all settings properties."""
    
    class MockVdSD:
        name = "Device"
    
    output = Output(vdsd=MockVdSD())
    
    # Set some non-default values
    output.active_group = 2
    output.on_threshold = 35.0
    output.dim_time_up = 50
    output.heating_system_capability = 2
    
    data = output.to_dict()
    
    # Verify all settings exported
    assert "settings" in data
    settings = data["settings"]
    
    assert "activeGroup" in settings
    assert "groups" in settings
    assert "mode" in settings
    assert "pushChanges" in settings
    assert "onThreshold" in settings
    assert "minBrightness" in settings
    assert "dimTimeUp" in settings
    assert "dimTimeDown" in settings
    assert "dimTimeUpAlt1" in settings
    assert "dimTimeDownAlt1" in settings
    assert "dimTimeUpAlt2" in settings
    assert "dimTimeDownAlt2" in settings
    assert "heatingSystemCapability" in settings
    assert "heatingSystemType" in settings
    
    # Verify values
    assert settings["activeGroup"] == 2
    assert settings["onThreshold"] == 35.0
    assert settings["dimTimeUp"] == 50
    assert settings["heatingSystemCapability"] == 2


if __name__ == "__main__":
    test_binary_input_settings()
    test_binary_input_settings_persistence()
    test_output_settings_all_properties()
    test_output_settings_persistence()
    test_output_mode_enum_conversion()
    test_output_to_dict_includes_all_settings()
    print("✓ All settings tests passed!")
