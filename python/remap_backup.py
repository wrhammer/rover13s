import linuxcnc
import time
from interpreter import INTERP_OK, INTERP_ERROR

def change_prolog(self, **words):
    """Prolog function for tool change verification."""
    try:
        print("Running change_prolog...")

        # Check if tool change is already in progress
        if hasattr(self, 'tool_change_active') and self.tool_change_active:
            print("WARNING: Tool change already in progress. Skipping duplicate call.")
            return INTERP_OK  

        # Mark tool change as active
        self.tool_change_active = True

        # Ensure a tool is actually selected
        if not hasattr(self, 'selected_tool') or self.selected_tool < 1:
            self.set_errormsg("M6: No valid tool prepared.")
            self.tool_change_active = False
            return INTERP_ERROR
        
        # Store tool change parameters
        self.params["tool_in_spindle"] = self.current_tool
        self.params["selected_tool"] = self.selected_tool  # Store correct tool number!
        self.params["current_pocket"] = self.current_pocket
        self.params["selected_pocket"] = self.selected_pocket

        print(f"Tool change initiated: Tool {self.selected_tool} (Pocket {self.selected_pocket})")
        return INTERP_OK

    except Exception as e:
        print(f"Error in change_prolog: {e}")
        self.tool_change_active = False
        return INTERP_ERROR


def check_state(expected_state, input_pin, timeout=2.0):
    """Check the state of a digital input."""
    stat = linuxcnc.stat()
    start_time = time.time()

    while time.time() - start_time < timeout:
        stat.poll()
        state = bool(stat.din_bits[input_pin])

        if expected_state == "up" and state:
            return True
        if expected_state == "down" and state:
            return True

        time.sleep(0.1)

    print(f"ERROR: Device did not reach expected {expected_state} state on input {input_pin} in {timeout} seconds.")
    return False

def check_tool_locked(timeout=2.0):
    """Checks if the tool is locked and present."""
    stat = linuxcnc.stat()
    start_time = time.time()

    while time.time() - start_time < timeout:
        stat.poll()
        tool_locked = bool(stat.din_bits[4])  # motion.digital-in-04

        if tool_locked:
            return True

        time.sleep(0.1)

    print("ERROR: Tool is not locked and present!")
    return False
from interpreter import INTERP_OK, INTERP_ERROR

def remap_m6(self, **params):
    """Remap M6 to handle tool changes with verification for router (T18) and saw blade (T17)."""
    cmd = linuxcnc.command()
    stat = linuxcnc.stat()

    # Ensure we have a valid tool number
    if "selected_tool" not in self.params or self.params["selected_tool"] < 1:
        print("ERROR: No valid tool number received from change_prolog.")
        return INTERP_ERROR

    tool_number = int(self.params["selected_tool"])  # Extract tool number safely

    try:
        print(f"Executing tool change to Tool {tool_number}")

        # Tool-specific logic
        if tool_number == 18:  # Router tool
            print("Handling Router Tool (T18)")
            stat.poll()
            router_down = bool(stat.din_bits[3])  # motion.digital-in-03

            if not router_down:
                print("Lowering Router: Activating P13")
                cmd.mdi("M64 P13")  # Drop router (P13)

                if not check_state("down", 3):
                    print("ERROR: Router did not confirm down position!")
                    return INTERP_ERROR

            if not check_tool_locked():
                print("ERROR: Router tool is not locked! Aborting.")
                return INTERP_ERROR

        elif tool_number == 17:  # Saw Blade tool
            print("Handling Saw Blade Tool (T17)")
            stat.poll()
            blade_down = bool(stat.din_bits[1])  # motion.digital-in-01

            if not blade_down:
                print("Lowering Saw Blade: Activating P16")
                cmd.mdi("M64 P16")  # Drop saw blade (P16)

                if not check_state("down", 1):
                    print("ERROR: Saw blade did not confirm down position!")
                    return INTERP_ERROR

            if not check_tool_locked():
                print("ERROR: Saw blade tool is not locked! Aborting.")
                return INTERP_ERROR

        # Execute standard M6 tool change
        cmd.mdi(f"T{tool_number} M6")  # Pass correct tool number

        if tool_number == 18:
            print("Raising Router: Activating P14")
            cmd.mdi("M65 P14")  # Raise router (P14)

            if not check_state("up", 2):
                print("ERROR: Router did not confirm up position!")
                return INTERP_ERROR

        elif tool_number == 17:
            print("Raising Saw Blade: Activating P15")
            cmd.mdi("M65 P15")  # Raise saw blade (P15)

            if not check_state("up", 0):
                print("ERROR: Saw blade did not confirm up position!")
                return INTERP_ERROR

        print(f"Tool change completed successfully. Tool {tool_number} is now active.")
        self.tool_change_active = False  # Reset tool change flag
        return INTERP_OK  

    except Exception as e:
        print(f"Error in remap_m6: {e}")
        self.tool_change_active = False  # Reset flag on error
        return INTERP_ERROR
