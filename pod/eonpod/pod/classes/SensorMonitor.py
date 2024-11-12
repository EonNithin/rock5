import os
import subprocess
import threading
import time
import logging
from datetime import datetime
import pytz  # For timezone handling

class SensorMonitor:
    def __init__(self, output_file="sensor_logs.txt"):
        # Initialize logger
        self.logger = logging.getLogger('sensor_monitor')
        
        # Timezone setup
        self.timezone = pytz.timezone('Asia/Kolkata')
        
        # Setup output file path and directory
        self.output_file = output_file
        output_directory = os.path.dirname(output_file)
        if output_directory and not os.path.exists(output_directory):
            os.makedirs(output_directory)
            
        # Initialize threading components
        self.lock = threading.Lock()
        self.processing_thread = threading.Thread(target=self.monitor_sensors)
        self.processing_thread.daemon = True
        self.is_running = True
        
        # Start the monitoring thread
        self.processing_thread.start()
        self.logger.info(f"Initialized SensorMonitor processing thread, writing to {output_file}")
    
    def get_sensor_data(self):
        """Execute sensors command and return the output"""
        try:
            result = subprocess.run(['sensors'], 
                                  capture_output=True, 
                                  text=True, 
                                  check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Error running sensors command: {e}")
            return f"Error reading sensors: {str(e)}"
        except Exception as e:
            self.logger.error(f"Unexpected error getting sensor data: {e}")
            return f"Unexpected error: {str(e)}"
    
    def append_to_file(self, data):
        # Get the current time in the specified timezone
        now = datetime.now(self.timezone)
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S %Z")
    
        try:
            with self.lock:
                with open(self.output_file, 'a') as f:
                    f.write(f"\n=== {timestamp} ===\n")
                    f.write(data)
                    f.write("\n" + "=" * 50 + "\n")
            self.logger.info(f"Appended sensor data at {timestamp}")
        except Exception as e:
            self.logger.error(f"Error writing to file {self.output_file}: {e}")
    
    def monitor_sensors(self):
        """Main monitoring loop that runs in the background thread"""
        while self.is_running:
            try:
                # Get sensor data
                sensor_data = self.get_sensor_data()
                
                # Append to file
                if sensor_data:
                    self.append_to_file(sensor_data)
                
                # Wait for 10 seconds
                time.sleep(10)
                
            except Exception as e:
                self.logger.error(f"Error in monitor_sensors loop: {e}")
                time.sleep(10)  # Still sleep on error to prevent tight loop
    
    def stop(self):
        """Stop the monitoring thread"""
        self.is_running = False
        self.processing_thread.join()
        self.logger.info("Stopped sensor monitoring")

