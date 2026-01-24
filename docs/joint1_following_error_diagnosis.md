# Joint 1 (Y Axis) Following Error Diagnosis

## Issue Summary
Random "Joint 1 following error" occurring after ~15 minutes of operation. The error appears to cause a polarity flip on the Y axis. A full PC reboot temporarily resolves the issue.

## Critical Fix Applied

### Missing Analog Enable Connection
**Problem Found:** The Y axis was missing the critical `analogena` connection that enables all analog outputs on the Mesa 7i77 card.

**Fix Applied:**
- Created proper OR gate logic to combine X, Y, and Z axis enables
- Connected the OR'd enable signal to `analogena` (which enables ALL analog outputs on the 7i77 card)
- Fixed missing direction arrows (`<=`) in `y-pos-cmd`, `y-enable`, `z-pos-cmd`, and `z-enable` net connections

**What This Fixes:**
The `analogena` signal is a card-level enable that controls ALL analog outputs on the Mesa 7i77 card. Since X, Y, and Z all use analog outputs on the same card (`hm2_7i96s.0.7i77.0.1`), they must share the same `analogena` signal. Without proper enable logic, the Y axis analog output may not be properly enabled, causing:
- Intermittent operation
- Polarity reversals
- Following errors
- Unpredictable behavior after extended operation

**Technical Details:**
- X axis uses `analogout0`, Y axis uses `analogout1`, Z axis uses `analogout2`
- All three share the same `analogena` signal on the 7i77 card
- The fix properly ORs all three axis enables together before driving `analogena`

## Additional Diagnostic Steps

### 1. Verify HAL File Changes
After restarting LinuxCNC, verify the connections are correct:
```bash
halcmd show net y-enable
halcmd show net y-pos-cmd
halcmd show pin hm2_7i96s.0.7i77.0.1.analogena
```

### 2. Monitor Following Error in Real-Time
Use HALscope or halshow to monitor:
- `joint.1.f-error` - Following error value
- `joint.1.motor-pos-cmd` - Commanded position
- `joint.1.motor-pos-fb` - Feedback position
- `pid.y.output` - PID output
- `hm2_7i96s.0.encoder.01.position` - Raw encoder position

### 3. Check Ethernet Communication
The Mesa 7i96s is connected via Ethernet (10.10.10.10, 10.10.10.11). Monitor for:
- Network packet loss
- Communication timeouts
- Watchdog timeouts

Check the LinuxCNC log files for communication errors:
```bash
tail -f /var/log/linuxcnc.log
```

### 4. Verify Encoder Connections
The Y axis encoder (encoder.01) may have:
- Loose connections
- Damaged cable
- Electrical interference
- Thermal issues (cable or encoder heating up)

**Test:** Monitor `hm2_7i96s.0.encoder.01.rawcounts` - it should increment/decrement smoothly. Any jumps or reversals indicate encoder issues.

### 5. Check PID Tuning
Current Y axis PID settings:
- P = 2.0
- I = 0.01
- D = 0.0
- FF1 = 0.004

**Potential Issue:** The I gain (0.01) might cause integrator windup over time, especially if there's any steady-state error. Consider:
- Adding integrator anti-windup
- Reducing I gain if following errors persist
- Monitoring `pid.y.integral` for excessive values

### 6. Monitor Following Error Thresholds
Current settings:
- `FERROR = 3.0` (following error limit)
- `MIN_FERROR = 0.5` (minimum following error)

If errors persist, temporarily increase `FERROR` to 4.0 or 5.0 to see if it's a threshold issue, but this is a workaround, not a fix.

### 7. Check for Electrical Noise
After 15 minutes, components may heat up and:
- Increase electrical noise
- Change signal characteristics
- Cause ground loops

**Test:** 
- Check encoder cable routing (should be away from motor power cables)
- Verify proper grounding
- Check for loose connections

### 8. Verify Motor Driver
The Y axis motor driver may have:
- Thermal protection kicking in
- Fault conditions
- Loose connections

Check the `y-axis-ok` signal in `rover-custom.hal` (input-05) - this should remain true during operation.

### 9. Communication Timeout Settings
Current settings:
- `COMM_TIMEOUT = 1.0` seconds
- Watchdog timeout = 5ms (5000000 ns)

If Ethernet communication is intermittent, consider:
- Increasing `COMM_TIMEOUT` to 2.0 seconds
- Checking network cable quality
- Verifying network switch/router stability

### 10. Thermal Monitoring
Since the issue occurs after ~15 minutes, monitor:
- Mesa card temperature
- Motor driver temperature
- Encoder temperature
- Cable temperatures

## Testing After Fix

1. **Restart LinuxCNC** completely (not just reload HAL)
2. **Home all axes** to verify proper operation
3. **Run a test program** for at least 20-30 minutes
4. **Monitor** the following error continuously:
   ```bash
   watch -n 0.1 'halcmd getp joint.1.f-error'
   ```

## If Issue Persists

If the problem continues after the HAL fix, check in order:

1. **Encoder cable** - Replace or reseat Y axis encoder cable
2. **Encoder itself** - Test with a known-good encoder
3. **Motor driver** - Check for thermal issues or faults
4. **Network connection** - Test Ethernet cable and switch
5. **Mesa card** - May need firmware update or replacement
6. **PID tuning** - May need retuning for current conditions

## Logging for Diagnosis

Enable detailed logging:
```bash
# In Rover13s.ini, increase debug level:
[EMCMOT]
DEBUG = 1

# Monitor real-time:
halcmd setp motion.debug 1
```

Check LinuxCNC messages window for detailed error information when the fault occurs.

## Expected Behavior After Fix

After applying the fix:
- Y axis should operate consistently
- No random polarity flips
- Following errors should only occur during actual following errors (not false triggers)
- No need for PC reboots to restore operation

