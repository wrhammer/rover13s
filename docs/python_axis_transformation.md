# Python-Based Axis Transformation for Horizontal Bits

## Overview

This document describes a **foolproof, post-processor-independent** solution for handling axis transformations for horizontal bits using LinuxCNC's Python remap functionality:

- **Horizontal Y-bits (T11-T14)**: Swap Y↔Z (bits drill along Y-axis)
- **Horizontal X-bits (T15-T16)**: Swap X↔Z (bits drill along X-axis)

## Why This Approach?

**Advantages:**
- ✅ **Post-processor independent** - Works with ANY g-code source (Fusion 360, Mastercam, hand-written, etc.)
- ✅ **Machine-specific** - Lives in your LinuxCNC config, travels with the machine
- ✅ **Easy to maintain** - All transformation logic in one place
- ✅ **Foolproof** - Can't be bypassed or forgotten
- ✅ **Documented** - Clear comments explain what's happening

**Disadvantages:**
- ⚠️ Requires LinuxCNC remap configuration
- ⚠️ Slightly more complex than post-processor approach

## Implementation

### Step 1: Add Remap Functions to remap.py

Add these functions to handle G0, G1, G2, G3 with axis swapping:

```python
# Horizontal X-bit tools that require X↔Z axis swap
HORIZONTAL_X_BITS = [15, 16]

def is_horizontal_bit(self):
    """Check if current tool is a horizontal X-bit requiring axis swap"""
    stat = linuxcnc.stat()
    stat.poll()
    return stat.tool_in_spindle in HORIZONTAL_X_BITS

def swap_xz(self, **words):
    """Swap X and Z coordinates for horizontal bits"""
    if not is_horizontal_bit(self):
        return words  # No swap needed
    
    # Swap X and Z
    swapped = words.copy()
    if 'x' in words and 'z' in words:
        swapped['x'], swapped['z'] = words['z'], words['x']
    elif 'x' in words:
        swapped['z'] = words.pop('x')
        swapped['x'] = None  # Clear X
    elif 'z' in words:
        swapped['x'] = words.pop('z')
        swapped['z'] = None  # Clear Z
    
    # For circular moves, also swap I and K (arc center offsets)
    if 'i' in words and 'k' in words:
        swapped['i'], swapped['k'] = words['k'], words['i']
    elif 'i' in words:
        swapped['k'] = words.pop('i')
        swapped['i'] = None
    elif 'k' in words:
        swapped['i'] = words.pop('k')
        swapped['k'] = None
    
    return swapped

def remap_g0(self, **words):
    """Remap G0 (rapid) with X↔Z swap for horizontal bits"""
    if self.task == 0:  # Preview interpreter
        yield INTERP_EXECUTE_FINISH
        return INTERP_OK
    
    swapped = swap_xz(self, **words)
    
    # Remove None values
    swapped = {k: v for k, v in swapped.items() if v is not None}
    
    # Execute the motion with swapped coordinates
    if swapped:
        cmd = "G0"
        for axis, value in swapped.items():
            cmd += f" {axis.upper()}{value}"
        self.execute(cmd)
        yield INTERP_EXECUTE_FINISH
    
    yield INTERP_OK

def remap_g1(self, **words):
    """Remap G1 (linear) with X↔Z swap for horizontal bits"""
    if self.task == 0:  # Preview interpreter
        yield INTERP_EXECUTE_FINISH
        return INTERP_OK
    
    swapped = swap_xz(self, **words)
    
    # Remove None values
    swapped = {k: v for k, v in swapped.items() if v is not None}
    
    # Execute the motion with swapped coordinates
    if swapped:
        cmd = "G1"
        for axis, value in swapped.items():
            cmd += f" {axis.upper()}{value}"
        if 'f' in words:
            cmd += f" F{words['f']}"
        self.execute(cmd)
        yield INTERP_EXECUTE_FINISH
    
    yield INTERP_OK

def remap_g2(self, **words):
    """Remap G2 (circular CW) with X↔Z swap for horizontal bits"""
    if self.task == 0:  # Preview interpreter
        yield INTERP_EXECUTE_FINISH
        return INTERP_OK
    
    swapped = swap_xz(self, **words)
    
    # Remove None values
    swapped = {k: v for k, v in swapped.items() if v is not None}
    
    # Execute the motion with swapped coordinates
    if swapped:
        cmd = "G2"
        for axis, value in swapped.items():
            cmd += f" {axis.upper()}{value}"
        if 'f' in words:
            cmd += f" F{words['f']}"
        self.execute(cmd)
        yield INTERP_EXECUTE_FINISH
    
    yield INTERP_OK

def remap_g3(self, **words):
    """Remap G3 (circular CCW) with X↔Z swap for horizontal bits"""
    if self.task == 0:  # Preview interpreter
        yield INTERP_EXECUTE_FINISH
        return INTERP_OK
    
    swapped = swap_xz(self, **words)
    
    # Remove None values
    swapped = {k: v for k, v in swapped.items() if v is not None}
    
    # Execute the motion with swapped coordinates
    if swapped:
        cmd = "G3"
        for axis, value in swapped.items():
            cmd += f" {axis.upper()}{value}"
        if 'f' in words:
            cmd += f" F{words['f']}"
        self.execute(cmd)
        yield INTERP_EXECUTE_FINISH
    
    yield INTERP_OK
```

