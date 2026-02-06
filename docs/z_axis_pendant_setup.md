# Z Axis Pendant Jogging Setup

## Current Status

### ✅ Already Configured
The Z axis jogging signals are already defined in `Rover13s.hal`:
```hal
net jog-z-pos               halui.axis.z.plus
net jog-z-neg               halui.axis.z.minus
net jog-z-analog            halui.axis.z.analog
```

These connect to LinuxCNC's HALUI (Human-Application-User-Interface) which provides jogging functionality.

### ❌ Missing: Physical Input Connections
The signals are **not connected to any physical inputs** yet. You need to connect them to buttons/switches on your pendant or control panel.

## Available Input Pins

### Mesa 7i77 (in cabinet) - `hm2_7i96s.0.7i77.0.0`
**Currently Used:**
- `input-00` - (unused - was Y home switch, now in HAL file)
- `input-01` - X home switch
- `input-02` - Z home switch
- `input-03` - Remote E-stop
- `input-04` - X axis OK
- `input-05` - Y axis OK
- `input-06` - Z axis OK
- `input-07` - Motor stopped
- `input-08` - VFD reset button
- `input-09` - Tooling in progress
- `input-10` - Start lube
- `input-11` - Speed increase
- `input-12` - Speed decrease
- `input-13` - VFD overload

**Available:** None on 7i77 (all used)

### Mesa 7i84-00 (machine head) - `hm2_7i94.0.7i84.0.0`
**Currently Used:**
- `input-00` - Blade is up
- `input-01` - Blade is down
- `input-02` - Router is up
- `input-03` - Router is down
- `input-04` - Tool locked present
- `input-05` - Tool released
- `input-06` - Release tool button
- `input-07` - X safe zone
- `input-08` - Y safe zone

**Available:** None (all used)

### Mesa 7i84-01 (machine head) - `hm2_7i94.0.7i84.0.1`
**Currently Used:**
- All outputs used for router/blade/tool control
- **TB1 INPUTS:** Appears to be unused (check if available)

**Available:** Check if `input-00` through `input-07` are available on TB1

### Mesa 7i84-02 (front of table) - `hm2_7i94.0.7i84.0.2`
**Currently Used:**
- `input-00` - Left area button
- `input-01` - Right area button
- `input-02` - Vacuum pedal
- `input-03` - E-stop PCells
- `input-04` - Vacuum OK

**Available:** Check if `input-05` through `input-07` are available on TB1

## Setup Options

### Option 1: Use Available Inputs on 7i84 Cards
If you have available inputs on the 7i84 cards, connect your pendant buttons there.

**Example for 7i84-02 (front of table):**
```hal
# Z axis jogging from pendant (if inputs 5-7 are available)
net z-jog-up-btn      hm2_7i94.0.7i84.0.2.input-05    =>  jog-z-pos
net z-jog-down-btn    hm2_7i94.0.7i84.0.2.input-06    =>  jog-z-neg
```

### Option 2: Use MPG (Manual Pulse Generator)
If you have an MPG pendant with an encoder, you'll need to:
1. Connect the MPG encoder to an available encoder input
2. Configure the MPG component
3. Connect MPG output to Z axis jogging

**MPG Setup (if you have an MPG):**
```hal
# Load MPG component
loadrt mpg

# Connect MPG encoder (example - check your MPG wiring)
net mpg-encoder-a     hm2_7i96s.0.encoder.03.phase-a
net mpg-encoder-b     hm2_7i96s.0.encoder.03.phase-b

# Connect MPG to Z axis jogging
net mpg-counts        mpg.0.counts                    =>  jog-z-analog
net mpg-direction    mpg.0.direction                  =>  (determines up/down)
```

### Option 3: Add to Existing Control Panel
If you have a control panel with buttons, connect them to available inputs.

## Implementation Steps

### Step 1: Identify Your Pendant/Buttons
- What type of pendant do you have? (MPG, simple buttons, etc.)
- Where are the Z up/down buttons located?
- What inputs are they currently connected to (if any)?

### Step 2: Choose Available Inputs
Based on your hardware, identify which input pins are available. Check:
- Mesa 7i84-01 TB1 inputs (if available)
- Mesa 7i84-02 TB1 inputs 5-7 (if available)
- Or add a new input card if needed

### Step 3: Wire Physical Connections
Connect your pendant buttons to the chosen input pins.

### Step 4: Add HAL Connections
Add to `rover-custom.hal`:
```hal
# Z Axis Pendant Jogging
# Replace with your actual input pin numbers
net z-jog-up-btn      hm2_7i94.0.7i84.0.2.input-05    =>  jog-z-pos
net z-jog-down-btn    hm2_7i94.0.7i84.0.2.input-06    =>  jog-z-neg
```

### Step 5: Test
1. Restart LinuxCNC
2. Enable the machine
3. Test Z axis jogging with pendant buttons

## Alternative: Use GUI Jogging
If you don't have a physical pendant, you can use the LinuxCNC GUI jogging controls. The Z axis should already be available in the GUI (gmoccapy interface).

## Checking Available Inputs

To see what inputs are actually available, run:
```bash
halcmd show pin | grep input | grep -v "<= TRUE\|<= FALSE"
```

This will show all input pins and their current connections.

## Notes

- **Z axis direction**: Make sure "up" button moves Z positive (up) and "down" button moves Z negative (down)
- **Jog speed**: Controlled by `halui.axis.jog-speed` which is already connected
- **Axis selection**: You may need to select Z axis first before jogging (check your GUI/pendant setup)
