#   This is a component of LinuxCNC
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#

from stdglue import *
import linuxcnc
import time  # Add import for sleep function
import emccanon
from itertools import count

def get_simple_tools():
    """Dynamically build the simple_tools dictionary from the tool table.
    Special pin mapping:
    - Tools 1-10: map to pins 0-9 respectively
    - Tools 11-12: both map to pin 10
    - Tools 13-14: both map to pin 11
    - Tools 15-16: both map to pin 12
    - Tool 19: combines tools 1-5 (vertical Y spindles)
    - Tool 20: combines tools 6-10 (vertical X spindles)
    """
    stat = linuxcnc.stat()
    stat.poll()
    simple_tools = {}
    
    # Handle tools 1-10 with direct pin mapping
    for tool_num in range(1, 11):
        for tool in stat.tool_table:
            if tool.id == tool_num:
                simple_tools[tool_num] = {
                    "down_pin": tool_num - 1,  # Tools 1-10 map directly to pins 0-9
                    "name":  f"Tool-{tool_num}"
                }
                break
    
    # Handle special pin mappings for tools 11-16
    special_mappings = {
        11: {"pin": 10, "pair": 12},  # Tools 11 and 12 share pin 10
        12: {"pin": 10, "pair": 11},
        13: {"pin": 11, "pair": 14},  # Tools 13 and 14 share pin 11
        14: {"pin": 11, "pair": 13},
        15: {"pin": 12, "pair": 16},  # Tools 15 and 16 share pin 12
        16: {"pin": 12, "pair": 15}
    }
    
    for tool_num, mapping in special_mappings.items():
        for tool in stat.tool_table:
            if tool.id == tool_num:
                simple_tools[tool_num] = {
                    "down_pin": mapping["pin"],
                    "name":  f"Tool-{tool_num}",
                    "shared_pin": True,
                    "paired_tool": mapping["pair"]
                }
                break
    
    # Below are the 5 combined vertical X and 
    combined_tools = {
        19: {  # Vertical Y spindles (tools 1-5)
            "name": "Vertical Y Spindles",
            "pins": [0, 1, 2, 3, 4],  # Pins for tools 1-5
            "tools": [1, 2, 3, 4, 5]
        },
        20: {  # Vertical X spindles (tools 6-10)
            "name": "Vertical X Spindles",
            "pins": [5, 6, 7, 8, 9],  # Pins for tools 6-10
            "tools": [6, 7, 8, 9, 10]
        }
    }
    
    for tool_num, info in combined_tools.items():
        for tool in stat.tool_table:
            if tool.id == tool_num:
                simple_tools[tool_num] = {
                    "name": info["name"],
                    "combined": True,
                    "pins": info["pins"],
                    "tools": info["tools"]
                }
                break
    
    return simple_tools