### Step 2: Update Rover13s.ini

Add remap configurations for G0, G1, G2, G3:

```ini
[RS274NGC]
PARAMETER_FILE = linuxcnc.var
USER_M_PATH = ngc
SUBROUTINE_PATH = ngc
RS274NGC_STARTUP_CODE = G21 G40 G90 G94 G97 G64 P0.025
REMAP=M6 modalgroup=6 prolog=change_prolog python=remap_m6
REMAP=G0 modalgroup=1 argspec=xz argspec=xyz argspec=xy argspec=xz argspec=yz python=remap_g0
REMAP=G1 modalgroup=1 argspec=xz argspec=xyz argspec=xy argspec=xz argspec=yz python=remap_g1
REMAP=G2 modalgroup=1 argspec=xz argspec=xyz argspec=xy argspec=xz argspec=yz argspec=ijk argspec=ij argspec=ik argspec=jk python=remap_g2
REMAP=G3 modalgroup=1 argspec=xz argspec=xyz argspec=xy argspec=xz argspec=yz argspec=ijk argspec=ij argspec=ik argspec=jk python=remap_g3
ENABLE_EMBEDDED_PYTHON=1
DEBUG = 5
MDI_TIMEOUT = 0
```

**Note**: The `argspec` entries tell LinuxCNC which arguments each remap can handle. Multiple argspec lines allow different combinations.

### Step 3: Alternative Simpler Approach (Recommended)

Actually, a simpler and more robust approach is to use a **prolog/epilog** pattern that intercepts the motion before it executes:

```python
def motion_prolog(self, **words):
    """Prolog for G0/G1/G2/G3 - swaps X↔Z for horizontal bits"""
    if self.task == 0:  # Preview interpreter
        return INTERP_OK
    
    stat = linuxcnc.stat()
    stat.poll()
    
    # Check if current tool is horizontal X-bit
    if stat.tool_in_spindle not in [15, 16]:
        return INTERP_OK  # No transformation needed
    
    # Swap X and Z in the current block
    c = self.blocks[self.remap_level]
    
    if c.x_flag and c.z_flag:
        # Both X and Z present - swap them
        temp = c.x_number
        c.x_number = c.z_number
        c.z_number = temp
    elif c.x_flag:
        # Only X present - move to Z
        c.z_flag = True
        c.z_number = c.x_number
        c.x_flag = False
        c.x_number = 0
    elif c.z_flag:
        # Only Z present - move to X
        c.x_flag = True
        c.x_number = c.z_number
        c.z_flag = False
        c.z_number = 0
    
    # For circular moves, also swap I and K
    if c.i_flag and c.k_flag:
        temp = c.i_number
        c.i_number = c.k_number
        c.k_number = temp
    elif c.i_flag:
        c.k_flag = True
        c.k_number = c.i_number
        c.i_flag = False
        c.i_number = 0
    elif c.k_flag:
        c.i_flag = True
        c.i_number = c.k_number
        c.k_flag = False
        c.k_number = 0
    
    return INTERP_OK
```

