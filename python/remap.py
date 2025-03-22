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
    
    # Handle combined tools 19 and 20
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

def remap_m6(self, **params):
    """Remap M6 to handle tool changes with verification for router (T18) and saw blade (T17)."""
    cmd = linuxcnc.command()
    stat = linuxcnc.stat()
    stat.poll()

    previous_tool = self.current_tool
    tool_number = getattr(self, "selected_tool", -1)
    print(f"Previous tool:{previous_tool} Selected Tool: {tool_number}")
    if tool_number < 1:
        print("ERROR: No valid tool number received from change_prolog.")
        return INTERP_ERROR

    try:
        print(f"Executing tool change to Tool {tool_number}")
        stat = linuxcnc.stat()
        stat.poll()
        # Sensor states
        blade_up = bool(stat.din[0])
        print(f"Blade up status {blade_up}")
        blade_down = bool(stat.din[1])
        print(f"Blade dwon status {blade_down}")
        router_up = bool(stat.din[2])
        print(f"Router up status {router_up}")
        router_down = bool(stat.din[3])
        print(f"Router down status {router_down}")

        simple_tools = get_simple_tools()

        # --- Retract Previous Tool ---
        if previous_tool != tool_number:
            stat = linuxcnc.stat()
            stat.poll()
            if previous_tool == 18 and router_down:
                print("Raising Router")
                self.execute(f"M64 P14")  # Activate retract
                time.sleep(3)
                self.execute(f"M65 P14")  # Turn off after 3 seconds

            elif previous_tool == 17 and blade_down:
                print("Raising Saw Blade")
                self.execute(f"M64 P15")  # Activate retract
                time.sleep(3)
                self.execute(f"M65 P15")  # Turn off after 3 seconds

            elif previous_tool in simple_tools:
                prev_info = simple_tools[previous_tool]
                if prev_info.get("combined"):
                    print(f"Retracting {prev_info['name']}")
                    for pin in prev_info["pins"]:
                        self.execute(f"M65 P{pin}")
                elif not (prev_info.get("shared_pin") and tool_number == prev_info.get("paired_tool")):
                    print(f"Retracting {prev_info['name']}")
                    self.execute(f"M65 P{prev_info['down_pin']}")

        # --- Activate New Tool ---
        if tool_number == 18:
            stat = linuxcnc.stat()
            stat.poll()
            print("Activating Router (T18)")
            if router_up and not router_down:
                print("Lowering Router: P13 ON")
                # self.execute("M65 P14")
                self.execute(f"M64 P13")
                time.sleep(3)
                self.execute(f"M65 P13")
                print("Waiting for router to reach down position...")
                if not wait_for_input(stat, 3, True, timeout=5):
                    print("⚠️ Router did not reach down position within timeout!")

        elif tool_number == 17:
            stat = linuxcnc.stat()
            stat.poll()
            print("Activating Saw Blade (T17)")
            if blade_up and not blade_down:
                print("Lowering Saw Blade: P16 ON")
                # self.execute("M65 P15")
                self.execute(f"M64 P16")
                time.sleep(3)
                self.execute(f"M65 P16")
                print("Waiting for saw blade to reach down position...")
                if not wait_for_input(stat, 1, True, timeout=5):
                    print("⚠️ Saw blade did not reach down position within timeout!")

        elif tool_number in simple_tools:
            info = simple_tools[tool_number]
            if info.get("combined"):
                print(f"Activating {info['name']}")
                for pin in info["pins"]:
                    self.execute(f"M64 P{pin}")
            elif not (info.get("shared_pin") and previous_tool == info.get("paired_tool")):
                print(f"Activating {info['name']}")
                self.execute(f"M64 P{info['down_pin']}")

        # --- Apply Tool Change Internally ---
        print(f"Tool change in progress. Changing to tool {tool_number}")
        emccanon.CHANGE_TOOL_NUMBER(tool_number)
        self.current_tool = tool_number
        self.selected_tool = -1
        self.toolchange_flag = True

        # --- Apply Offsets via G10 ---
        stat.poll()
        tool_data = next((t for t in stat.tool_table if t.id == tool_number), None)
        if tool_data:
            x = tool_data.xoffset
            y = tool_data.yoffset
            z = tool_data.zoffset
            d = tool_data.diameter
            r = d / 2 if d else 0

            g10_cmd = f"G10 L1 P{tool_number} X{x} Y{y} Z{z} R{r}"
            print(f"Applying offsets: {g10_cmd}")
            self.execute(g10_cmd)
        else:
            print(f"Tool {tool_number} not found in tool table.")
            return INTERP_ERROR

        print(f"Tool change completed successfully. Changed from T{previous_tool} to T{tool_number}.")
        return INTERP_OK

    except Exception as e:
        print(f"Error in remap_m6: {e}")
        return INTERP_ERROR
