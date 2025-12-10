# Horizontal Bits Workflow Analysis

## Current Horizontal X-Bit Configuration

From `tool.tbl`, the horizontal X-bits are configured as:

| Tool | X Offset | Y Offset | Z Offset | Description |
|------|----------|----------|----------|-------------|
| T11  | +32.0mm  | -119.0mm | +46.35mm | Horizontal X Bit A1 (P10) |
| T12  | +32.0mm  | -9.0mm   | +46.35mm | Horizontal X Bit A2 (P10) |
| T13  | +64.0mm  | -119.0mm | +46.35mm | Horizontal X Bit B1 (P11) |
| T14  | +64.0mm  | -9.0mm   | +46.35mm | Horizontal X Bit B2 (P11) |

### Key Observations:

1. **Z Offset (+46.35mm)**: All horizontal bits have a Z offset of +46.35mm, meaning they are positioned 46.35mm above the machine's Z=0 reference. This is the height of the horizontal bit's cutting centerline relative to the table.

2. **X/Y Positioning**: The bits are positioned at different X and Y locations:
   - T11/T12: X = +32mm (closer to origin)
   - T13/T14: X = +64mm (farther from origin)
   - T11/T13: Y = -119mm (one end position)
   - T12/T14: Y = -9mm (other end position)

3. **Shared Pins**: T11/T12 share pin P10, and T13/T14 share pin P11. Only one bit per pair can be active at a time.

## Workflow: Router Grooves + Horizontal Tenons

