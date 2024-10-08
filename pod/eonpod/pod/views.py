from datetime import datetime
import glob
import json
import os
from django.shortcuts import render, redirect
from django.http import JsonResponse
from whisper_cpp_python import whisper
from django.conf import settings
from eonpod import settings
from django.http import JsonResponse, HttpResponseBadRequest, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from pod.classes.ProcessingQueue import ProcessingQueue
from pod.classes.Recorder import Recorder
from django.http import HttpResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
import time
import cv2
import numpy
from pod.classes.CheckConnections import CheckConnections
import logging
from django.shortcuts import render

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')


# Define the base path for media files
media_folderpath = os.path.join(settings.BASE_DIR, 'media', 'processed_files')

# Initialize the recorder instance
recorder = Recorder()

# Initialize the processing queue
processing_queue = ProcessingQueue()

# initialize the check device connections
connections = CheckConnections()

# Global variables to hold device statuses
camera_status = False
mic_status = False
screen_capture_status = False


@csrf_exempt
@xframe_options_exempt
def video_stream(request):
    # Open the video capture (replace with your RTSP URL)
    video_source = 'rtsp://admin:hik@9753@192.168.0.252:554/Streaming/Channels/101'
    cap = cv2.VideoCapture(video_source)

    # Define a generator function to stream the video frames
    def generate():
        while True:
            success, frame = cap.read()
            if not success:
                break
            # Encode the frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            frame_data = buffer.tobytes()
            # Yield the frame data in the correct format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' +
                   frame_data + b'\r\n')

    return StreamingHttpResponse(generate(), content_type='multipart/x-mixed-replace; boundary=frame')


@csrf_exempt
def start_recording_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            selected_subject = data.get('subject', '')  # Get the subject from the request
            logger.info(f"selected subject is : {selected_subject}")
            logger.info(f"Started recording for subject: {selected_subject}")
            recorder.start_recording(selected_subject)
            logger.info(f"Just after start recording and before start screen grab: {datetime.now().time()}")
            recorder.start_screen_grab()
            logger.info(f"Just after start screen grab: {datetime.now().time()}")

            return JsonResponse({"success": True, "message": "Recording started."})
        except Exception as e:
            logger.error(f"Error starting recording: {str(e)}")
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method."})


@csrf_exempt
def stop_recording_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            selected_subject = data.get('subject', '')  
            logger.info(f"Stopped recording for subject: {selected_subject}")
            recorder.stop_recording()
            logger.info(f"Just after stop recording and before stop screen grab: {datetime.now().time()}")
            recorder.stop_screen_grab()
            logger.info(f"Just after stop screen grab: {datetime.now().time()}")
            file_info = recorder.get_file_info()
            logger.info(f"File Info: {file_info}")

            processing_queue.add_to_queue(file_info['filename'], file_info['filepath'], selected_subject)
            # processing_queue.add_to_queue('recordedfiles.mp4', os.path.join(media_folderpath, 'Mathematics/04-10-2024_08-57-20/16-09-2024_06-34-24_recorded_video.mp4'), selected_subject)


            return JsonResponse({
                "success": True,
                "message": "Recording stopped.",
                "filename": file_info["filename"],
                "filepath": file_info["filepath"]
            })
        except Exception as e:
            logger.error(f"Error stopping recording: {str(e)}")
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method."})


@csrf_exempt
def check_device_connections(request):

    global camera_status, mic_status, screen_capture_status
    if request.method == "POST":
        try:
            connections = CheckConnections()
            camera_status = connections.test_rtsp_connection()
            mic_status = connections.test_alsa_connection()
            screen_capture_status = connections.test_video_device()
            
            logger.info(f"Camera status: {camera_status}, Mic status: {mic_status}, Screen capture status: {screen_capture_status}")

            return JsonResponse({
                'camera_status': camera_status,
                'mic_status': mic_status,
                'screen_capture_status': screen_capture_status
            })
        except Exception as e:
            logger.error(f"Error checking device connections: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)



@csrf_exempt
def login_page(request):
    error_message = None  # Initialize error_message here
    rfid = None  # Initialize rfid to avoid UnboundLocalError
    pin = None   # Initialize pin to avoid UnboundLocalError

    if request.method == 'POST':
        value = request.POST.get('pin')  # Retrieve the PIN from the form name attribute
        username = "Kaushik"
        # rfid Kaushik = 0133014078
        if len(value) == 10:
            rfid = value
        elif len(value) == 4:
            pin = value

        if rfid and len(rfid) == 10:
            logger.info(f"RFID entered: {rfid}")
            logger.info("Redirecting to eonpod page")
            return render(request, 'eonpod.html', {'username': username})  # Redirect to the eonpod page if RFID matches
        elif pin and len(pin) == 4:
            logger.info(f"PIN entered: {pin}")
            logger.info("Redirecting to eonpod page")
            return render(request, 'eonpod.html', {'username': username})  # Redirect to the eonpod page if PIN matches
        else:
            error_message = "Invalid credentials. Please try again."
            logger.warning(f"Login failed with PIN: {pin} or RFID: {rfid}")
            return render(request, 'login_page.html', {'error_message': error_message})

    return render(request, 'login_page.html', {'error_message': error_message})

# @login_required
def ai_chatpage(request):
   return render(request, 'ai_chatpage.html')


# @login_required
def eonpod(request):
    # start_preview()
    # global recording_status, streaming_status
    # Log the current recording and streaming status
    # logger.info(f"Streaming status in eonpod view: {streaming_status}")
    # print(f"Recording status is : {recording_status}, Streaming status is : {streaming_status}")
    return render(request, 'eonpod.html')

