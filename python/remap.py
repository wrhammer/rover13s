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

    # Get the tool number from the selected tool or parameters
    tool_number = getattr(self, "selected_tool", -1)
    if tool_number < 0:  # If not set in selected_tool, try to get it from params
        tool_number = int(params.get("tool_in_spindle", -1))
    
    if tool_number < 1:
        print("ERROR: No valid tool number received.")
        yield INTERP_ERROR
        return

    previous_tool = int(params.get("tool_in_spindle", self.current_tool))
    is_auto_mode = stat.task_mode == linuxcnc.MODE_AUTO
    print(f"Starting tool change: T{previous_tool} -> T{tool_number} (Mode: {'Auto' if is_auto_mode else 'MDI'})")

    def execute_command(command):
        if is_auto_mode:
            cmd.mode(linuxcnc.MODE_MDI)
            cmd.wait_complete()
            cmd.mdi(command)
            cmd.wait_complete()
        else:
            self.execute(command)
            yield INTERP_EXECUTE_FINISH

    try:
        # Wait for the interpreter to be ready
        timeout = 0
        while True:
            stat.poll()
            if stat.interp_state == linuxcnc.INTERP_IDLE:
                break
            time.sleep(0.1)
            timeout += 1
            if timeout > 50:  # 5 second timeout
                print("ERROR: Interpreter not ready after 5 seconds")
                yield INTERP_ERROR
                return

        # --- Optional: Release all outputs first ---
        yield from release_all_outputs(self)
        stat.poll()
        blade_up = bool(stat.din[0])
        blade_down = bool(stat.din[1])
        router_up = bool(stat.din[2])
        router_down = bool(stat.din[3])

        simple_tools = get_simple_tools()

        # Get tool data to check for router flag
        tool_data = next((t for t in stat.tool_table if t.id == tool_number), None)
        is_router = False
        if tool_data and hasattr(tool_data, 'comment') and tool_data.comment:
            is_router = "ROUTER=1" in tool_data.comment

        # --- Retract Router or Blade ---
        if not is_router and tool_number != 19:
            if router_down:
                print("Raising Router (P14)")
                execute_command("M64 P14")
                time.sleep(2)
                execute_command("M65 P14")

            if blade_down:
                print("Raising Saw Blade (P15)")
                execute_command("M64 P15")
                time.sleep(2)
                execute_command("M65 P15")

        # --- Retract Previous Simple or Combined Tool ---
        if previous_tool != tool_number:
            if previous_tool == 17:
                print("Retracting T18 (Vertical Y Spindles)")
                for pin in [0, 1, 2, 3, 4]:
                    execute_command(f"M65 P{pin}")
                    time.sleep(0.1)

            elif previous_tool == 18:
                print("Retracting T17 (Vertical Y Spindles)")
                for pin in [5, 6, 7, 8, 9]:
                    execute_command(f"M65 P{pin}")
                    time.sleep(0.1)

            elif previous_tool == 20:  # Special handling for router tool
                print("Retracting Router (T20)")
                stat.poll()
                router_up = bool(stat.din[2])
                router_down = bool(stat.din[3])
                
                if router_down:
                    print("Router is in down position, raising it first")
                    execute_command("M64 P14")  # Raise router
                    time.sleep(2)
                    execute_command("M65 P14")
                    time.sleep(2)
                    
                    # Verify router is up
                    stat.poll()
                    if not bool(stat.din[2]):  # If router is not up
                        print("⚠️ Router did not reach up position!")
                        yield INTERP_ERROR
                        return
                
                # Now retract the router control
                execute_command("M65 P13")  # Router control pin
                time.sleep(1)

            elif previous_tool in simple_tools:
                prev_info = simple_tools[previous_tool]
                if prev_info.get("shared_pin"):
                    paired_tool = prev_info.get("paired_tool")
                    if tool_number != paired_tool:
                        print(f"Retracting shared-pin tool: {prev_info['name']}")
                        execute_command(f"M65 P{prev_info['down_pin']}")
                    else:
                        print(f"Skipping retraction: {prev_info['name']} shares pin with T{tool_number}")
                else:
                    print(f"Retracting standard tool: {prev_info['name']}")
                    execute_command(f"M65 P{prev_info['down_pin']}")

        # --- Activate New Tool ---
        if tool_number == 20:  # Special handling for router tool
            print("Activating Router (T20)")
            stat.poll()
            router_up = bool(stat.din[2])
            router_down = bool(stat.din[3])
            
            if router_up and not router_down:
                print("Router is up, activating...")
                # First ensure router is fully up
                if not router_up:
                    print("Raising router first...")
                    execute_command("M64 P14")
                    time.sleep(2)
                    execute_command("M65 P14")
                    time.sleep(2)
                
                # Now activate the router
                print("Activating router control...")
                execute_command("M64 P13")
                time.sleep(3)
                execute_command("M65 P13")
                
                # Wait for router to reach down position with longer timeout
                print("Waiting for router to reach down position...")
                timeout = 0
                while timeout < 20:  # 20 second timeout
                    stat.poll()
                    if bool(stat.din[3]):  # Router is down
                        print("Router reached down position")
                        break
                    time.sleep(0.5)
                    timeout += 1
                    print(f"Waiting... ({timeout}/20 seconds)")
                
                if timeout >= 20:
                    print("⚠️ Router did not reach down position after 20 seconds!")
                    # Try to recover by raising the router
                    print("Attempting to raise router...")
                    execute_command("M64 P14")
                    time.sleep(2)
                    execute_command("M65 P14")
                    yield INTERP_ERROR
                    return
            else:
                print("Router is already in position")

        elif tool_number == 19:
            print("Activating Saw Blade (T19)")
            if blade_up and not blade_down:
                execute_command("M64 P16")
                time.sleep(3)
                execute_command("M65 P16")
                print("Waiting for saw blade to reach down position...")
                stat.poll()
                if not wait_for_input(stat, 1, True, timeout=10):
                    print("⚠️ Saw blade did not reach down position!")
                    yield INTERP_ERROR
                    return

        elif tool_number == 17:
            print("Activating T17 (Vertical Y Spindles)")
            for pin in [0, 1, 2, 3, 4]:
                execute_command(f"M64 P{pin}")
                time.sleep(0.1)

        elif tool_number == 18:
            print("Activating T18 (Vertical X Spindles)")
            for pin in [5, 6, 7, 8, 9]:
                execute_command(f"M64 P{pin}")
                time.sleep(0.1)

        elif tool_number in simple_tools:
            info = simple_tools[tool_number]
            if not (info.get("shared_pin") and previous_tool == info.get("paired_tool")):
                print(f"Activating {info['name']}")
                execute_command(f"M64 P{info['down_pin']}")
                time.sleep(0.5)

        # --- Update Tool State ---
        self.current_tool = tool_number
        self.selected_tool = -1
        self.toolchange_flag = True

        # First tell LinuxCNC this is the active tool
        try:
            emccanon.CHANGE_TOOL(tool_number)
            time.sleep(1.0)  # Wait for tool change to register
            
            # Check interpreter state with timeout
            timeout = 0
            max_attempts = 3
            for attempt in range(max_attempts):
                stat.poll()
                if stat.interp_state == linuxcnc.INTERP_IDLE:
                    break
                print(f"Waiting for interpreter (attempt {attempt + 1}/{max_attempts})...")
                time.sleep(1.0)
                timeout += 1
                if timeout >= 10:  # 10 second timeout per attempt
                    if attempt < max_attempts - 1:
                        print("Retrying tool change...")
                        emccanon.CHANGE_TOOL(tool_number)
                        time.sleep(1.0)
                        timeout = 0
                    else:
                        print("ERROR: Interpreter not ready after multiple attempts")
                        yield INTERP_ERROR
                        return

            # Let LinuxCNC handle the tool length offset
            try:
                print("Setting tool length offset")
                execute_command(f"G43 H{tool_number}")
                time.sleep(1.0)  # Wait for tool length offset to be applied
            except Exception as e:
                print(f"WARNING: Tool length offset failed: {e}")
                yield INTERP_ERROR
                return

        except Exception as e:
            print(f"ERROR: Tool change failed: {e}")
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
    