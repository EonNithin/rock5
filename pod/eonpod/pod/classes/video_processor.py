import os
import shutil
import random
import traceback
import logging
from uuid import uuid4
from datetime import datetime
from pod.classes.ai_processor import ProcessVideoService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

INPUT_FOLDER = "input"
OUTPUT_FOLDER = "output"

def process_video_background(data):

    input_video_path = data['file_path']
    log_file_name = "log.txt"
    try:
        input_video_url = data["file_path"]
        class_n = data["class_no"]
        subject = data["subject"]
        use_gpt = data["use_gpt"]
        syllabus = data["syllabus"]
        render_final_video = data["render_final_video"]

        logger.info(
            f"start processing: input_video_url: {input_video_url}, class_n: {class_n}, subject: {subject}, use_gpt: {use_gpt}, render_final_video: {render_final_video}"
        )

        logger.info("starting processing video")
        pvs = ProcessVideoService(
            input_video_path,
            class_n,
            subject,
            use_gpt=use_gpt,
            regenerate_audio=False,
            regenerate_transcription=False,
            write_final_video=render_final_video,
            syllabus=syllabus
        )
        pvs.process()
        logger.info("processing completed")

    except Exception:
        logger.error(f"error during video processing: {traceback.format_exc()}")
        raise


# if __name__ == "__main__":
#     os.makedirs(INPUT_FOLDER, exist_ok=True)
#     os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
#     data = {
#         "file_path": os.path.join("19-10-2024_13-29-47", "19-10-2024_13-29-47_recorded_video.mp4"),  
#         "class_n": "9",           
#         "subject": "Chemistry",        
#         "use_gpt": True,             
#         "render_final_video": True,
#         "syllabus": "CBSE"
#     }
    
    # process_video_background(data)