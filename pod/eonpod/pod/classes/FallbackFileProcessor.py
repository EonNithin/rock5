import os
from platform import processor
from django.conf import settings
from eonpod import settings
import requests
from pod.classes.FileProcessor import FileProcessor
from pod.classes.JsonBuilder import JsonBuilder
import logging
import threading
import pytz
from datetime import datetime, timedelta
import time
import shutil
from pod.dbmodels.models import DATABASE_URL, get_session
from pod.dbmodels.queries import get_if_subject_is_language_by_title
from pod.classes.S3Uploader import S3UploadQueue


# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')

school_id = settings.SCHOOL_NAME

class FallbackFileProcessor:
    def __init__(self):
        # Initialize the FileProcessor instance
        self.processor = FileProcessor()
        logger.info("Initialized FallbackFileProcessor")

        # Start the background thread for daily processing
        self.keep_running = True
        self.thread = threading.Thread(target=self.run_daily_processing, daemon=True)
        self.thread.start()
        self.json = JsonBuilder()
        self.s3_obj = S3UploadQueue()
        logger.info("Started background fallback processing thread.")

    def check_file_in_files(self, file, filelist):
        for f in filelist:
            if file in f:
                return f
        return None



    def get_language_subject(self, school_id, subject):
        # API endpoint
        url = "http://13.202.101.139:5000/language_subject"
        title = subject
        # Query parameters for the GET request
        payload = {
            "school": school_id,
            "subject": subject
        }

        try:
            # Sending the GET request with query parameters
            response = requests.get(url, json=payload)
            logger.info(f"Response from API: {response.status_code}")
            # Check if the request was successful
            if response.status_code == 200:
                # Parse the JSON response
                data = response.json()
                logger.info(f"Response from API:, {data}")
                return data
            else:
                logger.info(f"Failed to get data. Status code: {response.status_code}")
                return self.get_language_from_local_db(school_id, title)
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during API call: {e}")
            return self.get_language_from_local_db(school_id, title)


    def get_language_from_local_db(self, school_id, title):
        try:
            # Create a new session for the database interaction
            session = get_session(database_url=DATABASE_URL)
        except Exception as e:
            logger.error(f"Error connecting to local DB: {e}")
            return {'error_message': "No Internet Connection and could not access local database"}

        try:
            # Query the database to check if the subject is a language
            is_language = get_if_subject_is_language_by_title(session, school_id, title)

            # Check if the result is valid
            if is_language is not None:
                logger.info(f"Subject {title} is_language: {is_language}")
                return is_language
            else:
                logger.warning(f"No subject found with title: {title}")
                return {'error_message': f"No subject found with title: {title}"}

        except Exception as e:
            logger.error(f"Error during local DB processing: {e}")
            return {'error_message': "An error occurred while processing the local database"}

        finally:
            # Always close the session to avoid any connection leaks
            session.close()


    def process_folders(self):
        logger.info("Started processing folders in media folder path.")
        # Get all subject folders in the media_folderpath
        subject_folders = [f for f in os.listdir(self.processor.media_folderpath) if os.path.isdir(os.path.join(self.processor.media_folderpath, f))]
        logger.debug(f"Found subject folders: {subject_folders}")

        # Iterate through each subject folder
        for subject_folder in subject_folders:
            subject_folder_path = os.path.join(self.processor.media_folderpath, subject_folder)
            logger.debug(f"Processing subject folder: {subject_folder_path}")

            # Get timestamp folders inside the subject folder
            timestamp_folders = [tf for tf in os.listdir(subject_folder_path) if os.path.isdir(os.path.join(subject_folder_path, tf))]
            logger.debug(f"Found timestamp folders: {timestamp_folders}")
            
            title = os.path.basename(subject_folder_path)
            is_language = self.get_language_subject(school_id, title)
            if is_language:
                continue
            try:
            # Iterate through each timestamp folder
                for timestamp_folder in timestamp_folders:
                    timestamp_folder_path = os.path.join(subject_folder_path, timestamp_folder)
                    logger.debug(f"Processing timestamp folder: {timestamp_folder_path}")

                    files = os.listdir(timestamp_folder_path)
                    logger.debug(f"Files in folder {timestamp_folder_path}: {files}")

                    # Sort files by modification time, latest first
                    files_with_paths = [os.path.join(timestamp_folder_path, f) for f in files]

                    if self.check_file_in_files("transcript.txt", files_with_paths):
                        continue
                    else:
                        mp3 = self.check_file_in_files("mp3", files_with_paths)
                        if mp3:
                            self.processor.mp3_to_transcript(mp3, subject_folder)
                        else:
                            video = self.check_file_in_files("recorded_video.mp4", files_with_paths)
                            if video:
                                self.processor.mp4_to_mp3(video, subject_folder)

                            #add a statement to call s3.add_to_queue
                            self.s3_obj.add_to_queue(school=settings.SCHOOL_NAME, subject=title, local_directory = os.path.dirname(mp3))

            except Exception as e:
                logger.info(f"Exception in Fallback Processor {str(e)}")


    def run_daily_processing(self):
        """
        Run the processing job at 5 PM daily.
        """
        logger.info("Fallback Processing Job is set to run daily at 5 PM.")
        while self.keep_running:
            now = datetime.now(pytz.timezone('Asia/Kolkata'))
            target_time = now.replace(hour=17, minute=0, second=0, microsecond=0)
            if now >= target_time:
                target_time += timedelta(days=1)

            sleep_duration = (target_time - now).total_seconds()
            logger.info(f"Sleeping for {sleep_duration/60} minutes until processing job.")
            time.sleep(sleep_duration)

            logger.info("Running processing job...")
            self.process_folders()  # Call your existing method to process folders
            logger.info("Processing job completed.")
        



