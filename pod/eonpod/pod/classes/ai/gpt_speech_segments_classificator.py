import json
import os
from openai import OpenAI
from .logging_service import logger
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()  

OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")
OPEN_AI_MODEL = os.getenv("OPEN_AI_MODEL")

OFF_TOPIC_PROMPT_FILE_PATH = "./pod/classes/llm_prompts/gpt_prompt_template.txt"
CBSE_PROMPT_FILE_PATH = "./pod/classes/llm_prompts/gpt_cbse_prompt_template.txt"


class GPTSpeechSegmentsClassificator:
    def __init__(self, input_folder) -> None:
        self.__open_ai_client = OpenAI(api_key=OPEN_AI_API_KEY)
        self.__open_ai_model = OPEN_AI_MODEL
        self.__gpt_prompt_template_path = OFF_TOPIC_PROMPT_FILE_PATH
        self.__gpt_cbse_prompt_template_path = CBSE_PROMPT_FILE_PATH
        self.OUTPUT_DIR = input_folder
        # Create output directory if it doesn't exist
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

    def _generate_output_filename(self, prefix: str, class_number: str, subject_name: str) -> str:
        0
        sanitized_subject = subject_name.replace(" ", "_")
        return os.path.join(self.OUTPUT_DIR, f"{prefix}_{sanitized_subject}_class{class_number}.json")

    def _write_results_to_file(self, results: dict, filename: str) -> None:
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Results written to {filename}")
        except Exception as e:
            logger.error(f"Error writing results to file: {e}")
            raise

    def classify(
        self, speech_segments: list, class_number: str, subject_name: str, syllabus: str
    ):
        logger.info("Generating GPT prompt...")
        prompt = self._load_prompt(self.__gpt_prompt_template_path)
        prompt = prompt.replace("{@class_number}", class_number)
        prompt = prompt.replace("{@subject_name}", subject_name)
        prompt = prompt.replace("{@syllabus}", syllabus)
        sentences = ""
        map = {}
        
        # Prepare segments dictionary for file output
        segments_output = {
            "class_number": class_number,
            "subject_name": subject_name,
            "analysis_timestamp": datetime.now().isoformat(),
            "segments": []
        }
        
        for i, segment in enumerate(speech_segments):
            segment.relevance_score_gpt = 1
            map[i] = segment
            sentences += f"{i}: {segment.text}\n"

        prompt += f"\n\n{sentences}"
        logger.info("Sending request to GPT...")
        gpt_results = self.__gpt_run_prompt(prompt)
        logger.info("GPT response received")

        # Process results and update segments
        for off_topic_sentence in gpt_results["off_topic_sentences"]:
            s_num = off_topic_sentence["sentence_number"]
            s_text = off_topic_sentence["text"]
            probability = off_topic_sentence.get("probability", 1.0)  # Default to 1.0 if not provided

            if s_num not in map:
                logger.error(f"Off-topic sentence {s_num} not found in the transcript")
                raise Exception(f"GPT provided irrelevant response")

            if map[s_num].text.strip() != s_text.strip():
                logger.warning(
                    f"Off-topic sentence {s_num} is not the same as in the transcript"
                )

            map[s_num].relevance_score_gpt = 0
            map[s_num].off_topic_probability = probability

        # Prepare detailed output for file
        for i, segment in enumerate(speech_segments):
            segments_output["segments"].append({
                "segment_number": i,
                "text": segment.text,
                "is_off_topic": segment.relevance_score_gpt == 0,
                "off_topic_probability": getattr(segment, 'off_topic_probability', 0.0)
            })

        # Write results to file
        output_filename = self._generate_output_filename("offtopic", class_number, subject_name)
        self._write_results_to_file(segments_output, output_filename)

    def classify_per_CBSE(self, speech_segments: list, class_number: str, subject_name: str, syllabus: str):
        logger.info("Generating CBSE GPT prompt...")
        prompt = self._load_prompt(self.__gpt_cbse_prompt_template_path)
        prompt = prompt.replace("{@class_number}", class_number)
        prompt = prompt.replace("{@subject_name}", subject_name)
        prompt = prompt.replace("{@syllabus}", syllabus)
        groups = ""
        map = {}
        
        # Prepare CBSE output dictionary
        cbse_output = {
            "class_number": class_number,
            "subject_name": subject_name,
            "analysis_timestamp": datetime.now().isoformat(),
            "groups": []
        }

        for i, segment in enumerate(speech_segments):
            map[i] = segment
            groups += f"{i}: {segment.text}\n"

        prompt += f"\n\n{groups}"
        logger.info("Sending request to GPT...")
        gpt_results = self.__gpt_run_prompt(prompt)
        logger.info("GPT response received")

        try:
            for group in gpt_results["groups"]:
                g_num = group["group_number"]
                if g_num not in map:
                    raise Exception(f"Group {g_num} not found in the transcript")

                map[g_num].syllabus_classification = f"{group['book']} - {group['chapter']}"
                probability = group.get("probability", 1.0)  # Default to 1.0 if not provided
                map[g_num].relevance_probability = probability

                # Add to CBSE output
                cbse_output["groups"].append({
                    "group_number": g_num,
                    "text": map[g_num].text,
                    "book": group["book"],
                    "chapter": group["chapter"],
                    "relevance_probability": probability
                })

            # Write CBSE results to file
            output_filename = self._generate_output_filename("cbse", class_number, subject_name)
            self._write_results_to_file(cbse_output, output_filename)

        except Exception as e:
            logger.error(f"Classification per CBSE failed: {e}")
            # Write error information to file
            error_output = {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "input_data": {
                    "class_number": class_number,
                    "subject_name": subject_name
                }
            }
            error_filename = self._generate_output_filename("cbse_error", class_number, subject_name)
            self._write_results_to_file(error_output, error_filename)

    def __gpt_run_prompt(self, prompt: str) -> dict:
        try:
            response = self.__open_ai_client.chat.completions.create(
                model=self.__open_ai_model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
            )

            result = json.loads(response.choices[0].message.content.strip())
            return result
        except Exception as e:
            logger.error(f"Error while calling OpenAI API: {e}")
            raise

    def _load_prompt(self, file_path: str):
        try:
            with open(file_path, "r") as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error while loading prompt file: {file_path}. Error:{e}")
            raise