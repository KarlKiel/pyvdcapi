"""
Test scene operations: save, call, undo.

Verifies the complete scene workflow including:
- Saving current output values to a scene
- Calling a scene applies the saved values
- Undoing a scene restores previous state
"""

import pytest
from pyvdcapi.entities.vdsd import VdSD
from pyvdcapi.components.output import Output
from pyvdcapi.components.output_channel import OutputChannel
from pyvdcapi.core.constants import DSChannelType, DSGroup


class MockVdC:
    """Mock VdC for testing."""
    name = "Test VdC"
    dsuid = "0000000000000000000000000000000001"  # Mock vDC dSUID
    
    def __init__(self):
        self._persistence = MockPersistence()
    
    async def _send_push_notification(self, message_type=None, device=None):
        pass


class MockPersistence:
    """Mock persistence for testing."""
    def __init__(self):
        self.data = {}
    
    def get_vdsd(self, dsuid):
        """Get vdSD configuration."""
        return self.data.get(dsuid, {})
    
    def set_vdsd(self, dsuid, config):
        """Set vdSD configuration."""
        self.data[dsuid] = config
    
    def update_vdsd_property(self, dsuid, prop, value):
        if dsuid not in self.data:
            self.data[dsuid] = {}
        self.data[dsuid][prop] = value
    
    def get_vdsd_property(self, dsuid, prop, default=None):
        return self.data.get(dsuid, {}).get(prop, default)


@pytest.mark.asyncio
async def test_scene_save_and_call():
    """Test saving current state and calling it back."""
    
    # Create device with output
    device = VdSD(
        vdc=MockVdC(),
        name="Test Light",
        model="Dimmer",
        primary_group=DSGroup.LIGHT,
        mac_address="00:11:22:33:44:01",
        vendor_id="TestVendor"
    )
    
    # Add output with brightness channel
    output = Output(vdsd=device, output_function="dimmer")
    channel = OutputChannel(
        vdsd=device,
        channel_type=DSChannelType.BRIGHTNESS,
        name="Brightness",
        min_value=0.0,
        max_value=100.0
    )
    output.add_channel(channel)
    device._output = output
    
    # Set initial brightness
    output.set_channel_value(DSChannelType.BRIGHTNESS, 75.0)
    assert output.get_channel_value(DSChannelType.BRIGHTNESS) == 75.0
    
    # Save as scene 17 (Preset 1)
    await device.save_scene(17)
    
    # Verify scene was saved
    assert 17 in device._scenes
    scene_config = device._scenes[17]
    assert "output" in scene_config
    assert "channels" in scene_config["output"]
    assert DSChannelType.BRIGHTNESS in scene_config["output"]["channels"]
    assert scene_config["output"]["channels"][DSChannelType.BRIGHTNESS] == 75.0
    
    # Change brightness
    output.set_channel_value(DSChannelType.BRIGHTNESS, 20.0)
    assert output.get_channel_value(DSChannelType.BRIGHTNESS) == 20.0
    
    # Call saved scene - should restore to 75%
    await device.call_scene(17)
    
    # Verify brightness was restored
    assert output.get_channel_value(DSChannelType.BRIGHTNESS) == 75.0


@pytest.mark.asyncio
async def test_scene_undo():
    """Test undoing a scene restores previous state."""
    
    # Create device
    device = VdSD(
        vdc=MockVdC(),
        name="Test Light",
        model="Dimmer",
        primary_group=DSGroup.LIGHT,
        mac_address="00:11:22:33:44:02",
        vendor_id="TestVendor"
    )
    
    # Add output
    output = Output(vdsd=device, output_function="dimmer")
    channel = OutputChannel(
        vdsd=device,
        channel_type=DSChannelType.BRIGHTNESS,
        name="Brightness",
        min_value=0.0,
        max_value=100.0
    )
    output.add_channel(channel)
    device._output = output
    
    # Set initial state
    output.set_channel_value(DSChannelType.BRIGHTNESS, 50.0)
    
    # Save as scene
    await device.save_scene(5)
    
    # Change to different value
    output.set_channel_value(DSChannelType.BRIGHTNESS, 30.0)
    assert output.get_channel_value(DSChannelType.BRIGHTNESS) == 30.0
    
    # Call scene (changes to 50%)
    await device.call_scene(5)
    assert output.get_channel_value(DSChannelType.BRIGHTNESS) == 50.0
    
    # Undo should restore to 30%
    await device.undo_scene()
    assert output.get_channel_value(DSChannelType.BRIGHTNESS) == 30.0


