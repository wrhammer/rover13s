# Fusion 360 Post-Processor for Horizontal X-Bits

## Overview

This guide explains how to create a Fusion 360 post-processor that automatically swaps **X and Z axes** when using horizontal X-bits (T15 or T16).

## Why This Is Needed

When creating tenons in Fusion 360:
- You model them in a **top-down view** (normal orientation)
- Fusion outputs: X, Y, Z coordinates
- For horizontal X-bits, you need: **Z, Y, X** (swapped X↔Z)

## Axis Mapping

| Fusion 360 (Top View) | Machine (Horizontal Bit) | Transformation |
|----------------------|-------------------------|----------------|
| X (tenon depth) | **Z** (depth of cut) | X → Z |
| Y (tenon width) | Y (vertical position) | Y → Y (unchanged) |
| Z (tenon length) | **X** (cutting direction) | Z → X |

**Key**: X and Z are swapped, Y stays the same.

## Creating the Post-Processor

### Step 1: Locate Post-Processor Directory

Fusion 360 post-processors are stored in:
- **Windows**: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\Posts\`
- **Mac**: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/Posts/`

### Step 2: Create New Post-Processor File

1. Open Fusion 360
2. Go to **Manufacture** workspace
3. Click **Post Process** (or right-click setup → **Post Process**)
4. Click the **Post Library** icon (folder icon)
5. Click **New Post** or **Edit Post**
6. This opens the Post Library folder

### Step 3: Copy Base Post-Processor

