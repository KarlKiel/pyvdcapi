"""
DSButtonStateMachine - digitalSTROM-compatible button timing helper.

This module provides timing-based clickType detection for buttons that send
simple press/release events. It implements digitalSTROM-compatible timing
patterns and generates appropriate clickType values for ButtonInput.

This is an OPTIONAL helper for applications that:
- Receive simple press/release events from hardware
- Want digitalSTROM-compatible click pattern detection
- Don't have smart buttons that detect patterns themselves

Usage:
    # Create ButtonInput for API compliance
    button_input = ButtonInput(vdsd=device, name="Light Switch", button_type=1)
    
    # Create state machine for timing-based clickType detection
    state_machine = DSButtonStateMachine(button_input)
    
    # Hardware callbacks
    def on_hardware_press():
        state_machine.on_press()
    
    def on_hardware_release():
        state_machine.on_release()
    
    # State machine automatically calls button_input.set_click_type()

Architecture:
    Hardware GPIO → State Machine → ButtonInput → VdSD → vdSM
    
The state machine is separate from ButtonInput to maintain API compliance.
ButtonInput always accepts clickType directly; the state machine is just
one possible source of those values.
"""

import time
import logging
import threading
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .button_input import ButtonInput

logger = logging.getLogger(__name__)


class DSButtonStateMachine:
    """
    digitalSTROM-compatible button state machine for timing-based clickType detection.
    
    This class implements the timing logic to detect button patterns and generate
    appropriate clickType values. It's designed to work with ButtonInput but is
    completely separate to maintain API compliance.
    
    Detected Patterns:
    - tip_1x (0): Single tap (quick press/release)
    - tip_2x (1): Double tap (two quick taps within interval)
    - tip_3x (2): Triple tap (three quick taps)
    - hold_start (4): Long press started (threshold reached)
    - hold_repeat (5): Long press continuing (periodic while held)
    - hold_end (6): Long press released
    
    Timing Constants (customizable):
    - MULTI_TAP_INTERVAL: Max time between taps for multi-tap (default: 400ms)
    - LONG_PRESS_THRESHOLD: Min time held for long press (default: 400ms)
    - HOLD_REPEAT_INTERVAL: Time between hold_repeat events (default: 250ms)
    - TIP_TO_CLICK_TIMEOUT: Time before tip converts to click (default: 500ms)
    
    Note: These defaults match digitalSTROM specification. For Plan 44 devices,
    timing may differ slightly.
    """
    
    # Default timing constants (in seconds)
    # These match digitalSTROM specification timing
    MULTI_TAP_INTERVAL = 0.4      # 400ms between taps
    LONG_PRESS_THRESHOLD = 0.4    # 400ms to trigger long press
    HOLD_REPEAT_INTERVAL = 0.25   # 250ms between hold_repeat events
    TIP_TO_CLICK_TIMEOUT = 0.5    # 500ms before tip → click conversion
    
    def __init__(
        self,
        button_input: "ButtonInput",
        enable_tip_to_click: bool = True,
        enable_hold_repeat: bool = False
    ):
        """
        Initialize button state machine.
        
        Args:
            button_input: ButtonInput instance to send clickType values to
            enable_tip_to_click: Auto-convert tip_Nx to click_Nx after timeout
            enable_hold_repeat: Send hold_repeat events periodically during long press
        
        Example:
            from pyvdcapi.components.button_input import ButtonInput
            from pyvdcapi.components.button_state_machine import DSButtonStateMachine
            
            # Create API-compliant button
            button = ButtonInput(vdsd=device, name="Dimmer", button_type=1)
            
            # Add state machine for timing-based pattern detection
            sm = DSButtonStateMachine(button, enable_hold_repeat=True)
            
            # Connect to hardware
            gpio.on_press(sm.on_press)
            gpio.on_release(sm.on_release)
        """
        self.button_input = button_input
        self.enable_tip_to_click = enable_tip_to_click
        self.enable_hold_repeat = enable_hold_repeat
        
        # State tracking
        self._pressed = False
        self._press_start_time: Optional[float] = None
        self._last_release_time: Optional[float] = None
        self._tap_count = 0
        self._long_press_active = False
        self._hold_repeat_sent = False
        
        # Timers for delayed events
        self._tip_timer: Optional[threading.Timer] = None
        self._hold_repeat_timer: Optional[threading.Timer] = None
        
        logger.debug(
            f"Created DSButtonStateMachine for button {button_input.button_id}, "
            f"tip_to_click={enable_tip_to_click}, hold_repeat={enable_hold_repeat}"
        )
        
    def on_press(self) -> None:
        """
        Handle button press event from hardware.
        
        Call this when physical button is pressed down.
        
        Example:
            # Hardware interrupt callback
            def gpio_press_handler():
                state_machine.on_press()
        """
        if self._pressed:
            logger.warning(
                f"Button {self.button_input.button_id} already pressed (ignoring)"
            )
            return
            
        current_time = time.time()
        self._pressed = True
        self._press_start_time = current_time
        
        # Update button value state
        self.button_input.set_value(True)
        
        # Check if this is part of a multi-tap sequence
        if self._last_release_time:
            time_since_last = current_time - self._last_release_time
            if time_since_last < self.MULTI_TAP_INTERVAL:
                # Continue multi-tap sequence
                self._tap_count += 1
                logger.debug(
                    f"Button {self.button_input.button_id} multi-tap continued "
                    f"(count={self._tap_count})"
                )
                
                # Cancel pending tip-to-click conversion
                if self._tip_timer:
                    self._tip_timer.cancel()
                    self._tip_timer = None
            else:
                # Too slow, start new sequence
                self._tap_count = 1
                logger.debug(
                    f"Button {self.button_input.button_id} new tap sequence"
                )
        else:
            # First tap
            self._tap_count = 1
            logger.debug(f"Button {self.button_input.button_id} first tap")
            
        # Start monitoring for long press
        if self.enable_hold_repeat:
            self._schedule_hold_repeat()
            
        logger.debug(
            f"Button {self.button_input.button_id} pressed (tap_count={self._tap_count})"
        )
        
    def on_release(self) -> None:
        """
        Handle button release event from hardware.
        
        Call this when physical button is released.
        
        Example:
            # Hardware interrupt callback
            def gpio_release_handler():
                state_machine.on_release()
        """
        if not self._pressed:
            logger.warning(
                f"Button {self.button_input.button_id} not currently pressed (ignoring)"
            )
            return
            
        current_time = time.time()
        press_duration = current_time - self._press_start_time
        
        self._pressed = False
        self._last_release_time = current_time
        
        # Update button value state
        self.button_input.set_value(False)
        
        # Cancel hold repeat timer if active
        if self._hold_repeat_timer:
            self._hold_repeat_timer.cancel()
            self._hold_repeat_timer = None
            
        # Determine clickType based on press duration and tap count
        if press_duration >= self.LONG_PRESS_THRESHOLD:
            # Long press released
            if self._long_press_active:
                # Send hold_end
                self.button_input.set_click_type(6)  # hold_end
                logger.info(
                    f"Button {self.button_input.button_id} hold_end "
                    f"(duration={press_duration:.3f}s)"
                )
                self._long_press_active = False
                self._hold_repeat_sent = False
            else:
                # Threshold reached but hold_start not yet sent
                # Send hold_start then hold_end
                self.button_input.set_click_type(4)  # hold_start
                time.sleep(0.01)  # Brief delay
                self.button_input.set_click_type(6)  # hold_end
                logger.info(
                    f"Button {self.button_input.button_id} hold_start+hold_end "
                    f"(duration={press_duration:.3f}s)"
                )
                
            # Reset tap sequence after long press
            self._tap_count = 0
            
        else:
            # Short press - generate tip_Nx
            if self._tap_count >= 1 and self._tap_count <= 4:
                # tip_1x (0), tip_2x (1), tip_3x (2), tip_4x (3)
                click_type = self._tap_count - 1
                self.button_input.set_click_type(click_type)
                logger.info(
                    f"Button {self.button_input.button_id} tip_{self._tap_count}x "
                    f"(clickType={click_type})"
                )
                
                # Schedule tip-to-click conversion
                if self.enable_tip_to_click:
                    self._schedule_tip_to_click()
            else:
                logger.warning(
                    f"Button {self.button_input.button_id} tap_count={self._tap_count} "
                    f"out of range (max 4)"
                )
                self._tap_count = 0
                
        logger.debug(
            f"Button {self.button_input.button_id} released "
            f"(duration={press_duration:.3f}s)"
        )
        
    def _schedule_hold_repeat(self) -> None:
        """Schedule hold_repeat event after long press threshold."""
        def send_hold_start():
            if self._pressed and not self._long_press_active:
                self.button_input.set_click_type(4)  # hold_start
                self._long_press_active = True
                logger.info(f"Button {self.button_input.button_id} hold_start")
                
                # Schedule periodic hold_repeat
                self._schedule_next_hold_repeat()
                
        # Cancel existing timer
        if self._hold_repeat_timer:
            self._hold_repeat_timer.cancel()
            
        # Schedule hold_start after threshold
        self._hold_repeat_timer = threading.Timer(
            self.LONG_PRESS_THRESHOLD,
            send_hold_start
        )
        self._hold_repeat_timer.daemon = True
        self._hold_repeat_timer.start()
        
    def _schedule_next_hold_repeat(self) -> None:
        """Schedule next hold_repeat event."""
        def send_hold_repeat():
            if self._pressed and self._long_press_active:
                self.button_input.set_click_type(5)  # hold_repeat
                self._hold_repeat_sent = True
                logger.debug(f"Button {self.button_input.button_id} hold_repeat")
                
                # Schedule next repeat
                self._schedule_next_hold_repeat()
                
        # Cancel existing timer
        if self._hold_repeat_timer:
            self._hold_repeat_timer.cancel()
            
        # Schedule next hold_repeat
        self._hold_repeat_timer = threading.Timer(
            self.HOLD_REPEAT_INTERVAL,
            send_hold_repeat
        )
        self._hold_repeat_timer.daemon = True
        self._hold_repeat_timer.start()
        
    def _schedule_tip_to_click(self) -> None:
        """Schedule tip_Nx to click_Nx conversion."""
        def convert_tip_to_click():
            # Convert tip_Nx (0-3) to click_Nx (7-9)
            # tip_1x (0) → click_1x (7)
            # tip_2x (1) → click_2x (8)
            # tip_3x (2) → click_3x (9)
            # tip_4x (3) → (no click_4x defined, stays as tip_4x)
            
            if self._tap_count >= 1 and self._tap_count <= 3:
                click_type = 6 + self._tap_count  # 7, 8, 9
                self.button_input.set_click_type(click_type)
                logger.info(
                    f"Button {self.button_input.button_id} "
                    f"tip_{self._tap_count}x → click_{self._tap_count}x "
                    f"(clickType={click_type})"
                )
                
            # Reset tap counter after conversion
            self._tap_count = 0
            
        # Cancel existing timer
        if self._tip_timer:
            self._tip_timer.cancel()
            
        # Schedule conversion
        self._tip_timer = threading.Timer(
            self.TIP_TO_CLICK_TIMEOUT,
            convert_tip_to_click
        )
        self._tip_timer.daemon = True
        self._tip_timer.start()
        
    def reset(self) -> None:
        """
        Reset state machine to initial state.
        
        Useful for error recovery or initialization.
        """
        # Cancel timers
        if self._tip_timer:
            self._tip_timer.cancel()
            self._tip_timer = None
        if self._hold_repeat_timer:
            self._hold_repeat_timer.cancel()
            self._hold_repeat_timer = None
            
        # Reset state
        self._pressed = False
        self._press_start_time = None
        self._last_release_time = None
        self._tap_count = 0
        self._long_press_active = False
        self._hold_repeat_sent = False
        
        # Reset button value
        self.button_input.set_value(None)
        self.button_input.set_click_type(255)  # idle
        
        logger.debug(f"Button {self.button_input.button_id} state machine reset")
        
    def __del__(self):
        """Cleanup timers on deletion."""
        if hasattr(self, '_tip_timer') and self._tip_timer:
            self._tip_timer.cancel()
        if hasattr(self, '_hold_repeat_timer') and self._hold_repeat_timer:
            self._hold_repeat_timer.cancel()
