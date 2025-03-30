#!/usr/bin/env python3
# command to make python files executable: chmod +x python/*.py

import hal
import time
from enum import Enum

class WorkAreaState(Enum):
    IDLE = 0
    SETUP_MODE = 1
    # WAITING_FOR_VACUUM = 2
    ERROR = 3

class WorkAreaControl:
    def __init__(self):
        self.h = hal.component("work_area")

        # Work Area Input pins
        self.h.newpin("left_button", hal.HAL_BIT, hal.HAL_IN)
        self.h.newpin("right_button", hal.HAL_BIT, hal.HAL_IN)
        self.h.newpin("work_area_setup", hal.HAL_BIT, hal.HAL_IN)    # From vacuum component

        # Work Area Output pins
        self.h.newpin("left_stops", hal.HAL_BIT, hal.HAL_OUT)
        self.h.newpin("right_stops", hal.HAL_BIT, hal.HAL_OUT)
        self.h.newpin("front_stops", hal.HAL_BIT, hal.HAL_OUT)

        # State tracking
        self.work_area_state = WorkAreaState.IDLE
        self.last_left_button = False
        self.last_right_button = False
        self.setup_side = None  # 'left' or 'right'

        # Initialize outputs
        self.h.left_stops = False
        self.h.right_stops = False
        self.h.front_stops = False
        self.h.work_area_setup = False

        self.h.ready()

    def update(self):
        # print(f"Work area state: {self.work_area_state}")
        # print(f"work_area_setup: {self.h.work_area_setup}")
        # print(f"left_button: {self.h.left_button}")
        # print(f"right_button: {self.h.right_button}")
        # print(f"left_stops: {self.h.left_stops}")
        # print(f"right_stops: {self.h.right_stops}")
        # print(f"front_stops: {self.h.front_stops}")
        # Read button states
        left_button = self.h.left_button
        right_button = self.h.right_button

        # Detect button press events
        left_pressed = left_button and not self.last_left_button
        right_pressed = right_button and not self.last_right_button

        # Work area state machine
        if self.work_area_state == WorkAreaState.IDLE:
            if left_pressed or right_pressed:
                self.work_area_state = WorkAreaState.SETUP_MODE
                self.setup_side = 'left' if left_pressed else 'right'

                # Raise appropriate stops
                self.h.left_stops = True 
                self.h.right_stops = True
                self.h.front_stops = True

        elif self.work_area_state == WorkAreaState.SETUP_MODE:
            self.h.work_area_setup = True
            if (left_pressed and self.setup_side == 'left') or \
               (right_pressed and self.setup_side == 'right'):
                # Return to idle state
                self.work_area_state = WorkAreaState.IDLE

                # Lower all stops
                self.h.left_stops = False
                self.h.right_stops = False
                self.h.front_stops = False

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
