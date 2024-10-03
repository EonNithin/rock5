import os
import time
import shutil
from pod.classes.JsonBuilder import JsonBuilder
from pod.classes.S3Uploader import S3UploadQueue
from datetime import datetime, timedelta
import threading
from django.conf import settings
import logging

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')

class DeletionJob:
    def __init__(self):
        """
        Initialize the DeletionJob class.
        """
        self.s3 = S3UploadQueue()
        self.current_time = datetime.now()
        self.json_obj = JsonBuilder()
        self.days_threshold = 7
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_folder = os.path.join(self.current_dir, '../../media/processed_files')
        logger.info(f"Initialized DeletionJob with base folder: {self.base_folder}")
        
        # Start the background thread
        self.keep_running = True
        self.thread = threading.Thread(target=self.run_daily_cleanup, daemon=True)
        self.thread.start()
        logger.info("Started background deletion thread.")

    def is_old_file(self, folder_path):
        """
        Check if the folder is old based on its deletion date.
        """
        timestamp = os.path.basename(folder_path)
        date = timestamp.split("_")[0]
        logger.debug(f"Checking folder {folder_path}, date: {date}, timestamp: {timestamp}")

        print(folder_path, date, timestamp)

        # Fetch the data for the specified date
        data = self.json_obj.fetch_json_from_date_folder(date).get(timestamp)
        if data and data['deletion_date']:
            file_age = self.current_time - datetime.fromisoformat(str(data['deletion_date']))
            logger.info(f"File {folder_path} is {file_age.days} days old.")
            if file_age > timedelta(days=self.days_threshold):
                if data["in_s3"]:
                    logger.info(f"File {folder_path} is old and already in S3. Marked for deletion.")
                    return True
                else:
                    logger.info(f"File {folder_path} is old but not in S3. Uploading to S3.")
                    self.s3.count_files_and_upload(
                        school=settings.SCHOOL_NAME, 
                        subject=data["subject"], 
                        local_directory=folder_path
                    )
        
        return False

    def delete_old_files(self):
        """
        Iterate through the base folder and subfolders, deleting old files.
        """
        target_folder = self.base_folder
        logger.info(f"Starting cleanup in folder: {target_folder}")
        for subject in os.scandir(target_folder):
            if subject.is_dir():
                logger.debug(f"Checking subject folder: {subject.path}")
                for timestamp_entry in os.scandir(subject.path):
                    if timestamp_entry.is_dir():  # Check if it's a directory
                        logger.debug(f"Checking timestamp folder: {timestamp_entry.path}")
                        if self.is_old_file(timestamp_entry.path):
                            try:
                                shutil.rmtree(timestamp_entry.path)
                                logger.info(f"Deleted old folder and all its contents: {timestamp_entry.path}")
                            except PermissionError:
                                logger.error(f"Permission denied when trying to delete: {timestamp_entry.path}")
                            except Exception as e:
                                logger.error(f"Error deleting folder {timestamp_entry.path}: {e}")

    def run_daily_cleanup(self):
        """
        Run the deletion job at 5 PM daily.
        """
        logger.info("Deletion Job is set to run at 5 PM daily.")
        while self.keep_running:
            now = datetime.now()
            # Check if it's past 1 AM (to avoid frequent checks)
            if now.hour >= 17:
                logger.info("Running deletion job...")
                self.delete_old_files()
                logger.info("Deletion job completed. Sleeping for 1 minute.")
                time.sleep(60)  # Wait a minute before checking again
            else:
                logger.debug("Not time for deletion job yet. Sleeping for an hour.")
            time.sleep(3600)  # Check every 30 minutes



