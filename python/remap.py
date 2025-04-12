#   This is a component of LinuxCNC
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#

from stdglue import *
import linuxcnc
import time

def remap_m6(self, **params):
    import linuxcnc
    import time

    cmd = linuxcnc.command()
    stat = linuxcnc.stat()
    stat.poll()

    # Debug mode information
    mode_names = {
        linuxcnc.MODE_MANUAL: "Manual",
        linuxcnc.MODE_AUTO: "Auto",
        linuxcnc.MODE_MDI: "MDI"
    }
    current_mode = mode_names.get(stat.task_mode, f"Unknown ({stat.task_mode})")
    
    print(f"\n=== Tool Change Debug Info ===")
    print(f"Current Mode: {current_mode}")
    print(f"Task State: {stat.task_state}")
    print(f"Task File: {stat.file}")
    print("============================\n")

    tool_number = getattr(self, "selected_tool", -1)
    previous_tool = int(params.get("tool_in_spindle", self.current_tool))
    
    if tool_number < 1:
        print("ERROR: No valid tool number received.")
        yield INTERP_ERROR

    try:
        # --- Simple Tool Change for T1 and T2 ---
        print(f"Tool change: T{previous_tool} -> T{tool_number}")
        
        # Only handle T1 and T2
        if tool_number not in [1, 2]:
            print(f"ERROR: Only T1 and T2 are supported in this simplified version")
            yield INTERP_ERROR
            return

        # Retract previous tool
        if previous_tool in [1, 2]:
            print(f"Retracting T{previous_tool}")
            self.execute(f"M65 P{previous_tool-1}")  # T1 uses P0, T2 uses P1
            yield INTERP_EXECUTE_FINISH
            time.sleep(1)  # Short delay for solenoid to retract

        # Activate new tool
        print(f"Activating T{tool_number}")
        self.execute(f"M64 P{tool_number-1}")  # T1 uses P0, T2 uses P1
        yield INTERP_EXECUTE_FINISH
        time.sleep(1)  # Short delay for solenoid to activate

        # Update tool state
        self.current_tool = tool_number
        self.selected_tool = -1
        self.toolchange_flag = True

        # Apply tool offsets
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
            yield INTERP_EXECUTE_FINISH
            self.execute(f"G43 H{tool_number}")
            yield INTERP_EXECUTE_FINISH

            # Update LinuxCNC's internal state
            emccanon.CHANGE_TOOL(tool_number)
        else:
            print(f"❌ Tool ID {tool_number} not found in tool table.")
            yield INTERP_ERROR
        
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
    
    # Only activate motor for tools 1-2
    if 1 <= self.current_tool <= 2:
        print("Activating Motor (P17)")
        self.execute("M64 P17")
        yield INTERP_EXECUTE_FINISH
    
    yield INTERP_OK

def remap_m5(self, **params):
    """Handle M5 (spindle off) command"""
    import linuxcnc
    stat = linuxcnc.stat()
    stat.poll()
    
    # Deactivate motor for tools 1-2
    if 1 <= self.current_tool <= 2:
        print("Deactivating Motor (P17)")
        self.execute("M65 P17")
        yield INTERP_EXECUTE_FINISH
    
    yield INTERP_OK
    