### Your Application:
- **Step 1**: Use T21 (1/2" end mill) to cut 3/4" grooves on top face
- **Step 2**: Use horizontal X-bits to cut tenons on each end
- **Goal**: Single g-code file with multiple Fusion 360 setups

## Workflow Options

### Option 1: Multiple Work Coordinate Systems (Recommended)

Use different work coordinate systems (G54, G55, G56) for each setup:

**Setup 1 (G54) - Top Face Grooves:**
- Origin: Top face of workpiece
- Tool: T21 (1/2" router)
- Operation: Cut 3/4" grooves on top
- Workpiece orientation: Normal (lying flat)

**Setup 2 (G55) - End Face 1 Tenon:**
- Origin: First end face of workpiece
- Tool: T11 or T13 (Horizontal X Bit)
- Operation: Cut tenon on first end
- Workpiece orientation: End face accessible to horizontal bit
- **Important**: The Z axis in this setup controls the depth of the tenon cut

**Setup 3 (G56) - End Face 2 Tenon:**
- Origin: Second end face of workpiece
- Tool: T12 or T14 (Horizontal X Bit)
- Operation: Cut tenon on second end
- Workpiece orientation: End face accessible to horizontal bit

#### Implementation in Fusion 360:

1. **Setup 1 (Top Face)**:
   - Create setup with top face as origin
   - Select T21 as tool
   - Generate toolpath for grooves
   - In post-processor, ensure it outputs `G54` (or set as default)

2. **Setup 2 (End Face 1)**:
   - Create new setup with first end face as origin
   - Rotate model view to show end face
   - Select T11 or T13 as tool
   - Generate toolpath for tenon
   - In post-processor, set to output `G55`

3. **Setup 3 (End Face 2)**:
   - Create new setup with second end face as origin
   - Rotate model view to show end face
   - Select T12 or T14 as tool
   - Generate toolpath for tenon
   - In post-processor, set to output `G56`

4. **Post-Processing**:
   - Post-process all setups in sequence
   - Manually combine the g-code files, or use Fusion's "Post Process All" feature
   - Add coordinate system switches between operations:
     ```
     (Setup 1 - Top Grooves)
     G54
     T21 M6
     ... (groove toolpaths) ...
     
     (Setup 2 - End 1 Tenon)
     G55
     T11 M6
     ... (tenon toolpaths) ...
     
     (Setup 3 - End 2 Tenon)
     G56
     T12 M6
     ... (tenon toolpaths) ...
     ```

### Option 2: Single Work Coordinate System with Manual Positioning

Use G54 for all operations, but manually adjust workpiece position between operations:

1. **Setup 1**: Cut grooves with T21 (workpiece in normal position)
2. **Manual Step**: Reposition workpiece so first end is accessible to horizontal bit
3. **Setup 2**: Cut first tenon with T11/T13
4. **Manual Step**: Reposition workpiece so second end is accessible
5. **Setup 3**: Cut second tenon with T12/T14

**Limitation**: Requires manual intervention between operations.

### Option 3: Transform Operations in Single Setup

Use coordinate transformations (G92 or coordinate rotation) to handle different orientations:

1. **Setup 1**: Top face grooves (normal orientation)
2. **Setup 2**: Use coordinate transformation to "rotate" the coordinate system for end face operations

**Complexity**: More complex to implement and verify.

## Verifying Horizontal Bit Offsets

### Critical Questions:

1. **Z Offset Verification**: 
   - Is +46.35mm the correct height for the horizontal bit's cutting centerline?
   - When cutting a tenon, you'll program Z moves relative to your work coordinate system origin
   - The tool offset will automatically account for the +46.35mm offset
   - **Test**: Manually position a test piece and verify the bit cuts at the expected location

2. **X/Y Offset Verification**:
   - Are the X and Y offsets correct for your workpiece positioning?
   - The offsets position the bit relative to machine origin
   - When you set your work coordinate system (G55/G56) on the end face, ensure the bit can reach the tenon location
   - **Test**: Use MDI to move to known positions and verify bit location

3. **Tenon Depth Calculation**:
   - For a tenon cut, the Z axis controls depth
   - If your tenon is 10mm deep, program Z moves accordingly
   - The tool offset (+46.35mm) is automatically applied by LinuxCNC
   - **Example**: To cut a 10mm deep tenon starting at the end face (Z=0 in your work coordinate), you'd program moves to Z=-10mm

## Recommended Workflow Steps

1. **Verify Offsets** (Do this first):
   ```
   - Place a test piece in position
   - Use MDI to move to a known position with a horizontal bit active
   - Verify the bit is where you expect it to be
   - Adjust tool.tbl offsets if needed
   ```

2. **Fusion 360 Setup**:
   - Create three separate setups as described in Option 1
   - Use different work coordinate systems (G54, G55, G56)
   - Ensure each setup has the correct origin and orientation

3. **Post-Process and Combine**:
   - Post-process each setup
   - Combine into single file with coordinate system switches
   - Add safety moves between operations (retract, move to safe position)

4. **Test Run**:
   - Run on a test piece first
   - Verify each operation cuts in the correct location
   - Adjust work coordinate system origins if needed

## Example G-Code Structure

```gcode
%
O1000 (Grooves and Tenons)
G21 G90 G94 G40 (Metric, Absolute, Feed/Min, Cutter Comp Off)
G17 (XY plane)

(========================================)
(SETUP 1: Top Face Grooves)
(========================================)
G54 (Top face coordinate system)
G0 Z50 (Safe height)
T21 M6 (1/2" Router)
G43 H21 (Apply tool length compensation)
M3 S18000 (Start spindle)
G0 X0 Y0 (Move to start position)
... (groove toolpaths) ...
M5 (Stop spindle)
G0 Z50 (Retract)

(========================================)
(SETUP 2: End Face 1 Tenon)
(========================================)
G55 (End face 1 coordinate system)
G0 Z50 (Safe height)
T11 M6 (Horizontal X Bit A1)
G43 H11 (Apply tool length compensation)
M3 S12000 (Start spindle - adjust speed for horizontal bit)
G0 X0 Y0 (Move to start position)
... (tenon toolpaths - Z controls depth) ...
M5 (Stop spindle)
G0 Z50 (Retract)

(========================================)
(SETUP 3: End Face 2 Tenon)
(========================================)
G56 (End face 2 coordinate system)
G0 Z50 (Safe height)
T12 M6 (Horizontal X Bit A2)
G43 H12 (Apply tool length compensation)
M3 S12000 (Start spindle)
G0 X0 Y0 (Move to start position)
... (tenon toolpaths) ...
M5 (Stop spindle)
G0 Z50 (Retract)

M2 (End program)
%
```

## Important Notes

1. **Tool Changes**: Your `remap.py` handles tool changes automatically, including retracting previous tools and activating new ones.

2. **Work Coordinate Systems**: You'll need to set G54, G55, and G56 origins manually on the machine before running the program, or use probing routines.

3. **Horizontal Bit Selection**: Choose T11/T12 vs T13/T14 based on which X position gives you better access to your workpiece ends.

4. **Safety**: Always verify tool offsets and work coordinate systems with a test piece before running on production parts.

## Questions to Verify

1. Are the horizontal bit Z offsets (+46.35mm) correct for your machine?
2. Can the horizontal bits reach both ends of your workpiece in their current positions?
3. What is the typical tenon depth you'll be cutting?
4. Do you need to adjust the X/Y offsets for your specific workpiece dimensions?