1. Find an existing LinuxCNC post-processor (or generic 3-axis)
2. Copy it and rename to: `LinuxCNC_Rover13s_Horizontal.cps`
3. Open it in a text editor (it's a JavaScript file)

### Step 4: Modify the Post-Processor

Add logic to detect T15/T16 and swap X↔Z coordinates.

## Post-Processor Code Modifications

### Key Functions to Modify

You need to modify the functions that output motion commands:
- `onLinear()` - for G1 moves
- `onRapid()` - for G0 moves  
- `onCircular()` - for G2/G3 arcs

### Example Code Structure

```javascript
// Add at the top of the file
var isHorizontalBit = false;
var currentTool = 0;

// Function to check if current tool is horizontal X-bit
function checkHorizontalBit() {
    var tool = getCurrentTool();
    if (tool) {
        currentTool = tool.number;
        isHorizontalBit = (currentTool == 15 || currentTool == 16);
    }
    return isHorizontalBit;
}

// Modify onLinear function (G1 moves)
function onLinear(_x, _y, _z) {
    checkHorizontalBit();
    
    var x = _x;
    var y = _y;
    var z = _z;
    
    if (isHorizontalBit) {
        // Swap X and Z for horizontal bits
        x = _z;  // Fusion Z → Machine X
        z = _x;  // Fusion X → Machine Z
        y = _y;  // Y stays the same
    }
    
    // Output the motion command
    writeBlock(
        gFormat.format(1),  // G1
        xFormat.format(x),
        yFormat.format(y),
        zFormat.format(z),
        fFormat.format(getFeedrate())
    );
}

// Modify onRapid function (G0 moves)
function onRapid(_x, _y, _z) {
    checkHorizontalBit();
    
    var x = _x;
    var y = _y;
    var z = _z;
    
    if (isHorizontalBit) {
        // Swap X and Z for horizontal bits
        x = _z;  // Fusion Z → Machine X
        z = _x;  // Fusion X → Machine Z
        y = _y;  // Y stays the same
    }
    
    // Output the rapid move
    writeBlock(
        gFormat.format(0),  // G0
        xFormat.format(x),
        yFormat.format(y),
        zFormat.format(z)
    );
}

// Modify onCircular function (G2/G3 arcs)
function onCircular(clockwise, cx, cy, cz, x, y, z) {
    checkHorizontalBit();
    
    var _x = x;
    var _y = y;
    var _z = z;
    var _cx = cx;
    var _cy = cy;
    var _cz = cz;
    
    if (isHorizontalBit) {
        // Swap X and Z for horizontal bits
        _x = z;   // Fusion Z → Machine X
        _z = x;   // Fusion X → Machine Z
        _y = y;   // Y stays the same
        
        _cx = cz; // Center X
        _cz = cx; // Center Z
        _cy = cy; // Center Y
    }
    
    // Calculate I, J, K (arc center offsets)
    var i = _cx - getCurrentX();
    var j = _cy - getCurrentY();
    var k = _cz - getCurrentZ();
    
    // Output circular move
    writeBlock(
        gFormat.format(clockwise ? 2 : 3),  // G2 or G3
        xFormat.format(_x),
        yFormat.format(_y),
        zFormat.format(_z),
        iFormat.format(i),
        jFormat.format(j),
        kFormat.format(k),
        fFormat.format(getFeedrate())
    );
}
```

## Complete Example Post-Processor

Here's a more complete example based on a standard LinuxCNC post:

```javascript
// LinuxCNC Post-Processor with Horizontal Bit Support
// For Rover13s - Swaps X↔Z for T15/T16

// Tool tracking
var isHorizontalBit = false;
var currentToolNumber = 0;

// Initialize
function onOpen() {
    isHorizontalBit = false;
    currentToolNumber = 0;
}

// Check tool on section start
function onSection() {
    var tool = getCurrentTool();
    if (tool) {
        currentToolNumber = tool.number;
        isHorizontalBit = (currentToolNumber == 15 || currentToolNumber == 16);
    }
}

// Linear move (G1)
function onLinear(x, y, z) {
    var outputX = x;
    var outputY = y;
    var outputZ = z;
    
    if (isHorizontalBit) {
        // Swap X and Z
        outputX = z;  // Fusion Z → Machine X
        outputZ = x;  // Fusion X → Machine Z
        outputY = y;  // Y unchanged
    }
    
    writeBlock(
        gFormat.format(1),
        xFormat.format(outputX),
        yFormat.format(outputY),
        zFormat.format(outputZ),
        fFormat.format(getFeedrate())
    );
}

// Rapid move (G0)
function onRapid(x, y, z) {
    var outputX = x;
    var outputY = y;
    var outputZ = z;
    
    if (isHorizontalBit) {
        // Swap X and Z
        outputX = z;  // Fusion Z → Machine X
        outputZ = x;  // Fusion X → Machine Z
        outputY = y;  // Y unchanged
    }
    
    writeBlock(
        gFormat.format(0),
        xFormat.format(outputX),
        yFormat.format(outputY),
        zFormat.format(outputZ)
    );
}

// Circular move (G2/G3)
function onCircular(clockwise, cx, cy, cz, x, y, z) {
    var outputX = x;
    var outputY = y;
    var outputZ = z;
    var centerX = cx;
    var centerY = cy;
    var centerZ = cz;
    
    if (isHorizontalBit) {
        // Swap X and Z
        outputX = z;
        outputZ = x;
        outputY = y;
        centerX = cz;
        centerZ = cx;
        centerY = cy;
    }
    
    // Calculate arc center offsets
    var currentPos = getCurrentPosition();
    var i = centerX - currentPos.x;
    var j = centerY - currentPos.y;
    var k = centerZ - currentPos.z;
    
    if (isHorizontalBit) {
        // Adjust I and K for swapped axes
        var temp = i;
        i = k;
        k = temp;
    }
    
    writeBlock(
        gFormat.format(clockwise ? 2 : 3),
        xFormat.format(outputX),
        yFormat.format(outputY),
        zFormat.format(outputZ),
        iFormat.format(i),
        jFormat.format(j),
        kFormat.format(k),
        fFormat.format(getFeedrate())
    );
}
```

## Testing the Post-Processor

1. **Create a test setup in Fusion 360:**
   - Simple tenon on end face
   - Use T15 or T16 as the tool
   - Post-process the setup

2. **Check the output g-code:**
   - Verify X and Z are swapped
   - Verify Y is unchanged
   - Check that coordinates make sense

3. **Test on machine:**
   - Run a simple test cut
   - Verify the tenon dimensions are correct

## Installation Steps

1. **Create the post-processor file:**
   - Name it: `LinuxCNC_Rover13s_Horizontal.cps`
   - Save it in the Fusion 360 Posts directory

2. **In Fusion 360:**
   - Go to Manufacture workspace
   - Right-click setup → **Post Process**
   - Select your new post-processor
   - Post-process the setup

3. **Verify output:**
   - Check that T15/T16 triggers X↔Z swap
   - Check that other tools (T21, etc.) output normally

## Important Notes

1. **Tool Detection**: The post-processor must detect T15 or T16 to activate the swap
2. **All Motion Commands**: G0, G1, G2, G3 all need the swap
3. **Arc Centers**: I, J, K offsets also need adjustment for arcs
4. **Tool Changes**: Make sure tool numbers are correctly identified
5. **Work Coordinate Systems**: G54, G55, G56 are output normally (no change needed)

## Troubleshooting

**Problem**: X and Z not swapping
- **Solution**: Check that tool number detection is working (add debug output)

**Problem**: Arcs not working correctly
- **Solution**: Verify I, J, K calculations account for swapped axes

**Problem**: Wrong coordinates
- **Solution**: Verify the swap direction (X→Z, Z→X) is correct for your setup

## Alternative: Two Post-Processors

You could create two separate post-processors:
1. `LinuxCNC_Rover13s.cps` - Normal (for T21, etc.)
2. `LinuxCNC_Rover13s_Horizontal.cps` - With X↔Z swap (for T15/T16)

Then select the appropriate one based on which tool you're using.

