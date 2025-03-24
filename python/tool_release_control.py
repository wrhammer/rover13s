#!/usr/bin/env python3

import hal
import time
from enum import Enum

class ToolState(Enum):
    IDLE = 0
    RELEASING = 1
    LOCKING = 2
    ERROR = 3

class ToolReleaseControl:
    def __init__(self):
        self.h = hal.component("tool_release")
        
        # Input pins
        self.h.newpin("release_button", hal.HAL_BIT, hal.HAL_IN)     # Button input
        self.h.newpin("tool_released", hal.HAL_BIT, hal.HAL_IN)      # Feedback that tool is released
        self.h.newpin("tool_locked", hal.HAL_BIT, hal.HAL_IN)        # Feedback that tool is locked
        self.h.newpin("x_safe_zone", hal.HAL_BIT, hal.HAL_IN)        # X axis in safe zone
        self.h.newpin("y_safe_zone", hal.HAL_BIT, hal.HAL_IN)        # Y axis in safe zone
        self.h.newpin("override_safety", hal.HAL_BIT, hal.HAL_IN)    # Override safety checks (for maintenance)
        
        # Output pins
        self.h.newpin("release_tool", hal.HAL_BIT, hal.HAL_OUT)      # Release tool output
        self.h.newpin("lock_tool", hal.HAL_BIT, hal.HAL_OUT)         # Lock tool output
        self.h.newpin("error_active", hal.HAL_BIT, hal.HAL_OUT)      # Error status
        self.h.newpin("in_safe_zone", hal.HAL_BIT, hal.HAL_OUT)      # Safe zone status
        
        # Parameters
        self.TIMEOUT = 5.0          # Timeout for operations (seconds)
        self.ERROR_RESET_TIME = 1.0 # Time button must be released to reset error
        
        # State tracking
        self.state = ToolState.IDLE
        self.last_button_state = False
        self.operation_start_time = 0
        self.error_reset_time = 0
        
        # Initialize outputs
        self.h.lock_tool = True     # Start with tool locked
        self.h.release_tool = False
        self.h.error_active = False
        self.h.in_safe_zone = False
        
        self.h.ready()
        
    def check_safe_zone(self):
        """Check if machine is in safe position for tool operations"""
        is_safe = (self.h.x_safe_zone and self.h.y_safe_zone) or self.h.override_safety
        self.h.in_safe_zone = is_safe
        return is_safe
    
    def check_timeout(self):
        """Check if current operation has timed out"""
        return time.time() - self.operation_start_time > self.TIMEOUT
    
    def handle_error(self):
        """Set error state and safe outputs"""
        self.state = ToolState.ERROR
        self.h.error_active = True
        self.h.release_tool = False
        self.h.lock_tool = True
    
    def update(self):
        # Read current button state
        button_pressed = self.h.release_button
        button_rising_edge = button_pressed and not self.last_button_state
        button_falling_edge = not button_pressed and self.last_button_state
        current_time = time.time()
        
        # Update safe zone status
        self.check_safe_zone()
        
        # State machine
        if self.state == ToolState.IDLE:
            if button_rising_edge:
                if self.check_safe_zone():
                    self.state = ToolState.RELEASING
                    self.h.release_tool = True
                    self.h.lock_tool = False
                    self.operation_start_time = current_time
                    self.h.error_active = False
        
        elif self.state == ToolState.RELEASING:
            if button_falling_edge:
                self.state = ToolState.LOCKING
                self.h.release_tool = False
                self.h.lock_tool = True
                self.operation_start_time = current_time
            elif self.check_timeout():
                self.handle_error()
        
        elif self.state == ToolState.LOCKING:
            if self.h.tool_locked:
                self.state = ToolState.IDLE
            elif self.check_timeout():
                self.handle_error()
        
        elif self.state == ToolState.ERROR:
            # Reset error if button released for ERROR_RESET_TIME
            if not button_pressed:
                if self.error_reset_time == 0:
                    self.error_reset_time = current_time
                elif current_time - self.error_reset_time >= self.ERROR_RESET_TIME:
                    self.state = ToolState.IDLE
                    self.h.error_active = False
            else:
                self.error_reset_time = 0
        
        # Update button state tracking
        self.last_button_state = button_pressed

def main():
    tool_control = ToolReleaseControl()
    
    try:
        while True:
            tool_control.update()
            time.sleep(0.1)  # 100ms update rate
            
    except KeyboardInterrupt:
        raise SystemExit

if __name__ == "__main__":
    main() 