import threading
import time
import os
from django.conf import settings
from pod.classes.FileProcessor import FileProcessor
from pod.classes.Delete import DeletionJob
from pod.classes.FallbackFileProcessor import FallbackFileProcessor
from pod.classes.S3Uploader import S3UploadQueue
import logging
import json

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')


class ProcessingQueue:
    def __init__(self):
        self.mp4_paths = {}
        self.lock = threading.Lock()
        self.processing_thread = threading.Thread(target=self.process_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        self.processor = FileProcessor()
        self.media_folderpath = os.path.join(settings.BASE_DIR, 'media', 'processed_files')
        self.delete_obj = DeletionJob()
        self.fallback = FallbackFileProcessor()
        self.s3_obj = S3UploadQueue()
        logger.info(f"Initialized ProcessingQueue")


    def add_to_queue(self, file_name, file_path, subject, is_language = False):
        with self.lock:
            self.mp4_paths[file_name] = {"file_path": file_path, "status": "NotStarted", "is_language": is_language, "subject": subject }
        logger.info(f"Added to queue: {file_name} with path: {file_path}, subject: {subject}")


    def process_queue(self):
        while True:
            with self.lock:
                files_to_delete = []
                for file_name, data in list(self.mp4_paths.items()):
                    subject = data["subject"]
                    if data["status"] == "NotStarted":
                        logger.info(f"Processing file: {file_name}")
                        self.mp4_paths[file_name]["status"] = "InProgress"
                        file_path = data["file_path"]  # Retrieve the correct file path
                        subject = data["subject"]  # Retrieve the subject
                        self.lock.release()  # Release the lock before processing
                        try:
                            logger.info(f"{type(data['is_language'])}, {data['is_language']}")
                            if data["is_language"] == "False":
                                logger.info(f"Sending {file_name} to processor to process files")
                                self.processor.process_mp4_files(file_path, subject)
                            with self.lock:
                                files_to_delete.append(file_name)
                        except Exception as e:
                            logger.error(f"Error processing file {file_name}: {str(e)}", exc_info=True)
                            with self.lock:
                                self.mp4_paths[file_name]["status"] = f"Error: {str(e)}"
                        finally:
                            logger.info("Adding to s3 queue")
                            self.s3_obj.add_to_queue(school=settings.SCHOOL_NAME, subject=subject, local_directory = os.path.dirname(file_path))
                            self.lock.acquire()  # Reacquire the lock
                    
                for file_name in files_to_delete:
                    del self.mp4_paths[file_name]
                    logger.info(f"File processed and removed from queue: {file_name}")
            time.sleep(100)
