import threading
import time
import os
from django.conf import settings
from pod.classes.Delete import DeletionJob
from pod.classes.FallbackFileProcessor import FallbackFileProcessor
from pod.classes.S3Uploader import S3UploadQueue
from pod.classes.video_processor import process_video_background
import logging

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')

class ProcessingQueue:
    def __init__(self):
        self.queue = []
        self.lock = threading.Lock()
        self.processing_thread = threading.Thread(target=self.process_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        self.media_folderpath = os.path.join(settings.BASE_DIR, 'media', 'processed_files')
        self.s3_obj = S3UploadQueue()
        # self.add_to_queue('04-11-2024_14-24-57_recorded_video.mp4', 
        # '/home/software-tesing/Desktop/rock5/pod/eonpod/media/processed_files/CL9AMATHS/04-11-2024_14-24-57/04-11-2024_14-24-57_recorded_video.mp4', 
        # 'Chemistry',
        #  False)
        logger.info("Initialized ProcessingQueue")

    def add_to_queue(self, file_name, file_path, subject, subject_name, class_no, is_language=False):
        with self.lock:
            self.queue.append({
                "file_name": file_name,
                "file_path": file_path,
                "status": "NotStarted",
                "subject": subject,
                "subject_name": subject_name,
                "class_no":class_no,
                "is_language": is_language
                
            })
        logger.info(f"Added to queue: {file_name} with path: {file_path}, subject: {subject}")

    def process_queue(self):
        while True:
            item_to_process = None
            with self.lock:
                if self.queue:
                    item_to_process = self.queue.pop(0)
            if item_to_process:
                file_name = item_to_process["file_name"]
                file_path = item_to_process["file_path"]
                subject = item_to_process["subject"]
                subject_name = item_to_process["subject_name"]
                class_no = item_to_process["class_no"]
                is_language = item_to_process["is_language"]

                try:
                    logger.info(f"Processing file: {file_name}")
                    # Log the type of `is_language`
                    logger.info(f"Type of is_language: {type(is_language)}: {is_language}")

                    if is_language == "False":
                        logger.info(f"Sending {file_name} to processor to process files")
                        process_data = {
                            "file_path": file_path,
                            "class_no": class_no,
                            "subject": subject,
                            "subject_name": subject_name,
                            "use_gpt": True,
                            "render_final_video": True,
                            "syllabus": "CBSE"
                        }
                        process_video_background(process_data)
                    logger.info(f"File processed and removed from queue: {file_name}")
                except Exception as e:
                    logger.error(f"Error processing file {file_name}: {str(e)}", exc_info=True)
                    # If processing fails, re-add to the queue with an error status
                    with self.lock:
                        self.queue.append({
                            "file_name": file_name,
                            "file_path": file_path,
                            "status": f"Error: {str(e)}",
                            "is_language": is_language,
                            "subject": subject,
                            "subject_name": subject_name,
                            "class_no": class_no
                        })
                finally:
                    logger.info("Adding to S3 queue")
                    self.s3_obj.add_to_queue(school=settings.SCHOOL_NAME, subject=subject,
                                            local_directory=os.path.dirname(file_path))

            time.sleep(5)  