Then in the INI file:

```ini
REMAP=G0 modalgroup=1 prolog=motion_prolog
REMAP=G1 modalgroup=1 prolog=motion_prolog
REMAP=G2 modalgroup=1 prolog=motion_prolog
REMAP=G3 modalgroup=1 prolog=motion_prolog
```

## Complete Implementation

Here's the complete code to add to `remap.py`:

```python
# Horizontal Y-bit tools that require Y↔Z axis swap
HORIZONTAL_Y_BITS = [11, 12, 13, 14]

# Horizontal X-bit tools that require X↔Z axis swap
HORIZONTAL_X_BITS = [15, 16]

def motion_prolog(self, **words):
    """
    Prolog for G0/G1/G2/G3 motion commands.
    Swaps axes when horizontal bits are active:
    - T11-T14 (Horizontal Y-bits): Swap Y↔Z
    - T15-T16 (Horizontal X-bits): Swap X↔Z
    
    This allows any post-processor to output standard g-code - the transformation
    happens automatically at the LinuxCNC level.
    """
    if self.task == 0:  # Preview interpreter - skip transformation
        return INTERP_OK
    
    import linuxcnc
    stat = linuxcnc.stat()
    stat.poll()
    
    tool_number = stat.tool_in_spindle
    
    # Check if current tool is a horizontal bit
    is_horizontal_y = tool_number in HORIZONTAL_Y_BITS
    is_horizontal_x = tool_number in HORIZONTAL_X_BITS
    
    if not (is_horizontal_y or is_horizontal_x):
        return INTERP_OK  # No transformation needed
    
    # Get current block
    c = self.blocks[self.remap_level]
    
    # Handle horizontal Y-bits (T11-T14): Swap Y↔Z
    if is_horizontal_y:
        # Swap Y and Z coordinates
        if c.y_flag and c.z_flag:
            temp = c.y_number
            c.y_number = c.z_number
            c.z_number = temp
            print(f"🔄 [T{tool_number}] Swapped Y↔Z: Y{c.z_number:.3f} Z{c.y_number:.3f}")
        elif c.y_flag:
            c.z_flag = True
            c.z_number = c.y_number
            c.y_flag = False
            c.y_number = 0
            print(f"🔄 [T{tool_number}] Moved Y→Z: Z{c.z_number:.3f}")
        elif c.z_flag:
            c.y_flag = True
            c.y_number = c.z_number
            c.z_flag = False
            c.z_number = 0
            print(f"🔄 [T{tool_number}] Moved Z→Y: Y{c.y_number:.3f}")
        
        # For circular moves, also swap J and K (arc center offsets)
        if c.j_flag and c.k_flag:
            temp = c.j_number
            c.j_number = c.k_number
            c.k_number = temp
        elif c.j_flag:
            c.k_flag = True
            c.k_number = c.j_number
            c.j_flag = False
            c.j_number = 0
        elif c.k_flag:
            c.j_flag = True
            c.j_number = c.k_number
            c.k_flag = False
            c.k_number = 0
    
    # Handle horizontal X-bits (T15-T16): Swap X↔Z
    if is_horizontal_x:
        # Swap X and Z coordinates
        if c.x_flag and c.z_flag:
            temp = c.x_number
            c.x_number = c.z_number
            c.z_number = temp
            print(f"🔄 [T{tool_number}] Swapped X↔Z: X{c.z_number:.3f} Z{c.x_number:.3f}")
        elif c.x_flag:
            c.z_flag = True
            c.z_number = c.x_number
            c.x_flag = False
            c.x_number = 0
            print(f"🔄 [T{tool_number}] Moved X→Z: Z{c.z_number:.3f}")
        elif c.z_flag:
            c.x_flag = True
            c.x_number = c.z_number
            c.z_flag = False
            c.z_number = 0
            print(f"🔄 [T{tool_number}] Moved Z→X: X{c.x_number:.3f}")
        
        # For circular moves, also swap I and K (arc center offsets)
        if c.i_flag and c.k_flag:
            temp = c.i_number
            c.i_number = c.k_number
            c.k_number = temp
        elif c.i_flag:
            c.k_flag = True
            c.k_number = c.i_number
            c.i_flag = False
            c.i_number = 0
        elif c.k_flag:
            c.i_flag = True
            c.i_number = c.k_number
            c.k_flag = False
            c.k_number = 0
    
    return INTERP_OK
```

