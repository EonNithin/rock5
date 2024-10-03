from pathlib import Path
from django.conf import settings
from pod.classes.FileProcessor import FileProcessor
import os
import logging

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')


class TestFileProcessor:
    def __init__(self):
        self.test_folder = os.path.join(settings.BASE_DIR, 'pod', 'tests', 'testdata')
        self.test_mp4_filepath = self.get_file_with_extension('_recorded_video.mp4')
        self.test_mp3_filepath = self.get_file_with_extension('.mp3')
        self.test_transcript_filepath = self.get_file_with_extension('_transcript.txt')
        self.test_summary_filepath = self.get_file_with_extension('_summary.txt')
        self.processor = FileProcessor()
        logger.info(f"Initialized TestFileProcessor")

    def get_file_with_extension(self, extension):
        """Helper method to find the file with a given extension."""
        for filename in os.listdir(self.test_folder):
            if filename.endswith(extension):
                return os.path.join(self.test_folder, filename)
        logger.warning(f"No file found with extension {extension} in test folder.")
        return None  # Return None if no file with the extension is found

    def count_files_in_directory(self, path):
        return len(list(Path(path).glob('*')))
    
    def test_process_mp4_files(self):
        logger.info("Testing process_mp4_files...")
        try:
            self.processor.process_mp4_files(self.test_mp4_filepath)
            logger.info("process_mp4_files test passed!")
        except Exception as e:
            logger.error(f"process_mp4_files test failed: {e}")

    def test_mp4_to_mp3(self):
        logger.info("Running test_mp4_to_mp3...")
        try:
            mp3_filepath = self.processor.mp4_to_mp3(self.test_mp4_filepath)
            assert mp3_filepath and os.path.exists(mp3_filepath), "MP3 file conversion failed"
            logger.info("test_mp4_to_mp3 passed!")
        except AssertionError as e:
            logger.error(f"test_mp4_to_mp3 failed: {e}")
        except Exception as e:
            logger.error(f"Error during test_mp4_to_mp3: {e}")

    def test_mp3_to_transcript(self):
        logger.info("Running test_mp3_to_transcript...")
        try:
            transcript_filepath = self.processor.mp3_to_transcript(self.test_mp3_filepath)
            assert transcript_filepath and os.path.exists(transcript_filepath), "Transcript generation failed"
            logger.info("test_mp3_to_transcript passed!")
        except AssertionError as e:
            logger.error(f"test_mp3_to_transcript failed: {e}")
        except Exception as e:
            logger.error(f"Error during test_mp3_to_transcript: {e}")

    def test_transcript_to_summary(self):
        logger.info("Running test_transcript_to_summary...")
        try:
            summary_filepath = self.processor.transcript_to_summary(self.test_transcript_filepath)
            assert summary_filepath and os.path.exists(summary_filepath), "Summary generation failed"
            logger.info("test_transcript_to_summary passed!")
        except AssertionError as e:
            logger.error(f"test_transcript_to_summary failed: {e}")
        except Exception as e:
            logger.error(f"Error during test_transcript_to_summary: {e}")

    def test_summary_to_quiz(self):
        logger.info("Running test_summary_to_quiz...")
        try:
            quiz_filepath = self.processor.summary_to_quiz(self.test_summary_filepath)
            assert quiz_filepath and os.path.exists(quiz_filepath), "Quiz generation failed"
            logger.info("test_summary_to_quiz passed!")
        except AssertionError as e:
            logger.error(f"test_summary_to_quiz failed: {e}")
        except Exception as e:
            logger.error(f"Error during test_summary_to_quiz: {e}")


if __name__ == "__main__":
    testprocessor = TestFileProcessor()
    logger.info("Starting FileProcessor tests...")
    testprocessor.test_process_mp4_files()
    testprocessor.test_mp4_to_mp3()
    testprocessor.test_mp3_to_transcript()
    testprocessor.test_transcript_to_summary()
    testprocessor.test_summary_to_quiz()
    logger.info("FileProcessor tests completed.")
