"""
Test OutputChannel bidirectional behavior (DSS ↔ Device).

This test verifies the critical distinction:
- set_value() (DSS → Device): Does NOT push back to DSS
- update_value() (Device → DSS): DOES push to DSS
"""

from pyvdcapi.components.output_channel import OutputChannel


def test_output_channel_bidirectional():
    """Test that set_value doesn't push but update_value does."""
    
    class MockVdSD:
        def __init__(self):
            self.push_calls = []
        
        def push_output_channel_value(self, channel_index, value):
            """Track push notifications."""
            self.push_calls.append(("push", channel_index, value))
    
    mock_vdsd = MockVdSD()
    
    channel = OutputChannel(
        vdsd=mock_vdsd,
        channel_type=0,  # Brightness
        min_value=0.0,
        max_value=100.0,
        resolution=0.1,
        initial_value=0.0,
        name="Brightness"
    )
    
    # Clear any initialization pushes
    mock_vdsd.push_calls.clear()
    
    # Test 1: set_value() (DSS → Device) should NOT push
    channel.set_value(50.0)
    assert len(mock_vdsd.push_calls) == 0, "set_value() should NOT push notification (DSS → Device)"
    assert channel.get_value() == 50.0
    
    # Test 2: update_value() (Device → DSS) SHOULD push
    channel.update_value(75.0)
    assert len(mock_vdsd.push_calls) == 1, "update_value() MUST push notification (Device → DSS)"
    assert mock_vdsd.push_calls[0] == ("push", 0, 75.0)
    assert channel.get_value() == 75.0
    
    # Test 3: Multiple updates from hardware
    mock_vdsd.push_calls.clear()
    channel.update_value(80.0)
    channel.update_value(90.0)
    assert len(mock_vdsd.push_calls) == 2
    
    # Test 4: update_value with same value still pushes (age update)
    mock_vdsd.push_calls.clear()
    channel.update_value(90.0)  # Same value
    # Age is updated even if value unchanged, so no push for unchanged value
    assert len(mock_vdsd.push_calls) == 0, "Same value should not trigger push"
    
    # Test 5: DSS sets value, then hardware confirms (should only push once)
    mock_vdsd.push_calls.clear()
    channel.set_value(100.0)  # DSS command - no push
    assert len(mock_vdsd.push_calls) == 0
    channel.update_value(100.0)  # Hardware confirms - no push (same value)
    assert len(mock_vdsd.push_calls) == 0


def test_output_channel_hardware_override():
    """Test hardware can override DSS commands."""
    
    class MockVdSD:
        def __init__(self):
            self.push_calls = []
        
        def push_output_channel_value(self, channel_index, value):
            self.push_calls.append(value)
    
    mock_vdsd = MockVdSD()
    
    channel = OutputChannel(
        vdsd=mock_vdsd,
        channel_type=0,
        min_value=0.0,
        max_value=100.0,
        resolution=1.0,
        initial_value=0.0
    )
    
    mock_vdsd.push_calls.clear()
    
    # DSS sets brightness to 50%
    channel.set_value(50.0)
    assert channel.get_value() == 50.0
    assert len(mock_vdsd.push_calls) == 0  # No push back to DSS
    
    # User manually adjusts wall dimmer to 80%
    channel.update_value(80.0)
    assert channel.get_value() == 80.0
    assert len(mock_vdsd.push_calls) == 1  # Push to inform DSS
    assert mock_vdsd.push_calls[0] == 80.0


if __name__ == "__main__":
    test_output_channel_bidirectional()
    test_output_channel_hardware_override()
    print("✓ All bidirectional tests passed!")
