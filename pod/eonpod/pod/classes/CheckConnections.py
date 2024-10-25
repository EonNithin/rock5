import subprocess
import re
import cv2
import pyaudio
import logging

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')

class CheckConnections:
    def __init__(self):
        self.rtsp_url = "rtsp://admin:learneon@123@192.168.0.76:554/Streaming/Channels/101"
        self.audio_device_index = None # Getting device index for ALSA
        self.video_device_path = "/dev/video1"
        logger.info("Initialized CheckConnections")

    def get_audio_device_index(self):
        # Get the list of USB devices
        result = subprocess.run(['lsusb'], stdout=subprocess.PIPE, text=True)

        if result.returncode != 0:
            logger.error("Error running lsusb command.")
            return None

        output = result.stdout
        device_pattern = re.compile(r'Bus \d+ Device \d+: ID \d{4}:\d{4} .*?USB Composite Device')

        if device_pattern.search(output):
            logger.info("Found USB Composite Device.")
            # Attempt to get the device index using PyAudio
            audio_index = self.get_pyaudio_device_index("USB Composite Device")
            if audio_index is not None:
                logger.info(f"Audio device index found: {audio_index}")
                return audio_index
            else:
                logger.warning("No matching audio device found in PyAudio.")
        else:
            logger.warning("No USB Composite Device found.")
        return None


    def get_pyaudio_device_index(self, device_name):
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            logger.info(f"Info of detected device is {info}")
            if device_name in info['name']:
                logger.info(f"Found audio device: {info['name']} at index {i}")
                return i  # Return the index of the device
        logger.warning("No matching audio device found in PyAudio.")
        return None

    def test_rtsp_connection(self):
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
