import os
import time
import shutil
from pod.classes.JsonBuilder import JsonBuilder
from pod.classes.S3Uploader import S3UploadQueue
from datetime import datetime, timedelta
import threading
from django.conf import settings
import logging
import pytz

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')


class DeletionJob:
    def __init__(self):
        """
        Initialize the DeletionJob class.
        """
        self.s3 = S3UploadQueue()
        self.current_time = datetime.now(pytz.timezone('Asia/Kolkata'))
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
        Check if the folder is old based on its timestamp.
        """
        timestamp = os.path.basename(folder_path)
        date = timestamp.split("_")[0]
        logger.debug(f"Checking folder {folder_path}, date: {date}, timestamp: {timestamp}")

        # Fetch the data for the specified date
        data = self.json_obj.fetch_json_from_date_folder(date).get(timestamp)

        if data:
            if data["in_s3"] == 0:
                self.s3.add_to_queue(
                    school=settings.SCHOOL_NAME,
                    subject=data["subject"],
                    local_directory=folder_path
                )
                return False
            
            for generated_file in data["generated_files"]:
                if (
                    ("transcript" in generated_file or "mp3" in generated_file) and
                    not any(generated_file in f for f in data["s3_path"])
                ):
                    self.s3.upload_file(local_file_path=generated_file, school=settings.SCHOOL_NAME, subject=data["subject"])

            try:
                current = datetime.now(pytz.timezone('Asia/Kolkata'))
                folder_time = datetime.strptime(timestamp, "%d-%m-%Y_%H-%M-%S")
                folder_time = pytz.timezone('Asia/Kolkata').localize(folder_time)  # Make folder_time timezone-aware
                file_age = current - folder_time

                if file_age > timedelta(days=self.days_threshold):
                    logger.info(f"File {folder_path} is old and already in S3. Marked for deletion.")
                    return True
            except ValueError:
                logger.error(f"Invalid timestamp format for {folder_path}")

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
        logger.info("Deletion Job is set to run daily at 6 PM.")
        while self.keep_running:
            now = datetime.now(pytz.timezone('Asia/Kolkata'))
            target_time = now.replace(hour=18, minute=0, second=0, microsecond=0)
            if now >= target_time:
                target_time += timedelta(days=1)

            sleep_duration = (target_time - now).total_seconds()
            logger.info(f"Sleeping for {sleep_duration/60} minutes until deletion job.")
            time.sleep(sleep_duration)

            logger.info("Running deletion job...")
            self.delete_old_files()
            logger.info("Deletion job completed.")