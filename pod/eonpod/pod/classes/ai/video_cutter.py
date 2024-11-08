import time
import subprocess
import traceback
import os
from .logging_service import logger

TRANSITION_TIME = 5


class VideoCutter:
    def __init__(
        self,
        input_video_path: str,
        output_video_path: str,
        transition_video_path: str,
        speech_segments: list,
    ) -> None:
        self.__input_video_path = input_video_path
        self.__output_dir = output_video_path
        self.__transition_video_path = transition_video_path
        self.__speech_segments = speech_segments

    def cut(self) -> None:
        self.__cut_ffmpeg_encoder(self.__input_video_path)
        screen_grab = self.__input_video_path.replace("recorded_video.mp4", "screen_grab.mp4")
        if os.path.exists(screen_grab):
            self.__cut_ffmpeg_encoder(screen_grab)
    

#     ffmpeg -i input.mp4 -ss 00:00:30 -to 00:01:00 -vf "fade=t=in:st=0:d=1,fade=t=out:st=29:d=1" -c:v libx264 -c:a copy segment1.mp4
# -vf "fade=t=in:st=0:d=1,fade=t=out:st={end-1}:d=1"
# cmd = base + f' -ss {start} -to {end} -c copy "segment_{i}.mp4"'
    def __cut_ffmpeg_encoder(self, video_file):
        if "recorded_video" in video_file:
            message = "recorded_segment"
        else:
            message = "ai_screen_grab_segment"
        concat_list = ""
        i =0
        timestamp = os.path.basename(self.__output_dir)
        base = f'ffmpeg -hwaccel rkmpp -i "{video_file}"'
        for segment in self.__speech_segments:
            segment_path = os.path.join(self.__output_dir, f"{timestamp}_ai_{message}_{i}.mp4")
            if not segment.is_relevant:
                continue
            print(f'SEGMENT {i}: {segment.start_time_sec} - {segment.end_time_sec}')
            start = round(segment.start_time_sec, 1)
            end = round(segment.end_time_sec, 1)
            cmd = base + f' -y -ss {start} -to {end} -c copy "{segment_path}"'
            i += 1
            subprocess.run(cmd, shell=True, check=True)
            concat_list += f"file {os.path.abspath(segment_path)} \n"
        if concat_list != "":
            concat_list_text_file = os.path.join(self.__output_dir, f"{message}_concat_list.txt")
            with open(concat_list_text_file, "w") as f:
                f.write(concat_list)
            concat_cmd = f"ffmpeg -y -f concat -safe 0 -i {os.path.abspath(concat_list_text_file)} -c copy {os.path.join(self.__output_dir, message.replace('_segment', '') + '.mp4')}"
            subprocess.run(concat_cmd, shell=True, check=True)

    def __cut_ffmpeg(self) -> None:
        TRANSITION_EFFECT = 'fade'
        TRANSITION_DURATION = 2
        
        try:
            vw_start_time = time.time()
            logger.debug(f'START VIDEO WRITING: {vw_start_time} (timestamp)')

            # Initialize filter complex with hardware acceleration
            cmd = f'ffmpeg -hwaccel rkmpp -c:v h264_rkmpp -i {self.__input_video_path}"'

            # First pass: normalize all segments to same fps
            k = 0
            for segment in self.__speech_segments:
                if not segment.is_relevant:
                    continue
                logger.debug(f'SEGMENT {k}: {segment.start_time_sec} - {segment.end_time_sec}')
                start = round(segment.start_time_sec, 1)
                end = round(segment.end_time_sec, 1)
                # Add fps filter before trim and ensure constant frame rate
                cmd += f''
                # cmd += f'[0:v]fps=25,trim={start}:{end},setpts=PTS-STARTPTS[vtemp{k}];'
                # cmd += f'[vtemp{k}]format=nv12[v{k}];'  # Changed to nv12 for hardware compatibility
                # cmd += f'[0:a]atrim={start}:{end},asetpts=PTS-STARTPTS[a{k}];'
                k += 1

            # Second pass: apply transitions
            k = 0
            total_duration = 0
            last_video_slug = 'v0'
            last_audio_slug = 'a0'

            for segment in self.__speech_segments[:-1]:
                if not segment.is_relevant:
                    continue
                k += 1
                start = round(segment.start_time_sec, 1)
                end = round(segment.end_time_sec, 1)
                segment_duration = round(end - start - TRANSITION_DURATION, 1)
                total_duration = round(total_duration + segment_duration, 1)
                new_video_slug = f'vc{k}'
                new_audio_slug = f'ac{k}'

                cmd += f'[{last_video_slug}][v{k}]'
                cmd += f'xfade=transition={TRANSITION_EFFECT}:duration={TRANSITION_DURATION}:offset={total_duration}[{new_video_slug}];'
                cmd += f'[{last_audio_slug}][a{k}]'
                cmd += f'acrossfade=d={TRANSITION_DURATION}:c1=tri:c2=tri[{new_audio_slug}];'

                last_video_slug = new_video_slug
                last_audio_slug = new_audio_slug

            cmd = cmd[:-1] + '"'

            # Add output options with hardware encoding
            cmd += f' -map "[{last_video_slug}]" -map "[{last_audio_slug}]"'
            cmd += f' -c:v h264_rkmpp'  # Use hardware encoder
            cmd += f' -c:a aac'
            cmd += f' -preset ultrafast'
            cmd += f' -pix_fmt nv12'  # Changed to nv12 for hardware compatibility
            cmd += f' -r 25'  # Ensure output frame rate
            cmd += f' -fps_mode cfr'  # Added for better hardware sync
            cmd += f' -f mp4 -y {self.__output_dir}'

            #logger.debug(f'RUNNING COMMAND: {cmd}')

            # Add environment variables for hardware acceleration
            env = os.environ.copy()
            env['FFMPEG_HWACCEL_DEVICE'] = '/dev/dri/renderD128'  # Adjust device path if needed
            
            subprocess.run(cmd, shell=True, check=True, env=env)  # Added environment variables
            logger.debug(f'TIME TAKEN ON VIDEO WRITING: {time.time() - vw_start_time} (seconds)')

        except subprocess.CalledProcessError as e:
            logger.error(f'FFMPEG ERROR:\nCommand: {e.cmd}\nOutput: {e.output}\nError: {e.stderr}')
            raise
        except Exception as e:
            logger.error(f'PROBLEM WITH VIDEO WRITING:\n{traceback.format_exc()}')
            raise
        
    def __cut_moviepy(self) -> None:
        pass
        # OLD APPROACH
        # try:
        #     transition_clip = VideoFileClip(self.__transition_video_path)
        #     transition_clip = transition_clip.subclip(0, TRANSITION_TIME)
        # except Exception as e:
        #     logger.error(
        #         f'problem with loading transition video: {self.__transition_video_path}\nerror: {e}'
        #     )
        #     raise e

        # try:
        #     video_clip = VideoFileClip(self.__input_video_path)
        # except Exception as e:
        #     logger.error(
        #         f'problem with loading input video: {self.__input_video_path}\nerror: {e}'
        #     )
        #     raise e

        # arr = []
        # for i, segment in enumerate(self.__speech_segments):
        #     logger.info(f'segment {i}: {segment}')
        #     if segment.is_relevant:
        #         arr.append(
        #             video_clip.subclip(segment.start_time_sec, segment.end_time_sec)
        #         )
        #     logger.info(f'segment {i} is done')

        # logger.info(f'start concatenating {len(arr)} clips')
        # final_clip = concatenate_videoclips(arr)
        # logger.info('finish concatenating, start writing')
        # final_clip.write_videofile(
        #     self.__output_video_path,
        #     codec='libx264',
        #     audio_codec='aac',
        #     temp_audiofile='./media/temp-audio.m4a',
        #     remove_temp=True,
        #     preset='ultrafast',
        #     logger=None,
        #     threads=4
        # )
