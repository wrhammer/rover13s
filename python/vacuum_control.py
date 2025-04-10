#!/usr/bin/env python3
# command to make python files executable: chmod +x python/*.py

import hal
import time
from enum import Enum

class VacuumState(Enum):
    IDLE = 0
    VACUUM_ON = 1
    VACUUM_OFF = 2
    ERROR = 3

class VacuumControl:
    def __init__(self):
        self.h = hal.component("vacuum")
        
        # Input pins
        self.h.newpin("vacuum_pedal", hal.HAL_BIT, hal.HAL_IN)
        self.h.newpin("vacuum_ok", hal.HAL_BIT, hal.HAL_IN)      # Vacuum level OK signal
        self.h.newpin("work_area_setup", hal.HAL_BIT, hal.HAL_IN)  # Set by work area control
        
        # Output pins
        self.h.newpin("suction_on", hal.HAL_BIT, hal.HAL_OUT)    # Turn vacuum on
        self.h.newpin("suction_off", hal.HAL_BIT, hal.HAL_OUT)   # Turn vacuum off
        self.h.newpin("suction_up", hal.HAL_BIT, hal.HAL_OUT)    # Raise suction cups
        self.h.newpin("low_vacuum", hal.HAL_BIT, hal.HAL_OUT)    # Low vacuum warning
        
        # State tracking
        self.vacuum_state = VacuumState.IDLE
        self.last_vacuum_ok = False
        self.last_vacuum_pedal = False
        
        # Initialize outputs
        self.h.suction_on = False
        self.h.suction_off = False
        self.h.suction_up = False
        self.h.low_vacuum = False
        
        self.h.ready()
    
    
    def update(self):
        # Check for vacuum loss in any state
        if not self.h.vacuum_ok:
            self.vacuum_state = VacuumState.ERROR
            self.h.low_vacuum = True
            return
        # print(f"Vacuum state: {self.vacuum_state}")
        # print(f"work_area_setup: {self.h.work_area_setup}")
        # print(f"vacuum_pedal: {self.h.vacuum_pedal}")
        # print(f"last_vacuum_pedal: {self.last_vacuum_pedal}")
        # print(f"suction_on: {self.h.suction_on}")
        # print(f"suction_off: {self.h.suction_off}")
        # print(f"low_vacuum: {self.h.low_vacuum}")

        # Detect rising edge of pedal press for latching behavior
        pedal_pressed = self.h.vacuum_pedal and not self.last_vacuum_pedal
        self.last_vacuum_pedal = self.h.vacuum_pedal
        
        # Only allow pedal control in setup mode
        if not self.h.work_area_setup:
            return  # Skip all control when not in setup mode
        
        # Handle pedal control in setup mode
        if self.vacuum_state == VacuumState.IDLE:
            if pedal_pressed:  # Toggle vacuum on
                print("  Action: Vacuum on, raising cups")
                self.vacuum_state = VacuumState.VACUUM_ON
                self.h.suction_on = True
                self.h.suction_off = False
                self.h.suction_up = True  # Raise cups when vacuum is on
                self.h.low_vacuum = False
        
        elif self.vacuum_state == VacuumState.VACUUM_ON:
            if pedal_pressed:  # Toggle vacuum off
                print("  Action: Vacuum off, lowering cups")
                self.vacuum_state = VacuumState.VACUUM_OFF
                self.h.suction_on = False
                self.h.suction_off = True
                self.h.suction_up = False  # Lower cups when vacuum is off
        
        elif self.vacuum_state == VacuumState.VACUUM_OFF:
            self.vacuum_state = VacuumState.IDLE
            self.h.suction_off = False
        
        elif self.vacuum_state == VacuumState.ERROR:
            if self.h.vacuum_ok:  # Reset error if vacuum restored
                self.vacuum_state = VacuumState.IDLE
                self.h.low_vacuum = False

def main():
    vacuum = VacuumControl()
    
    try:
        while True:
            vacuum.update()
            time.sleep(0.1)  # 100ms update rate
            
    except KeyboardInterrupt:
        raise SystemExit

if __name__ == "__main__":
    main() 
