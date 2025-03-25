#!/usr/bin/env python3
# command to make python files executable: chmod +x python/*.py

import hal
import time
from enum import Enum

class WorkAreaState(Enum):
    IDLE = 0
    SETUP_MODE = 1
    WAITING_FOR_VACUUM = 2
    ERROR = 3

class VacuumState(Enum):
    IDLE = 0
    VACUUM_ON = 1
    VACUUM_OFF = 2
    ERROR = 3

class WorkAreaControl:
    def __init__(self):
        self.h = hal.component("work_area")
        
        # Work Area Input pins
        self.h.newpin("left_button", hal.HAL_BIT, hal.HAL_IN)
        self.h.newpin("right_button", hal.HAL_BIT, hal.HAL_IN)
        self.h.newpin("vacuum_pedal", hal.HAL_BIT, hal.HAL_IN)
        self.h.newpin("machine_enabled", hal.HAL_BIT, hal.HAL_IN)      # Machine enable signal
        self.h.newpin("vacuum_ok", hal.HAL_BIT, hal.HAL_IN)      # Vacuum level OK signal
        self.h.newpin("estop_ok", hal.HAL_BIT, hal.HAL_IN)      # E-stop chain status
        self.h.newpin("x_axis_ok", hal.HAL_BIT, hal.HAL_IN)      # X axis status signal
        self.h.newpin("y_axis_ok", hal.HAL_BIT, hal.HAL_IN)      # Y axis status signal
        self.h.newpin("z_axis_ok", hal.HAL_BIT, hal.HAL_IN)      # Z axis status signal
        self.h.newpin("photo_eyes_bypass", hal.HAL_BIT, hal.HAL_IN)    # Photo eye bypass signal
        
        # Work Area Output pins
        self.h.newpin("left_stops", hal.HAL_BIT, hal.HAL_OUT)
        self.h.newpin("right_stops", hal.HAL_BIT, hal.HAL_OUT)
        self.h.newpin("front_stops", hal.HAL_BIT, hal.HAL_OUT)
        self.h.newpin("enable_machine", hal.HAL_BIT, hal.HAL_OUT)    # Machine enable output
        
        # Vacuum Output pins
        self.h.newpin("suction_on", hal.HAL_BIT, hal.HAL_OUT)    # Turn vacuum on
        self.h.newpin("suction_off", hal.HAL_BIT, hal.HAL_OUT)   # Turn vacuum off
        self.h.newpin("suction_up", hal.HAL_BIT, hal.HAL_OUT)    # Raise suction cups
        self.h.newpin("low_vacuum", hal.HAL_BIT, hal.HAL_OUT)    # Low vacuum warning
        
        # Machine control pins
        self.h.newpin("motion_enable", hal.HAL_BIT, hal.HAL_OUT)
        self.h.newpin("spindle_stop", hal.HAL_BIT, hal.HAL_OUT)
        self.h.newpin("enable_axes", hal.HAL_BIT, hal.HAL_OUT)    # Enable all axes
        
        # Parameters
        self.VACUUM_CHECK_TIME = 2.0    # Time to check for good vacuum (seconds)
        self.ERROR_TIMEOUT = 5.0        # Time before declaring vacuum error
        
        # State tracking
        self.work_area_state = WorkAreaState.IDLE
        self.vacuum_state = VacuumState.IDLE
        self.last_left_button = False
        self.last_right_button = False
        self.setup_side = None  # 'left' or 'right'
        
        # Vacuum tracking
        self.vacuum_timer_start = 0
        self.last_vacuum_ok = False
        self.vacuum_loss_time = 0
        
        # Initialize outputs
        self.h.left_stops = False
        self.h.right_stops = False
        self.h.front_stops = False
        self.h.enable_machine = True     # Start with machine enabled
        self.h.suction_on = False
        self.h.suction_off = False
        self.h.suction_up = False
        self.h.low_vacuum = False
        self.h.motion_enable = True
        self.h.spindle_stop = False
        self.h.enable_axes = True     # Start with axes enabled
        
        self.h.ready()
    
    def check_vacuum_loss(self, current_time):
        """Monitor vacuum level and detect losses"""
        if self.h.vacuum_ok:
            self.vacuum_loss_time = 0
            self.last_vacuum_ok = True
            return False
        elif self.last_vacuum_ok:  # Vacuum just lost
            self.vacuum_loss_time = current_time
            self.last_vacuum_ok = False
        
        # Check if vacuum has been lost for too long
        if self.vacuum_loss_time and (current_time - self.vacuum_loss_time > self.ERROR_TIMEOUT):
            return True
        
        return False
    
    def handle_vacuum_state(self, current_time):
        """Handle vacuum control state machine"""
        # Check for vacuum loss in any state
        if self.check_vacuum_loss(current_time):
            self.vacuum_state = VacuumState.ERROR
            self.h.low_vacuum = True
            return False  # Indicate vacuum not ready
        
        if self.vacuum_state == VacuumState.IDLE:
            if self.h.vacuum_pedal:
                self.vacuum_state = VacuumState.VACUUM_ON
                self.vacuum_timer_start = current_time
                self.h.suction_on = True
                self.h.suction_off = False
                self.h.low_vacuum = False
        
        elif self.vacuum_state == VacuumState.VACUUM_ON:
            if self.h.vacuum_ok:
                if current_time - self.vacuum_timer_start >= self.VACUUM_CHECK_TIME:
                    return True  # Indicate vacuum ready
            
            if not self.h.vacuum_pedal:  # Pedal released
                self.vacuum_state = VacuumState.VACUUM_OFF
                self.h.suction_on = False
                self.h.suction_off = True
        
        elif self.vacuum_state == VacuumState.VACUUM_OFF:
            self.vacuum_state = VacuumState.IDLE
            self.h.suction_off = False
        
        elif self.vacuum_state == VacuumState.ERROR:
            if self.h.vacuum_ok:  # Reset error if vacuum restored
                self.vacuum_state = VacuumState.IDLE
                self.h.low_vacuum = False
                self.vacuum_loss_time = 0
        
        return False  # Vacuum not ready by default
    
    def update(self):
        current_time = time.time()
        
        # Read button states
        left_button = self.h.left_button
        right_button = self.h.right_button
        
        # Detect button press events
        left_pressed = left_button and not self.last_left_button
        right_pressed = right_button and not self.last_right_button
        
        # Handle vacuum control
        vacuum_ready = self.handle_vacuum_state(current_time)
        
        # Work area state machine
        if self.work_area_state == WorkAreaState.IDLE:
            if left_pressed or right_pressed:
                self.work_area_state = WorkAreaState.SETUP_MODE
                self.setup_side = 'left' if left_pressed else 'right'
                
                # Disable machine and photo eyes
                self.h.motion_enable = False
                self.h.spindle_stop = True
                self.h.photo_eyes_bypass = True
                
                # Raise appropriate stops
                self.h.left_stops = True if left_pressed else False
                self.h.right_stops = True if right_pressed else False
                self.h.front_stops = True
        
        elif self.work_area_state == WorkAreaState.SETUP_MODE:
            if vacuum_ready:
                self.work_area_state = WorkAreaState.WAITING_FOR_VACUUM
                # Activate suction cups
                self.h.suction_up = True
        
        elif self.work_area_state == WorkAreaState.WAITING_FOR_VACUUM:
            if (left_pressed and self.setup_side == 'left') or \
               (right_pressed and self.setup_side == 'right'):
                # Return to idle state
                self.work_area_state = WorkAreaState.IDLE
                
                # Lower all stops
                self.h.left_stops = False
                self.h.right_stops = False
                self.h.front_stops = False
                
                # Re-enable machine and photo eyes
                self.h.motion_enable = True
                self.h.spindle_stop = False
                self.h.photo_eyes_bypass = False
                
                # Keep suction on but lower cups
                self.h.suction_up = False
        
        # Update button state tracking
        self.last_left_button = left_button
        self.last_right_button = right_button

def main():
    work_area = WorkAreaControl()
    
    try:
        while True:
            work_area.update()
            time.sleep(0.1)  # 100ms update rate
            
    except KeyboardInterrupt:
        raise SystemExit

if __name__ == "__main__":
    main() 