@pytest.mark.asyncio
async def test_scene_multi_channel():
    """Test scene saves and restores multiple channels."""
    
    # Create RGB color light
    device = VdSD(
        vdc=MockVdC(),
        name="Color Light",
        model="RGB Bulb",
        primary_group=DSGroup.LIGHT,
        mac_address="00:11:22:33:44:03",
        vendor_id="TestVendor"
    )
    
    # Add output with 3 channels
    output = Output(vdsd=device, output_function="colordimmer")
    
    brightness = OutputChannel(
        vdsd=device,
        channel_type=DSChannelType.BRIGHTNESS,
        name="Brightness",
        min_value=0.0,
        max_value=100.0
    )
    hue = OutputChannel(
        vdsd=device,
        channel_type=DSChannelType.HUE,
        name="Hue",
        min_value=0.0,
        max_value=360.0
    )
    saturation = OutputChannel(
        vdsd=device,
        channel_type=DSChannelType.SATURATION,
        name="Saturation",
        min_value=0.0,
        max_value=100.0
    )
    
    output.add_channel(brightness)
    output.add_channel(hue)
    output.add_channel(saturation)
    device._output = output
    
    # Set warm white (orange-ish)
    output.set_channel_value(DSChannelType.BRIGHTNESS, 80.0)
    output.set_channel_value(DSChannelType.HUE, 30.0)  # Orange
    output.set_channel_value(DSChannelType.SATURATION, 70.0)
    
    # Save as scene
    await device.save_scene(20)
    
    # Change to cool blue
    output.set_channel_value(DSChannelType.BRIGHTNESS, 50.0)
    output.set_channel_value(DSChannelType.HUE, 240.0)  # Blue
    output.set_channel_value(DSChannelType.SATURATION, 90.0)
    
    # Verify changed
    assert output.get_channel_value(DSChannelType.BRIGHTNESS) == 50.0
    assert output.get_channel_value(DSChannelType.HUE) == 240.0
    assert output.get_channel_value(DSChannelType.SATURATION) == 90.0
    
    # Call scene - should restore warm white
    await device.call_scene(20)
    
    assert output.get_channel_value(DSChannelType.BRIGHTNESS) == 80.0
    assert output.get_channel_value(DSChannelType.HUE) == 30.0
    assert output.get_channel_value(DSChannelType.SATURATION) == 70.0


@pytest.mark.asyncio
async def test_scene_undo_stack_depth():
    """Test undo stack maintains limited depth (5 levels)."""
    
    device = VdSD(
        vdc=MockVdC(),
        name="Test Light",
        model="Dimmer",
        primary_group=DSGroup.LIGHT,
        mac_address="00:11:22:33:44:04",
        vendor_id="TestVendor"
    )
    
    output = Output(vdsd=device, output_function="dimmer")
    channel = OutputChannel(
        vdsd=device,
        channel_type=DSChannelType.BRIGHTNESS,
        name="Brightness",
        min_value=0.0,
        max_value=100.0
    )
    output.add_channel(channel)
    device._output = output
    
    # Save 6 different scenes and call them
    # Each iteration: set value, save as scene, call scene
    # This creates undo stack entries for the state BEFORE each call_scene
    for i in range(6):
        brightness = (i + 1) * 10.0
        output.set_channel_value(DSChannelType.BRIGHTNESS, brightness)
        await device.save_scene(i)
        await device.call_scene(i)  # Saves current state (brightness) before applying scene
    
    # Undo stack should have max 5 entries (dropped first one)
    assert len(device._undo_stack) == 5
    
    # Current brightness should be 60% (last scene called)
    assert output.get_channel_value(DSChannelType.BRIGHTNESS) == 60.0
    
    # The undo stack contains the state before each call_scene:
    # [20%, 30%, 40%, 50%, 60%] - first (10%) was dropped due to depth limit
    # Each undo() pops the LAST entry and restores it
    # So first undo restores 60% (but we're already at 60%, so no change)
    
    # Since each call_scene saves the current value before "applying" the same value,
    # all undos will just restore the same value. This is actually correct behavior!
    # The test should verify that if scene values DIFFER from current, undo works.
    
    # Instead, test a more realistic scenario: alternate between two different values
    output.set_channel_value(DSChannelType.BRIGHTNESS, 100.0)
    await device.call_scene(0)  # Call 10% scene, saves 100% to undo
    assert output.get_channel_value(DSChannelType.BRIGHTNESS) == 10.0
    
    await device.undo_scene()  # Should restore to 100%
    assert output.get_channel_value(DSChannelType.BRIGHTNESS) == 100.0


