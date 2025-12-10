# Horizontal Bits Coordinate System Mapping

## The Challenge

When you create g-code in Fusion 360 for a horizontal X-bit operation, you're creating it from a "top down" perspective, but the actual cutting happens from the side. This requires understanding how Fusion's coordinate system maps to the machine's coordinate system.

## Axis Mapping for Horizontal X-Bits

For a **horizontal X-bit** (T15 or T16), the bit is oriented horizontally and cuts along the X-axis:

| Fusion 360 Axis (Top View) | Machine Axis | What It Controls |
|---------------------------|--------------|------------------|
| X (tenon depth) | **Z** | Depth of cut - bit moves in Z to control how deep the tenon is cut into the workpiece |
| Y (tenon width) | Y | Vertical position - bit moves in Y to control the height/vertical position of the tenon |
| Z (tenon length) | **X** | Cutting direction - bit moves along X to cut the tenon length |

### Visual Example

If you're cutting a tenon on the end of a piece:

```
Fusion 360 View (Top Down):
┌─────────────┐
│   Tenon     │  X = length (left to right)
│             │  Y = depth (into page)
│             │  Z = height (up/down)
└─────────────┘

Machine View (Side View):
     Y (up)
     ↑
     │  ┌─────┐
     │  │     │  ← Workpiece
     │  └─────┘
     │    ←───→ X (cutting direction)
     │
     Z (depth into workpiece)
```

## Solution: Axis Transformation Required

**Important**: G55/G56 work coordinate systems only change the origin, NOT the axis directions. You need to handle the axis transformation in Fusion 360, not in LinuxCNC.

**The transformation must happen in the Fusion 360 post-processor or setup orientation.**

### Step 1: Fusion 360 Setup for End Face

In Fusion 360, when creating a setup for the horizontal bit operation:

1. **Set the origin on the end face** of the workpiece
2. **Orient the setup** so the end face is facing "up" in Fusion's view
3. **Define the coordinate system**:
   - X-axis: Along the length of the tenon (left to right on the end face)
   - Y-axis: Into the workpiece (depth of tenon)
   - Z-axis: Up/down on the end face (height of tenon)

### Step 2: Machine Setup (G55/G56)

On the machine, you set the work coordinate system (G55 or G56) with the origin on the end face:

```
G55 (or G56) Setup:
- X=0: Left edge of end face (or wherever you define it)
- Y=0: Bottom edge of end face (or wherever you define it)  
- Z=0: Face of the end (where tenon starts)
```

### Step 3: How It Works Together

**Important**: The post-processor must swap X↔Z. After transformation, Fusion outputs:
```gcode
G55
T15 M6
G0 X2 Y5 Z10    ; After X↔Z swap (Fusion Z→X, Fusion X→Z)
G1 Z-10 F500    ; Cut 10mm deep
```

The machine interprets this as:
- **X2**: Move 2mm in X (tenon length) ✅ (was Fusion's Z)
- **Y5**: Move 5mm in Y (vertical position) ✅ (unchanged)
- **Z-10**: Move -10mm in Z (depth of cut) ✅ (was Fusion's X)

The tool offsets (X+23mm, Y-192mm, Z+46.35mm) are automatically applied by the remap code, so the bit ends up in the correct physical position.

## Important Considerations

### 1. Fusion 360 Post-Processor Settings

You need to ensure your Fusion 360 post-processor:
- **Swaps X↔Z when T15 or T16 is used** (critical!)
- Outputs the correct work coordinate system (G55, G56, etc.)
- Keeps Y unchanged
- Outputs standard G-code that LinuxCNC can interpret

**See `docs/fusion360_postprocessor_guide.md` for detailed post-processor creation instructions.**

### 2. Work Coordinate System Origin

When you set G55/G56 on the machine:
- The origin should be on the **end face** of the workpiece
- X=0, Y=0, Z=0 should be at a known reference point on that end face
- This might require probing or manual setup

### 3. Tool Offsets Are Still Applied

Remember, the tool offsets from `tool.tbl` are still applied automatically:
- T15: X+23.0mm, Y-192.0mm, Z+46.35mm
- T16: X-87.0mm, Y-192.0mm, Z+46.35mm

These offsets position the bit relative to the machine origin, and LinuxCNC handles this automatically when you use `G43 H15` or `G43 H16`.

## Example Workflow

### Fusion 360 Setup:

1. **Setup 1 (G54) - Top Face Grooves:**
   - Origin: Top face, normal orientation
   - Tool: T21
   - Output: Standard top-down g-code

2. **Setup 2 (G55) - End Face 1 Tenon:**
   - Origin: First end face
   - Orientation: **Top-down view** (normal Fusion orientation)
   - Tool: T15 (horizontal X-bit)
   - Model tenon in normal top view
   - Post-processor: **Must swap X↔Z**, output G55

3. **Setup 3 (G56) - End Face 2 Tenon:**
   - Origin: Second end face
   - Same orientation as Setup 2
   - Tool: T16 (horizontal X-bit)
   - Post-processor: Output G56

### Machine Setup:

1. Set G54 origin on top face (normal setup)
2. Set G55 origin on first end face:
   - Touch off on left edge (X=0)
   - Touch off on bottom edge (Y=0)
   - Touch off on face (Z=0)
3. Set G56 origin on second end face (same process)

### Combined G-Code:

```gcode
%
O1000 (Grooves and Tenons)

(Setup 1: Top Grooves)
G54
T21 M6
... (groove toolpaths) ...

(Setup 2: End 1 Tenon)
G55
T15 M6
G0 X0 Y0 Z0    ; After X↔Z swap: X=length, Y=height, Z=depth
G1 Z-5 F500    ; Cut 5mm deep (Z is depth after swap)
G1 X20         ; Cut 20mm long (X is length after swap)
G1 Z0          ; Retract
...

(Setup 3: End 2 Tenon)
G56
T16 M6
G0 X0 Y0 Z0    ; After X↔Z swap: X=length, Y=height, Z=depth
G1 Z-5 F500    ; Cut 5mm deep (Z is depth after swap)
G1 X20         ; Cut 20mm long (X is length after swap)
G1 Z0          ; Retract
...

M2
%
```

## Key Points

1. ⚠️ **G55/G56 work coordinate systems** only change the origin - they do NOT transform axes
2. ✅ **Axis transformation** must be handled in Fusion 360 post-processor
3. ✅ **Post-processor must swap X↔Z** when T15/T16 is used (Y stays unchanged)
4. ✅ **Tool offsets** are automatically applied by the remap code
5. ✅ **LinuxCNC** interprets the transformed coordinates correctly

**See `docs/fusion360_postprocessor_guide.md` for detailed post-processor creation instructions.**

## Verification

To verify this works correctly:

1. Create a simple test tenon in Fusion 360
2. Post-process with G55 work coordinate system
3. Set G55 origin on a test piece's end face
4. Run the g-code and verify:
   - Tenon length is correct (X-axis)
   - Tenon depth is correct (Z-axis in g-code, which is depth)
   - Tenon height is correct (Y-axis in g-code, which is vertical position)

If the tenon dimensions don't match, check:
- Work coordinate system origin setup
- Fusion 360 setup orientation
- Tool offsets in tool.tbl

