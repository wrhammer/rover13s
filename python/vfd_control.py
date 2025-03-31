#!/usr/bin/env python3

import hal
import time

class VFDControl:
    def __init__(self):
        self.h = hal.component("vfd_control")
        
        # Input pins
        self.h.newpin("spindle_on", hal.HAL_BIT, hal.HAL_IN)        # Command to run spindle
        self.h.newpin("vfd_fault", hal.HAL_BIT, hal.HAL_IN)         # VFD fault input
        self.h.newpin("motor_stopped", hal.HAL_BIT, hal.HAL_IN)     # Motor stopped feedback
        self.h.newpin("vfd_overload", hal.HAL_BIT, hal.HAL_IN)      # VFD overload signal
        self.h.newpin("reset_button", hal.HAL_BIT, hal.HAL_IN)      # Manual reset button
        self.h.newpin("spindle_speed", hal.HAL_FLOAT, hal.HAL_IN)   # Commanded spindle speed
        
        # Output pins
        self.h.newpin("vfd_run", hal.HAL_BIT, hal.HAL_OUT)          # VFD run command
        self.h.newpin("vfd_reset", hal.HAL_BIT, hal.HAL_OUT)        # VFD reset command
        self.h.newpin("fault_active", hal.HAL_BIT, hal.HAL_OUT)     # Fault status
        self.h.newpin("vfd_speed", hal.HAL_FLOAT, hal.HAL_OUT)      # Scaled speed output
        
        # Parameters
        self.START_DELAY = 0.5       # Delay before starting VFD (seconds)
        self.RESET_PULSE = 1.0       # Duration of reset pulse (seconds)
        self.STOP_TIMEOUT = 10.0      # Maximum time to wait for motor to stop
        self.MAX_SPEED = 24000.0     # Maximum spindle speed
        self.MIN_SPEED = 300.0       # Minimum spindle speed
        
        # State variables
        self.timer_start = 0
        self.reset_timer = 0
        self.is_resetting = False
        self.last_reset_button = False
        
        # Initialize outputs
        self.h.vfd_run = False
        self.h.vfd_reset = False
        self.h.fault_active = False
        self.h.vfd_speed = 0.0
        
        self.h.ready()
    
    def check_faults(self):
        """Check for VFD faults"""
        return self.h.vfd_fault or self.h.vfd_overload
    
    def handle_reset(self, current_time):
        """Handle VFD reset sequence"""
        if not self.is_resetting:
            self.reset_timer = current_time
            self.is_resetting = True
            self.h.vfd_reset = True
        elif current_time - self.reset_timer >= self.RESET_PULSE:
            self.h.vfd_reset = False
            self.is_resetting = False
            self.h.fault_active = False
    
    def scale_speed(self, speed):
        """Scale the spindle speed to VFD range"""
        # Ensure speed is within limits
        speed = max(self.MIN_SPEED, min(self.MAX_SPEED, speed))
        # Scale to 0-100% for VFD
        return (speed / self.MAX_SPEED) * 100.0
    
    def update(self):
        current_time = time.time()
        
        # Check for faults
        fault_detected = self.check_faults()
        
        # Handle reset button
        reset_button_pressed = self.h.reset_button
        reset_button_rising_edge = reset_button_pressed and not self.last_reset_button
        
        if fault_detected:
            self.h.vfd_run = False
            self.h.fault_active = True
            self.h.vfd_speed = 0.0
        else:
            self.h.fault_active = False
        
        # Handle reset sequence on button press
        if reset_button_rising_edge and fault_detected and not self.is_resetting:
            self.handle_reset(current_time)
        
        # Normal operation
        if self.h.spindle_on and not self.h.fault_active:
            if self.timer_start == 0:
                self.timer_start = current_time
            elif current_time - self.timer_start >= self.START_DELAY:
                self.h.vfd_run = True
                # Scale and output the speed
                self.h.vfd_speed = self.scale_speed(self.h.spindle_speed)
        else:
            self.h.vfd_run = False
            self.h.vfd_speed = 0.0
            self.timer_start = 0
            
            # Check motor stop timeout
            if not self.h.motor_stopped and self.h.spindle_on == False:
                if self.timer_start == 0:
                    self.timer_start = current_time
                elif current_time - self.timer_start >= self.STOP_TIMEOUT:
                    self.h.fault_active = True
        
        # Update button state tracking
        self.last_reset_button = reset_button_pressed

def main():
    vfd = VFDControl()
    
    try:
        while True:
            vfd.update()
            time.sleep(0.1)  # 100ms update rate
            
    except KeyboardInterrupt:
        raise SystemExit

if __name__ == "__main__":
    main() 