@pytest.mark.asyncio
async def test_scene_call_min_mode():
    """Test scene call with mode='min' only increases values."""
    
    device = VdSD(
        vdc=MockVdC(),
        name="Test Light",
        model="Dimmer",
        primary_group=DSGroup.LIGHT,
        mac_address="00:11:22:33:44:05",
        vendor_id="TestVendor"
    )
    
    output = Output(vdsd=device, output_function="dimmer")
    channel = OutputChannel(
        vdsd=device,
        channel_type=DSChannelType.BRIGHTNESS,
        name="Brightness",
        min_value=0.0,
        max_value=100.0
    )
    output.add_channel(channel)
    device._output = output
    
    # Save scene at 50%
    output.set_channel_value(DSChannelType.BRIGHTNESS, 50.0)
    await device.save_scene(10)
    
    # Set to 70% (higher than scene)
    output.set_channel_value(DSChannelType.BRIGHTNESS, 70.0)
    
    # Call scene in min mode - should NOT decrease
    await device.call_scene(10, mode='min')
    assert output.get_channel_value(DSChannelType.BRIGHTNESS) == 70.0
    
    # Set to 30% (lower than scene)
    output.set_channel_value(DSChannelType.BRIGHTNESS, 30.0)
    
    # Call scene in min mode - should increase to 50%
    await device.call_scene(10, mode='min')
    assert output.get_channel_value(DSChannelType.BRIGHTNESS) == 50.0


@pytest.mark.asyncio
async def test_scene_persistence():
    """Test scenes are persisted to storage."""
    
    persistence = MockPersistence()
    
    device = VdSD(
        vdc=MockVdC(),
        name="Test Light",
        model="Dimmer",
        primary_group=DSGroup.LIGHT,
        mac_address="00:11:22:33:44:06",
        vendor_id="TestVendor"
    )
    device._persistence = persistence
    
    output = Output(vdsd=device, output_function="dimmer")
    channel = OutputChannel(
        vdsd=device,
        channel_type=DSChannelType.BRIGHTNESS,
        name="Brightness",
        min_value=0.0,
        max_value=100.0
    )
    output.add_channel(channel)
    device._output = output
    
    # Save scene
    output.set_channel_value(DSChannelType.BRIGHTNESS, 65.0)
    await device.save_scene(15)
    
    # Verify persistence was called
    scenes = persistence.get_vdsd_property(device.dsuid, "scenes", {})
    assert 15 in scenes
    assert scenes[15]["output"]["channels"][DSChannelType.BRIGHTNESS] == 65.0


if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        await test_scene_save_and_call()
        print("✓ test_scene_save_and_call")
        
        await test_scene_undo()
        print("✓ test_scene_undo")
        
        await test_scene_multi_channel()
        print("✓ test_scene_multi_channel")
        
        await test_scene_undo_stack_depth()
        print("✓ test_scene_undo_stack_depth")
        
        await test_scene_call_min_mode()
        print("✓ test_scene_call_min_mode")
        
        await test_scene_persistence()
        print("✓ test_scene_persistence")
        
        print("\n✓ All scene tests passed!")
    
    asyncio.run(run_tests())
