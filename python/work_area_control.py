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
        
        # E-stop chain input pins
        self.h.newpin("emc_enable_in", hal.HAL_BIT, hal.HAL_IN)        # EMC enable input
        self.h.newpin("user_enable_out", hal.HAL_BIT, hal.HAL_IN)      # User enable output
        self.h.newpin("estop_latch_ok", hal.HAL_BIT, hal.HAL_IN)       # E-stop latch OK output
        self.h.newpin("estop_latch_fault", hal.HAL_BIT, hal.HAL_IN)    # E-stop latch fault input
        self.h.newpin("remote_estop", hal.HAL_BIT, hal.HAL_IN)         # Remote E-stop input
        
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
        self.h.newpin("spindle_stop", hal.HAL_BIT, hal.HAL_IN)     # Spindle state input
        self.h.newpin("enable_axes", hal.HAL_BIT, hal.HAL_OUT)    # Enable all axes
        
        # Debug Output pins
        self.h.newpin("debug_axes_ok", hal.HAL_BIT, hal.HAL_OUT)     # Shows if all axes are OK
        self.h.newpin("debug_machine_safe", hal.HAL_BIT, hal.HAL_OUT) # Shows if machine is safe to enable
        self.h.newpin("debug_halui_on", hal.HAL_BIT, hal.HAL_OUT)    # Shows HALUI machine.is-on state
        
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
        self.last_vacuum_pedal = False
        
        # Machine enable state tracking
        self.machine_enabled_state = False  # Latch state for machine enable
        self.last_machine_enabled = False   # For edge detection
        
        # Initialize outputs
        self.h.left_stops = False
        self.h.right_stops = False
        self.h.front_stops = False
        self.h.enable_machine = False    # Start with machine disabled
        self.h.suction_on = False
        self.h.suction_off = False
        self.h.suction_up = False
        self.h.low_vacuum = False
        self.h.motion_enable = False     # Start with motion disabled
        self.h.enable_axes = False       # Start with axes disabled
        self.h.debug_axes_ok = False
        self.h.debug_machine_safe = False
        self.h.debug_halui_on = False
        
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
        
        # Detect rising edge of pedal press for latching behavior
        pedal_pressed = self.h.vacuum_pedal and not self.last_vacuum_pedal
        self.last_vacuum_pedal = self.h.vacuum_pedal
        
        if self.vacuum_state == VacuumState.IDLE:
            if pedal_pressed:  # Toggle vacuum on
                self.vacuum_state = VacuumState.VACUUM_ON
                self.vacuum_timer_start = current_time
                self.h.suction_on = True
                self.h.suction_off = False
                self.h.low_vacuum = False
        
        elif self.vacuum_state == VacuumState.VACUUM_ON:
            if self.h.vacuum_ok:
                if current_time - self.vacuum_timer_start >= self.VACUUM_CHECK_TIME:
                    return True  # Indicate vacuum ready
            
            if pedal_pressed:  # Toggle vacuum off
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
        
        # Check machine enable and safety conditions
        safety_ok = self.h.estop_ok
        machine_enabled = self.h.machine_enabled  # From HALUI machine.is-on
        
        # Monitor axis status
        x_ok = self.h.x_axis_ok
        y_ok = self.h.y_axis_ok
        z_ok = self.h.z_axis_ok
        
        # Detailed debug output
        print(f"\nEnable Chain Status:")
        print(f"  E-Stop Chain:")
        print(f"    estop_ok: {safety_ok}")
        print(f"    emc-enable-in: {self.h.emc_enable_in}")
        print(f"    user-enable-out: {self.h.user_enable_out}")
        print(f"    estop-latch.ok-out: {self.h.estop_latch_ok}")
        print(f"    estop-latch.fault-in: {self.h.estop_latch_fault}")
        print(f"    remote-estop (input-03): {self.h.remote_estop}")
        print(f"  Machine State:")
        print(f"    machine_enabled (from HALUI): {machine_enabled}")
        print(f"    machine_on (from HALUI): {self.h.machine_on}")
        print(f"    machine_enabled_state (internal): {self.machine_enabled_state}")
        print(f"  Axis Status:")
        print(f"    X: {x_ok}")
        print(f"    Y: {y_ok}")
        print(f"    Z: {z_ok}")
        print(f"  Current Outputs:")
        print(f"    enable_machine: {self.h.enable_machine}")
        print(f"    enable_axes: {self.h.enable_axes}")
        print(f"    motion_enable: {self.h.motion_enable}")
        
        # Update debug pins
        self.h.debug_machine_safe = safety_ok
        self.h.debug_halui_on = machine_enabled
        self.h.debug_axes_ok = x_ok and y_ok and z_ok
        
        # Handle machine enable state
        if safety_ok and machine_enabled:
            # Safety OK and machine enabled, enable machine
            self.machine_enabled_state = True
            self.h.enable_machine = True
            self.h.enable_axes = True
            # Only enable motion if all axes are OK
            if x_ok and y_ok and z_ok:
                self.h.motion_enable = True
            print("  Action: Machine enabled - safety OK and machine enabled")
        else:
            # Safety not OK or machine not enabled, disable machine
            if self.machine_enabled_state:  # Only print if state is changing
                print(f"  Action: Machine disabled - safety_ok: {safety_ok}, machine_enabled: {machine_enabled}")
            self.machine_enabled_state = False
            self.h.enable_machine = False
            self.h.enable_axes = False
            self.h.motion_enable = False
            
            # Return to IDLE state
            self.work_area_state = WorkAreaState.IDLE
            self.h.left_stops = False
            self.h.right_stops = False
            self.h.front_stops = False
            self.h.suction_on = False
            self.h.suction_off = False
            self.h.suction_up = False
            self.vacuum_state = VacuumState.IDLE
        
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
            if left_pressed or right_pressed and self.h.machine_enabled and self.machine_enabled_state:
                self.work_area_state = WorkAreaState.SETUP_MODE
                self.setup_side = 'left' if left_pressed else 'right'
                
                # Temporarily disable motion but keep machine enabled
                self.h.motion_enable = False
                
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
                
                # Re-enable motion if machine is still enabled and safe
                if self.h.machine_enabled and self.machine_enabled_state:
                    self.h.motion_enable = True
                
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