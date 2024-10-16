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

from pod.dbmodels.models import DATABASE_URL, get_session
from pod.dbmodels.queries import get_staff_by_rfid, get_staff_by_pin, get_teacher_subject_groups_by_staff


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
def pause_recording_view(request):
    if request.method == 'POST':
        try:
            # Call the pause recording method
            recorder.pause_recording()

            # Return success response
            return JsonResponse({'status': 'success', 'message': 'Recording paused successfully'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400) 


@csrf_exempt
def resume_recording_view(request):
    if request.method == 'POST':
        try:
            # Call the pause recording method
            recorder.resume_recording()

            # Return success response
            return JsonResponse({'status': 'success', 'message': 'Recording paused successfully'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400) 


@csrf_exempt
def start_recording_view(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            selected_subject = data.get('subject', '')  # Get the subject from the request
            logger.info(f"selected subject is : {selected_subject}")
            logger.info(f"Started recording for subject: {selected_subject}")
            is_language = data.get('isLanguage', '') 
            logger.info(f"Is language: {is_language}")
            recorder.start_recording(selected_subject)
            recorder.start_screen_grab()
            return JsonResponse({"success": True, "message": "Recording started."})
        except Exception as e:
            logger.error(f"Error starting recording: {str(e)}")
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Invalid request method."})


@csrf_exempt
def stop_recording_view(request):
    if request.method == "POST":
        # try:
        data = json.loads(request.body)
        selected_subject = data.get('subject', '')  
        
        is_language = data.get('isLanguage', '') 
        logger.info(f"Is language: {is_language}")
        recorder.stop_recording()
        recorder.stop_screen_grab()
        logger.info(f"Stopped recording for subject: {selected_subject}")
        # Once the recording stops, concatenate parts
        recorded_files = recorder.get_recorded_files()

        if len(recorded_files) == 0:
            logger.info("No recordings found.")
        elif len(recorded_files) == 1:
            logger.info("Single recording found.")
            recorder.rename_outputfile()
        else:
            # Multiple recordings found, concatenate them
            logger.info("Multiple recordings found, concatenating...")
            # Call your concatenation function here
            recorder.concat_recording_parts()
        

        # Once the recording stops, concatenate parts
        screengrab_files = recorder.get_screengrab_files()

        if len(screengrab_files) == 0:
            logger.info("No Screen grab Recording found.")
        elif len(screengrab_files) == 1:
            logger.info("Single Screen grab recording found.")
            recorder.rename_screengrabfile()
        else:
            # Multiple recordings found, concatenate them
            logger.info("Multiple recordings found, concatenating...")
            # Call your concatenation function here
            recorder.concat_screengrab_parts()

        
        file_info = recorder.get_file_info()
        logger.info(f"File Info: {file_info}")
        
        logger.info(f"Processing happens, as it's not a language subject: {is_language}")

        processing_queue.add_to_queue(file_info['filename'], file_info['filepath'], selected_subject, is_language)

        return JsonResponse({
            "success": True,
            "message": "Recording stopped.",
            "filename": file_info["filename"],
            "filepath": file_info["filepath"]
        })
        # except Exception as e:
        #     logger.error(f"Error stopping recording: {str(e)}")
        #     return JsonResponse({"success": False, "error": str(e)})

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

school_id = settings.SCHOOL_NAME

@csrf_exempt
def login_page(request):
    error_message = None  # Initialize error_message here
    staff_member = None  # To store the retrieved staff member details

    if request.method == 'POST':
        value = request.POST.get('pin')  # Retrieve the PIN or RFID from the form field
        try:
            session = get_session(DATABASE_URL)  # Create a new session for the database interaction
        except:
            return render(request, 'login_page.html', {'error_message': "No Internet Connection"})

        try:
            if value and len(value) > 4:
                # Retrieve staff details based on RFID
                staff_member = get_staff_by_rfid(session, value, school_id)
                
            elif value and len(value) == 4:
                # Retrieve staff details based on PIN (you need to implement this method if required)
                value = int(value)
                # Log the new type after conversion
                staff_member = get_staff_by_pin(session, value, school_id)  # Assuming you'll create this method

            if staff_member:
                logger.info(f"Login successful: {staff_member.first_name} {staff_member.last_name}")
                
                subjects = get_teacher_subject_groups_by_staff(session, staff_member=staff_member)

                # for subject in subjects:
                #     print(f"Subjects for {staff_member.first_name}: {subject.subject_group_id}")

                #     # Accessing attributes from SubjectGroup
                #     subject_group = subject.subject_group  # Accessing the related SubjectGroup instance
                #     print(f"Title: {subject_group.title}")
                #     print(f"Class: {subject_group.class_name}")
                #     print(f"Subject: {subject_group.subject}")
                #     print(f"Is Active: {subject_group.is_active}")
                #     print(f"Is Language Subject: {subject_group.is_language_subject}")

                # Redirect to the eonpod page with the staff member's details
                # return render(request, 'eonpod.html', {'username': f"{staff_member.first_name} {staff_member.last_name}"})
                # Redirect to the eonpod page with the staff member's details and subjects

                subject_data = []
                for subject in subjects:
                    subject_group = subject.subject_group  # Access the related SubjectGroup instance

                    subject_data.append({
                        'title': subject_group.title,
                        'class_name': subject_group.class_name,
                        'subject': subject_group.subject,
                        'is_active': subject_group.is_active,
                        'is_language_subject': subject_group.is_language_subject,
                    })

                return render(request, 'eonpod.html', {
                    'username': f"{staff_member.first_name} {staff_member.last_name}",
                    'subjects': subjects  # Pass the subjects to the template
                })
                
            else:
                error_message = "Invalid credentials. Please try again."
        except Exception as e:
            logger.error(f"An error occurred during login: {e}")
            error_message = "Invalid Credentials. Please try again."
        finally:
            session.close()

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

