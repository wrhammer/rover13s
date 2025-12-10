# Horizontal Bits Offset Verification Checklist

## Purpose
This checklist helps verify that the horizontal X-bit offsets in `tool.tbl` are correct for your machine setup.

## Current Tool Table Values

```
T11: X+32.0mm, Y-119.0mm, Z+46.35mm (Horizontal X Bit A1)
T12: X+32.0mm, Y-9.0mm,   Z+46.35mm (Horizontal X Bit A2)
T13: X+64.0mm, Y-119.0mm, Z+46.35mm (Horizontal X Bit B1)
T14: X+64.0mm, Y-9.0mm,   Z+46.35mm (Horizontal X Bit B2)
```

## Verification Steps

### Step 1: Physical Inspection
- [ ] Locate the horizontal X-bits on your machine
- [ ] Identify which physical bit corresponds to which tool number (T11-T14)
- [ ] Note the physical mounting positions relative to machine origin

### Step 2: Z-Offset Verification (Most Critical)

The Z offset of +46.35mm means the horizontal bit's cutting centerline is 46.35mm above the machine's Z=0 reference.

**Test Procedure:**
1. [ ] Home the machine (G28 or home sequence)
2. [ ] Place a test block on the table at a known location
3. [ ] Set a work coordinate system (G54) with origin on the table surface (Z=0 at table)
4. [ ] Load T11 (or T13) with `T11 M6`
5. [ ] Use MDI to move to a position where the bit should touch the test block:
   ```
   G54
   G0 X[test_x] Y[test_y] Z0
   ```
6. [ ] Manually jog the bit to touch the test block
7. [ ] Read the current Z position from the DRO
8. [ ] **Expected**: The DRO should show approximately Z=46.35mm when the bit centerline is at the table surface
9. [ ] **If different**: Adjust the Z offset in `tool.tbl` accordingly

**Example Calculation:**
- If the bit centerline is at the table when DRO shows Z=45.0mm, then the offset should be +45.0mm
- If the bit centerline is at the table when DRO shows Z=48.0mm, then the offset should be +48.0mm

### Step 3: X-Offset Verification

The X offsets position the bits along the X-axis relative to machine origin.

**Test Procedure:**
1. [ ] Home the machine
2. [ ] Load T11 with `T11 M6`
3. [ ] Set G54 with origin at a known reference point (e.g., table corner)
4. [ ] Use MDI to move to X=0:
   ```
   G54
   G0 X0 Y0 Z50
   ```
5. [ ] Visually check if the bit is 32mm away from your G54 origin
6. [ ] Repeat for T13 (should be 64mm from origin)
7. [ ] **If positions don't match**: Adjust X offsets in `tool.tbl`

### Step 4: Y-Offset Verification

The Y offsets position the bits along the Y-axis. Note that T11/T13 are at Y=-119mm and T12/T14 are at Y=-9mm.

**Test Procedure:**
1. [ ] Home the machine
2. [ ] Load T11 with `T11 M6`
3. [ ] Set G54 with origin at a known reference point
4. [ ] Use MDI to move to Y=0:
   ```
   G54
   G0 X0 Y0 Z50
   ```
5. [ ] Check if the bit is positioned correctly relative to your workpiece area
6. [ ] **Important**: The Y offsets determine which end of your workpiece each bit can reach
7. [ ] **If positions don't match**: Adjust Y offsets in `tool.tbl`

### Step 5: Tenon Cutting Test

**Test Procedure:**
1. [ ] Set up a test piece (e.g., 100mm x 50mm x 20mm block)
2. [ ] Position it so one end is accessible to a horizontal bit
3. [ ] Set G55 work coordinate system with origin on the end face:
   - X=0: Left edge of end face
   - Y=0: Bottom edge of end face  
   - Z=0: Face of the end (where tenon will start)
4. [ ] Load T11 with `T11 M6`
5. [ ] Program a simple test cut:
   ```gcode
   G55
   T11 M6
   G43 H11
   M3 S12000
   G0 X10 Y10 Z0 (Move to start position)
   G1 Z-5 F500 (Cut 5mm deep tenon)
   G1 X20 (Cut along X)
   G1 Z0 (Retract)
   M5
   ```
6. [ ] Run the test and verify:
   - [ ] The bit cuts at the expected location on the end face
   - [ ] The tenon depth is correct (5mm in this example)
   - [ ] The bit doesn't collide with the workpiece
7. [ ] **If issues**: Adjust work coordinate system origin or tool offsets

## Common Issues and Solutions

### Issue: Bit cuts too high or too low
**Solution**: Adjust Z offset in `tool.tbl`. If bit cuts 2mm too high, reduce Z offset by 2mm.

### Issue: Bit doesn't reach workpiece end
**Solution**: Adjust Y offset. For T11/T13, if you need them closer to origin, reduce the negative Y value (e.g., change Y-119 to Y-100).

### Issue: Bit is offset left/right from expected position
**Solution**: Adjust X offset. If bit is 5mm too far right, reduce X offset by 5mm.

### Issue: Tenon depth is incorrect
**Solution**: This is usually a work coordinate system issue, not a tool offset issue. Verify your G55/G56 origin is set correctly on the end face.

## Recommended Test Sequence

1. **Start with Z-offset verification** (most critical)
2. **Then verify X/Y positions** (for workpiece accessibility)
3. **Finally test actual tenon cutting** (end-to-end verification)

## Recording Your Findings

Document any adjustments needed:

```
Tool: T11
Current Z Offset: +46.35mm
Measured Z Position: _____ mm
Adjusted Z Offset: _____ mm

Tool: T11
Current X Offset: +32.0mm
Measured X Position: _____ mm
Adjusted X Offset: _____ mm

Tool: T11
Current Y Offset: -119.0mm
Measured Y Position: _____ mm
Adjusted Y Offset: _____ mm
```

## After Verification

Once offsets are verified and adjusted:
1. [ ] Update `tool.tbl` with corrected values
2. [ ] Restart LinuxCNC to load new tool table
3. [ ] Re-run verification tests to confirm
4. [ ] Document final offset values for future reference

