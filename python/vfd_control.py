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
        
        # Output pins
        self.h.newpin("vfd_run", hal.HAL_BIT, hal.HAL_OUT)          # VFD run command
        self.h.newpin("vfd_reset", hal.HAL_BIT, hal.HAL_OUT)        # VFD reset command
        self.h.newpin("fault_active", hal.HAL_BIT, hal.HAL_OUT)     # Fault status
        
        # Parameters
        self.START_DELAY = 0.5       # Delay before starting VFD (seconds)
        self.RESET_PULSE = 1.0       # Duration of reset pulse (seconds)
        self.STOP_TIMEOUT = 10.0      # Maximum time to wait for motor to stop
        
        # State variables
        self.timer_start = 0
        self.reset_timer = 0
        self.is_resetting = False
        
        # Initialize outputs
        self.h.vfd_run = False
        self.h.vfd_reset = False
        self.h.fault_active = False
        
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
    
    def update(self):
        current_time = time.time()
        
        # Check for faults
        if self.check_faults():
            self.h.vfd_run = False
            self.h.fault_active = True
            self.handle_reset(current_time)
            return
        
        # Normal operation
        if self.h.spindle_on and not self.h.fault_active:
            if self.timer_start == 0:
                self.timer_start = current_time
            elif current_time - self.timer_start >= self.START_DELAY:
                self.h.vfd_run = True
        else:
            self.h.vfd_run = False
            self.timer_start = 0
            
            # Check motor stop timeout
            if not self.h.motor_stopped and self.h.spindle_on == False:
                if self.timer_start == 0:
                    self.timer_start = current_time
                elif current_time - self.timer_start >= self.STOP_TIMEOUT:
                    self.h.fault_active = True

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