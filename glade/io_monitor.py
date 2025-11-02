#!/usr/bin/env python3
"""
IO Monitor GladeVCP Handler
Simple handler for IO monitor panel - HAL pins are connected directly via glade file
"""

import hal
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

class HandlerClass:
    def __init__(self, halcomp, builder, useropts):
        self.hal = halcomp
        self.builder = builder
        
        # HAL pins are connected directly via the glade file using hal_pin_name property
        # No additional setup needed unless you want to add custom logic
        
        print("IO Monitor panel loaded successfully")
    
    def periodic(self):
        """Called periodically by the HAL component"""
        # Add any periodic updates here if needed
        return True

def get_handlers(halcomp, builder, useropts):
    return [HandlerClass(halcomp, builder, useropts)] 