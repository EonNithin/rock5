import subprocess
import os
from datetime import datetime
from django.conf import settings
import logging
import re

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')

class Recorder:
    def __init__(self):
        self.process = None
        self.streaming_process = None
        self.grab_process = None
        self.stream_port = 8090  # You can choose a different port if needed
        self.timestamp = None
        self.subject = None
        self.media_folderpath = os.path.join(settings.BASE_DIR, 'media', 'processed_files')
        self.camera_url = 'rtsp://admin:hik@9753@192.168.0.252:554/Streaming/Channels/101'
        self.devnull = open(os.devnull, 'w')
        logger.info("Initialized Recorder")


    def update_timestamp(self):
        self.timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")


    def get_audio_device_info(self):
        # Run the arecord -l command and capture the output
        result = subprocess.run(['arecord', '-l'], stdout=subprocess.PIPE, text=True)

        # Check if the command was successful
        if result.returncode != 0:
            logger.error("Error running arecord command.")
            return None, None

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
            return f"hw:{card},{device}"
        else:
            logger.warning("No USB Composite Device found.")
            return None, None


    def start_recording(self, subject):
        self.update_timestamp()
        self.subject = subject

        if self.process and self.process.poll() is None:
            logger.warning("Recording is already in progress.")
            return

        # Get the audio device info
        self.audio_device = self.get_audio_device_info()

        # Log and check types of variables
        logger.info(f"Media folder path: {self.media_folderpath} (Type: {type(self.media_folderpath)})")
        logger.info(f"Subject: {self.subject} (Type: {type(self.subject)})")
        logger.info(f"Timestamp: {self.timestamp} (Type: {type(self.timestamp)})")

        # Construct the filepath
        self.filepath = os.path.join(self.media_folderpath, self.subject, self.timestamp)
        
        # Ensure the filepath is a valid string
        logger.info(f"Constructed filepath: {self.filepath} (Type: {type(self.filepath)})")

        # Create directory if not exists
        os.makedirs(self.filepath, exist_ok=True)

        # Create the filename
        self.filename = f"{self.timestamp}_recorded_video.mp4"
        logger.info(f"Filename: {self.filename} (Type: {type(self.filename)})")

        # Append filename to the filepath
        self.filepath = os.path.join(self.filepath, self.filename)
        logger.info(f"Full filepath with filename: {self.filepath} (Type: {type(self.filepath)})")

        # Start recording with ffmpeg
        if self.audio_device:
            try:
                self.process = subprocess.Popen(
                    ['ffmpeg', '-f', 'alsa', '-channels', '1', '-i', self.audio_device, '-i', self.camera_url, 
                    '-c:v', 'copy', '-c:a', 'aac', self.filepath],
                    stdin=subprocess.PIPE,
                    stdout=self.devnull,
                    stderr=self.devnull         
                )
                logger.info(f"Recording started: {self.filename}, File path: {self.filepath}")
            except Exception as e:
                logger.error(f"Error starting subprocess: {str(e)}")
        else:
            logger.error("Cannot start recording, audio device not found.")


    def start_screen_grab(self):
        if self.grab_process and self.grab_process.poll() is None:
            logger.warning("Screen grab is already in progress.")
            return

        self.grabpath = os.path.join(self.media_folderpath, self.subject, self.timestamp)
        os.makedirs(self.grabpath, exist_ok=True)
        self.grab_filename = f"{self.timestamp}_screen_grab.mp4"
        self.grab_filepath = os.path.join(self.grabpath, self.grab_filename)

        self.grab_process = subprocess.Popen(
            ['ffmpeg', '-thread_queue_size', '1024', '-i', '/dev/video1', '-r', '30', '-c:v', 'hevc_rkmpp', '-preset', 'medium', '-crf', '21', self.grab_filepath],
            stdin=subprocess.PIPE,
            stdout=self.devnull,
            stderr=self.devnull 
        )
        logger.info(f"Screen Grab started: {self.grab_filename}, File path: {self.grab_filepath}")


    def stop_recording(self):
        if self.process and self.process.poll() is None:
            self.process.stdin.write(b'q')  # Encode 'q' as bytes
            self.process.stdin.flush()
            self.process.wait()
            logger.info("Recording stopped.")
        else:
            logger.warning("No recording in progress.")


    def stop_screen_grab(self):
        if self.grab_process and self.grab_process.poll() is None:
            self.grab_process.stdin.write(b'q')  # Encode 'q' as bytes
            self.grab_process.stdin.flush()
            self.grab_process.wait()
            logger.info("Screen Grab stopped.")
        else:
            logger.warning("No screen grab in progress.")


    def get_file_info(self):
        logger.debug(f"File Info Retrieved: filename={self.filename}, filepath={self.filepath}")
        return {"filename": self.filename, "filepath": self.filepath}


    def __del__(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            logger.info("FFmpeg recording process terminated on deletion.")
        if self.streaming_process and self.streaming_process.poll() is None:
            self.streaming_process.terminate()
            logger.info("FFmpeg streaming process terminated on deletion.")


# if __name__ == "__main__":
#     recorder = Recorder()
#     # Here you can call methods like recorder.start_recording("example_subject")
