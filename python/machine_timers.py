#!/usr/bin/env python3

import hal
import time
import os
from datetime import datetime
import sqlite3
# Firestore imports commented out for now
# import firebase_admin
# from firebase_admin import credentials, firestore
# from google.cloud import firestore as firestore_types

class MachineTimers:
    def __init__(self):
        self.h = hal.component("machine_timers")
        
        # Input pins
        self.h.newpin("spindle_on", hal.HAL_BIT, hal.HAL_IN)        # Spindle running state
        self.h.newpin("machine_running", hal.HAL_BIT, hal.HAL_IN)    # Machine running state
        self.h.newpin("current_tool", hal.HAL_S32, hal.HAL_IN)       # Current tool number
        
        # Output pins for total times (in seconds)
        self.h.newpin("total_machine_time", hal.HAL_FLOAT, hal.HAL_OUT)
        self.h.newpin("total_spindle_time", hal.HAL_FLOAT, hal.HAL_OUT)
        self.h.newpin("current_tool_time", hal.HAL_FLOAT, hal.HAL_OUT)
        
        # State variables
        self.start_time = time.time()
        self.spindle_start_time = 0
        self.tool_start_time = 0
        self.last_tool = 0
        
        # Initialize outputs
        self.h.total_machine_time = 0.0
        self.h.total_spindle_time = 0.0
        self.h.current_tool_time = 0.0
        
        # Create log directory if it doesn't exist
        self.log_dir = os.path.join(os.environ.get('LINUXCNC_CONFIG_DIR', ''), 'logs')
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Initialize SQLite database
        self.db_path = os.path.join(self.log_dir, 'machine_timers.db')
        self.init_database()
        
        # Load accumulated times from database
        self.load_accumulated_times()
        
        # Firestore initialization commented out for now
        # try:
        #     # Get the config directory from the environment
        #     config_dir = os.environ.get('LINUXCNC_CONFIG_DIR', '')
        #     if not config_dir:
        #         print("Warning: LINUXCNC_CONFIG_DIR not set, Firestore disabled")
        #         self.firestore_enabled = False
        #     else:
        #         # Initialize Firebase Admin SDK
        #         cred_path = os.path.join(config_dir, 'firebase-credentials.json')
        #         if os.path.exists(cred_path):
        #             cred = credentials.Certificate(cred_path)
        #             firebase_admin.initialize_app(cred)
        #             self.db = firestore.client()
        #             self.firestore_enabled = True
        #             print("Firestore initialized successfully")
        #         else:
        #             print(f"Warning: Firebase credentials not found at {cred_path}")
        #             self.firestore_enabled = False
        # except Exception as e:
        #     print(f"Warning: Failed to initialize Firestore: {e}")
        #     self.firestore_enabled = False
        
        print("Machine Timers initialized")
        self.h.ready()
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Create events table
            c.execute('''CREATE TABLE IF NOT EXISTS events
                        (timestamp TEXT, event_type TEXT, details TEXT)''')
            
            # Create accumulated_times table
            c.execute('''CREATE TABLE IF NOT EXISTS accumulated_times
                        (key TEXT PRIMARY KEY, value REAL)''')
            
            # Create tool_times table
            c.execute('''CREATE TABLE IF NOT EXISTS tool_times
                        (tool_number INTEGER, total_time REAL)''')
            
            conn.commit()
            conn.close()
            print(f"Database initialized at {self.db_path}")
        except Exception as e:
            print(f"Warning: Failed to initialize database: {e}")
    
    def load_accumulated_times(self):
        """Load accumulated times from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Load total spindle time
            c.execute("SELECT value FROM accumulated_times WHERE key = 'total_spindle_time'")
            result = c.execute("SELECT value FROM accumulated_times WHERE key = 'total_spindle_time'").fetchone()
            if result:
                self.h.total_spindle_time = float(result[0])
            
            conn.close()
        except Exception as e:
            print(f"Warning: Failed to load accumulated times: {e}")
    
    def save_accumulated_times(self):
        """Save accumulated times to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Save total spindle time
            c.execute("""INSERT OR REPLACE INTO accumulated_times (key, value)
                        VALUES ('total_spindle_time', ?)""", (self.h.total_spindle_time,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Warning: Failed to save accumulated times: {e}")
    
    def log_event(self, event_type, details=""):
        """Log timing events to file and database"""
        timestamp = datetime.now()
        
        # Log to file
        log_file = os.path.join(self.log_dir, f"machine_timers_{timestamp.strftime('%Y%m%d')}.log")
        with open(log_file, "a") as f:
            f.write(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {event_type}: {details}\n")
        
        # Log to database
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute("""INSERT INTO events (timestamp, event_type, details)
                        VALUES (?, ?, ?)""", 
                        (timestamp.strftime('%Y-%m-%d %H:%M:%S'), event_type, details))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Warning: Failed to log event to database: {e}")
    
    def update_tool_time(self, tool_number, duration):
        """Update accumulated time for a specific tool"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Get current tool time
            c.execute("SELECT total_time FROM tool_times WHERE tool_number = ?", (tool_number,))
            result = c.execute("SELECT total_time FROM tool_times WHERE tool_number = ?", (tool_number,)).fetchone()
            
            current_time = float(result[0]) if result else 0.0
            new_time = current_time + duration
            
            # Update tool time
            c.execute("""INSERT OR REPLACE INTO tool_times (tool_number, total_time)
                        VALUES (?, ?)""", (tool_number, new_time))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Warning: Failed to update tool time: {e}")
    
    def update(self):
        current_time = time.time()
        
        # Update total machine time
        self.h.total_machine_time = current_time - self.start_time
        
        # Update spindle time
        if self.h.spindle_on:
            if self.spindle_start_time == 0:
                self.spindle_start_time = current_time
                self.log_event("SPINDLE_START", f"Tool: {self.h.current_tool}")
        else:
            if self.spindle_start_time != 0:
                spindle_duration = current_time - self.spindle_start_time
                self.h.total_spindle_time += spindle_duration
                self.spindle_start_time = 0
                self.log_event("SPINDLE_STOP", f"Duration: {spindle_duration:.1f}s, Tool: {self.h.current_tool}")
                self.save_accumulated_times()
        
        # Update tool time
        if self.h.current_tool != self.last_tool:
            if self.tool_start_time != 0:
                tool_duration = current_time - self.tool_start_time
                self.log_event("TOOL_CHANGE", 
                             f"From: {self.last_tool}, To: {self.h.current_tool}, Duration: {tool_duration:.1f}s")
                self.update_tool_time(self.last_tool, tool_duration)
            
            self.tool_start_time = current_time
            self.last_tool = self.h.current_tool
        
        self.h.current_tool_time = current_time - self.tool_start_time

def main():
    timers = MachineTimers()
    
    try:
        while True:
            timers.update()
            time.sleep(0.1)  # 100ms update rate
            
    except KeyboardInterrupt:
        raise SystemExit

if __name__ == "__main__":
    main() 