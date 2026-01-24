# Joint 1 Following Error - Diagnostic Commands

Since the encoder filter parameter doesn't seem to be available, here are alternative diagnostic approaches:

## Real-Time Monitoring Commands

### Monitor Encoder Counts (Most Important)
```bash
# Watch for encoder count jumps - should be smooth
watch -n 0.1 'halcmd getp hm2_7i96s.0.encoder.01.rawcounts'
```

If you see sudden jumps or reversals when the error occurs, it's encoder signal noise.

### Monitor Following Error
```bash
# Watch following error in real-time
watch -n 0.1 'halcmd getp joint.1.f-error'
```

### Monitor Position Command vs Feedback
```bash
# See if they diverge
watch -n 0.1 'echo "Cmd: $(halcmd getp joint.1.motor-pos-cmd) Fb: $(halcmd getp joint.1.motor-pos-fb) Error: $(halcmd getp joint.1.f-error)"'
```

### Monitor PID Output
```bash
# Check if PID is saturating
watch -n 0.1 'halcmd getp pid.y.output'
```

### Monitor PID Integrator
```bash
# Check for integrator windup
watch -n 0.1 'halcmd getp pid.y.integral'
```

## When Error Occurs - Capture Data

When the error happens, immediately run:
```bash
halcmd getp joint.1.f-error
halcmd getp joint.1.motor-pos-cmd
halcmd getp joint.1.motor-pos-fb
halcmd getp hm2_7i96s.0.encoder.01.rawcounts
halcmd getp pid.y.output
halcmd getp pid.y.integral
halcmd getp hm2_7i96s.0.status
```

## Hardware Checks (Most Likely Causes)

### 1. Encoder Cable
- Check Y axis encoder cable routing - should be away from motor power cables
- Verify cable is not damaged or pinched
- Check for loose connections at encoder and Mesa card
- Try swapping X and Y encoder cables temporarily to see if problem follows the cable

### 2. Network/Ethernet
- Check Ethernet cable quality (use shielded Cat6)
- Verify network switch/router is not overheating
- Monitor for packet loss: `ethtool -S eth0 | grep -i error`
- Try a different Ethernet cable

### 3. Motor Driver
- Check Y axis motor driver for thermal issues
- Verify `y-axis-ok` signal: `halcmd getp hm2_7i96s.0.7i77.0.0.input-05`
- Check for loose power connections
- Verify driver cooling/fan operation

### 4. Grounding
- Check for proper grounding of encoder shield
- Verify no ground loops
- Check Mesa card grounding

## Alternative Software Fixes

Since encoder filter doesn't work, try:

### Reduce PID I Gain (if integrator windup)
In `Rover13s.ini`, try reducing I gain:
```ini
[JOINT_1]
I = 0.005  # Reduce from 0.01
```

### Increase Following Error Tolerance (temporary test)
```ini
[JOINT_1]
FERROR = 4.0  # Increase from 3.0 (temporary test only)
```

### Check Communication Timeout
You rejected the timeout change, but if network issues are suspected, you can test it:
```ini
[EMCMOT]
COMM_TIMEOUT = 2.0  # Test with 2.0 seconds
```

## Most Likely Root Cause

Given the symptoms (15 min delay, polarity flip, reboot fixes it), the most likely causes are:

1. **Encoder cable/connection issue** (60%) - Loose connection, damaged cable, or interference
2. **Network communication degradation** (30%) - Ethernet issues after heating
3. **Motor driver thermal issue** (10%) - Driver overheating

Start by checking the encoder cable and connections - that's the easiest to verify and most likely culprit.

