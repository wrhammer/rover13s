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
    - Tool 17: combines tools 1-5 (vertical Y spindles)
    - Tool 18: combines tools 6-10 (vertical X spindles)
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

    # Ignore the preview interpreter
    if self.task == 0:
        yield INTERP_EXECUTE_FINISH
        return INTERP_OK

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
    
    # Get the actual tool currently in spindle from LinuxCNC stat
    stat.poll()
    previous_tool = stat.tool_in_spindle
    
    # Fallback to stored current_tool if stat doesn't have a tool
    if previous_tool <= 0:
        previous_tool = int(params.get("tool_in_spindle", getattr(self, "current_tool", 0)))
    
    if tool_number < 1:
        print("ERROR: No valid tool number received.")
        yield INTERP_ERROR

    try:
        # --- Release all outputs first ---
        print(f"Tool change: T{previous_tool} -> T{tool_number}")
        print(f"Current Mode: {mode_names.get(stat.task_mode, 'Unknown')}")  # Get fresh mode info
        stat.poll()
        blade_up = bool(stat.din[0])
        blade_down = bool(stat.din[1])
        router_up = bool(stat.din[2])
        router_down = bool(stat.din[3])

        simple_tools = get_simple_tools()

        # Check if current or previous tool is a router (T20 or greater)
        is_router = tool_number >= 20
        was_router = previous_tool >= 20
        both_routers = is_router and was_router  # Switching between router tools
        
        # Check if this router tool is different from the last one used
        last_router_tool = getattr(self, "last_router_tool", None)
        router_tool_changed = (is_router and last_router_tool is not None and tool_number != last_router_tool)

        # --- Retract Router or Blade ---
        if was_router and not both_routers:  # If previous tool was a router AND we're switching to non-router
            if router_down:
                print(f"Raising Router (T{previous_tool})")
                self.execute("M64 P14")
                self.execute("G04 P2")  # Wait 2 seconds
                self.execute("M65 P14")
                yield INTERP_EXECUTE_FINISH
        elif previous_tool == 19:  # If previous tool was saw
            if blade_down:
                print("Raising Saw Blade (T19)")
                self.execute("M64 P15")
                self.execute("G04 P2")  # Wait 2 seconds
                self.execute("M65 P15")
                yield INTERP_EXECUTE_FINISH
        elif not is_router and tool_number != 19:  # For other tools
            if router_down:
                print("Raising Router (P14)")
                self.execute("M64 P14")
                self.execute("G04 P2")  # Wait 2 seconds
                self.execute("M65 P14")
                yield INTERP_EXECUTE_FINISH

            if blade_down:
                print("Raising Saw Blade (P15)")
                self.execute("M64 P15")
                self.execute("G04 P2")  # Wait 2 seconds
                self.execute("M65 P15")
                yield INTERP_EXECUTE_FINISH

        # --- Retract Previous Simple or Combined Tool ---
        if previous_tool != tool_number and previous_tool > 0:
            if previous_tool == 17:
                print("Retracting T17 (Vertical Y Spindles)")
                for pin in [0, 1, 2, 3, 4]:
                    self.execute(f"M65 P{pin}")
                    yield INTERP_EXECUTE_FINISH

            elif previous_tool == 18:
                print("Retracting T18 (Vertical X Spindles)")
                for pin in [5, 6, 7, 8, 9]:
                    self.execute(f"M65 P{pin}")
                    yield INTERP_EXECUTE_FINISH

            elif previous_tool in simple_tools:
                prev_info = simple_tools[previous_tool]
                if prev_info.get("shared_pin"):
                    paired_tool = prev_info.get("paired_tool")
                    if tool_number != paired_tool:
                        print(f"Retracting shared-pin tool: {prev_info['name']}")
                        self.execute(f"M65 P{prev_info['down_pin']}")
                        yield INTERP_EXECUTE_FINISH
                    else:
                        print(f"Skipping retraction: {prev_info['name']} shares pin with T{tool_number}")
                else:
                    print(f"Retracting standard tool: {prev_info['name']} (T{previous_tool}, Pin P{prev_info['down_pin']})")
                    self.execute(f"M65 P{prev_info['down_pin']}")
                    yield INTERP_EXECUTE_FINISH
            
            # Fallback: If previous tool is 1-10 but not in simple_tools for some reason,
            # retract based on tool number (tools 1-10 map to pins 0-9)
            elif 1 <= previous_tool <= 10:
                pin_to_retract = previous_tool - 1
                print(f"Fallback retraction: Retracting T{previous_tool} on pin P{pin_to_retract}")
                self.execute(f"M65 P{pin_to_retract}")
                yield INTERP_EXECUTE_FINISH
        
        # Safety: If switching to router and we're not sure what the previous tool was,
        # retract all standard tool pins (0-9) to be safe
        elif is_router and previous_tool <= 0:
            print(f"Warning: Previous tool unknown. Retracting all standard tool pins (P0-P9) as safety measure.")
            for pin in range(10):
                self.execute(f"M65 P{pin}")
                yield INTERP_EXECUTE_FINISH

        # --- Activate New Tool ---
        if is_router:  # Any tool T20 or greater is a router
            # Poll fresh router state after retractions
            stat.poll()
            router_up = bool(stat.din[2])
            router_down = bool(stat.din[3])
            
            # Move to router tool change position only if router tool has changed
            # (skip if using same router bit as last time)
            # if router_tool_changed:
            #     # OPTION 1: Using G54 work coordinate system (coordinates relative to G54 origin)
            #     # print(f"Router tool changed - Moving to safe zone (X800 Y0 in G54)")
            #     # self.execute("G90")  # Ensure absolute mode
            #     # self.execute("G54")  # Ensure G54 coordinate system
            #     # self.execute("G0 Z15")  # Move to safe Z height first
            #     # yield INTERP_EXECUTE_FINISH
            #     # self.execute("G0 X800 Y0")  # Rapid move to tool change position in G54
            #     # yield INTERP_EXECUTE_FINISH
            #     # print("At tool change position (X800 Y0 in G54)")
            #     
            #     # OPTION 2: Using G53 machine coordinates (coordinates relative to machine home)
            #     # current_machine_pos = stat.actual_position  # Machine coordinates
            #     # target_x = 800.0  # Desired X in machine coordinates
            #     # target_y = 0.0    # Desired Y in machine coordinates
            #     # target_z = 30.0   # Safe Z height in machine coordinates
            #     # print(f"Router tool changed - Moving to safe zone (X{target_x} Y{target_y} in machine coordinates)")
            #     # self.execute("G90")  # Ensure absolute mode
            #     # self.execute("G53")  # Use machine coordinate system
            #     # self.execute(f"G0 Z{target_z}")  # Move to safe Z height first
            #     # yield INTERP_EXECUTE_FINISH
            #     # self.execute(f"G0 X{target_x} Y{target_y}")  # Rapid move to tool change position
            #     # yield INTERP_EXECUTE_FINISH
            #     # print(f"At tool change position (X{target_x} Y{target_y} in machine coordinates)")
            # else:
            #     print(f"Router bit unchanged - Skipping move to safe zone (T{tool_number})")
            # NOTE: Currently disabled - enable one of the options above as needed
            
            if both_routers:
                # Switching between router tools (e.g., T20 -> T21)
                # Router is already down, just verify it's in position
                if router_down:
                    print(f"Router already down - Skipping raise/lower cycle (T{previous_tool} -> T{tool_number})")
                else:
                    # Router is up when it shouldn't be, lower it
                    print(f"Router is up - Lowering for T{tool_number}")
                    self.execute("M64 P13")
                    self.execute("G04 P3")  # Wait 3 seconds
                    self.execute("M65 P13")
                    yield INTERP_EXECUTE_FINISH
                    stat.poll()
                    if not wait_for_input(stat, 3, True, timeout=5):
                        print("⚠️ Router did not reach down position!")
            else:
                # Switching to router from non-router tool
                print(f"Activating Router (T{tool_number})")
                # Always lower router when switching from non-router to router tool
                self.execute("M64 P13")
                self.execute("G04 P3")  # Wait 3 seconds
                self.execute("M65 P13")
                yield INTERP_EXECUTE_FINISH
                print("Waiting for router to reach down position...")
                stat.poll()
                if not wait_for_input(stat, 3, True, timeout=5):
                    print("⚠️ Router did not reach down position!")

        elif tool_number == 19:  # Saw
            print("Activating Saw Blade (T19)")
            if blade_up and not blade_down:
                self.execute("M64 P16")
                self.execute("G04 P3")  # Wait 3 seconds
                self.execute("M65 P16")
                yield INTERP_EXECUTE_FINISH
                print("Waiting for saw blade to reach down position...")
                stat.poll()
                if not wait_for_input(stat, 1, True, timeout=5):
                    print("⚠️ Saw blade did not reach down position!")

        elif tool_number == 17:
            print("Activating T17 (Vertical Y Spindles)")
            for pin in [0, 1, 2, 3, 4]:
                self.execute(f"M64 P{pin}")
                yield INTERP_EXECUTE_FINISH

        elif tool_number == 18:
            print("Activating T18 (Vertical X Spindles)")
            for pin in [5, 6, 7, 8, 9]:
                self.execute(f"M64 P{pin}")
                yield INTERP_EXECUTE_FINISH

        elif tool_number in simple_tools:
            info = simple_tools[tool_number]
            if not (info.get("shared_pin") and previous_tool == info.get("paired_tool")):
                print(f"Activating {info['name']}")
                self.execute(f"M64 P{info['down_pin']}")
                yield INTERP_EXECUTE_FINISH

        # --- Finalize Tool Change State ---
        self.current_tool = tool_number
        self.selected_tool = -1
        self.toolchange_flag = True
        
        # Track last router tool used (T20+) for safe zone movement logic
        if is_router:
            self.last_router_tool = tool_number

        # --- Apply Tool Offsets ---
        stat.poll()
        tool_data = next((t for t in stat.tool_table if t.id == tool_number), None)
        if not tool_data:
            print(f"❌ Tool ID {tool_number} not found in tool table.")
            yield INTERP_ERROR
        else:
            # Use tool's own offsets for tool length compensation (X, Y, Z, diameter)
            x = tool_data.xoffset
            y = tool_data.yoffset
            z = tool_data.zoffset
            d = tool_data.diameter
            r = d / 2 if d else 0
            g10_cmd = f"G10 L1 P{tool_number} X{x} Y{y} Z{z} R{r}"
            print(f"Applying tool offsets: {g10_cmd}")

            if tool_number <= 0:
                print(f"Invalid tool number for G10: {tool_number}")
                yield INTERP_ERROR
            else:
                self.execute(g10_cmd)
                self.execute(f"G43 H{tool_number}")
                yield INTERP_EXECUTE_FINISH

                # Now tell LinuxCNC this is the active tool
                emccanon.CHANGE_TOOL(tool_number)
        
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
    
    # Get current tool from LinuxCNC stat (more reliable than self.current_tool)
    current_tool = stat.tool_in_spindle
    if current_tool <= 0:
        # Fallback to self.current_tool if stat doesn't have a tool
        current_tool = getattr(self, "current_tool", 0)
    
    # Only activate motor for tools 1-19 (not router T20+)
    if 1 <= current_tool <= 19:
        print(f"Activating Motor (P17) for T{current_tool}")
        self.execute("M64 P17")
        yield INTERP_EXECUTE_FINISH
    
    yield INTERP_OK

