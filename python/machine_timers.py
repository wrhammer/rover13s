#!/usr/bin/env python3

import hal
import time
import os
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as firestore_types

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
        
        # Initialize Firestore
        try:
            # Get the config directory from the environment
            config_dir = os.environ.get('LINUXCNC_CONFIG_DIR', '')
            if not config_dir:
                print("Warning: LINUXCNC_CONFIG_DIR not set, Firestore disabled")
                self.firestore_enabled = False
            else:
                # Initialize Firebase Admin SDK
                cred_path = os.path.join(config_dir, 'firebase-credentials.json')
                if os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    self.db = firestore.client()
                    self.firestore_enabled = True
                    print("Firestore initialized successfully")
                else:
                    print(f"Warning: Firebase credentials not found at {cred_path}")
                    self.firestore_enabled = False
        except Exception as e:
            print(f"Warning: Failed to initialize Firestore: {e}")
            self.firestore_enabled = False
        
        print("Machine Timers initialized")
        self.h.ready()
    
    def log_event(self, event_type, details=""):
        """Log timing events to a file and Firestore"""
        timestamp = datetime.now()
        log_file = os.path.join(self.log_dir, f"machine_timers_{timestamp.strftime('%Y%m%d')}.log")
        
        # Log to file
        with open(log_file, "a") as f:
            f.write(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {event_type}: {details}\n")
        
        # Log to Firestore if enabled
        if self.firestore_enabled:
            try:
                # Create a new document in the events collection
                event_data = {
                    'timestamp': firestore_types.SERVER_TIMESTAMP,
                    'event_type': event_type,
                    'details': details,
                    'machine_time': self.h.total_machine_time,
                    'spindle_time': self.h.total_spindle_time,
                    'current_tool': self.h.current_tool,
                    'current_tool_time': self.h.current_tool_time
                }
                
                self.db.collection('machine_events').add(event_data)
                
                # Update daily summary
                daily_doc = self.db.collection('daily_summaries').document(timestamp.strftime('%Y%m%d'))
                daily_doc.set({
                    'date': timestamp.strftime('%Y-%m-%d'),
                    'total_machine_time': self.h.total_machine_time,
                    'total_spindle_time': self.h.total_spindle_time,
                    'tool_times': {
                        str(self.h.current_tool): self.h.current_tool_time
                    }
                }, merge=True)
                
            except Exception as e:
                print(f"Warning: Failed to log to Firestore: {e}")
    
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
        
        # Update tool time
        if self.h.current_tool != self.last_tool:
            if self.tool_start_time != 0:
                tool_duration = current_time - self.tool_start_time
                self.log_event("TOOL_CHANGE", 
                             f"From: {self.last_tool}, To: {self.h.current_tool}, Duration: {tool_duration:.1f}s")
            
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