def wait_for_input(stat, index, expected_state=True, timeout=5):
    """Wait for digital input to reach expected_state within timeout."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        stat.poll()
        if bool(stat.din[index]) == expected_state:
            return True
        time.sleep(0.05)  # poll every 50ms
    return False  # timeout

def release_all_outputs(self):
    print("🔁 Releasing all tool digital outputs (P0-P16)...")
    stat = linuxcnc.stat()
    stat.poll()
    for pin in range(17):  # Only check pins 0-16 for tools 1-19
        if stat.dout[pin]:
            print(f"  - P{pin} (was ON)")
            self.execute(f"M65 P{pin}")
            yield INTERP_EXECUTE_FINISH
        else:
            print(f"  - P{pin} already OFF")


def remap_m8(self, **words):
    """Remap M8 (coolant) to retract all bits for tools 1-19"""
    try:
        print("M8: Retracting all bits (tools 1-19)...")
        yield from release_all_outputs(self)
        yield INTERP_OK
    except Exception as e:
        self.set_errormsg(f"M8 remap error: {str(e)}")
        yield INTERP_ERROR


def remap_m9(self, **words):
    """Remap M9 (coolant off) to do nothing since M8 already retracts"""
    yield INTERP_OK


def remap_m6(self, **params):
    import linuxcnc
    import time

    cmd = linuxcnc.command()
    stat = linuxcnc.stat()
    stat.poll()

    tool_number = getattr(self, "selected_tool", -1)
    previous_tool = int(params.get("tool_in_spindle", self.current_tool))
    if tool_number < 1:
        print("ERROR: No valid tool number received.")
        yield INTERP_ERROR

    try:
        # --- Optional: Release all outputs first ---
        yield from release_all_outputs(self)
        print(f"Tool change: T{previous_tool} -> T{tool_number}")
        stat.poll()
        blade_up = bool(stat.din[0])
        blade_down = bool(stat.din[1])
        router_up = bool(stat.din[2])
        router_down = bool(stat.din[3])

        simple_tools = get_simple_tools()

        # --- Retract Router or Blade ---
        if tool_number != 20:  # Only check if we're not switching to router
            if router_down:
                print("Raising Router (P14)")
                self.execute("M64 P14")
                yield INTERP_EXECUTE_FINISH
                time.sleep(3)
                self.execute("M65 P14")
                yield INTERP_EXECUTE_FINISH

        if tool_number != 17:  # Only check if we're not switching to saw blade
            if blade_down:
                print("Raising Saw Blade (P15)")
                self.execute("M64 P15")
                yield INTERP_EXECUTE_FINISH
                time.sleep(3)
                self.execute("M65 P15")
                yield INTERP_EXECUTE_FINISH

        # For router (T20), use manual tool change
        if tool_number >= 20:
            self.selected_pocket = int(self.params["selected_pocket"])
            # Manual tool change - requires user confirmation
            emccanon.CHANGE_TOOL()
            self.current_pocket = self.selected_pocket
            self.selected_pocket = -1
            self.selected_tool = -1
            # cause a sync()
            self.set_tool_parameters()
            self.toolchange_flag = True
        else:
            # For all other tools (T1-T19), skip manual confirmation
            self.current_tool = tool_number
            self.current_pocket = tool_number
            self.selected_pocket = -1
            self.selected_tool = -1
            self.set_tool_parameters()
            self.toolchange_flag = True

        # --- Activate New Tool ---
        if tool_number == 20:  # Router is now T20
            print("Activating Router (T20)")
            if router_up and not router_down:
                self.execute("M64 P13")
                yield INTERP_EXECUTE_FINISH
                time.sleep(3)
                self.execute("M65 P13")
                yield INTERP_EXECUTE_FINISH
                print("Waiting for router to reach down position...")
                stat.poll()
                if not wait_for_input(stat, 3, True, timeout=5):
                    print("⚠️ Router did not reach down position!")

        elif tool_number == 17:
            print("Activating Saw Blade (T17)")
            if blade_up and not blade_down:
                self.execute("M64 P16")
                yield INTERP_EXECUTE_FINISH
                time.sleep(3)
                self.execute("M65 P16")
                yield INTERP_EXECUTE_FINISH
                print("Waiting for saw blade to reach down position...")
                stat.poll()
                if not wait_for_input(stat, 1, True, timeout=5):
                    print("⚠️ Saw blade did not reach down position!")

        elif tool_number == 18:  # Combined Vertical Y Spindles (was T19)
            print("Activating T18 (Vertical Y Spindles)")
            for pin in [0, 1, 2, 3, 4]:
                self.execute(f"M64 P{pin}")
                yield INTERP_EXECUTE_FINISH

        elif tool_number == 19:  # Combined Vertical X Spindles (was T20)
            print("Activating T19 (Vertical X Spindles)")
            for pin in [5, 6, 7, 8, 9]:
                self.execute(f"M64 P{pin}")
                yield INTERP_EXECUTE_FINISH

        elif tool_number in simple_tools:
            info = simple_tools[tool_number]
            if not (info.get("shared_pin") and previous_tool == info.get("paired_tool")):
                print(f"Activating {info['name']}")
                self.execute(f"M64 P{info['down_pin']}")
                yield INTERP_EXECUTE_FINISH

        yield INTERP_OK

    except Exception as e:
        self.set_errormsg(f"M6 remap error: {str(e)}")
        yield INTERP_ERROR

