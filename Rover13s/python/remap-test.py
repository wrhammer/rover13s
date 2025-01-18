import linuxcnc
import time
import xml.etree.ElementTree as ET
import stdglue

# Load the machine configuration from the XML file
config_path = "/home/wrhammer/linuxcnc/configs/Rover13s/python/tool_remap.xml"  # Update with the correct path
tree = ET.parse(config_path)
root = tree.getroot()

# Helper: Get tool series from XML
def get_tool_series(tool_series_id):
    for tool_series in root.findall("Tools/ToolSeries"):
        if tool_series.get("id") == str(tool_series_id):
            return tool_series
    return None

# Helper: Get signal for a specific tool
def get_signal_for_tool(tool_id, tool_series_id):
    tool_series = get_tool_series(tool_series_id)
    if not tool_series:
        print(f"Tool series {tool_series_id} not found!")
        return None

    for tool in tool_series.findall("Tool"):
        if tool.get("id") == str(tool_id):
            return tool.get("signal")

    print(f"Tool {tool_id} not found in tool series {tool_series_id}")
    return None

# Helper: Get delay from XML
def get_delay(name):
    for delay in root.findall("Delays/Delay"):
        if delay.get("name") == name:
            return float(delay.get("val"))
    return 0

# Dynamic tool activation function
def dynamic_tool_remap(prolog, params, tool_series_id):
    # Parse arguments (P, Q, R, S for bits)
    tool_ids = []
    for arg in ["P", "Q", "R", "S"]:  # Expandable for more arguments
        tool_id = getattr(params, arg, None)
        if tool_id is not None:
            tool_ids.append(tool_id)

    # Default: Activate all tools in the series if none specified
    if not tool_ids:
        tool_series = get_tool_series(tool_series_id)
        tool_ids = [int(tool.get("id")) for tool in tool_series.findall("Tool")]
        print("No tools specified! Activating all tools in the series.")

    print(f"Activating tools: {tool_ids} in tool series {tool_series_id}")

    # Activate the selected tools
    for tool_id in tool_ids:
        signal = get_signal_for_tool(tool_id, tool_series_id)
        if signal:
            print(f"Activating signal for tool {tool_id}: {signal}")
            linuxcnc.hal.set(signal, True)
            time.sleep(0.1)  # Small delay between activations

    # Apply the activation delay
    delay = get_delay("toolActivationDelay")
    print(f"Waiting {delay} seconds for activation...")
    time.sleep(delay)

    return stdglue_epilog(prolog)

# Remap functions for different tool series
def remap_vertical_x(prolog, params):
    return dynamic_tool_remap(prolog, params, tool_series_id=101)

def remap_vertical_y(prolog, params):
    return dynamic_tool_remap(prolog, params, tool_series_id=102)

def remap_horizontal_x(prolog, params):
    return dynamic_tool_remap(prolog, params, tool_series_id=120)

def remap_horizontal_y(prolog, params):
    return dynamic_tool_remap(prolog, params, tool_series_id=110)

def remap_saw_blade(prolog, params):
    return dynamic_tool_remap(prolog, params, tool_series_id=201)

def remap_router(prolog, params):
    return dynamic_tool_remap(prolog, params, tool_series_id=301)

# Register remaps
linuxcnc.remap.add("M200", remap_vertical_x)   # Vertical X-axis tools
linuxcnc.remap.add("M201", remap_vertical_y)   # Vertical Y-axis tools
linuxcnc.remap.add("M210", remap_horizontal_y) # Horizontal Y-axis tools
linuxcnc.remap.add("M220", remap_horizontal_x) # Horizontal X-axis tools
linuxcnc.remap.add("M250", remap_saw_blade)    # Saw blade
linuxcnc.remap.add("M260", remap_router)       # Router head
