import subprocess
import os
from datetime import datetime
from django.conf import settings
import logging

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
        logger.info(f"Initialized Recorder ")

    def update_timestamp(self):
        self.timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")

    def start_recording(self, subject):
        self.update_timestamp()
        self.subject = subject
        if self.process and self.process.poll() is None:
            logger.warning("Recording is already in progress.")
            return

        self.filepath = os.path.join(self.media_folderpath, self.subject, self.timestamp)
        os.makedirs(self.filepath, exist_ok=True)
        self.filename = f"{self.timestamp}_recorded_video.mp4"
        self.filepath = os.path.join(self.filepath, self.filename)

        self.process = subprocess.Popen(
            ['ffmpeg', '-f', 'alsa', '-channels', '1', '-i', 'hw:5,0', '-i', self.camera_url, '-c:v', 'copy', '-c:a', 'aac', self.filepath],
            stdin=subprocess.PIPE,
            stdout=self.devnull, 
            stderr=self.devnull         
        )
        logger.info(f"Recording started: {self.filename}, File path: {self.filepath}")

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

