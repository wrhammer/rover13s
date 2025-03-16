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

def remap_m6(self, **params):
    """Remap M6 to handle tool changes with verification for router (T18) and saw blade (T17)."""
    cmd = linuxcnc.command()
    stat = linuxcnc.stat()

    stat.poll()  # Ensure we have fresh data from LinuxCNC

    # Retrieve the selected tool from self.selected_tool instead of params
    tool_number = getattr(self, "selected_tool", -1)  # Use getattr to prevent crashes

    if tool_number < 1:
        print("ERROR: No valid tool number received from change_prolog.")
        return INTERP_ERROR

    try:
        print(f"Executing tool change to Tool {tool_number}")

        # Store current tool for later
        previous_tool = stat.tool_in_spindle

        # First, retract any currently active tools
        blade_up = bool(stat.din[0])  # motion.digital-in-00
        blade_down = bool(stat.din[1])  # motion.digital-in-01
        router_up = bool(stat.din[2])  # motion.digital-in-02
        router_down = bool(stat.din[3])  # motion.digital-in-03

        # Define simple tools (those without position feedback)
        simple_tools = {
            1: {"down_pin": 0, "name": "V-Y-Spindle-1"},  # motion.digital-out-00
            2: {"down_pin": 1, "name": "V-Y-Spindle-2"},  # motion.digital-out-01
            3: {"down_pin": 2, "name": "V-Y-Spindle-3"},  # motion.digital-out-02
            4: {"down_pin": 3, "name": "V-Y-Spindle-4"},  # motion.digital-out-03
            5: {"down_pin": 4, "name": "V-Y-Spindle-5"},  # motion.digital-out-04
            6: {"down_pin": 5, "name": "V-X-Spindle-6"},  # motion.digital-out-05
            7: {"down_pin": 6, "name": "V-X-Spindle-7"},  # motion.digital-out-06
            8: {"down_pin": 7, "name": "V-X-Spindle-8"},  # motion.digital-out-07
            9: {"down_pin": 8, "name": "V-X-Spindle-9"},  # motion.digital-out-08
            10: {"down_pin": 9, "name": "V-X-Spindle-10"},  # motion.digital-out-09
            11: {"down_pin": 10, "name": "H-X-Spindle-11"},  # motion.digital-out-10
            12: {"down_pin": 11, "name": "H-X-Spindle-12"},  # motion.digital-out-11
            13: {"down_pin": 12, "name": "H-X-Spindle-13"},  # motion.digital-out-12
            14: {"down_pin": 13, "name": "H-X-Spindle-14"},  # motion.digital-out-13
            15: {"down_pin": 14, "name": "H-Y-Spindle-15"},  # motion.digital-out-14
            16: {"down_pin": 15, "name": "H-Y-Spindle-16"},  # motion.digital-out-15      
            # Add more tools here in the same format:
            # tool_number: {"down_pin": pin_number, "name": "Tool Name"}
        }

        # Retract all simple tools if they're not the selected tool
        for tool_id, tool_info in simple_tools.items():
            if tool_number != tool_id:
                print(f"Retracting {tool_info['name']}")
                cmd.mdi(f"M65 P{tool_info['down_pin']}")  # Release the down command

        # Handle router position when not selected
        if tool_number != 18:  # If router is not the selected tool
            if router_down:  # If router is down, retract it
                print("Retracting Router")
                cmd.mdi("M65 P13")  # Deactivate router down
            
            if not router_up:  # If router is not up, raise it
                print("Raising Router: Activating P14")
                cmd.mdi("M64 P14")  # Raise router
            elif router_up:  # If router is already up, release the raise command
                print("Router already up: Releasing P14")
                cmd.mdi("M65 P14")  # Release router up command
        
        # Handle saw blade position when not selected
        if tool_number != 17:  # If saw blade is not the selected tool
            if blade_down:  # If blade is down, retract it
                print("Retracting Saw Blade")
                cmd.mdi("M65 P16")  # Deactivate blade down
            
            if not blade_up:  # If blade is not up, raise it
                print("Raising Saw Blade: Activating P15")
                cmd.mdi("M64 P15")  # Raise saw blade
            elif blade_up:  # If blade is already up, release the raise command
                print("Saw Blade already up: Releasing P15")
                cmd.mdi("M65 P15")  # Release saw blade up command

        # Handle simple tool activation
        if tool_number in simple_tools:
            tool_info = simple_tools[tool_number]
            print(f"Activating {tool_info['name']}")
            cmd.mdi(f"M64 P{tool_info['down_pin']}")  # Activate tool down command

        # Tool-specific activation logic with position verification
        elif tool_number == 18:  # Router tool
            print("Handling Router Tool (T18)")
            if not router_down:
                print("Lowering Router: Activating P13")
                cmd.mdi("M64 P13")  # Drop router (P13)
                if router_up:  # If router was up, release the up command
                    print("Releasing router up command")
                    cmd.mdi("M65 P14")
                
                # Verify router has reached down position
                max_wait = 5  # Maximum wait time in seconds
                wait_start = time.time()
                while time.time() - wait_start < max_wait:
                    stat.poll()
                    if bool(stat.din[3]):  # Check router_down sensor
                        print("Router successfully reached down position")
                        break
                    time.sleep(0.1)  # Check every 100ms
                else:  # This runs if the while loop completes without breaking
                    print("WARNING: Router may not have reached down position within timeout")
                    return INTERP_ERROR

        elif tool_number == 17:  # Saw Blade tool
            print("Handling Saw Blade Tool (T17)")
            if not blade_down:
                print("Lowering Saw Blade: Activating P16")
                cmd.mdi("M64 P16")  # Drop saw blade (P16)
                if blade_up:  # If blade was up, release the up command
                    print("Releasing saw blade up command")
                    cmd.mdi("M65 P15")
                
                # Verify saw blade has reached down position
                max_wait = 5  # Maximum wait time in seconds
                wait_start = time.time()
                while time.time() - wait_start < max_wait:
                    stat.poll()
                    if bool(stat.din[1]):  # Check blade_down sensor
                        print("Saw Blade successfully reached down position")
                        break
                    time.sleep(0.1)  # Check every 100ms
                else:  # This runs if the while loop completes without breaking
                    print("WARNING: Saw Blade may not have reached down position within timeout")
                    return INTERP_ERROR

        # Update tool information in LinuxCNC
        cmd.mode(linuxcnc.MODE_MDI)
        cmd.wait_complete()
        
        # Change to the new tool
        cmd.change_tool(tool_number)
        cmd.wait_complete()
        
        # Load the tool offsets
        cmd.mdi(f"G43 H{tool_number}")  # Apply tool length offset
        cmd.wait_complete()

        print(f"Tool change completed successfully. Changed from T{previous_tool} to T{tool_number}.")
        print(f"Current tool position: X{stat.position[0]:.3f} Y{stat.position[1]:.3f}")
        return INTERP_OK  

    except Exception as e:
        print(f"Error in remap_m6: {e}")
        return INTERP_ERROR
