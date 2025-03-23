#!/usr/bin/env python3

import hal
import time
from enum import Enum

class WorkAreaState(Enum):
    IDLE = 0
    SETUP_MODE = 1
    WAITING_FOR_VACUUM = 2

class WorkAreaControl:
    def __init__(self):
        self.h = hal.component("work_area")
        
        # Input pins
        self.h.newpin("left_button", hal.HAL_BIT, hal.HAL_IN)
        self.h.newpin("right_button", hal.HAL_IN)
        self.h.newpin("vacuum_pedal", hal.HAL_BIT, hal.HAL_IN)
        self.h.newpin("machine_enabled", hal.HAL_BIT, hal.HAL_IN)
        
        # Output pins
        self.h.newpin("left_stops", hal.HAL_BIT, hal.HAL_OUT)
        self.h.newpin("right_stops", hal.HAL_BIT, hal.HAL_OUT)
        self.h.newpin("front_stops", hal.HAL_BIT, hal.HAL_OUT)
        self.h.newpin("suction_on", hal.HAL_BIT, hal.HAL_OUT)
        self.h.newpin("suction_off", hal.HAL_BIT, hal.HAL_OUT)
        self.h.newpin("suction_up", hal.HAL_BIT, hal.HAL_OUT)
        self.h.newpin("photo_eyes_bypass", hal.HAL_BIT, hal.HAL_OUT)
        
        # Machine control pins
        self.h.newpin("motion_enable", hal.HAL_BIT, hal.HAL_OUT)  # Control motion enable
        self.h.newpin("spindle_stop", hal.HAL_BIT, hal.HAL_OUT)   # Control spindle
        
        # State tracking
        self.state = WorkAreaState.IDLE
        self.last_left_button = False
        self.last_right_button = False
        self.setup_side = None  # 'left' or 'right'
        
        # Initialize outputs
        self.h.motion_enable = True  # Start with motion enabled
        self.h.spindle_stop = False  # Start with spindle control normal
        
        self.h.ready()
    
    def update(self):
        # Read inputs
        left_button = self.h.left_button
        right_button = self.h.right_button
        vacuum_pedal = self.h.vacuum_pedal
        
        # Detect button press events (rising edge)
        left_pressed = left_button and not self.last_left_button
        right_pressed = right_button and not self.last_right_button
        
        # State machine
        if self.state == WorkAreaState.IDLE:
            if left_pressed or right_pressed:
                self.state = WorkAreaState.SETUP_MODE
                self.setup_side = 'left' if left_pressed else 'right'
                
                # Disable machine motion and spindle
                self.h.motion_enable = False  # Disable motion
                self.h.spindle_stop = True    # Stop spindle
                self.h.photo_eyes_bypass = True
                
                # Raise appropriate stops
                self.h.left_stops = True if left_pressed else False
                self.h.right_stops = True if right_pressed else False
                self.h.front_stops = True
                
        elif self.state == WorkAreaState.SETUP_MODE:
            if vacuum_pedal:
                self.state = WorkAreaState.WAITING_FOR_VACUUM
                # Activate suction
                self.h.suction_up = True
                self.h.suction_on = True
                self.h.suction_off = False
                
        elif self.state == WorkAreaState.WAITING_FOR_VACUUM:
            if (left_pressed and self.setup_side == 'left') or \
               (right_pressed and self.setup_side == 'right'):
                # Return to idle state
                self.state = WorkAreaState.IDLE
                
                # Lower all stops
                self.h.left_stops = False
                self.h.right_stops = False
                self.h.front_stops = False
                
                # Re-enable machine and photo eyes
                self.h.motion_enable = True   # Re-enable motion
                self.h.spindle_stop = False   # Allow spindle control
                self.h.photo_eyes_bypass = False
                
                # Keep suction on but lower cups
                self.h.suction_up = False
        
        # Update button state tracking
        self.last_left_button = left_button
        self.last_right_button = right_button

def main():
    control = WorkAreaControl()
    try:
        while True:
            control.update()
            time.sleep(0.1)  # 100ms update rate
    except KeyboardInterrupt:
        raise SystemExit 