## INI File Configuration

Add to `Rover13s.ini`:

```ini
[RS274NGC]
# ... existing settings ...
REMAP=G0 modalgroup=1 prolog=motion_prolog
REMAP=G1 modalgroup=1 prolog=motion_prolog  
REMAP=G2 modalgroup=1 prolog=motion_prolog
REMAP=G3 modalgroup=1 prolog=motion_prolog
```

## Testing

1. **Test with Horizontal Y-bits (T11-T14):**
   - Load T11, T12, T13, or T14
   - Run g-code with Y and Z moves
   - Verify Y and Z are swapped in the output
   - Test G2/G3 arcs - verify J and K are swapped

2. **Test with Horizontal X-bits (T15/T16):**
   - Load T15 or T16
   - Run g-code with X and Z moves
   - Verify X and Z are swapped in the output
   - Test G2/G3 arcs - verify I and K are swapped

3. **Test with other tools:**
   - Load T21 (router) or any other tool
   - Run the same g-code
   - Verify axes are NOT swapped

## Advantages of This Approach

1. **Universal Compatibility**: Works with any CAM software or post-processor
2. **Machine-Specific**: Lives in your LinuxCNC config, travels with the machine
3. **Automatic**: No need to remember to use a special post-processor
4. **Maintainable**: All transformation logic in one place
5. **Debuggable**: Print statements show when transformations occur
6. **Future-Proof**: New owner can use any post-processor they want

## Documentation for New Owner

Include this in your machine documentation:

```
HORIZONTAL BITS - AUTOMATIC AXIS TRANSFORMATION:
================================================

The machine automatically swaps axes when horizontal bits are active:

HORIZONTAL Y-BITS (T11-T14):
- Automatically swaps Y↔Z axes
- Bits drill along the Y-axis direction
- Use for operations on workpiece sides (Y-direction)

HORIZONTAL X-BITS (T15-T16):
- Automatically swaps X↔Z axes  
- Bits drill along the X-axis direction
- Use for operations on workpiece ends (X-direction)

This allows you to:
- Use ANY post-processor (Fusion 360, Mastercam, etc.)
- Create g-code normally (top-down view)
- The transformation happens automatically at the LinuxCNC level

No special post-processor needed - just use T11-T16 and the machine
handles the axis transformation automatically.
```

## Troubleshooting

**Problem**: X and Z not swapping
- **Solution**: Check that T15 or T16 is loaded (use `T15 M6` or `T16 M6`)
- **Solution**: Verify remap is enabled in `Rover13s.ini`
- **Solution**: Check LinuxCNC logs for remap errors

**Problem**: Transformation happening for wrong tools
- **Solution**: Verify tool number lists in remap.py:
  - `HORIZONTAL_Y_BITS = [11, 12, 13, 14]`
  - `HORIZONTAL_X_BITS = [15, 16]`

**Problem**: Circular moves not working
- **Solution**: Verify I and K are being swapped in the prolog function

