import subprocess
import os
from datetime import datetime
from django.conf import settings
import logging
import re
import pytz
import signal 

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
        self.media_folderpath = os.path.join(settings.BASE_DIR, 'media', 'processed_files')
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


    def pause_recording(self):
        self.stop_recording()
        self.stop_screen_grab()


    def resume_recording(self):
        self.part += 1
        self.start_recording(self.subject, self.part)
        self.start_screen_grab(self.part)
    

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
            self.filepath = os.path.join(files_dir, f"{self.timestamp}_recorded_video.mp4")

            # Run FFmpeg command to concatenate files
            concat_command = [
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_list_path,
                '-c', 'copy', self.filepath
            ]

            # Execute the FFmpeg process
            subprocess.run(concat_command, check=True)

            logger.info(f"All parts concatenated successfully into {self.filepath}")

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
    

    def rename_outputfile(self):
        # Once the recording stops, concatenate parts
        recorded_files = self.get_recorded_files()
        # Only one recording found, process it directly
        single_file = recorded_files[0]
        logger.info(f"Single file: {single_file}, No need concatination")
        # Path to the single file
        files_dir = os.path.join(self.media_folderpath, self.subject, self.timestamp)
        original_filepath = os.path.join(files_dir, single_file)

        # Remove the part number (_0) before the extension, if present
        base_name, extension = os.path.splitext(single_file)  # Separate the name and extension
        updated_name = base_name.rsplit('_', 1)[0] + extension
        self.filename = updated_name
        updated_filepath = os.path.join(files_dir, updated_name)
        self.filepath = updated_filepath
        logger.info(f"File renamed from {original_filepath} to {updated_filepath}")
        os.rename(original_filepath, self.filepath)

        return self.filepath


    def start_recording(self, subject, part=0):
        # self.part = part
        if part == 0:
            self.part = 0  # Reset part numbering for each new recording
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
        self.filename = f"{self.timestamp}_recorded_video_{self.part}.mp4"
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
                    stderr=self.devnull,
                    preexec_fn=os.setsid         
                )
                logger.info(f"Recording started: {self.filename}, File path: {self.filepath}")
            except Exception as e:
                logger.error(f"Error starting subprocess: {str(e)}")
        else:
            logger.error("Cannot start recording, audio device not found.")


    def stop_recording(self):
        if self.process and self.process.poll() is None:
            # Send 'q' to stop recording
            self.process.stdin.write(b'q')  # Encode 'q' as bytes
            self.process.stdin.flush()
            logger.info("Sent 'q' to stop recording.")
            
            # Wait for a brief moment to allow FFmpeg to terminate gracefully
            try:
                self.process.wait(timeout=5)  # Wait for a maximum of 5 seconds
                logger.info("Recording stopped gracefully.")
            except subprocess.TimeoutExpired:
                logger.warning("Recording did not stop in time. Attempting to terminate process.")
                self.process.terminate()  # Attempt to terminate
                
                try:
                    self.process.wait(timeout=3)  # Wait for a maximum of 5 seconds again
                    logger.info("Recording forcefully stopped.")
                except subprocess.TimeoutExpired:
                    logger.warning("Recording still running. Forcing termination.")
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)  # Force kill the process group
                    logger.info("Recording forcefully stopped using os.killpg.")
        else:
            logger.warning("No recording in progress.")



    def start_screen_grab(self, part=0):
        # self.part = part
        if part == 0:
            self.part = 0  # Reset part numbering for each new recording
            
        if self.grab_process and self.grab_process.poll() is None:
            logger.warning("Screen grab is already in progress.")
            return

        self.grabpath = os.path.join(self.media_folderpath, self.subject, self.timestamp)
        os.makedirs(self.grabpath, exist_ok=True)
        self.grab_filename = f"{self.timestamp}_screen_grab_{self.part}.mp4"
        self.grab_filepath = os.path.join(self.grabpath, self.grab_filename)

        self.grab_process = subprocess.Popen(
            ['ffmpeg', '-thread_queue_size', '1024', '-i', '/dev/video1', '-r', '30', '-c:v', 'hevc_rkmpp', '-preset', 'medium', '-crf', '21', self.grab_filepath],
            stdin=subprocess.PIPE,
            stdout=self.devnull,
            stderr=self.devnull,
            preexec_fn=os.setsid
        )
        logger.info(f"Screen Grab started: {self.grab_filename}, File path: {self.grab_filepath}")


    def stop_screen_grab(self):
        if self.grab_process and self.grab_process.poll() is None:
            # Send 'q' to stop the screen grab
            self.grab_process.stdin.write(b'q')  # Encode 'q' as bytes
            self.grab_process.stdin.flush()
            logger.info("Sent 'q' to stop screen grab.")
            
            # Wait for a brief moment to allow the process to terminate gracefully
            try:
                self.grab_process.wait(timeout=5)  # Wait for a maximum of 5 seconds
                logger.info("Screen grab stopped gracefully.")
            except subprocess.TimeoutExpired:
                logger.warning("Screen grab did not stop in time. Attempting to terminate process.")
                self.grab_process.terminate()  # Attempt to terminate
                
                try:
                    self.grab_process.wait(timeout=5)  # Wait for termination again
                    logger.info("Screen grab forcefully stopped.")
                except subprocess.TimeoutExpired:
                    logger.warning("Screen grab still running. Forcing termination.")
                    os.killpg(os.getpgid(self.grab_process.pid), signal.SIGKILL)  # Force kill the process group
                    logger.info("Screen grab forcefully stopped using os.killpg.")
        else:
            logger.warning("No screen grab in progress.")


    def get_screengrab_files(self):
        # Directory where parts are saved
        files_dir = os.path.join(self.media_folderpath, self.subject, self.timestamp)

        # Find all recorded video files
        screengrab_files = sorted(
            [f for f in os.listdir(files_dir) 
            if re.match(r'^\d{2}-\d{2}-\d{4}_\d{2}-\d{2}-\d{2}_screen_grab_\d+\.mp4$', f)],
            key=lambda x: int(re.search(r'_(\d+)\.mp4', x).group(1))
        )
        return screengrab_files


    def rename_screengrabfile(self):
        # Once the recording stops, concatenate parts
        screengrab_files = self.get_screengrab_files()
        # Only one recording found, process it directly
        single_file = screengrab_files[0]
        logger.info(f"Single file: {single_file}, No need concatination")
        # Path to the single file
        files_dir = os.path.join(self.media_folderpath, self.subject, self.timestamp)
        original_filepath = os.path.join(files_dir, single_file)

        # Remove the part number (_0) before the extension, if present
        base_name, extension = os.path.splitext(single_file)  # Separate the name and extension
        updated_name = base_name.rsplit('_', 1)[0] + extension

        updated_filepath = os.path.join(files_dir, updated_name)
        logger.info(f"File renamed from {original_filepath} to {updated_filepath}")
        os.rename(original_filepath, updated_filepath)

        return updated_name
    

    def concat_screengrab_parts(self):
        """Concatenate all screen grab parts into one final MP4 file."""
        try:
            # Directory where parts are saved
            files_dir = os.path.join(self.media_folderpath, self.subject, self.timestamp)

            # Find all part files in the directory that match the recorded video naming pattern
            part_files = sorted(
                [f for f in os.listdir(files_dir) 
                if re.match(r'^\d{2}-\d{2}-\d{4}_\d{2}-\d{2}-\d{2}_screen_grab_\d+\.mp4$', f)],  # Match the full naming pattern
                key=lambda x: int(re.search(r'_(\d+)\.mp4', x).group(1))  # Sort by part number
            )

            # Create a file with the list of files to be concatenated
            concat_screengrab_list_path = os.path.join(files_dir, "concat_screengrab_list.txt")
            with open(concat_screengrab_list_path, 'w') as concat_list:
                for part_file in part_files:
                    concat_list.write(f"file '{os.path.join(files_dir, part_file)}'\n")

            # Output file (final concatenated MP4 file)
            self.grab_filename= os.path.join(files_dir, f"{self.timestamp}_screen_grab.mp4")

            # Run FFmpeg command to concatenate files
            concat_command = [
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_screengrab_list_path,
                '-c', 'copy', self.grab_filename
            ]

            # Execute the FFmpeg process
            subprocess.run(concat_command, check=True)

            logger.info(f"All screen grab parts concatenated successfully into {self.grab_filename}")

        except Exception as e:
            logger.error(f"Error concatenating recording parts: {str(e)}")


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
