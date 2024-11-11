import subprocess
import re
import cv2
import pyaudio
import logging
from dotenv import load_dotenv
# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')
import os 

class CheckConnections:
    def __init__(self):
        self.rtsp_url = None
        self.audio_device_index = None # Getting device index for ALSA
        self.video_device_path = "/dev/video1"
        logger.info("Initialized CheckConnections")

    def get_audio_device_index(self):
        # Find the device index by name
        device_index, hw_value = self.get_pyaudio_device_index("USB Composite Device")
        if device_index is not None:
            logger.info(f"Found audio device at index {device_index} with hw value {hw_value}")
            return device_index  # Use this integer index for ALSA
        else:
            logger.warning("No matching audio device found.")
        return None

    def get_pyaudio_device_index(self, device_name):
        p = pyaudio.PyAudio()
        hw_pattern = re.compile(r'\(hw:\d+,\d+\)')  # Pattern to find (hw:X,Y)
        
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            
            # Check if the device name matches
            if device_name in info['name']:
                logger.info(f"Info of detected device is {info}")
                # Extract the hw value if present
                hw_match = hw_pattern.search(info['name'])
                hw_value = hw_match.group() if hw_match else None
                logger.info(f"Found audio device: {info['name']} with index {i} and hw value {hw_value}")
                return i, hw_value  # Return index and hw value
        logger.warning("No matching audio device with hw value found in PyAudio.")
        return None, None


    def test_rtsp_connection(self):
        load_dotenv()
        self.rtsp_url = os.getenv('camera_url')
        logger.info(f"Testing RTSP connection to {self.rtsp_url}")
        cap = cv2.VideoCapture(self.rtsp_url)
        if cap.isOpened():
            logger.debug("RTSP connection successful!")
            cap.release()
            return True
        else:
            logger.error("Failed to connect to RTSP stream.")
            return False

    def test_alsa_connection(self):
        self.audio_device_index = self.get_audio_device_index() 
        if self.audio_device_index is None:
            logger.error("No audio device found, skipping ALSA test.")
            return False

        logger.info(f"Testing ALSA connection with device index {self.audio_device_index}")
        p = pyaudio.PyAudio()
        try:
            stream = p.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=48000,
                            input=True,
                            input_device_index=self.audio_device_index)

            logger.info("ALSA audio device is available at 48000 Hz!")
            data = stream.read(1024)
            logger.debug("Successfully read audio data.")

            stream.stop_stream()
            stream.close()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ALSA audio device: {e}")
            return False
        finally:
            p.terminate()

    def test_video_device(self):
        logger.info(f"Testing video device at {self.video_device_path}")
        cap = cv2.VideoCapture(self.video_device_path)
        if not cap.isOpened():
            logger.error(f"Failed to connect to video device at {self.video_device_path}. Check if the device path is correct and accessible.")
            return False

        ret, frame = cap.read()
        if ret:
            logger.info("Successfully read a frame from the video device.")
            cap.release()
            return True
        else:
            logger.error("Video device opened, but failed to read a frame.")
            cap.release()
            return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)  # Set to DEBUG for detailed logs
    connections = CheckConnections()

    if connections.test_rtsp_connection():
        logger.info("RTSP connection test was successful.")
    else:
        logger.error("RTSP connection test failed.")

    if connections.test_alsa_connection():
        logger.info("ALSA connection test was successful.")
    else:
        logger.error("ALSA connection test failed.")

    if connections.test_video_device():
        logger.info("Video device test was successful.")
    else:
        logger.error("Video device test failed.")
