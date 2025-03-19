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
                    "name": tool.comment or f"Tool-{tool_num}"
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
                    "name": tool.comment or f"Tool-{tool_num}",
                    "shared_pin": True,
                    "paired_tool": mapping["pair"]
                }
                break
    
    return simple_tools

def remap_m6(self, **params):
    """Remap M6 to handle tool changes with verification for router (T18) and saw blade (T17)."""
    cmd = linuxcnc.command()
    stat = linuxcnc.stat()
    previous_tool = stat.tool_in_spindle

    stat.poll()  # Ensure we have fresh data from LinuxCNC

    # Retrieve the selected tool from self.selected_tool instead of params
    tool_number = getattr(self, "selected_tool", -1)  # Use getattr to prevent crashes

    if tool_number < 1:
        print("ERROR: No valid tool number received from change_prolog.")
        return INTERP_ERROR

    try:
        print(f"Executing tool change to Tool {tool_number}")

        # First, retract any currently active tools
        blade_up = bool(stat.din[0])  # motion.digital-in-00
        blade_down = bool(stat.din[1])  # motion.digital-in-01
        router_up = bool(stat.din[2])  # motion.digital-in-02
        router_down = bool(stat.din[3])  # motion.digital-in-03

        # Get the current simple tools from the tool table
        simple_tools = get_simple_tools()

        # Fixed Indentation Her
        if previous_tool in simple_tools and previous_tool != tool_number:
            prev_tool_info = simple_tools[previous_tool]
            # Only retract if we're not switching to a tool that shares the same pin
            if not (prev_tool_info.get("shared_pin") and tool_number == prev_tool_info.get("paired_tool")):
                print(f"Retracting {prev_tool_info['name']}")
                cmd.mdi(f"M65 P{prev_tool_info['down_pin']}")  # Release the previous tool's down command
                cmd.wait_complete()

        # T18 (Router) - Logic Restored
        if previous_tool == 18 and previous_tool != tool_number:  
            if router_down:  
                print("Retracting Router")
                cmd.mdi("M65 P13")  
                cmd.wait_complete()
            
            if not router_up:
                print("Raising Router: Activating P14")
                cmd.mdi("M64 P14")  
            elif router_up:
                print("Router already up: Releasing P14")
                cmd.mdi("M65 P14")  

        # T17 (Saw Blade) - Logic Restored
        if previous_tool == 17 and previous_tool != tool_number:
            if blade_down:
                print("Retracting Saw Blade")
                cmd.mdi("M65 P16")  
                cmd.wait_complete()
            
            if not blade_up:
                print("Raising Saw Blade: Activating P15")
                cmd.mdi("M64 P15")  
            elif blade_up:
                print("Saw Blade already up: Releasing P15")
                cmd.mdi("M65 P15")  

        # Activate new tool
        if tool_number in simple_tools:
            tool_info = simple_tools[tool_number]
            # Only activate if we're not already using this pin (in case of shared pins)
            if not (tool_info.get("shared_pin") and 
                   previous_tool == tool_info.get("paired_tool")):
                print(f"Activating {tool_info['name']}")
                cmd.mdi(f"M64 P{tool_info['down_pin']}")
                cmd.wait_complete()

        # Execute the manual tool change
        print(f"Manual tool change: Please change to Tool {tool_number}")
        emccanon.CHANGE_TOOL_NUMBER(tool_number)  # This updates LinuxCNC's internal state
        self.current_tool = tool_number
        self.selected_tool = -1  # Reset selection after change
        self.toolchange_flag = True
        
        # Apply all offsets from tool table using G10
        cmd.mdi(f"G10 L1 P{tool_number}")  # This loads all offsets for the tool from the tool table
        cmd.mdi("G43")  # Enable tool length compensation with the loaded offsets
        cmd.wait_complete()

        print(f"Tool change completed successfully. Changed from T{previous_tool} to T{tool_number}.")
        return INTERP_OK  

    except Exception as e:
        print(f"Error in remap_m6: {e}")
        return INTERP_ERROR
