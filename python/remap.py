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

        # Tool-specific logic
        if tool_number == 18:  # Router tool
            print("Handling Router Tool (T18)")
            router_down = bool(stat.din[3])  # motion.digital-in-03

            if not router_down:
                print("Lowering Router: Activating P13")
                cmd.mdi("M64 P13")  # Drop router (P13)

        elif tool_number == 17:  # Saw Blade tool
            print("Handling Saw Blade Tool (T17)")
            blade_down = bool(stat.din[1])  # motion.digital-in-01

            if not blade_down:
				# print("Release Raise Saw Blade: Activating P15")
                # cmd.mdi("M65 P15")  # Drop saw blade (P15)
                print("Lowering Saw Blade: Activating P16")
                cmd.mdi("M64 P16")  # Drop saw blade (P16)
				

        print(f"Tool change completed successfully. Tool {tool_number} is now active.")
        return INTERP_OK  

    except Exception as e:
        print(f"Error in remap_m6: {e}")
        return INTERP_ERROR
