import subprocess
import re
import cv2
import pyaudio
import logging

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')

class CheckConnections:
    def __init__(self):
        self.rtsp_url = "rtsp://admin:hik@9753@192.168.0.252:554/Streaming/Channels/101"
        self.audio_device_index = self.get_audio_device_info()  # Getting device index for ALSA
        self.video_device_path = "/dev/video1"
        logger.info(f"Initialized CheckConnections")

    def get_audio_device_info(self):
        # Run the arecord -l command and capture the output
        result = subprocess.run(['arecord', '-l'], stdout=subprocess.PIPE, text=True)

        # Check if the command was successful
        if result.returncode != 0:
            logger.error("Error running arecord command.")
            return None

        # Decode the output
        output = result.stdout

        # Regular expression to match the card and device numbers
        device_pattern = re.compile(r'card (\d+): .*?\[.*?USB Composite Device.*?\], device (\d+):')

        # Search for the device in the output
        matches = device_pattern.findall(output)

        # Return the first found card and device number, if any
        if matches:
            card, device = matches[0]
            logger.info(f"Found audio device: Card {card}, Device {device}")
            return int(card)  # Returning the card as the index for PyAudio
        else:
            logger.warning("No USB Composite Device found.")
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

# # Example usage
# if __name__ == "__main__":
#     connections = CheckConnections()
#     # Test the devices
#     connections.test_rtsp_connection()
#     connections.test_alsa_connection()
#     connections.test_video_device()
