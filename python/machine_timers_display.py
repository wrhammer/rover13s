#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import os
import sqlite3
import time
from datetime import datetime

class MachineTimersDisplay(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Machine Timers")
        self.set_default_size(400, 500)
        
        # Get the config directory
        self.config_dir = os.environ.get('LINUXCNC_CONFIG_DIR', '')
        self.db_path = os.path.join(self.config_dir, 'logs', 'machine_timers.db')
        
        # Create main container
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.box.set_margin_start(10)
        self.box.set_margin_end(10)
        self.box.set_margin_top(10)
        self.box.set_margin_bottom(10)
        self.add(self.box)
        
        # Create frames and labels
        self.create_machine_times_frame()
        self.create_current_tool_frame()
        self.create_tool_history_frame()
        
        # Start update timer
        GLib.timeout_add(1000, self.update_times)  # Update every second
        
        # Connect delete event
        self.connect("delete-event", Gtk.main_quit)
    
    def create_machine_times_frame(self):
        frame = Gtk.Frame(label="Machine Times")
        frame.set_margin_bottom(10)
        self.box.pack_start(frame, False, False, 0)
        
        grid = Gtk.Grid()
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_row_spacing(5)
        grid.set_column_spacing(10)
        frame.add(grid)
        
        # Total Machine Time
        label = Gtk.Label(label="Total Machine Time:")
        label.set_xalign(0)
        grid.attach(label, 0, 0, 1, 1)
        
        self.total_machine_time = Gtk.Label(label="0:00:00")
        self.total_machine_time.set_xalign(1)
        grid.attach(self.total_machine_time, 1, 0, 1, 1)
        
        # Total Spindle Time
        label = Gtk.Label(label="Total Spindle Time:")
        label.set_xalign(0)
        grid.attach(label, 0, 1, 1, 1)
        
        self.total_spindle_time = Gtk.Label(label="0:00:00")
        self.total_spindle_time.set_xalign(1)
        grid.attach(self.total_spindle_time, 1, 1, 1, 1)
    
    def create_current_tool_frame(self):
        frame = Gtk.Frame(label="Current Tool")
        frame.set_margin_bottom(10)
        self.box.pack_start(frame, False, False, 0)
        
        grid = Gtk.Grid()
        grid.set_margin_start(10)
        grid.set_margin_end(10)
        grid.set_margin_top(10)
        grid.set_margin_bottom(10)
        grid.set_row_spacing(5)
        grid.set_column_spacing(10)
        frame.add(grid)
        
        # Tool Number
        label = Gtk.Label(label="Tool Number:")
        label.set_xalign(0)
        grid.attach(label, 0, 0, 1, 1)
        
        self.current_tool = Gtk.Label(label="0")
        self.current_tool.set_xalign(1)
        grid.attach(self.current_tool, 1, 0, 1, 1)
        
        # Tool Time
        label = Gtk.Label(label="Tool Time:")
        label.set_xalign(0)
        grid.attach(label, 0, 1, 1, 1)
        
        self.current_tool_time = Gtk.Label(label="0:00:00")
        self.current_tool_time.set_xalign(1)
        grid.attach(self.current_tool_time, 1, 1, 1, 1)
    
    def create_tool_history_frame(self):
        frame = Gtk.Frame(label="Tool History")
        frame.set_margin_bottom(10)
        self.box.pack_start(frame, True, True, 0)
        
        # Create scrolled window
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        frame.add(scrolled_window)
        
        # Create tree view
        self.tool_history = Gtk.TreeView()
        scrolled_window.add(self.tool_history)
        
        # Create list store
        self.tool_store = Gtk.ListStore(int, str)  # Tool number, Total time
        self.tool_history.set_model(self.tool_store)
        
        # Add columns
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Tool", renderer, text=0)
        self.tool_history.append_column(column)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Total Time", renderer, text=1)
        self.tool_history.append_column(column)
    
    def format_time(self, seconds):
        """Format seconds into HH:MM:SS"""
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
    
    def load_tool_history(self):
        """Load tool history from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Get all tool times
            c.execute("SELECT tool_number, total_time FROM tool_times ORDER BY tool_number")
            rows = c.fetchall()
            
            # Clear existing data
            self.tool_store.clear()
            
            # Add tool times to list store
            for tool_number, total_time in rows:
                time_str = self.format_time(total_time)
                self.tool_store.append([tool_number, time_str])
            
            conn.close()
        except Exception as e:
            print(f"Warning: Failed to load tool history: {e}")
    
    def update_times(self):
        """Update all time displays"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Get total machine time (time since first event)
            c.execute("SELECT MIN(timestamp) FROM events")
            first_event = c.fetchone()[0]
            if first_event:
                first_time = datetime.strptime(first_event, "%Y-%m-%d %H:%M:%S")
                machine_time = (datetime.now() - first_time).total_seconds()
                self.total_machine_time.set_text(self.format_time(machine_time))
            
            # Get total spindle time
            c.execute("SELECT value FROM accumulated_times WHERE key = 'total_spindle_time'")
            result = c.fetchone()
            if result:
                self.total_spindle_time.set_text(self.format_time(result[0]))
            
            # Get current tool and time
            c.execute("SELECT tool_number, total_time FROM tool_times ORDER BY tool_number DESC LIMIT 1")
            result = c.fetchone()
            if result:
                self.current_tool.set_text(str(result[0]))
                self.current_tool_time.set_text(self.format_time(result[1]))
            
            conn.close()
            
            # Reload tool history periodically
            if int(time.time()) % 30 == 0:  # Every 30 seconds
                self.load_tool_history()
            
        except Exception as e:
            print(f"Warning: Failed to update times: {e}")
        
        return True  # Keep the timer running

def main():
    win = MachineTimersDisplay()
    win.show_all()
    Gtk.main()

if __name__ == "__main__":
    main() 