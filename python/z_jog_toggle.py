#!/usr/bin/env python3
# Z-axis jog toggle control
# Allows toggling pendant jog control to Z-axis for Z0 setup

import hal
import time

class ZJogToggle:
    def __init__(self):
        self.h = hal.component("z_jog_toggle")
        
        # Input pins
        self.h.newpin("toggle_button", hal.HAL_BIT, hal.HAL_IN)  # Toggle button from GUI
        self.h.newpin("pendant_up", hal.HAL_BIT, hal.HAL_IN)  # Pendant Up button (shared with speed increase)
        self.h.newpin("pendant_down", hal.HAL_BIT, hal.HAL_IN)  # Pendant Down button (shared with speed decrease)
        
        # Output pins
        self.h.newpin("z_jog_mode_active", hal.HAL_BIT, hal.HAL_OUT)  # Status: Z jog mode active
        self.h.newpin("z_jog_up", hal.HAL_BIT, hal.HAL_OUT)  # Z jog up (when active)
        self.h.newpin("z_jog_down", hal.HAL_BIT, hal.HAL_OUT)  # Z jog down (when active)
        self.h.newpin("spindle_speed_incr", hal.HAL_BIT, hal.HAL_OUT)  # Spindle speed increase (when NOT in Z-mode)
        self.h.newpin("spindle_speed_decr", hal.HAL_BIT, hal.HAL_OUT)  # Spindle speed decrease (when NOT in Z-mode)
        
        # State tracking
        self.z_mode_active = False
        self.last_toggle_button = False
        
        # Initialize outputs
        self.h.z_jog_mode_active = False
        self.h.z_jog_up = False
        self.h.z_jog_down = False
        self.h.spindle_speed_incr = False
        self.h.spindle_speed_decr = False
        
        print("Z-axis jog toggle control initialized")
        self.h.ready()
    
    def update(self):
        # Detect toggle button press (rising edge)
        toggle_button = self.h.toggle_button
        toggle_pressed = toggle_button and not self.last_toggle_button
        
        if toggle_pressed:
            self.z_mode_active = not self.z_mode_active
            self.h.z_jog_mode_active = self.z_mode_active
            if self.z_mode_active:
                print("Z-axis jog mode ACTIVATED - Pendant now controls Z-axis")
            else:
                print("Z-axis jog mode DEACTIVATED - Pendant back to normal control")
        
        self.last_toggle_button = toggle_button
        
        # Route pendant signals based on mode
        if self.z_mode_active:
            # In Z-mode: route buttons to Z-axis jog
            self.h.z_jog_up = self.h.pendant_up
            self.h.z_jog_down = self.h.pendant_down
            # Spindle speed controls inactive
            self.h.spindle_speed_incr = False
            self.h.spindle_speed_decr = False
        else:
            # In normal mode: route buttons to spindle speed control
            self.h.spindle_speed_incr = self.h.pendant_up
            self.h.spindle_speed_decr = self.h.pendant_down
            # Z jog outputs inactive
            self.h.z_jog_up = False
            self.h.z_jog_down = False

def main():
    z_jog = ZJogToggle()
    
    try:
        while True:
            z_jog.update()
            time.sleep(0.05)  # 20Hz update rate (50ms)
    
    except KeyboardInterrupt:
        raise SystemExit

if __name__ == "__main__":
    main()

