#   This is a component of LinuxCNC
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
from stdglue import *
import linuxcnc
import time  # Add import for sleep function
import emccanon
from itertools import count

def get_simple_tools():
    """Dynamically build the simple_tools dictionary from the tool table."""
    stat = linuxcnc.stat()
    stat.poll()
    simple_tools = {}
    
    # Iterate through possible tool numbers
    for tool_num in range(1, 17):
        # Check if tool exists in tool table
        for tool in stat.tool_table:
            if tool.id == tool_num:
                # Map tool numbers 1-16 to pins 0-15
                down_pin = tool_num - 1
                simple_tools[tool_num] = {
                    "down_pin": down_pin,
                    "name": tool.comment or f"Tool-{tool_num}"  # Use tool comment from tool table, fallback to generic name
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

        # Fixed Indentation Here
        if previous_tool in simple_tools and previous_tool != tool_number:
            prev_tool_info = simple_tools[previous_tool]
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
