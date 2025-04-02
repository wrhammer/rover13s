#!/usr/bin/env python3
import hal
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import gladevcp
import os

class HandlerClass:
    def __init__(self, halcomp, builder, useropts):
        self.hal = halcomp
        self.builder = builder
        
        # Get the main window
        self.window = self.builder.get_object('window1')
        
        # Create a notebook (tab container)
        self.notebook = Gtk.Notebook()
        self.notebook.set_show_tabs(True)
        self.notebook.set_show_border(True)
        
        # Get the original box from the glade file
        self.io_monitor_box = self.builder.get_object('io_monitor_box')
        
        # Create a scrolled window for the IO monitor
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        # Add the IO monitor box to the scrolled window
        self.scrolled_window.add(self.io_monitor_box)
        
        # Add the IO monitor as the first tab
        self.notebook.append_page(self.scrolled_window, Gtk.Label(label="IO Monitor"))
        
        # Create a second tab for future use
        self.tab2_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.tab2_label = Gtk.Label(label="Tab 2")
        self.notebook.append_page(self.tab2_box, self.tab2_label)
        
        # Replace the original box in the window with our notebook
        self.window.get_child().remove(self.io_monitor_box)
        self.window.add(self.notebook)
        
        # Connect HAL signals
        self.setup_hal_signals()
        
        # Show all widgets
        self.window.show_all()
        
        # Optional: Set the window position
        self.window.set_position(Gtk.WindowPosition.CENTER)
        
        # Optional: Make the window resizable
        self.window.set_resizable(True)
        
        # Optional: Set minimum window size
        self.window.set_size_request(400, 300)
    
    def setup_hal_signals(self):
        """Setup HAL signal connections"""
        # Example of how to connect HAL signals programmatically
        # This is optional since we're using hal_pin in the glade file
        try:
            # Example of connecting a signal programmatically
            self.hal.newpin("example_signal", hal.HAL_BIT, hal.HAL_OUT)
            self.hal.example_signal = True
        except Exception as e:
            print(f"Error setting up HAL signals: {e}")
    
    def on_window_destroy(self, widget, data=None):
        """Handle window close button"""
        Gtk.main_quit()
        return False
    
    def periodic(self):
        """Called periodically by the HAL component"""
        # Add any periodic updates here
        return True

def get_handlers(halcomp, builder, useropts):
    return [HandlerClass(halcomp, builder, useropts)] 