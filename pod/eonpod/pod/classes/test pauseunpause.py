import subprocess
import os
from datetime import datetime
import logging
import re
import pytz
import time

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')

class Recorder:
    def __init__(self):
        self.process = None
        self.streaming_process = None
        self.grab_process = None
        self.stream_port = 8090  # You can choose a different port if needed
        self.timestamp = None
        self.timezone = pytz.timezone('Asia/Kolkata')
        self.subject = None
        self.part = 0
        base_dir = "/home/eon/Desktop/rock5/pod/eonpod/media/processed_files"  # Change this to your desired folder path
        self.media_folderpath = os.path.join(base_dir)
        print(f"Media folder path: {self.media_folderpath}")
        self.camera_url = 'rtsp://admin:hik@9753@192.168.0.252:554/Streaming/Channels/101'
        self.devnull = open(os.devnull, 'w')
        logger.info("Initialized Recorder")

    def update_timestamp(self):
        self.timestamp = datetime.now(self.timezone).strftime("%d-%m-%Y_%H-%M-%S")

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
        match = device_pattern.search(output)

        # Return the device path (e.g., hw:0,0) if a match is found
        if match:
            card, device = match.groups()
            device_str = f"hw:{card},{device}"
            logger.info(f"Found audio device: {device_str}")
            return device_str
        else:
            logger.warning("No USB Composite Device found.")
            return None


    def pause_recording(self):
        self.stop_recording()


    def unpause_recording(self):
        self.part += 1
        self.start_recording(self.subject, self.part)


    def concat_recording_parts(self):
        """Concatenate all recorded parts into one final MP4 file."""
        try:
            # Directory where parts are saved
            files_dir = os.path.join(self.media_folderpath, self.subject, self.timestamp)

            # Find all part files in the directory that match the recorded video naming pattern
            part_files = sorted(
                [f for f in os.listdir(files_dir) 
                if re.match(r'^\d{2}-\d{2}-\d{4}_\d{2}-\d{2}-\d{2}_recorded_video_\d+\.mp4$', f)],  # Match the full naming pattern
                key=lambda x: int(re.search(r'_(\d+)\.mp4', x).group(1))  # Sort by part number
            )

            # Create a file with the list of files to be concatenated
            concat_list_path = os.path.join(files_dir, "concat_list.txt")
            with open(concat_list_path, 'w') as concat_list:
                for part_file in part_files:
                    concat_list.write(f"file '{os.path.join(files_dir, part_file)}'\n")

            # Output file (final concatenated MP4 file)
            output_file = os.path.join(files_dir, f"{self.timestamp}_recorded_video.mp4")

            # Run FFmpeg command to concatenate files
            concat_command = [
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_list_path,
                '-c', 'copy', output_file
            ]

            # Execute the FFmpeg process
            subprocess.run(concat_command, check=True)

            logger.info(f"All parts concatenated successfully into {output_file}")

        except Exception as e:
            logger.error(f"Error concatenating recording parts: {str(e)}")


    def get_recorded_files(self):
        # Directory where parts are saved
        files_dir = os.path.join(self.media_folderpath, self.subject, self.timestamp)

        # Find all recorded video files
        recorded_files = sorted(
            [f for f in os.listdir(files_dir) 
            if re.match(r'^\d{2}-\d{2}-\d{4}_\d{2}-\d{2}-\d{2}_recorded_video_\d+\.mp4$', f)],
            key=lambda x: int(re.search(r'_(\d+)\.mp4', x).group(1))
        )
        return recorded_files
    

    def start_recording(self, subject="Science", part=0):
        if part == 0:
            self.update_timestamp()
        self.subject = subject

        if self.process and self.process.poll() is None:
            logger.warning("Recording is already in progress.")
            return

        # Get the audio device info
        self.audio_device = self.get_audio_device_info()

        if not self.audio_device:
            logger.error("Cannot start recording, audio device not found.")
            return

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
        self.filename = f"{self.timestamp}_recorded_video_{self.part}.mp4"
        logger.info(f"Filename: {self.filename} (Type: {type(self.filename)})")

        # Append filename to the filepath
        self.filepath = os.path.join(self.filepath, self.filename)
        logger.info(f"Full filepath with filename: {self.filepath} (Type: {type(self.filepath)})")

        # Start recording with ffmpeg
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
            # self.concat_recording_parts()

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


if __name__ == "__main__":
    recorder = Recorder()
    # Here you can call methods like recorder.start_recording("example_subject")
    print("started recording")
    recorder.start_recording()
    time.sleep(60)

    print("pause recording")
    recorder.pause_recording()
    time.sleep(30)

    print("unpause recording")
    recorder.unpause_recording()
    time.sleep(30)

    print("pause recording")
    recorder.pause_recording()
    time.sleep(30)

    print("unpause recording")
    recorder.unpause_recording()
    time.sleep(30)

    print("stopped recording")
    recorder.stop_recording()
    time.sleep(10)

        # Once the recording stops, concatenate parts
    recorded_files = recorder.get_recorded_files()

    if len(recorded_files) == 0:
        print("No recordings found.")
    elif len(recorded_files) == 1:
        # Only one recording found, process it directly
        single_file = recorded_files[0]
        print(f"Single file: {single_file}, No need concatination")
    else:
        # Multiple recordings found, concatenate them
        print("Multiple recordings found, concatenating...")
        # Call your concatenation function here
        recorder.concat_recording_parts()

   
         