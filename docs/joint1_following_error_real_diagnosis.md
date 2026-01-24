# Joint 1 (Y Axis) Following Error - Real Root Cause Analysis

## Issue Pattern
- **Works fine for ~15 minutes**, then fails
- **Joint 1 (Y axis) following error** occurs
- **Appears to "flip polarity"** - axis moves in wrong direction
- **Full PC reboot fixes it temporarily**
- **Other axes (X, Z) are fine**

This pattern strongly suggests **thermal, electrical noise, or communication issues** that develop over time, NOT configuration problems.

## Most Likely Causes (in order of probability)

### 1. **Ethernet Communication Timeout/Interference** ⚠️ HIGH PROBABILITY
**Why:** Mesa 7i96s uses Ethernet (10.10.10.10, 10.10.10.11). After 15 minutes:
- Network switch/router may heat up and become unstable
- Ethernet cable may have thermal issues
- Packet loss increases with temperature
- `COMM_TIMEOUT = 1.0` seconds may be too short if network degrades

**Symptoms match:**
- Intermittent failures
- Reboot fixes it (resets network stack)
- Only affects one axis (Y axis encoder data on specific channel)

**Diagnosis:**
```bash
# Monitor network statistics
watch -n 1 'cat /proc/net/dev | grep eth0'

# Check for packet errors
ethtool -S eth0 | grep -i error

# Monitor Mesa communication
halcmd show pin hm2_7i96s.0.status
halcmd show pin hm2_7i96s.0.watchdog
```

**Fix:**
- Increase `COMM_TIMEOUT` to 2.0 or 3.0 seconds in `Rover13s.ini`
- Replace Ethernet cable (use shielded Cat6)
- Check network switch/router for thermal issues
- Consider using a dedicated network switch (not shared with other devices)

### 2. **Encoder Signal Degradation (Electrical Noise)** ⚠️ HIGH PROBABILITY
**Why:** After 15 minutes, electrical noise increases:
- Motor drivers heat up → more electrical noise
- Encoder cable may be picking up interference
- Ground loops develop with temperature changes
- Encoder filter (currently `filter = 1`) may be insufficient

**Symptoms match:**
- "Polarity flip" = encoder counts jumping/reversing
- Only Y axis affected = Y encoder cable/connection issue
- Thermal related = noise increases with temperature

**Diagnosis:**
```bash
# Monitor raw encoder counts - should be smooth, no jumps
halcmd show pin hm2_7i96s.0.encoder.01.rawcounts

# Watch for sudden jumps or reversals
watch -n 0.1 'halcmd getp hm2_7i96s.0.encoder.01.rawcounts'
```

**Fix:**
- Increase encoder filter: `setp hm2_7i96s.0.encoder.01.filter 2` or `3`
- Check Y axis encoder cable routing (away from motor power cables)
- Verify encoder cable shielding is properly grounded
- Check for loose encoder connections
- Consider replacing Y axis encoder cable

### 3. **PID Integrator Windup** ⚠️ MEDIUM PROBABILITY
**Why:** Current Y axis PID settings:
- `I = 0.01` (integrator gain)
- `D = 0.0` (no derivative)
- Over 15 minutes, any steady-state error accumulates in the integrator

**Symptoms match:**
- Builds up over time
- Causes following error
- Can cause "wrong direction" if integrator saturates

**Diagnosis:**
```bash
# Monitor PID integrator value
halcmd show pin pid.y.integral

# Should stay reasonable, not grow unbounded
watch -n 1 'halcmd getp pid.y.integral'
```

**Fix:**
- Add integrator anti-windup (if PID component supports it)
- Reduce I gain: `I = 0.005` or `0.002`
- Add D gain: `D = 0.1` to help with stability
- Monitor `pid.y.output` - should not saturate

### 4. **Motor Driver Thermal Protection** ⚠️ MEDIUM PROBABILITY
**Why:** Y axis motor driver may be:
- Overheating after 15 minutes
- Entering thermal protection mode
- Losing enable signal intermittently

**Symptoms match:**
- Thermal related (15 minute delay)
- Only Y axis affected
- "Polarity flip" could be driver fault mode

**Diagnosis:**
- Check `y-axis-ok` signal: `halcmd getp hm2_7i96s.0.7i77.0.0.input-05`
- Monitor motor driver temperature (if accessible)
- Check for fault LEDs on Y axis driver
- Verify Y axis driver cooling/fan operation

**Fix:**
- Improve Y axis motor driver cooling
- Check driver mounting/thermal paste
- Verify driver is not overloaded
- Check for loose power connections

### 5. **Mesa Card Thermal Issues** ⚠️ LOW-MEDIUM PROBABILITY
**Why:** Mesa 7i96s card may be:
- Overheating after extended operation
- Losing communication with encoder.01 channel
- FPGA timing issues with temperature

**Diagnosis:**
- Monitor Mesa card temperature (if accessible)
- Check for cooling issues
- Monitor watchdog timeouts: `halcmd getp hm2_7i96s.0.watchdog.timeout`

**Fix:**
- Improve Mesa card cooling
- Check card mounting/thermal management
- Verify power supply is stable

## Immediate Diagnostic Steps

### Step 1: Monitor During Failure
When the error occurs, immediately check:
```bash
# Following error value
halcmd getp joint.1.f-error

# Encoder position vs commanded
halcmd getp joint.1.motor-pos-cmd
halcmd getp joint.1.motor-pos-fb
halcmd getp hm2_7i96s.0.encoder.01.position

# PID output
halcmd getp pid.y.output
halcmd getp pid.y.integral

# Network/communication status
halcmd getp hm2_7i96s.0.status
```

### Step 2: Increase Encoder Filter
Try increasing the encoder filter to reduce noise:
```hal
setp hm2_7i96s.0.encoder.01.filter 2
```
Or in the HAL file, change line 146 from `filter 1` to `filter 2` or `3`.

### Step 3: Increase Communication Timeout
In `Rover13s.ini`, change:
```ini
[EMCMOT]
COMM_TIMEOUT = 2.0  # Increase from 1.0 to 2.0
```

### Step 4: Monitor Encoder Raw Counts
Set up continuous monitoring:
```bash
# Create a monitoring script
while true; do
  echo "$(date): $(halcmd getp hm2_7i96s.0.encoder.01.rawcounts) $(halcmd getp joint.1.f-error)"
  sleep 0.1
done > /tmp/y_axis_monitor.log
```

When the error occurs, check the log for encoder count jumps.

## Quick Test: Encoder Filter Increase

The fastest thing to try is increasing the encoder filter. This will help if it's electrical noise:

1. Edit `Rover13s.hal` line 146
2. Change: `setp hm2_7i96s.0.encoder.01.filter 1`
3. To: `setp hm2_7i96s.0.encoder.01.filter 2` or `3`
4. Restart LinuxCNC
5. Test for 20+ minutes

If this helps, it confirms encoder signal noise is the issue.

## Most Likely Root Cause

Based on the symptoms (15 minute delay, polarity flip, reboot fixes it), I'd bet on:
1. **Ethernet communication degradation** (60% probability)
2. **Encoder signal noise** (30% probability)  
3. **PID integrator windup** (10% probability)

Start with increasing the encoder filter and communication timeout - these are the easiest to test and most likely to help.

