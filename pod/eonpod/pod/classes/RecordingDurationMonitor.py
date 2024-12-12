# pod/classes/RecordingDurationMonitor.py

from threading import Thread
import time
import json
import logging
from django.http import JsonResponse

logger = logging.getLogger('pod')

class RecordingDurationMonitor:
    def __init__(self):
        self.current_recording_start_time = None
        self.current_recording_request = None
        self.RECORDING_LIMIT = 90 * 60  # 90 minutes in seconds
        self.monitor_thread = None
        
    def start_monitor(self):
        """Start the monitoring thread"""
        self.monitor_thread = Thread(target=self._monitor_recording_duration, daemon=True)
        self.monitor_thread.start()
        logger.info("Recording duration monitor thread started")
        
    def set_recording_start(self, request_data):
        """Set the recording start time and request data"""
        self.current_recording_request = request_data
        self.current_recording_start_time = time.time()
        logger.info("Recording start time set")
        
    def clear_recording_data(self):
        """Clear the recording data"""
        self.current_recording_start_time = None
        self.current_recording_request = None
        logger.info("Recording data cleared")
        
    def _monitor_recording_duration(self):
        """Monitor the recording duration"""
        while True:
            try:
                if self.current_recording_start_time is not None:
                    current_duration = time.time() - self.current_recording_start_time
                    
                    if current_duration >= self.RECORDING_LIMIT:
                        logger.info("Recording duration exceeded 90 minutes, restarting recording")
                        
                        # Create a fake request object with the stored data
                        class FakeRequest:
                            method = "POST"
                            body = json.dumps(self.current_recording_request).encode()
                        
                        from pod.views import stop_recording_view, start_recording_view  
                        
                        stop_recording_view(FakeRequest())
                        
                        start_recording_view(FakeRequest())
                        
                        self.current_recording_start_time = time.time()
                
                # Check every 5 seconds
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in monitor_recording_duration: {str(e)}")
                time.sleep(5)  # Wait before retrying