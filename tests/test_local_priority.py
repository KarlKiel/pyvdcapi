"""
Tests for local priority enforcement and ignoreLocalPriority flag.

This module tests the dS 1.0 compatibility features for local scene priority:
- Setting and clearing local priority
- Priority enforcement during scene calls
- Scene ignoreLocalPriority flag bypass
- Force parameter override
"""

import pytest
from pyvdcapi.entities.vdsd import VdSD
from pyvdcapi.components.output import Output
from pyvdcapi.components.output_channel import OutputChannel
from pyvdcapi.core.constants import DSGroup, DSChannelType


class MockVdC:
    """Mock VdC for testing."""
    name = "Test VdC"
    dsuid = "0000000000000000000000000000000001"  # Mock vDC dSUID
    
    def __init__(self):
        self._persistence = MockPersistence()
    
    async def _send_push_notification(self, message_type=None, device=None):
        pass


class MockPersistence:
    """Mock persistence for testing without file I/O."""

    def __init__(self):
        self.data = {}

    def get_vdc(self, dsuid):
        return self.data.get(f"vdc_{dsuid}")

    def set_vdc(self, dsuid, config):
        self.data[f"vdc_{dsuid}"] = config

    def get_vdsd(self, dsuid):
        return self.data.get(dsuid, {})

    def set_vdsd(self, dsuid, config):
        self.data[dsuid] = config

    def update_vdsd_property(self, dsuid, property_name, value):
        """Update a single property of a vdSD."""
        if dsuid not in self.data:
            self.data[dsuid] = {}
        self.data[dsuid][property_name] = value

    def get_vdsd_property(self, dsuid, property_name, default=None):
        """Get a single property of a vdSD."""
        return self.data.get(dsuid, {}).get(property_name, default)


def create_test_device():
    """Helper to create a test device with output channel."""
    device = VdSD(
        vdc=MockVdC(),
        name="Test Light",
        model="Dimmer",
        primary_group=DSGroup.YELLOW,
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
    
    return device, channel


@pytest.mark.asyncio
async def test_local_priority_blocks_other_scenes():
    """Verify localPriority blocks non-matching scenes."""
    device, channel = create_test_device()
    
    # Save two scenes
    channel.set_value(50.0)
    await device.save_scene(5)
    
    channel.set_value(75.0)
    await device.save_scene(10)
    
    # Set local priority to scene 10
    device.set_local_priority(10)
    
    # Scene 10 should work (matches priority)
    channel.set_value(0.0)
    await device.call_scene(10)
    assert channel.get_value() == 75.0
    
    # Scene 5 should be blocked
    await device.call_scene(5)
    assert channel.get_value() == 75.0  # Unchanged (blocked)
    
    # Scene 5 with force should work
    await device.call_scene(5, force=True)
    assert channel.get_value() == 50.0


@pytest.mark.asyncio
async def test_local_priority_cleared():
    """Verify clearing localPriority allows all scenes."""
    device, channel = create_test_device()
    
    channel.set_value(50.0)
    await device.save_scene(5)
    
    # Set and clear priority
    device.set_local_priority(10)
    device.set_local_priority(None)
    
    # Scene 5 should work now
    channel.set_value(0.0)
    await device.call_scene(5)
    assert channel.get_value() == 50.0


@pytest.mark.asyncio
async def test_ignore_local_priority_flag():
    """Verify ignoreLocalPriority flag bypasses priority lock."""
    device, channel = create_test_device()
    
    # Save scene 5 with ignoreLocalPriority=True
    channel.set_value(50.0)
    await device.save_scene(5, ignore_local_priority=True)
    
    # Save scene 10 normally (ignoreLocalPriority=False)
    channel.set_value(75.0)
    await device.save_scene(10, ignore_local_priority=False)
    
    # Set local priority to scene 10
    device.set_local_priority(10)
    
    # Scene 5 should work (ignoreLocalPriority=True)
    channel.set_value(0.0)
    await device.call_scene(5)
    assert channel.get_value() == 50.0
    
    # Scene 10 should also work (matches priority)
    await device.call_scene(10)
    assert channel.get_value() == 75.0


@pytest.mark.asyncio
async def test_local_priority_with_multiple_scenes():
    """Test priority enforcement with multiple scenes."""
    device, channel = create_test_device()
    
    # Save multiple scenes
    for scene_num, brightness in [(1, 25.0), (2, 50.0), (3, 75.0), (4, 100.0)]:
        channel.set_value(brightness)
        await device.save_scene(scene_num)
    
    # Set priority to scene 3
    device.set_local_priority(3)
    
    # Only scene 3 should work
    channel.set_value(0.0)
    
    await device.call_scene(1)
    assert channel.get_value() == 0.0  # Blocked
    
    await device.call_scene(2)
    assert channel.get_value() == 0.0  # Blocked
    
    await device.call_scene(3)
    assert channel.get_value() == 75.0  # Allowed (matches priority)
    
    await device.call_scene(4)
    assert channel.get_value() == 75.0  # Blocked


@pytest.mark.asyncio
async def test_no_priority_allows_all_scenes():
    """Test that without priority set, all scenes work."""
    device, channel = create_test_device()
    
    # Save multiple scenes
    channel.set_value(25.0)
    await device.save_scene(1)
    
    channel.set_value(75.0)
    await device.save_scene(2)
    
    # No priority set - all scenes should work
    channel.set_value(0.0)
    
    await device.call_scene(1)
    assert channel.get_value() == 25.0
    
    await device.call_scene(2)
    assert channel.get_value() == 75.0


@pytest.mark.asyncio
async def test_ignore_priority_flag_persisted():
    """Verify ignoreLocalPriority flag is persisted in scene config."""
    device, channel = create_test_device()
    
    # Save scene with ignoreLocalPriority=True
    channel.set_value(50.0)
    await device.save_scene(5, ignore_local_priority=True)
    
    # Check scene config
    scene_config = device._scenes.get(5)
    assert scene_config is not None
    assert scene_config.get("ignoreLocalPriority") == True
    
    # Save scene with ignoreLocalPriority=False (default)
    channel.set_value(75.0)
    await device.save_scene(10)
    
    scene_config = device._scenes.get(10)
    assert scene_config is not None
    assert scene_config.get("ignoreLocalPriority") == False
