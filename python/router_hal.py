#!/usr/bin/env python3
# Router HAL component - creates remap_router component early for HAL connections

import hal
import time

def main():
    """Create remap_router HAL component early so HAL connections can find it"""
    try:
        h = hal.component('remap_router')
        h.newpin("safe_zone", hal.HAL_BIT, hal.HAL_OUT)
        h.ready()
        print("Router HAL component initialized (standalone)")
        
        # Keep component alive
        while True:
            time.sleep(1)
    except Exception as e:
        print(f"Failed to initialize router HAL component: {e}")
        raise SystemExit

if __name__ == "__main__":
    main()

