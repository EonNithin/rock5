import json
import threading
import time
import os
import cv2
from django.conf import settings
from pod.classes.Delete import DeletionJob
from pod.classes.FallbackFileProcessor import FallbackFileProcessor
from pod.classes.S3Uploader import S3UploadQueue
from pod.classes.video_processor import process_video_background
import logging
from datetime import datetime


# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')


class ProcessingQueue:
    def __init__(self):

        self.media_folderpath = os.path.join(settings.BASE_DIR, 'media', 'processed_files')
        self.json_file_path = os.path.join(settings.BASE_DIR, 'media', 'processing_queue_state.json')  # For testing

        self.queue_buffer = 2

        # Initialize the queue from the JSON file
        self.queue = self.load_queue_from_json()

        self.lock = threading.Lock()
        self.processing_thread = threading.Thread(target=self.process_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        self.s3_obj = S3UploadQueue()
        self.delete_job = DeletionJob()

        logger.info("Initialized ProcessingQueue")


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
                return []  # Return an empty queue if there's an error
        else:
            logger.info(f"Queue JSON file not found at {self.json_file_path}. Creating a new one.")
            # If the file does not exist, create it with an empty list
            try:
                with open(self.json_file_path, 'w') as json_file:
                    json.dump([], json_file, indent=4)  # Save an empty list
                logger.info(f"Created a new empty JSON file at {self.json_file_path}.")
                return []  # Return an empty queue after creating the file
            except Exception as e:
                logger.error(f"Error creating the queue JSON file: {str(e)}", exc_info=True)
                return []  # Return an empty queue if the file can't be created


    def save_queue_to_json(self):
        """Overwrite the entire queue in the JSON file with the current queue contents."""
        try:
            with open(self.json_file_path, 'w') as json_file:
                json.dump(self.queue, json_file, indent=4)  # Write the entire queue
            logger.info(f"Queue saved to JSON file at {self.json_file_path}.")
        except Exception as e:
            logger.error(f"Error saving queue to JSON file: {str(e)}", exc_info=True)

    def add_to_queue(self, file_name, file_path, subject, subject_name, class_no, is_language="False"):
        
        # Get the parent directory of the file
        parent_directory = os.path.basename(os.path.dirname(file_path))

        with self.lock:
            self.queue.append({
                "file_name": file_name,
                "file_path": file_path,
                "status": "NotStarted",
                "subject": subject,
                "subject_name": subject_name,
                "class_no":class_no,
                "is_language": is_language,
                "folder_timestamp": parent_directory   
            })
            self.save_queue_to_json()  # Save the updated queue to JSON immediately  
        logger.info(f"Added to queue: {file_name} with path: {file_path}, subject: {subject}, is_language: {is_language}")


    def generate_thumbnail(self, mp4_filepath):
        # Get the directory where the MP4 file is located
        directory = os.path.dirname(mp4_filepath)
        
        # Capture the video
        cap = cv2.VideoCapture(mp4_filepath)
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Define timestamps where you want to take screenshots
        timestamps = [0.1, 2]  # In seconds

        # Create the output directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)

        # Generate thumbnails and save them in the same directory as the MP4 file
        for idx, t in enumerate(timestamps, 1):  # Start the index from 1
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)  # Set position in milliseconds
            ret, frame = cap.read()
            if ret:
                # Save the frame as an image in the same folder as the MP4 file
                thumbnail_path = os.path.join(directory, f"thumbnail_{idx}.png")
                cv2.imwrite(thumbnail_path, frame)
                logger.info(f"Thumbnail saved at: {thumbnail_path}")
                # Add the thumbnail to the list of generated files for JSON and S3 upload

        cap.release()
        return


    def process_queue(self):
        while True:
            try:
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
                    folder_timestamp = item_to_process["folder_timestamp"]
                    
                    # Check if the file path exists
                    if not os.path.exists(file_path):
                        logger.error(f"File path does not exist: {file_path}. Skipping {file_name}.")
                        continue
                    
                    # Ensure timestamp is in correct format before proceeding
                    folder_timestamp = folder_timestamp
                    
                    try:
                        if isinstance(folder_timestamp, str):
                            try:
                                folder_timestamp = datetime.strptime(folder_timestamp, "%d-%m-%Y_%H-%M-%S")
                            except ValueError as ve:
                                logger.error(f"Invalid timestamp format for {item_to_process['file_path']}: {folder_timestamp}. Error: {str(ve)}")
                                continue  # Skip this item if the timestamp is invalid
                        elif isinstance(folder_timestamp, datetime):
                            # If it's already a datetime object, no conversion is needed
                            folder_timestamp = folder_timestamp
                        else:
                            logger.error(f"Invalid timestamp type for {item_to_process['file_path']}: {type(folder_timestamp)}. Expected str or datetime.")
                            continue  # Skip this item if the type is not str or datetime

                        # Check buffer size
                        time_difference = datetime.now() - folder_timestamp
                        if time_difference.days > self.queue_buffer:
                            logger.info(f"Skipping {file_name} as buffer size exceeded.")
                            continue
                    except Exception as e:
                        logger.error(f"Error while processing folder_timestamp or buffer size for file {file_name}. Error: {str(e)}")
                        continue  # Skip processing if any exception occurs


                    try:
                        logger.info(f"Processing file: {file_name}")
                        # Log the type of `is_language`
                        logger.info(f"Type of is_language: {type(is_language)}: value : {is_language}")
                
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
                            self.generate_thumbnail(file_path)
                            process_video_background(process_data)
                        logger.info(f"File processed and removed from queue: {file_name}")
                        self.save_queue_to_json()
                        logger.info("process queue state updated")

                    except Exception as e:
                        logger.error(f"Error processing file {file_name}: {str(e)}", exc_info=True)

                        # try:
                        #     # Ensure folder_timestamp is in the correct format string 
                        #     if isinstance(folder_timestamp, datetime):
                        #         folder_timestamp = folder_timestamp.strftime("%d-%m-%Y_%H-%M-%S")
                        #     elif isinstance(folder_timestamp, str):
                        #         folder_timestamp = folder_timestamp
                        #     else:
                        #         raise TypeError(f"Invalid folder_timestamp type: {type(folder_timestamp)}")
                        # except Exception as e:
                        #     logger.error(f"Error processing folder_timestamp for file {file_path}: {str(e)}. Skipping re-queue.")
                        #     continue  # Skip re-queue if any exception occurs

                        # If processing fails, re-add to the queue with an error status
                        logger.info(f"Retrying processing for {file_path})")
                        with self.lock:
                            self.queue.append(item_to_process)
                            # self.queue.append({
                            #     "file_name": file_name,
                            #     "file_path": file_path,
                            #     "status": f"Error: {str(e)}",
                            #     "is_language": is_language,
                            #     "subject": subject,
                            #     "subject_name": subject_name,
                            #     "class_no": class_no,
                            #     "folder_timestamp": folder_timestamp
                            # })
                        logger.info(f"Retrying file processing after 5 minutes: {file_name}")
                        time.sleep(300)

                        
                    finally:
                        self.s3_obj.add_to_queue(school=settings.SCHOOL_NAME, subject=subject,
                                                local_directory=os.path.dirname(file_path))
                        try:
                            self.save_queue_to_json()
                        except Exception as e :
                            logger.debug(f"error in save queue to json in finally: {str(e)}")
                        logger.info("Processing queue updated and Adding to S3 queue")


            except Exception as e:
                logger.error(f"Unexpected error in process_queue: {str(e)}", exc_info=True)
            finally:
                time.sleep(60) 

