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
        # self.logger = logging.getLogger('sensor_monitor')
        
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
        # self.logger.info(f"Initialized SensorMonitor processing thread, writing to {output_file}")

    def get_sensor_and_memory_data(self):
        """Execute sensors and free commands, and return the combined output"""
        try:
            # Run the `sensors` command
            sensors_result = subprocess.run(['sensors'],
                                            capture_output=True,
                                            text=True,
                                            check=True)
            sensors_output = sensors_result.stdout
        except subprocess.CalledProcessError as e:
            sensors_output = f"Error reading sensors: {str(e)}"
        except Exception as e:
            sensors_output = f"Unexpected error: {str(e)}"

        try:
            # Run the `free` command
            free_result = subprocess.run(['free', '-h'],  # Use '-h' for human-readable format
                                         capture_output=True,
                                         text=True,
                                         check=True)
            free_output = free_result.stdout
        except subprocess.CalledProcessError as e:
            free_output = f"Error reading memory data: {str(e)}"
        except Exception as e:
            free_output = f"Unexpected error: {str(e)}"

        # Combine outputs
        combined_output = f"Sensors Data:\n{sensors_output}\nMemory Data:\n{free_output}"
        return combined_output
    
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
            # self.logger.info(f"Appended sensor data at {timestamp}")
        except Exception as e:
            # self.logger.error(f"Error writing to file {self.output_file}: {e}")
            pass
    
    def monitor_sensors(self):
        """Main monitoring loop that runs in the background thread"""
        while self.is_running:
            try:
                # Get sensor data
                sensor_data = self.get_sensor_and_memory_data()
                
                # Append to file
                if sensor_data:
                    self.append_to_file(sensor_data)
                
                # Wait for 10 seconds
                time.sleep(180)
                
            except Exception as e:
                # self.logger.error(f"Error in monitor_sensors loop: {e}")
                time.sleep(10)  # Still sleep on error to prevent tight loop
    
    def stop(self):
        """Stop the monitoring thread"""
        self.is_running = False
        self.processing_thread.join()
        # self.logger.info("Stopped sensor monitoring")