def remap_m5(self, **params):
    """Handle M5 (spindle off) command"""
    import linuxcnc
    stat = linuxcnc.stat()
    stat.poll()
    
    # Get current tool from LinuxCNC stat (more reliable than self.current_tool)
    current_tool = stat.tool_in_spindle
    if current_tool <= 0:
        # Fallback to self.current_tool if stat doesn't have a tool
        current_tool = getattr(self, "current_tool", 0)
    
    # Deactivate motor for tools 1-19 (not router T20+)
    if 1 <= current_tool <= 19:
        print(f"Deactivating Motor (P17) for T{current_tool}")
        self.execute("M65 P17")
        yield INTERP_EXECUTE_FINISH
    
    yield INTERP_OK

# ============================================================================
# HORIZONTAL BIT AXIS TRANSFORMATION
# ============================================================================
# This section handles automatic axis swapping for horizontal bits.
# This allows ANY post-processor to be used - the transformation happens
# automatically at the LinuxCNC level, making it foolproof and machine-specific
# rather than post-processor-specific.
#
# Horizontal Y-bits (T11-T14): Swap Y↔Z (bits drill along Y-axis)
# Horizontal X-bits (T15-T16): Swap X↔Z (bits drill along X-axis)
#
# When a horizontal bit is active, this prolog function intercepts G0/G1/G2/G3
# motion commands and swaps the appropriate axes before execution.
# ============================================================================

