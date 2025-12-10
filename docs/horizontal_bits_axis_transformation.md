# Horizontal Bits: Axis Transformation Solution

## The Problem

**G55 (and all work coordinate systems) only change the origin, NOT the axis directions.**

- G54: X=X, Y=Y, Z=Z (just an origin offset)
- G55: X=X, Y=Y, Z=Z (just a different origin offset)
- G56: X=X, Y=Y, Z=Z (just another origin offset)

**They don't automatically transform axes!**

## The Real Solution

For horizontal X-bit operations, you need to handle the axis transformation in **Fusion 360**, not in LinuxCNC. Here are the options:

## Option 1: Custom Post-Processor (Recommended)

Create or modify a Fusion 360 post-processor to swap axes when a horizontal bit tool is selected.

### How It Works:

1. In Fusion 360, create your setup normally with the end face as origin (top-down view)
2. The post-processor detects when T15 or T16 is used
3. The post-processor swaps **X↔Z** in the output g-code:
   - Fusion X → Machine Z (swapped - depth of cut)
   - Fusion Y → Machine Y (unchanged)
   - Fusion Z → Machine X (swapped - cutting direction)

### Example Post-Processor Logic:

```javascript
// In Fusion 360 post-processor
if (toolNumber == 15 || toolNumber == 16) {
    // Horizontal X-bit: swap X and Z
    var temp = x;
    x = z;  // Fusion Z → Machine X
    z = temp;  // Fusion X → Machine Z
    // Y stays the same
    // Now output: Z (was X), Y, X (was Z)
}
```

### Result:

Fusion outputs (top-down view):
```gcode
G55
T15 M6
G0 X10 Y5 Z20    ; Fusion's coordinates (X=depth, Y=width, Z=length)
```

Post-processor transforms to:
```gcode
G55
T15 M6
G0 X20 Y5 Z10    ; Swapped X and Z for horizontal bit
```

Machine interprets:
- X20: Move in X (tenon length) ✅ (was Fusion's Z)
- Y5: Move in Y (vertical position) ✅ (unchanged)
- Z10: Move in Z (depth of cut) ✅ (was Fusion's X)

## Option 2: Fusion 360 Setup Orientation

Orient the setup in Fusion 360 so the coordinate system naturally outputs the correct axes.

### How It Works:

1. In Fusion 360, when creating the setup for the end face:
   - Set the **X-axis** to point into the workpiece (machine Z - depth)
   - Set the **Y-axis** to point left/right (machine Y - vertical position)
   - Set the **Z-axis** to point along the tenon length (machine X - cutting direction)

2. Fusion outputs g-code with these axes already "correct" for the horizontal bit

**Note**: This is more complex and may be harder to visualize. The post-processor approach (Option 1) is recommended.

### Fusion 360 Setup Steps:

1. Create new setup
2. Select the end face as the origin plane
3. In "Orientation" settings:
   - **X-axis**: Select an edge along the tenon length direction
   - **Y-axis**: Select an edge pointing into the workpiece (or use "Flip" to reverse)
   - **Z-axis**: Will be perpendicular (up/down on end face)

4. Fusion will now output:
   - X moves → Machine X (tenon length)
   - Y moves → Machine Z (depth) 
   - Z moves → Machine Y (height)

## Option 3: Python Remap for Axis Swapping

Create a Python remap that intercepts g-code and swaps axes when horizontal bits are active.

### Implementation:

Add to `remap.py`:

```python
def remap_g0_g1(self, **params):
    """Intercept G0/G1 and swap X/Z for horizontal bits"""
    stat = linuxcnc.stat()
    stat.poll()
    
    if stat.tool_in_spindle in [15, 16]:  # Horizontal X-bits
        # Swap X and Z coordinates
        if 'x' in params and 'z' in params:
            params['x'], params['z'] = params['z'], params['x']
        elif 'x' in params:
            params['z'] = params.pop('x')
        elif 'z' in params:
            params['x'] = params.pop('z')
    
    # Call original G0/G1
    yield INTERP_OK
```

**Note**: This would require remapping G0 and G1, which is more complex and may interfere with other operations. The post-processor approach (Option 1) is recommended.

## Option 4: Manual G-Code Editing

Post-process normally, then manually edit the g-code to swap X and Z axes.

### Process:

1. Post-process the Fusion 360 setup normally
2. Open the g-code file
3. Find all lines with X and Z coordinates
4. Swap them:
   - `X10 Z5` becomes `X5 Z10`
5. Save and run

**Limitation**: Time-consuming and error-prone.

## Recommended Approach: Option 1 (Custom Post-Processor)

### Why Post-Processor is Best:

1. ✅ Automatic - no manual editing
2. ✅ Integrated into workflow
3. ✅ Can be tool-specific (only swaps for T15/T16)
4. ✅ Works with all Fusion 360 operations
5. ✅ Reusable for future projects

### Post-Processor Implementation:

You'll need to modify your Fusion 360 post-processor to:

1. Detect when T15 or T16 is selected
2. Swap **X and Z** coordinates in all motion commands (G0, G1, G2, G3, etc.)
3. Keep Y unchanged
4. Output standard LinuxCNC g-code

### Example Post-Processor Code:

```javascript
// In your Fusion post-processor JavaScript
var isHorizontalBit = false;

function onSection() {
    // Check if current tool is horizontal X-bit
    var tool = getTool();
    isHorizontalBit = (tool.number == 15 || tool.number == 16);
}

function writeMotionBlock(x, y, z) {
    if (isHorizontalBit) {
        // Swap X and Z for horizontal bits
        writeBlock(
            gFormat.format(z),  // Fusion Z → Machine X
            yFormat.format(y),  // Fusion Y → Machine Y (unchanged)
            zFormat.format(x)   // Fusion X → Machine Z
        );
    } else {
        // Normal output for other tools
        writeBlock(
            gFormat.format(x),
            yFormat.format(y),
            zFormat.format(z)
        );
    }
}
```

## Summary

**The key point**: G55 doesn't transform axes - you need to handle the transformation in Fusion 360 (via post-processor or setup orientation) so that the g-code outputs the correct axes for the horizontal bit.

**Best solution**: Custom post-processor that automatically swaps **X↔Z** when T15 or T16 is used.

**Axis mapping for horizontal X-bits:**
- Fusion X (depth) → Machine Z (depth of cut)
- Fusion Y (width) → Machine Y (vertical position) - unchanged
- Fusion Z (length) → Machine X (cutting direction)

## Next Steps

1. Identify which Fusion 360 post-processor you're using
2. Modify it to detect T15/T16 and swap Y↔Z axes
3. Test with a simple tenon operation
4. Verify the machine moves correctly

Would you like help creating or modifying a Fusion 360 post-processor for this?

