import os
import json
from datetime import datetime
from django.conf import settings
import logging

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')

class JsonBuilder:
    def __init__(self):
        self.date = datetime.now().strftime('%d-%m-%Y')
        self.current_json_file = None
        self.media_folderpath = os.path.join(settings.BASE_DIR, 'media', 'json_data')
        # self.fetch_json_from_date_folder()
        logger.info(f"Initialized JsonBuilder")

    def folder_metadata(self, subject_id, directory):
        # JSON file attributes - school-id, subject, subject-title, topic, sub-topic, id for the subject group
        metadata_file = os.path.join(directory, "folder_metadata.json")
        school_id = settings.SCHOOL_NAME
        subject_title = "Science"
        topic = ""
        subtopic = ""
        temp = {
            "school_id" : school_id,
            "subject_id" : subject_id,
            "subject_title" : subject_title,
            "topic": topic,
            "sub_topic": subtopic
        }
        with open(metadata_file, "w") as f:
            json.dump(temp, f)
        logger.info(f"Folder metadata created at {metadata_file} for subject {subject_title}.")


    def fetch_json_from_date_folder(self, date = None):
        if date is None:
            json_file = os.path.join(self.media_folderpath, f"{self.date}.json")
        else:
            json_file = os.path.join(self.media_folderpath, f"{date}.json")
        if os.path.exists(json_file):
            with open(json_file, 'r') as file:
                content = json.load(file)
        else:
            content = {}
            with open(json_file, 'w') as file:
                json.dump(content, file)
        self.current_json_file = json_file
        return content

    def add_generated_files(self, name, timetaken):
        fname = os.path.basename(name)
        directory = os.path.dirname(name)
        parts = directory.split("/")
        logger.debug(f"fname, directory and parts: {fname}, {directory}, {parts}")
        subject = parts[-2]
        timestamp = parts[-1]
        data = self.fetch_json_from_date_folder(date=timestamp.split("_")[0])


        if timestamp not in  data:
            data[timestamp] = {
                'generated_files': [],
                'subject': subject,
                'in_s3': 0,
                's3_date': None,
                's3_path': [],
                'deletion_date': None,
                'timestamps': {}
            }
        if name not in data[timestamp]['generated_files']:
            data[timestamp]['generated_files'].append(name)
            data[timestamp]['timestamps'][os.path.basename(name)] = timetaken
        if len(data[timestamp]["generated_files"]) == 1:
            self.folder_metadata(subject, directory)
            logger.info(f"Folder metadata generated for {subject} at {directory}.")
        with open(self.current_json_file, 'w') as file:
            json.dump(data, file)
        

    def update_s3(self, local_file_path, timestamp, s3_path, date = None, s3_upload_date=None, ):
        data = self.fetch_json_from_date_folder(date)
        if timestamp not in data:
            self.add_generated_files(local_file_path, "100")
            data = self.fetch_json_from_date_folder(date)
        data[timestamp]['in_s3'] = 1
        data[timestamp]['s3_date'] = s3_upload_date
        data[timestamp]['s3_path'].append(s3_path)
        if len(data[timestamp]['s3_path']) == 4:
            data[timestamp]["deletion_date"] = 7
        with open(self.current_json_file, 'w') as file:
            json.dump(data, file)
        logger.info(f"Updated S3 metadata for timestamp {timestamp}: path {s3_path}.")
        
    def no_of_files(self, timestamp, date = None):
        data = self.fetch_json_from_date_folder(date)
        if timestamp in data:
            count = len(data[timestamp]['generated_files'])
            logger.info(f"Number of generated files for {timestamp}: {count}")
            return len(data[timestamp]['generated_files'])
        logger.warning(f"No files found for timestamp {timestamp}.")
        return 0

    def get_latest_file(self, filepath, date = None):
        parts = filepath.split("\\")
        subject_name = parts[-2]
        timestamp = parts[-1]
        logger.debug(f"Subject name is:{subject_name}, timestamp is:{timestamp}, date is:{date}")
        if date is None:
            date = self.date
        else:
            date = timestamp.split("_")[-2]
        data = self.fetch_json_from_date_folder(date)
        logger.info(f"Looking for latest file in JSON data on {date} for subject {subject_name}.")
        if timestamp in data:
            return data[timestamp]['generated_files'][-1]
        logger.warning(f"No files found for subject {subject_name} on {timestamp}.")
        return None