# Horizontal Y-bit tools that require Y↔Z axis swap
HORIZONTAL_Y_BITS = [11, 12, 13, 14]

# Horizontal X-bit tools that require X↔Z axis swap
HORIZONTAL_X_BITS = [15, 16]

def motion_prolog(self, **words):
    """
    Prolog for G0/G1/G2/G3 motion commands.
    - Saw blade (T19) safety: When blade is below material surface, only allow Y movement
    - Swaps axes when horizontal bits are active:
      - T11-T14 (Horizontal Y-bits): Swap Y↔Z
      - T15-T16 (Horizontal X-bits): Swap X↔Z
    
    This allows any post-processor to output standard g-code - the transformation
    happens automatically at the LinuxCNC level. This is the foolproof approach
    that works regardless of which CAM software or post-processor is used.
    
    Usage: Add to Rover13s.ini:
        REMAP=G0 modalgroup=1 prolog=motion_prolog
        REMAP=G1 modalgroup=1 prolog=motion_prolog
        REMAP=G2 modalgroup=1 prolog=motion_prolog
        REMAP=G3 modalgroup=1 prolog=motion_prolog
    """
    if self.task == 0:  # Preview interpreter - skip transformation
        return INTERP_OK
    
    import linuxcnc
    stat = linuxcnc.stat()
    stat.poll()
    
    tool_number = stat.tool_in_spindle
    
    # Get current block
    c = self.blocks[self.remap_level]
    
    # ========================================================================
    # SAW BLADE (T19) SAFETY CHECK
    # When blade is below material surface, restrict dangerous movements
    # Blade doesn't swivel, so X movement and circular moves when engaged are dangerous
    # Z movement and Y± movement are allowed (for depth changes and cleanup passes)
    # ========================================================================
    if tool_number == 19:  # Saw blade
        # Get current Z position (work coordinates)
        current_z = stat.position[2]  # Z position in work coordinates
        
        # Material surface is typically at Z=0 in work coordinates
        # Blade is engaged if Z < 0 (below material surface)
        # You can adjust this threshold if needed (e.g., Z < 0.5 for safety margin)
        MATERIAL_SURFACE_Z = 0.0  # Z=0 is typically the material surface
        blade_engaged = current_z < MATERIAL_SURFACE_Z
        
        if blade_engaged:
            # Blade is below material surface - restrict dangerous movements
            # Allow: Y movement (both directions for cleanup passes), Z movement (for depth changes)
            # Block: X movement (sideways movement is dangerous), circular moves (G2/G3)
            
            # Check for X movement - block it (sideways movement is dangerous)
            if c.x_flag:
                error_msg = f"⚠️ SAW BLADE SAFETY: X movement blocked! Blade is engaged (Z={current_z:.3f} < {MATERIAL_SURFACE_Z}). X movement is not allowed when blade is below material surface."
                print(error_msg)
                self.set_errormsg(error_msg)
                return INTERP_ERROR
            
            # Block circular moves (G2/G3) when blade is engaged
            # Circular moves have I, J, or K parameters (arc center offsets)
            if c.i_flag or c.j_flag or c.k_flag:
                error_msg = f"⚠️ SAW BLADE SAFETY: Circular moves (G2/G3) blocked! Blade is engaged (Z={current_z:.3f} < {MATERIAL_SURFACE_Z}). Only straight linear movement allowed when blade is below material surface."
                print(error_msg)
                self.set_errormsg(error_msg)
                return INTERP_ERROR
            
            # Z movement is allowed (for depth changes)
            # Y movement is allowed in both directions (for cleanup passes)
        
        # If blade is not engaged (above material surface), allow all movements
        # Continue to horizontal bit transformations below
    
    # Check if current tool is a horizontal bit
    is_horizontal_y = tool_number in HORIZONTAL_Y_BITS
    is_horizontal_x = tool_number in HORIZONTAL_X_BITS
    
    if not (is_horizontal_y or is_horizontal_x):
        return INTERP_OK  # No transformation needed
    
    # Handle horizontal Y-bits (T11-T14): Swap Y↔Z
    if is_horizontal_y:
        # Swap Y and Z coordinates
        if c.y_flag and c.z_flag:
            # Both Y and Z present - swap them
            temp = c.y_number
            c.y_number = c.z_number
            c.z_number = temp
            if hasattr(self, 'debug') and self.debug:
                print(f"🔄 [T{tool_number}] Swapped Y↔Z: Y{c.z_number:.3f} Z{c.y_number:.3f}")
        elif c.y_flag:
            # Only Y present - move to Z
            c.z_flag = True
            c.z_number = c.y_number
            c.y_flag = False
            c.y_number = 0
            if hasattr(self, 'debug') and self.debug:
                print(f"🔄 [T{tool_number}] Moved Y→Z: Z{c.z_number:.3f}")
        elif c.z_flag:
            # Only Z present - move to Y
            c.y_flag = True
            c.y_number = c.z_number
            c.z_flag = False
            c.z_number = 0
            if hasattr(self, 'debug') and self.debug:
                print(f"🔄 [T{tool_number}] Moved Z→Y: Y{c.y_number:.3f}")
        
        # For circular moves (G2/G3), also swap J and K (arc center offsets)
        if c.j_flag and c.k_flag:
            temp = c.j_number
            c.j_number = c.k_number
            c.k_number = temp
            if hasattr(self, 'debug') and self.debug:
                print(f"🔄 [T{tool_number}] Swapped J↔K: J{c.k_number:.3f} K{c.j_number:.3f}")
        elif c.j_flag:
            c.k_flag = True
            c.k_number = c.j_number
            c.j_flag = False
            c.j_number = 0
        elif c.k_flag:
            c.j_flag = True
            c.j_number = c.k_number
            c.k_flag = False
            c.k_number = 0
    
    # Handle horizontal X-bits (T15-T16): Swap X↔Z
    if is_horizontal_x:
        # Swap X and Z coordinates
        if c.x_flag and c.z_flag:
            # Both X and Z present - swap them
            temp = c.x_number
            c.x_number = c.z_number
            c.z_number = temp
            if hasattr(self, 'debug') and self.debug:
                print(f"🔄 [T{tool_number}] Swapped X↔Z: X{c.z_number:.3f} Z{c.x_number:.3f}")
        elif c.x_flag:
            # Only X present - move to Z
            c.z_flag = True
            c.z_number = c.x_number
            c.x_flag = False
            c.x_number = 0
            if hasattr(self, 'debug') and self.debug:
                print(f"🔄 [T{tool_number}] Moved X→Z: Z{c.z_number:.3f}")
        elif c.z_flag:
            # Only Z present - move to X
            c.x_flag = True
            c.x_number = c.z_number
            c.z_flag = False
            c.z_number = 0
            if hasattr(self, 'debug') and self.debug:
                print(f"🔄 [T{tool_number}] Moved Z→X: X{c.x_number:.3f}")
        
        # For circular moves (G2/G3), also swap I and K (arc center offsets)
        if c.i_flag and c.k_flag:
            temp = c.i_number
            c.i_number = c.k_number
            c.k_number = temp
            if hasattr(self, 'debug') and self.debug:
                print(f"🔄 [T{tool_number}] Swapped I↔K: I{c.k_number:.3f} K{c.i_number:.3f}")
        elif c.i_flag:
            c.k_flag = True
            c.k_number = c.i_number
            c.i_flag = False
            c.i_number = 0
        elif c.k_flag:
            c.i_flag = True
            c.i_number = c.k_number
            c.k_flag = False
            c.k_number = 0
    
    return INTERP_OK
    