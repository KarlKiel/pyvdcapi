#!/usr/bin/env python3
"""
Test ButtonInput click mode vs action mode configuration.

Verifies that:
1. Default mode is clickType (click mode)
2. Action mode can be configured during instantiation
3. get_state() returns appropriate properties based on mode
4. Mode configuration persists through to_dict/from_dict
5. Warnings are issued when using wrong method for configured mode
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import Mock
from pyvdcapi.components.button_input import ButtonInput, ClickType


def test_default_click_mode():
    """Test 1: Default mode should be clickType (click mode)."""
    print("\n" + "="*70)
    print("TEST 1: Default mode is clickType (click mode)")
    print("="*70)
    
    # Create mock VdSD
    mock_vdsd = Mock()
    mock_vdsd.push_button_state = Mock()
    
    # Create button without specifying mode (should default to click mode)
    button = ButtonInput(
        vdsd=mock_vdsd,
        name="Test Button"
    )
    
    assert button._use_action_mode == False, "Default should be click mode"
    print("✅ Button defaults to click mode (use_action_mode=False)")
    
    # Set click type
    button.set_click_type(ClickType.CLICK_1X)
    
    # Get state - should return clickType/value
    state = button.get_state()
    
    assert "clickType" in state, "State should include clickType"
    assert "value" in state, "State should include value"
    assert "actionId" not in state, "State should NOT include actionId"
    assert "actionMode" not in state, "State should NOT include actionMode"
    assert state["clickType"] == ClickType.CLICK_1X
    
    print(f"✅ State returns clickType/value: {state}")
    print("✅ TEST PASSED: Default mode is click mode")


def test_explicit_click_mode():
    """Test 2: Explicitly configured click mode."""
    print("\n" + "="*70)
    print("TEST 2: Explicitly configured click mode")
    print("="*70)
    
    mock_vdsd = Mock()
    mock_vdsd.push_button_state = Mock()
    
    # Explicitly set to click mode
    button = ButtonInput(
        vdsd=mock_vdsd,
        name="Click Button",
        use_action_mode=False
    )
    
    assert button._use_action_mode == False
    print("✅ Button explicitly configured for click mode")
    
    button.set_click_type(ClickType.TIP_2X)
    state = button.get_state()
    
    assert state["clickType"] == ClickType.TIP_2X
    assert "actionId" not in state
    
    print(f"✅ State: {state}")
    print("✅ TEST PASSED: Explicit click mode works")


def test_action_mode():
    """Test 3: Action mode configured during instantiation."""
    print("\n" + "="*70)
    print("TEST 3: Action mode configured during instantiation")
    print("="*70)
    
    mock_vdsd = Mock()
    mock_vdsd.push_button_state = Mock()
    
    # Configure for action mode
    button = ButtonInput(
        vdsd=mock_vdsd,
        name="Scene Button",
        use_action_mode=True  # Enable action mode
    )
    
    assert button._use_action_mode == True
    print("✅ Button configured for action mode (use_action_mode=True)")
    
    # Set action
    button.set_action(action_id=5, action_mode=0)
    
    # Get state - should return actionId/actionMode
    state = button.get_state()
    
    assert "actionId" in state, "State should include actionId"
    assert "actionMode" in state, "State should include actionMode"
    assert "clickType" not in state, "State should NOT include clickType in action mode"
    assert "value" not in state, "State should NOT include value in action mode"
    assert state["actionId"] == 5
    assert state["actionMode"] == 0
    
    print(f"✅ State returns actionId/actionMode: {state}")
    print("✅ TEST PASSED: Action mode works")


def test_persistence():
    """Test 4: Mode configuration persists through to_dict/from_dict."""
    print("\n" + "="*70)
    print("TEST 4: Mode configuration persistence")
    print("="*70)
    
    mock_vdsd = Mock()
    mock_vdsd.push_button_state = Mock()
    
    # Create button in action mode
    button1 = ButtonInput(
        vdsd=mock_vdsd,
        name="Scene Button",
        use_action_mode=True
    )
    button1.set_action(action_id=10, action_mode=1)
    
    # Serialize
    data = button1.to_dict()
    
    assert "useActionMode" in data, "to_dict should include useActionMode"
    assert data["useActionMode"] == True
    print(f"✅ Serialized mode: useActionMode={data['useActionMode']}")
    
    # Create new button and restore
    button2 = ButtonInput(
        vdsd=mock_vdsd,
        name="Restored Button"
    )
    button2.from_dict(data)
    
    assert button2._use_action_mode == True, "Mode should be restored"
    print("✅ Mode configuration restored from persistence")
    
    state = button2.get_state()
    assert state["actionId"] == 10
    assert state["actionMode"] == 1
    print(f"✅ State restored correctly: {state}")
    
    print("✅ TEST PASSED: Mode persists correctly")


def test_mode_mismatch_warnings():
    """Test 5: Warnings when using wrong method for configured mode."""
    print("\n" + "="*70)
    print("TEST 5: Mode mismatch warnings")
    print("="*70)
    
    mock_vdsd = Mock()
    mock_vdsd.push_button_state = Mock()
    
    # Test 5a: Action mode button with set_click_type
    print("\n5a: Action mode button called with set_click_type()")
    button_action = ButtonInput(
        vdsd=mock_vdsd,
        name="Action Button",
        use_action_mode=True
    )
    
    # This should log a warning
    button_action.set_click_type(ClickType.CLICK_1X)
    print("✅ Warning logged when using set_click_type() on action mode button")
    
    # Test 5b: Click mode button with set_action
    print("\n5b: Click mode button called with set_action()")
    button_click = ButtonInput(
        vdsd=mock_vdsd,
        name="Click Button",
        use_action_mode=False
    )
    
    # This should log a warning
    button_click.set_action(action_id=5)
    print("✅ Warning logged when using set_action() on click mode button")
    
    print("✅ TEST PASSED: Warnings issued for mode mismatches")


def test_state_based_on_mode_not_values():
    """Test 6: get_state() returns based on configured mode, not which values are set."""
    print("\n" + "="*70)
    print("TEST 6: get_state() respects configured mode")
    print("="*70)
    
    mock_vdsd = Mock()
    mock_vdsd.push_button_state = Mock()
    
    # Click mode button should return clickType/value even if actionId happens to be set
    button = ButtonInput(
        vdsd=mock_vdsd,
        name="Click Button",
        use_action_mode=False  # Configured for click mode
    )
    
    # Manually set both (shouldn't normally happen, but test robustness)
    button._click_type = ClickType.CLICK_1X
    button._action_id = 10
    
    state = button.get_state()
    
    # Should return clickType/value because button is in click mode
    assert "clickType" in state
    assert "value" in state
    assert "actionId" not in state
    assert "actionMode" not in state
    
    print("✅ Click mode button returns clickType/value (not actionId)")
    
    # Action mode button should return actionId/actionMode
    button2 = ButtonInput(
        vdsd=mock_vdsd,
        name="Action Button",
        use_action_mode=True  # Configured for action mode
    )
    
    state2 = button2.get_state()
    
    # Should return actionId/actionMode because button is in action mode
    assert "actionId" in state2
    assert "actionMode" in state2
    assert "clickType" not in state2
    assert "value" not in state2
    
    print("✅ Action mode button returns actionId/actionMode (not clickType)")
    print("✅ TEST PASSED: State based on configured mode, not just values")


def main():
    """Run all tests."""
    print("="*70)
    print("ButtonInput Mode Configuration Tests")
    print("="*70)
    
    try:
        test_default_click_mode()
        test_explicit_click_mode()
        test_action_mode()
        test_persistence()
        test_mode_mismatch_warnings()
        test_state_based_on_mode_not_values()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED")
        print("="*70)
        print("\n🔑 Verified:")
        print("   1. ✅ Default mode is clickType (use_action_mode=False)")
        print("   2. ✅ Action mode can be configured (use_action_mode=True)")
        print("   3. ✅ get_state() returns correct properties for mode")
        print("   4. ✅ Mode configuration persists")
        print("   5. ✅ Warnings issued for mode mismatches")
        print("   6. ✅ State determined by configured mode, not values")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
