from interpreter import *
from emccanon import MESSAGE
def tool_change(self, **words):
    tool = int(words['T'])
    print(f"Changing to tool {tool}")
    self.call_default()
