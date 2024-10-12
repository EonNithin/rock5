from datetime import datetime
import os
import json
from django.conf import settings
from moviepy.editor import VideoFileClip
from whisper_cpp_python import whisper
from django.http import JsonResponse
from pod.classes.JsonBuilder import JsonBuilder
from pod.classes.S3Uploader import S3UploadQueue
import logging

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')

class FileProcessor:
    def __init__(self):
        # Initialize the models
        self.whisper_model = whisper.Whisper(model_path=os.path.join(settings.BASE_DIR, 'models', 'ggml-base.en.bin'))
        self.media_folderpath = os.path.join(settings.BASE_DIR, 'media', 'processed_files')
        self.json_builder = JsonBuilder()
        self.s3 = S3UploadQueue()
        logger.info(f"Initialized FileProcessor ")
    

        
    def getTimeStamp(self):
        # Use time() correctly to get the current timestamp
        curr_time = datetime.now()
        logger.debug(f"Current timestamp: {curr_time}")
        return curr_time

    def calculate_time_taken(self, start_time, end_time):
        # Calculate the difference between start and end time
        time_taken = end_time - start_time
        total_seconds = time_taken.total_seconds()  # Get total time in seconds
        logger.debug(f"Time taken: {total_seconds} seconds")
        return (total_seconds)  # Converting time difference to seconds
    

    def mp4_to_mp3(self, mp4_filepath, subject):
        # Extract the directory from the MP4 file path
        directory = os.path.dirname(mp4_filepath)
        mp3_filepath = os.path.join(directory, os.path.basename(mp4_filepath).replace('_recorded_video.mp4', '.mp3'))
        # mp3_filepath = os.path.join(directory, os.path.splitext(os.path.basename(mp4_filepath))[0] + '.mp3')

        # Check if the MP4 file exists
        if not os.path.exists(mp4_filepath):
            logger.error(f"MP4 file not found: {mp4_filepath}")
            return None

        try:
            logger.info(f"Converting MP4 to MP3 for file: {mp4_filepath}")
            start_time = self.getTimeStamp() 
            video = VideoFileClip(mp4_filepath)
            
            # Check if the video has an audio stream
            if video.audio is None:
                logger.error(f"No audio stream found in {mp4_filepath}")
                return None
            
            audio = video.audio
            audio.write_audiofile(mp3_filepath, codec="libmp3lame")
            logger.info(f"MP3 file saved at: {mp3_filepath}")
            end_time = self.getTimeStamp()
            time_taken = self.calculate_time_taken(start_time, end_time)
            self.json_builder.add_generated_files(mp3_filepath, time_taken)
            return self.mp3_to_transcript(mp3_filepath, subject)
            
        except Exception as e:
            logger.error(f"Error converting MP4 to MP3: {e}")
            return None


    def mp3_to_transcript(self, mp3_filepath, subject):
        try:
            logger.info(f"Transcribing MP3 file: {mp3_filepath}")
            start_time = self.getTimeStamp()
            logger.debug(f"mp3filepath received: {mp3_filepath}")
            result = self.whisper_model.transcribe(mp3_filepath)
            transcript_text = result["text"]
            logger.debug("Got Transcript from Whisper: ")
            # Define the path to save the transcript file in the same directory as the MP3 file
            transcript_filepath = mp3_filepath.replace('.mp3', '_transcript.txt')
            # Save the transcript to a text file
            self.save_text_as_file(transcript_text, transcript_filepath)
            logger.info(f"Transcript file saved at: {transcript_filepath}")
            end_time = self.getTimeStamp()
            time_taken = self.calculate_time_taken(start_time, end_time)
            self.json_builder.add_generated_files(transcript_filepath, time_taken)
            # return self.transcript_to_summary(transcript_filepath)
            self.s3.add_to_queue(school=settings.SCHOOL_NAME, subject=subject, local_directory= os.path.dirname(transcript_filepath))
            return True
        except Exception as e:
            logger.error(f"Error transcribing MP3: {e}")
            return None


    def save_text_as_file(self, text, file_path):
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(text)
            logger.info(f"Text file saved at: {file_path}")
        except Exception as e:
            logger.error(f"Error saving text file: {file_path}: {e}")

    def load_text_from_file(self, txt_filepath):
        try:
            with open(txt_filepath, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error loading text from file: {txt_filepath}: {e}")
            return ""
        
        
    def process_mp4_files(self, mp4_filepath, subject):
        logger.info(f"Processing MP4 file: {mp4_filepath} for subject: {subject}")
        self.json_builder.add_generated_files(mp4_filepath, timetaken = 1)
        # grab_path = mp4_filepath.replace("recorded_video", "screen_grab")
        # if os.path.exists(grab_path):
        #     self.json_builder.add_generated_files(grab_path)
        return self.mp4_to_mp3(mp4_filepath, subject)

