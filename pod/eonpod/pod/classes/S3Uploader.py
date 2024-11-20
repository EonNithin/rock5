from datetime import datetime
import os
import subprocess
import boto3
from django.conf import settings
import threading
import time
from multiprocessing import Process, Lock, Manager, Queue
import logging
from dotenv import load_dotenv
from pod.classes.JsonBuilder import JsonBuilder
import json
import sys

load_dotenv(dotenv_path="base.env")
load_dotenv(dotenv_path="config.env", override=True)

logger = logging.getLogger('pod')

aws_access_key_id = os.getenv('aws_access_key_id')
aws_secret_access_key = os.getenv('aws_secret_access_key')
region_name = os.getenv('region_name')
s3_bucket_name = os.getenv('s3_bucket_name')

class S3UploadQueue:
    def __init__(self):
        self.json_file_path = os.path.join(settings.BASE_DIR, 'media', 'S3_queue_state.json')
        
        # Use Manager for shared state
        self.manager = Manager()
        # Use a Manager list for the queue
        self.upload_queue = self.manager.list()
        # Use Manager Lock for process-safe locking
        self.process_lock = self.manager.Lock()
        
        self.queue_buffer = 2

        self.shutdown_flag = self.manager.Value('b', False)
        self.json_info = JsonBuilder()
        self.s3_bucket_name = s3_bucket_name
        
        # Load existing queue
        self._load_existing_queue()
        
        # Initialize AWS clients
        self._initialize_aws_clients()
        
        # Start processing daemon
        self.processing_process = Process(target=self._process_queue)
        self.processing_process.daemon = True
        self.processing_process.start()
        logger.info(f"Initialized S3UploadQueue processor daemon with queue size: {len(self.upload_queue)}")

    def _load_existing_queue(self):
        """Load existing queue items from JSON file"""
        try:
            existing_items = self.load_queue_from_json()
            with self.process_lock:
                self.upload_queue.extend(existing_items)
                logger.info(f"Loaded {len(existing_items)} items from existing queue")
        except Exception as e:
            logger.error(f"Error loading existing queue: {str(e)}")

    def _initialize_aws_clients(self):
        """Initialize AWS clients with proper error handling"""
        try:
            self.session = boto3.session.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name
            )
            self.s3_resource = self.session.resource("s3")
            self.s3_client = self.session.client("s3")
            logger.info("Successfully initialized AWS clients")
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {str(e)}")
            raise

    def load_queue_from_json(self):
        """Load the queue state from the JSON file or create one if it doesn't exist."""
        if os.path.exists(self.json_file_path):
            try:
                with open(self.json_file_path, 'r') as json_file:
                    queue_data = json.load(json_file)
                    logger.info(f"Loaded queue from JSON file: {self.json_file_path}")
                    return queue_data
            except Exception as e:
                logger.error(f"Error loading queue from JSON file: {str(e)}", exc_info=True)
                return []
        else:
            logger.info(f"Queue JSON file not found at {self.json_file_path}. Creating a new one.")
            try:
                with open(self.json_file_path, 'w') as json_file:
                    json.dump([], json_file, indent=4)
                logger.info(f"Created a new empty JSON file at {self.json_file_path}.")
                return []
            except Exception as e:
                logger.error(f"Error creating the queue JSON file: {str(e)}", exc_info=True)
                return []

    def save_queue_to_json(self):
        """Save queue to JSON with proper locking"""
        try:
            current_queue = list(self.upload_queue)  # Convert manager list to regular list
            with open(self.json_file_path, 'w') as json_file:
                json.dump(current_queue, json_file, indent=4)
            logger.info(f"Saved queue to JSON. Current size: {len(current_queue)}")
        except Exception as e:
            logger.error(f"Error saving queue to JSON: {str(e)}", exc_info=True)

    def compress_mp4(self, input_file, output_file):
        """Compress an MP4 file using ffmpeg"""
        if not os.path.exists(input_file):
            logger.error(f"Input file does not exist: {input_file}")
            return False
            
        try:
            command = [
                'ffmpeg',
                '-hwaccel', 'rkmpp',
                '-i', input_file,       
                '-c:v', 'h264_rkmpp', 
                '-b:v', '2000k', 
                '-c:a', 'copy',    
                output_file             
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)
            
            if not os.path.exists(output_file):
                logger.error(f"Compression failed: Output file not created: {output_file}")
                return False
                
            logger.info(f"Successfully compressed video to: {output_file}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg compression failed: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error compressing MP4: {e}")
            return False

    def check_edited_video(self, local_file_path):
        """
        Check if edited video files exist and return both the check result and the replacement file path
        Returns: (bool, str or None) - (has_edited_files, replacement_path)
        """
        if not os.path.exists(local_file_path):
            logger.error(f"Local file path does not exist: {local_file_path}")
            return False, None
            
        directory = os.path.dirname(local_file_path)
        try:
            all_files = os.listdir(directory)
        except Exception as e:
            logger.error(f"Error listing directory {directory}: {e}")
            return False, None
            
        base_name = os.path.basename(local_file_path)
        
        has_edited_files = "recorded.mp4" in all_files or "ai_screen_grab.mp4" in all_files
        
        if not has_edited_files:
            return False, None
            
        if "_recorded_video.mp4" in base_name and "recorded.mp4" in all_files:
            replacement_path = os.path.join(directory, "recorded.mp4")
            if os.path.exists(replacement_path):
                return True, replacement_path
        elif "_screen_grab.mp4" in base_name and "ai_screen_grab.mp4" in all_files:
            replacement_path = os.path.join(directory, "ai_screen_grab.mp4")
            if os.path.exists(replacement_path):
                return True, replacement_path
        
        return True, None

    def _is_excluded(self, file_name):
        """Check if file should be excluded from processing"""
        excluded_list = ["grab_segment", "recorded_segment", "concat", "recorded_video_", "recorded.mp4", "ai_screen_grab.mp4", "screen_grab_"]
        for ex in excluded_list:
            if ex in file_name:
                return True
        return False

    def add_to_queue(self, school, subject, local_directory):
        """Add files to the upload queue with proper locking"""
        if not os.path.exists(local_directory):
            logger.error(f"Directory does not exist: {local_directory}")
            return
            
        try:
            files_to_add = []
            
            # First collect all files
            for root, _, files in os.walk(local_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    # if not os.path.exists(file_path):
                    #     continue
                    if os.path.exists(file_path):
                        # Get file size and store it alongside the file path
                        file_size = os.path.getsize(file_path)
                        files_to_add.append((file_size, file_path))
                    else:
                        logger.warning(f"File no longer exists: {file_path}")
                        continue

            # Sort files by size in descending order
            files_to_add.sort(reverse=True, key=lambda x: x[0])

            # Create tasks from sorted files
            tasks_to_add = []
            for file_size, file_path in files_to_add:
                timestamp = os.path.basename(os.path.dirname(file_path))  # Get parent folder name
                task = {
                    "file_path": file_path,
                    "school": school,
                    "subject": subject,
                    "timestamp": timestamp
                }
                tasks_to_add.append(task)

            # Add all files under a single lock
            with self.process_lock:
                original_size = len(self.upload_queue)
                for task in tasks_to_add:
                    self.upload_queue.append(task)
                    logger.info(f"Added to queue: {task['file_path']}")
                
                new_size = len(self.upload_queue)
                files_added = new_size - original_size
                
                logger.info(f"Added {files_added} files. Queue size now: {new_size}")
                self.save_queue_to_json()

        except Exception as e:
            logger.error(f"Error adding files to queue: {str(e)}", exc_info=True)


    def _upload_single_file(self, task):
        """Handle the upload of a single file with retries"""
        try:
            if not os.path.exists(task['file_path']):
                logger.error(f"Source file no longer exists: {task['file_path']}")
                return False

            original_file_name = os.path.basename(task['file_path'])
            
            if self._is_excluded(original_file_name):
                logger.info(f"{original_file_name} is in excluded list, skipping...")
                return True

            s3_object_key = f"{task['school']}/{task['subject']}/{task['timestamp']}/{original_file_name}"
            date = task['timestamp'].split("_")[0]

            # Check if file is already uploaded
            jsonfile = self.json_info.fetch_json_from_date_folder(date)
            if jsonfile and task['timestamp'] in jsonfile:
                s3_paths = jsonfile[task['timestamp']].get("s3_path", [])
                if any(original_file_name in path for path in s3_paths):
                    logger.info(f"{original_file_name} already present in S3, skipping")
                    return True

            # Check for edited videos and get replacement path if available
            has_edited_files, replacement_path = self.check_edited_video(task['file_path'])
            
            upload_path = task['file_path']
            if has_edited_files and replacement_path:
                if not os.path.exists(replacement_path):
                    logger.error(f"Replacement file does not exist: {replacement_path}")
                    return False
                    
                upload_path = replacement_path
                logger.info(f"Using edited file {replacement_path} instead of {task['file_path']}")
                
                if "_recorded_video.mp4" in original_file_name:
                    compressed_path = os.path.join(
                        os.path.dirname(task['file_path']),
                        f"{task['timestamp']}_compressed_file.mp4"
                    )
                    if not self.compress_mp4(upload_path, compressed_path):
                        logger.error(f"Failed to compress {upload_path}")
                        return False
                    upload_path = compressed_path
                    logger.info(f"Using compressed file {compressed_path}")

            if not os.path.exists(upload_path):
                logger.error(f"Final upload file does not exist: {upload_path}")
                return False

            try:
                if not os.path.isfile(upload_path):
                    logger.error(f"File does not exist: {upload_path}")
                    return False

                self.s3_client.upload_file(
                    Filename=upload_path,
                    Bucket=self.s3_bucket_name,
                    Key=s3_object_key
                )
                logger.info(f"Successfully uploaded to S3: {s3_object_key}")
            except Exception as e:
                logger.error(f"S3 upload failed for {upload_path}: {str(e)}")
                return False
            
            try:
                self.json_info.update_s3(
                    local_file_path=upload_path,
                    timestamp=task['timestamp'],
                    s3_path=s3_object_key,
                    date=date
                )
            except Exception as e:
                logger.error(f"Failed to update JSON info: {str(e)}")
            
            return True

        except Exception as e:
            logger.error(f"Error in _upload_single_file for {task['file_path']}: {str(e)}")
            return False

    def _process_queue(self):
        """Main queue processing loop with improved handling"""
        logger.info("Starting queue processor")
        
        # Initialize AWS clients in the processor
        try:
            self._initialize_aws_clients()
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients in processor: {str(e)}")
            return

        while not self.shutdown_flag.value:
            try:
                current_item = None
                queue_size = 0
                
                # Get item from queue with proper locking
                with self.process_lock:
                    queue_size = len(self.upload_queue)
                    if queue_size > 0:
                        current_item = self.upload_queue.pop(0)
                        logger.info(f"Processing item. Queue size now: {len(self.upload_queue)}")
                
                if current_item:
                    logger.info(f"Uploading file: {current_item['file_path']}")
                    
                    if not os.path.exists(current_item['file_path']):
                        logger.info(f"File no longer exists: {current_item['file_path']}")
                        continue
                    
                    current_timestamp = datetime.now()
                    file_timestamp = current_item['timestamp']
                    file_timestamp = datetime.strptime(file_timestamp, "%d-%m-%Y_%H-%M-%S")
                    # Subtract the timestamps
                    time_difference = current_timestamp - file_timestamp

                    if time_difference.days < self.queue_buffer:
                        success = self._upload_single_file(current_item)

                        if not success:
                            current_timestamp = datetime.now()
                            file_timestamp = current_item['timestamp']
                            file_timestamp = datetime.strptime(file_timestamp, "%d-%m-%Y_%H-%M-%S")
                            # Subtract the timestamps
                            time_difference = current_timestamp - file_timestamp

                            if time_difference.days < self.queue_buffer:
                                logger.info(f"Retrying upload for {current_item['file_path']} ")
                                # Re-add to queue with proper locking
                                with self.process_lock:
                                    self.upload_queue.append(current_item)
                                    self.save_queue_to_json()
                                time.sleep(300)
                            else:
                                logger.error(f"Failed to upload {current_item['file_path']} as buffer size exceeded")
                                with self.process_lock:
                                    self.save_queue_to_json()
                        else:
                            logger.info(f"Successfully processed: {current_item['file_path']}")
                            with self.process_lock:
                                self.save_queue_to_json()
                    else:
                        logger.info("Not uploading as buffer size exceeded")
                    # Small delay between processing files
                    time.sleep(30)
                else:
                    # Longer delay when queue is empty
                    time.sleep(300)

            except Exception as e:
                logger.error(f"Error in queue processor: {str(e)}", exc_info=True)
                time.sleep(5)

        logger.info("Queue processor shutting down")
