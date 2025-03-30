#!/usr/bin/env python3
# command to make python files executable: chmod +x python/*.py

import hal
import time

class MachineEnable:
    def __init__(self):
        self.h = hal.component("machine_enable")
        
        # Input pins
        self.h.newpin("estop_ok", hal.HAL_BIT, hal.HAL_IN)       # E-stop chain status
        self.h.newpin("estop_pcells", hal.HAL_BIT, hal.HAL_IN)   # E-stop PCells
        self.h.newpin("machine_btn_on", hal.HAL_BIT, hal.HAL_IN)       # Machine button state
        self.h.newpin("work_area_setup", hal.HAL_BIT, hal.HAL_IN) 	# Work area setup state (from work_area component)
        
        # Output pins
        self.h.newpin("enable_machine", hal.HAL_BIT, hal.HAL_OUT)      # Machine enable output
        self.h.newpin("enable_axes", hal.HAL_BIT, hal.HAL_OUT)         # Enable all axes
        
        # State tracking
        self.machine_enabled_state = False
        self.pcells_latched = False  # Track if PCells are latched
        
        # Initialize outputs
        self.h.enable_machine = False    # Start with machine disabled
        self.h.enable_axes = False       # Start with axes disabled
        
        print("Machine Enable initialized with PCells latch = False")
        self.h.ready()
    
    def update(self):
        # Check machine enable and safety conditions
        machine_btn_on = self.h.machine_btn_on
        
        # Handle PCells latching
        if not machine_btn_on:  # Machine is turned off
            if self.pcells_latched:  # Only print if we're actually resetting
                print("  Action: PCells latch reset (machine turned off)")
            self.pcells_latched = False  # Reset latch when machine is turned off
        elif self.h.work_area_setup:  # Reset latch when entering setup mode
            if self.pcells_latched:
                print("  Action: PCells latch reset (entering setup mode)")
            self.pcells_latched = False
        elif machine_btn_on and self.machine_enabled_state:  # Only check PCells if machine is running
            if not self.h.estop_pcells:  # PCells just tripped
                self.pcells_latched = True
                print("  Action: PCells tripped and latched")
        
        # Use latched state for safety check
        safety_ok = self.h.estop_ok and not self.pcells_latched

        # Print detailed state information
        # print(f"Machine Enable State:")
        # print(f"  estop_ok: {self.h.estop_ok}")
        # print(f"  estop_pcells: {self.h.estop_pcells}")
        # print(f"  pcells_latched: {self.pcells_latched}")
        # print(f"  work_area_setup: {self.h.work_area_setup}")
        # print(f"  machine_btn_on: {machine_btn_on}")
        # print(f"  safety_ok: {safety_ok}")
        # print(f"  current_state: {'Enabled' if self.machine_enabled_state else 'Disabled'}")

        if safety_ok and machine_btn_on:
            if not self.machine_enabled_state:
                print(f"  Action: Machine enabled - safety_ok: {safety_ok}, machine_btn_on: {machine_btn_on}")
            self.machine_enabled_state = True
            self.h.enable_machine = True
            self.h.enable_axes = True
        else:
            if self.machine_enabled_state:
                print(f"  Action: Machine disabled - safety_ok: {safety_ok}, machine_btn_on: {machine_btn_on}")
            self.machine_enabled_state = False
            self.h.enable_machine = False
            self.h.enable_axes = False

def main():
    machine_enable = MachineEnable()
    
    try:
        while True:
            machine_enable.update()
            time.sleep(0.1)  # Changed to 0.1 second
            
    except KeyboardInterrupt:
        raise SystemExit

if __name__ == "__main__":
    main() 
