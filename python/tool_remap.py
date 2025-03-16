import linuxcnc
import time

def check_router_state(expected_state, timeout=2.0):
    """
    Checks whether the router is in the expected position.
    expected_state: "up" or "down"
    timeout: Maximum time (seconds) to wait for confirmation.
    """
    stat = linuxcnc.stat()
    start_time = time.time()

    while time.time() - start_time < timeout:
        stat.poll()
        router_up = bool(stat.din_bits[2])   # motion.digital-in-02
        router_down = bool(stat.din_bits[3]) # motion.digital-in-03

        if expected_state == "up" and router_up:
            return True
        if expected_state == "down" and router_down:
            return True

        time.sleep(0.1)

    print(f"ERROR: Router did not reach expected {expected_state} state in {timeout} seconds.")
    return False

def check_tool_locked(timeout=2.0):
    """
    Checks if the tool is locked and present.
    timeout: Maximum time (seconds) to wait for confirmation.
    """
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

def remap_m6(prolog, params=None):
    """
    Remap M6 to handle tool changes with router verification.
    """
    cmd = linuxcnc.command()
    stat = linuxcnc.stat()
    
    tool_number = int(params.get('tool', 0))  # Extract tool number

    try:
        if tool_number == 18:  # Router tool is selected
            stat.poll()
            router_down = bool(stat.din_bits[3])  # Check if router is already down

            if not router_down:
                print("Lowering Router: Activating P13")
                cmd.mdi("M64 P13")  # Drop router (P13)

                if not check_router_state("down"):
                    print("ERROR: Router did not confirm down position!")
                    return

            # Verify that the tool is locked before proceeding
            print("Checking if tool is locked and present...")
            if not check_tool_locked():
                print("ERROR: Tool is not locked! Aborting operation.")
                return

        # Execute standard M6 tool change
        cmd.mdi("M6")

        if tool_number == 18:
            print("Raising Router: Activating P14")
            cmd.mdi("M65 P14")  # Raise router (P14)

            if not check_router_state("up"):
                print("ERROR: Router did not confirm up position!")
                return

    except Exception as e:
        print(f"Error in remap_m6: {e}")

    return
