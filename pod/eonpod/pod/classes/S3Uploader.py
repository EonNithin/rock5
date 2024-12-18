import os
import subprocess
import boto3
from tqdm import tqdm
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pod.classes.JsonBuilder import JsonBuilder
import logging
from dotenv import load_dotenv

load_dotenv()

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')

aws_access_key_id = os.getenv('aws_access_key_id')
aws_secret_access_key = os.getenv('aws_secret_access_key')
region_name = os.getenv('region_name')
s3_bucket_name = os.getenv('s3_bucket_name')


class S3UploadQueue:
    def __init__(self):
        self.s3_queue = []
        self.lock = threading.Lock()
        self.json_info = JsonBuilder()
        
        self.s3_bucket_name = s3_bucket_name
        # AWS session setup
        self.session = boto3.session.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name
        )
        self.s3_resource = self.session.resource("s3")
        self.s3_client = self.session.client("s3")
        self.processing_thread = threading.Thread(target=self.process_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        logger.info(f"Initialized processing_thread for S3Uploader ")
    
    
    def compress_mp4(self, input_file, output_file, codec='libx264', crf=23):
        """
        Compress an MP4 file to a smaller size using ffmpeg.

        :param input_file: Path to the input MP4 file.
        :param output_file: Path where the compressed MP4 file will be saved.
        :param codec: Codec to use for compression (default is 'libx264').
        :param crf: Constant Rate Factor for quality (lower is better quality, default is 23).
        """
        try:
            command = [
                'ffmpeg',
                '-hwaccel',
                'rkmpp',
                '-i', input_file,       
                '-c:v', 'h264_rkmpp', '-b:v', '2000k', '-c:a', 'copy',    
                output_file             
            ]

            # Run the command
            subprocess.run(command, check=True)
            logger.info(f"Compressed video saved to: {output_file}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error compressing MP4: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")


    def create_folder_in_s3(self, folder_name):
        # Ensure the folder name ends with a trailing slash
        folder_key = folder_name if folder_name.endswith('/') else folder_name + '/'

        # Use the existing s3_client to put an empty object representing the folder
        try:
            self.s3_client.put_object(Bucket=self.s3_bucket_name, Key=folder_key)
            logger.info(f"Folder '{folder_name}' created successfully in bucket '{self.s3_bucket_name}'")
        except Exception as e:
            logger.error(f"Error creating folder '{folder_name}' in bucket '{self.s3_bucket_name}': {e}")


    def add_to_queue(self, school, subject, local_directory):
        # Expects a folderpath where we have all the files inplace
        # if True:
        with self.lock:
            for root, _, files in os.walk(local_directory):
                for file in files:
                    # Construct the full file path
                    file_path = os.path.join(root, file)

                    # Extract timestamp from the parent directory name
                    timestamp = os.path.basename(root)

                    # Add the file to the queue with relevant information
                    self.s3_queue.append({
                        "file_path": file_path,
                        "school": school,
                        "subject": subject,
                        "timestamp": timestamp,
                    })
                    logger.info(f"Added to queue: {file_path} for {subject} with timestamp {timestamp}")
   

    def check_edited_video(self, local_file_path):
        all_files =  os.listdir(os.path.dirname(local_file_path))
        if "recorded.mp4" in all_files or "screen_grab.mp4" in all_files:
            return True
        return False

    def upload_file(self, local_file_path, school, subject, timestamp):
        # Get the base name (filename) from the local file path
        file_name = os.path.basename(local_file_path)

        # Construct the S3 object key using the school, subject, and the file name

        s3_object_key = f"{school}/{subject}/{timestamp}/{file_name}"
        date = timestamp.split("_")[0]

        jsonfile = self.json_info.fetch_json_from_date_folder(date)
        if jsonfile is not None:
            jsondata = jsonfile[timestamp]
            logger.info(f"jsondata available for timestamp {timestamp}")  
        
            if jsondata is not None:
                # Extract the s3_path values
                s3_paths = jsondata.get("s3_path", [])
                logger.info(f"retrieved files available in s3_path for timestamp {timestamp}")  
                # Check if the file is in any of the s3_path values
                file_in_s3 = any(file_name in path for path in s3_paths)

                # Output the result
                if file_in_s3:
                    logger.info(f"{file_name} is already present in S3 paths, skipping upload.")
                    return  # No need to continue, exit function if file is already uploaded

        try:
            # Use the s3_client to upload the file 
            final_name = os.path.basename(local_file_path)
            timestamp_folder = os.path.dirname(local_file_path)
            is_ai_edited = self.check_edited_video(local_file_path)
            if is_ai_edited:
                local_file_path = os.path.join(timestamp_folder, "recorded.mp4") if "recorded_video.mp4" in local_file_path else os.path.join(timestamp_folder, "screen_grab.mp4")
                if "recorded" in local_file_path:
                    compressed_file_path = os.path.join(os.path.dirname(local_file_path), f"{timestamp}_compressed_file.mp4")
                    self.compress_mp4(input_file=local_file_path, output_file=compressed_file_path)
                    local_file_path = compressed_file_path  # Now use the compressed file for uploading    
            logger.info(f"compressed file path is : {local_file_path}")
            self.s3_client.upload_file(Filename=local_file_path, Bucket=self.s3_bucket_name, Key=s3_object_key)
            logger.info(f"Uploaded {local_file_path} to s3://{self.s3_bucket_name}/{s3_object_key}")
            self.json_info.update_s3(timestamp=timestamp, s3_path=s3_object_key, date = date)
        except Exception as e:
            logger.error(f"Error uploading file {local_file_path}: {e}")
            raise


    def count_files_and_upload(self, local_directory, school, subject):
        timestamp = os.path.basename(local_directory)
        self.create_folder_in_s3(folder_name=f"{school}/{subject}/{timestamp}")

        for root, _, files in os.walk(local_directory):
            for file in files:
                local_file_path = os.path.join(root, file)

                # Apply filter logic
                if file.endswith("_recorded_video.mp4"):
                    # Compress the _recorded_video.mp4 file before uploading
                    self.upload_file(local_file_path, school, subject, timestamp)
                elif file.endswith("_screen_grab.mp4") or file.endswith("_transcript.txt") or file.endswith(".mp3") or file == "folder_metadata.json":
                    # Upload screen_grab.mp4, transcript.txt, .mp3 and folder_metadata.json files
                    self.upload_file(local_file_path, school, subject, timestamp)
                else:
                    logger.info(f"Skipping file: {file}")


    def process_queue(self):

        while True:
            with self.lock:
                if not self.s3_queue:
                    time.sleep(10)  # Sleep for a while if the queue is empty
                    continue

                current_task = self.s3_queue.pop(0)

            try:
                file_path = current_task["file_path"]
                school = current_task["school"]
                subject = current_task["subject"]
                timestamp = current_task["timestamp"]

                logger.info(f"Starting S3 upload for {file_path}")
                # Upload the file with provided details
                self.upload_file(file_path, school, subject, timestamp)
                logger.info(f"Finished uploading file {file_path}")
            

            except Exception as e:
                logger.error(f"Error processing S3 upload for {file_path}: {str(e)}")
                # Re-add the current task to the queue in case of failure
                with self.lock:
                    self.s3_queue.append(current_task)
                logger.info(f"Re-added file to queue: {file_path}")
            time.sleep(20)  # Sleep for a short while before processing the next item


