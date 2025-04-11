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
    
    # Handle combined tools 17 and 18
    combined_tools = {
        17: {  # Vertical Y spindles (tools 1-5)
            "name": "Vertical Y Spindles",
            "pins": [0, 1, 2, 3, 4],  # Pins for tools 1-5
            "tools": [1, 2, 3, 4, 5]
        },
        18: {  # Vertical X spindles (tools 6-10)
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
    print("🔁 Releasing all digital outputs (P0–P16)...")
    stat = linuxcnc.stat()
    stat.poll()
    for pin in range(17):
        if stat.dout[pin]:
            print(f"  - M65 P{pin} (was ON)")
            self.execute(f"M65 P{pin}")
            yield INTERP_EXECUTE_FINISH
        else:
            print(f"  - P{pin} already OFF")


def remap_m6(self, **params):
    import linuxcnc
    import time

    cmd = linuxcnc.command()
    stat = linuxcnc.stat()
    stat.poll()

    print("=== Starting M6 Tool Change ===")
    print(f"Params received: {params}")
    
    tool_number = getattr(self, "selected_tool", -1)
    previous_tool = int(params.get("tool_in_spindle", self.current_tool))
    print(f"Tool change requested: T{previous_tool} -> T{tool_number}")
    
    if tool_number < 1:
        print("ERROR: No valid tool number received.")
        yield INTERP_ERROR
        return

    try:
        # --- Optional: Release all outputs first ---
        print("Releasing all outputs...")
        yield from release_all_outputs(self)
        
        stat.poll()
        print(f"Current tool state - Previous: T{previous_tool}, New: T{tool_number}")
        print(f"Input states - Blade up: {bool(stat.din[0])}, Blade down: {bool(stat.din[1])}, Router up: {bool(stat.din[2])}, Router down: {bool(stat.din[3])}")

        simple_tools = get_simple_tools()
        print(f"Simple tools configuration: {simple_tools}")

        # Get tool data to check for router flag
        tool_data = next((t for t in stat.tool_table if t.id == tool_number), None)
        print(f"Tool data for T{tool_number}: {tool_data}")
        is_router = False
        if tool_data and hasattr(tool_data, 'comment') and tool_data.comment:
            is_router = "ROUTER=1" in tool_data.comment
        print(f"Is router tool: {is_router}")

        # --- Retract Router or Blade ---
        if not is_router and tool_number != 19:
            print("Checking router and blade positions...")
            if bool(stat.din[3]):  # router_down
                print("Raising Router (P14)")
                self.execute("M64 P14")
                yield INTERP_EXECUTE_FINISH
                if not wait_for_input(stat, 2, True, timeout=5):
                    print("⚠️ Router did not reach up position!")
                    yield INTERP_ERROR
                    return
                self.execute("M65 P14")
                yield INTERP_EXECUTE_FINISH

            if bool(stat.din[1]):  # blade_down
                print("Raising Saw Blade (P15)")
                self.execute("M64 P15")
                yield INTERP_EXECUTE_FINISH
                if not wait_for_input(stat, 0, True, timeout=5):
                    print("⚠️ Saw blade did not reach up position!")
                    yield INTERP_ERROR
                    return
                self.execute("M65 P15")
                yield INTERP_EXECUTE_FINISH

        # --- Activate New Tool ---
        print(f"Activating new tool T{tool_number}...")
        if is_router:
            print("Activating Router")
            if bool(stat.din[2]) and not bool(stat.din[3]):  # router_up and not router_down
                print("Sending M64 P13 command")
                self.execute("M64 P13")
                yield INTERP_EXECUTE_FINISH
                print("Waiting for router activation...")
                if not wait_for_input(stat, 3, True, timeout=5):
                    print("⚠️ Router did not reach down position!")
                    yield INTERP_ERROR
                    return
                print("Sending M65 P13 command")
                self.execute("M65 P13")
                yield INTERP_EXECUTE_FINISH

        elif tool_number == 19:
            print("Activating Saw Blade")
            if bool(stat.din[0]) and not bool(stat.din[1]):  # blade_up and not blade_down
                print("Sending M64 P16 command")
                self.execute("M64 P16")
                yield INTERP_EXECUTE_FINISH
                print("Waiting for blade activation...")
                if not wait_for_input(stat, 1, True, timeout=5):
                    print("⚠️ Saw blade did not reach down position!")
                    yield INTERP_ERROR
                    return
                print("Sending M65 P16 command")
                self.execute("M65 P16")
                yield INTERP_EXECUTE_FINISH

        # --- Finalize Tool Change State ---
        print("Finalizing tool change...")
        self.current_tool = tool_number
        self.selected_tool = -1
        self.toolchange_flag = True

        stat.poll()
        tool_data = next((t for t in stat.tool_table if t.id == tool_number), None)
        if not tool_data:
            print(f"❌ Tool ID {tool_number} not found in tool table.")
            yield INTERP_ERROR
            return

        print(f"✅ Tool change to T{tool_number} complete.")
        yield INTERP_OK

    except Exception as e:
        print(f"❌ Error in remap_m6: {e}")
        yield INTERP_ERROR

def remap_m3(self, **params):
    """Handle M3 (spindle on) command"""
    import linuxcnc
    stat = linuxcnc.stat()
    stat.poll()
    
    # Only activate motor for tools 1-19 (not router)
    if 1 <= self.current_tool <= 19:
        print("Activating Motor (P17)")
        self.execute("M64 P17")
        yield INTERP_EXECUTE_FINISH
    
    yield INTERP_OK

def remap_m5(self, **params):
    """Handle M5 (spindle off) command"""
    import linuxcnc
    stat = linuxcnc.stat()
    stat.poll()
    
    # Deactivate motor for tools 1-19 (not router)
    if 1 <= self.current_tool <= 19:
        print("Deactivating Motor (P17)")
        self.execute("M65 P17")
        yield INTERP_EXECUTE_FINISH
    
    yield INTERP_OK
    