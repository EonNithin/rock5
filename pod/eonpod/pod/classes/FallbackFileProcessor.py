import os
from pod.classes.FileProcessor import FileProcessor
import logging

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')


class FallbackFileProcessor:
    def __init__(self):
        # Initialize the FileProcessor instance
        self.processor = FileProcessor()
        logger.info(f"Initialized FallbackFileProcessor ")

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

            # Iterate through each timestamp folder
            for timestamp_folder in timestamp_folders:
                timestamp_folder_path = os.path.join(subject_folder_path, timestamp_folder)
                logger.debug(f"Processing timestamp folder: {timestamp_folder_path}")

                files = os.listdir(timestamp_folder_path)
                logger.debug(f"Files in folder {timestamp_folder_path}: {files}")

                # Check if there are 6 files in the subject folder
                if len(files) == 6:
                    logger.info(f"Skipping {timestamp_folder_path}, already processed (6 files).")
                    continue  # Skip processing if file count is 6

                # Sort files by modification time, latest first
                files_with_paths = [os.path.join(subject_folder_path, f) for f in files]
                latest_filepath = max(files_with_paths, key=os.path.getmtime)
                logger.info(f"Latest file to process: {latest_filepath}")

                try:
                    # Process the latest file based on its extension
                    if latest_filepath.endswith('recorded_video.mp4') and not any(f.endswith('.mp3') for f in files):
                        mp3_file = self.processor.process_mp4_files(latest_filepath)
                        if mp3_file:
                            logger.info(f"Mp3 file processed for {os.path.basename(latest_filepath)}")

                    elif latest_filepath.endswith('.mp3') and not any(f.endswith('_transcript.txt') for f in files):
                        transcript = self.processor.mp3_to_transcript(latest_filepath)
                        if transcript:
                            logger.info(f"Transcript processed for {os.path.basename(latest_filepath)}")

                    elif latest_filepath.endswith('_transcript.txt') and not any(f.endswith('_summary.txt') for f in files):
                        summary = self.processor.transcript_to_summary(latest_filepath)
                        if summary:
                            logger.info(f"Summary processed for {os.path.basename(latest_filepath)}")

                    elif latest_filepath.endswith('_summary.txt') and not any(f.endswith('_quiz.txt') for f in files):
                        quiz = self.processor.summary_to_quiz(latest_filepath)
                        if quiz:
                            logger.info(f"Quiz processed for {os.path.basename(latest_filepath)}")

                except Exception as e:
                    logger.error(f"Error processing file {latest_filepath}: {e}", exc_info=True)

