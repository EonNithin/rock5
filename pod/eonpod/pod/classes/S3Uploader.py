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
from multiprocessing import Process, Queue
from queue import Empty
import sys


load_dotenv()

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')

aws_access_key_id = os.getenv('aws_access_key_id')
aws_secret_access_key = os.getenv('aws_secret_access_key')
region_name = os.getenv('region_name')
s3_bucket_name = os.getenv('s3_bucket_name')

class S3UploadTask:
    def __init__(self, file_path, school, subject, timestamp):
        self.file_path = file_path
        self.school = school
        self.subject = subject
        self.timestamp = timestamp
        self.retry_count = 0
        self.max_retries = 7

class S3UploadQueue:
    def __init__(self):
        self.upload_queue = Queue()
        self.process_lock = threading.Lock()
        self.shutdown_flag = False
        self.json_info = JsonBuilder()
        self.s3_bucket_name = s3_bucket_name
        
        # Initialize AWS clients
        self._initialize_aws_clients()
        
        # Start the processing daemon
        self.processing_process = Process(target=self._process_queue, daemon=True)
        self.processing_process.start()
        logger.info("Initialized S3UploadQueue processor daemon")
        

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
                
            logger.info(f"Compressed video saved to: {output_file}")
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

    def add_to_queue(self, school, subject, local_directory):
        """Add files to the upload queue - can be called from any process"""
        if not os.path.exists(local_directory):
            logger.error(f"Directory does not exist: {local_directory}")
            return
            
        try:
            file_count = 0
            for root, _, files in os.walk(local_directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if not os.path.exists(file_path):
                        logger.warning(f"File no longer exists: {file_path}")
                        continue
                        
                    timestamp = os.path.basename(root)
                    
                    task = S3UploadTask(
                        file_path=file_path,
                        school=school,
                        subject=subject,
                        timestamp=timestamp
                    )
                    
                    self.upload_queue.put(task)
                    file_count += 1
                    logger.info(f"Added to queue: {file_path} for {subject} with timestamp {timestamp}")
            
            logger.info(f"Added {file_count} files to upload queue from {local_directory}")
        except Exception as e:
            logger.error(f"Error adding files to queue: {str(e)}")

    def _is_excluded(self, file_name):
        excluded_list = ["segment", "concat", "recorded_video_", "recorded.mp4", "ai_screen_grab.mp4", "screen_grab_"]
        for ex in excluded_list:
            if ex in file_name:
                return True
        return False

    def _upload_single_file(self, task):
        """Handle the upload of a single file with retries"""
        try:
            with self.process_lock:
                if not os.path.exists(task.file_path):
                    logger.error(f"Source file no longer exists: {task.file_path}")
                    return False

                original_file_name = os.path.basename(task.file_path)
                
                if self._is_excluded(original_file_name):
                    logger.info(f"{original_file_name} is in excluded list, so ignoring it...")
                    return True

                s3_object_key = f"{task.school}/{task.subject}/{task.timestamp}/{original_file_name}"
                date = task.timestamp.split("_")[0]

                # Check if file is already uploaded
                jsonfile = self.json_info.fetch_json_from_date_folder(date)
                if jsonfile and task.timestamp in jsonfile:
                    s3_paths = jsonfile[task.timestamp].get("s3_path", [])
                    if any(original_file_name in path for path in s3_paths):
                        logger.info(f"{original_file_name} already present in S3, skipping")
                        return True

                # Check for edited videos and get replacement path if available
                has_edited_files, replacement_path = self.check_edited_video(task.file_path)
                
                # Determine the actual file to upload
                upload_path = task.file_path
                if has_edited_files and replacement_path:
                    if not os.path.exists(replacement_path):
                        logger.error(f"Replacement file does not exist: {replacement_path}")
                        return False
                        
                    upload_path = replacement_path
                    logger.info(f"Using edited file {replacement_path} instead of {task.file_path}")
                    
                    # Handle compression for recorded video
                    if "_recorded_video.mp4" in original_file_name:
                        compressed_path = os.path.join(
                            os.path.dirname(task.file_path),
                            f"{task.timestamp}_compressed_file.mp4"
                        )
                        if not self.compress_mp4(upload_path, compressed_path):
                            logger.error(f"Failed to compress {upload_path}")
                            return False
                        upload_path = compressed_path
                        logger.info(f"Using compressed file {compressed_path}")

                # Verify the final upload path exists
                if not os.path.exists(upload_path):
                    logger.error(f"Final upload file does not exist: {upload_path}")
                    return False

                # Perform the upload
                try:
                # logger.debug(f"upload_path: {upload_path} (type: {type(upload_path)})")
                # logger.debug(f"s3_bucket_name: {s3_bucket_name} (type: {type(s3_bucket_name)})")
                # logger.debug(f"s3_object_key: {s3_object_key} (type: {type(s3_object_key)})")
                    # Check if the file exists
                    if not os.path.isfile(upload_path):
                        logger.error(f"File does not exist: {upload_path}")
                        return False

                    self.s3_client.upload_file(
                        Filename=upload_path,
                        Bucket=self.s3_bucket_name,
                        Key=s3_object_key
                    )
                except Exception as e:
                    logger.error(f"S3 upload failed for {upload_path}: {str(e)}")
                    return False
                
                # Update JSON info
                try:
                    self.json_info.update_s3(
                        local_file_path = upload_path,
                        timestamp=task.timestamp,
                        s3_path=s3_object_key,
                        date=date
                    )
                except Exception as e:
                    logger.error(f"Failed to update JSON info: {str(e)}")
                    # Don't return False here as the file was uploaded successfully
                
                logger.info(f"Successfully uploaded {upload_path} to S3 as {s3_object_key}")
                return True

        except Exception as e:
            logger.error(f"Error in _upload_single_file for {task.file_path}: {str(e)}")
            return False

    def _process_queue(self):
        """Main queue processing loop"""
        # Initialize AWS clients in the child process
        try:
            self._initialize_aws_clients()
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients in processing thread: {str(e)}")
            return
            
        while not self.shutdown_flag:
            try:
                # Try to get a task with timeout
                task = self.upload_queue.get(timeout=5)
                
                # Verify file still exists before processing
                if not os.path.exists(task.file_path):
                    logger.warning(f"File no longer exists, skipping: {task.file_path}")
                    continue
                
                # Process the task
                success = self._upload_single_file(task)
                
                if not success and task.retry_count < task.max_retries:
                    # Re-queue failed task with increased retry count
                    task.retry_count += 1
                    logger.info(f"Retrying upload for {task.file_path} (attempt {task.retry_count}/{task.max_retries})")
                    self.upload_queue.put(task)
                elif not success:
                    logger.error(f"Failed to upload {task.file_path} after {task.max_retries} attempts")
                
                time.sleep(1)
                
            except Empty:
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error in queue processor: {str(e)}")
                time.sleep(5)

    def get_queue_size(self):
        """Get current size of upload queue"""
        try:
            return self.upload_queue.qsize()
        except Exception as e:
            logger.error(f"Error getting queue size: {str(e)}")
            return 0
