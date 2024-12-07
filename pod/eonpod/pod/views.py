import asyncio
from datetime import datetime
import glob
import socket
import requests
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
from pod.classes.SensorMonitor import SensorMonitor
from django.views.decorators.cache import cache_control
import logging
from django.shortcuts import render
from uuid import UUID
from dotenv import load_dotenv
from pod.dbmodels.models import DATABASE_URL, get_session
from pod.dbmodels.queries import get_staff_by_rfid_or_pin, get_teacher_subject_groups_by_staff
from pod.classes.DBOffloader import DBOffloader
# from pod.dbmodels.models.staff import Staff
from pod.classes.RecordingDurationMonitor import RecordingDurationMonitor
# Load environment variables
load_dotenv(dotenv_path="base.env")
load_dotenv(dotenv_path="config.env", override=True)

# Get the logger instance for the 'pod' app
logger = logging.getLogger('pod')


# Define the base path for media files
media_folderpath = os.path.join(settings.BASE_DIR, 'media', 'processed_files')

# Initialize the recorder instance
recorder = Recorder()

# Initialize the processing queue
processing_queue = ProcessingQueue()

# Initialize the DB Offloader 
db_offloader = DBOffloader()

# initialize the check device connections
connection_obj = CheckConnections()

SensorMonitor_obj = SensorMonitor()

school_id = settings.SCHOOL_NAME

recording_monitor = RecordingDurationMonitor()
recording_monitor.start_monitor()


# Global variables to hold device statuses
camera_status = False
mic_status = False
screen_capture_status = False


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
            subject_name = data.get('subject_name', '') 
            class_no = data.get('class_no', '')
            logger.info(f"selected subject is : {selected_subject}")
            logger.info(f"subject name is : {subject_name}")
            logger.info(f"class_no  is : {class_no}")
            logger.info(f"Started recording for subject: {selected_subject}")
            is_language = data.get('isLanguage', '') 
            logger.info(f"Is language: {is_language}")

            # Call both recording and screen grab concurrently
            recording_monitor.set_recording_start(data) 
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
        try:
            data = json.loads(request.body)
            selected_subject = data.get('subject', '')  
            subject_name = data.get('subject_name', '') 
            class_no = data.get('class_no', '') 
            is_language = data.get('isLanguage', '') 

            logger.info(f"Selected Subject: {selected_subject}")
            logger.info(f"Subject Name: {subject_name}")
            logger.info(f"Class Number: {class_no}")
            logger.info(f"Is Language: {is_language} (Type: {type(is_language)})")
            
            try:
                recording_monitor.clear_recording_data()
                recorder.stop_recording()
                recorder.stop_screen_grab()
                logger.info(f"Stopped recording for subject: {selected_subject}")
            except Exception as e:
                logger.error(f"Error stopping recording or screen grab: {str(e)}")
                return JsonResponse({"success": False, "message": "Error stopping recording or screen grab.", "error": str(e)})

            try:
                recorded_files = recorder.get_recorded_files()
                if len(recorded_files) == 0:
                    logger.info("No recordings found.")
                elif len(recorded_files) == 1:
                    logger.info("Single recording found.")
                    recorder.rename_outputfile()
                else:
                    logger.info("Multiple recordings found, concatenating...")
                    recorder.concat_recording_parts()
            except Exception as e:
                logger.error(f"Error handling recorded files: {str(e)}")
                return JsonResponse({"success": False, "message": "Error handling recorded files.", "error": str(e)})

            try:
                screengrab_files = recorder.get_screengrab_files()
                if len(screengrab_files) == 0:
                    logger.info("No Screen grab recording found.")
                elif len(screengrab_files) == 1:
                    logger.info("Single Screen grab recording found.")
                    recorder.rename_screengrabfile()
                else:
                    logger.info("Multiple screen grabs found, concatenating...")
                    recorder.concat_screengrab_parts()
            except Exception as e:
                logger.error(f"Error handling screen grab files: {str(e)}")
                return JsonResponse({"success": False, "message": "Error handling screen grab files.", "error": str(e)})

            try:
                if recorded_files:
                    file_info = recorder.get_file_info()
                    logger.info(f"File Info: {file_info}")
                    processing_queue.add_to_queue(
                        file_info['filename'], 
                        file_info['filepath'], 
                        selected_subject, 
                        subject_name, 
                        class_no, 
                        is_language
                    )
                    return JsonResponse({
                        "success": True,
                        "message": "Recording stopped and sent to processing.",
                        "filename": file_info["filename"],
                        "filepath": file_info["filepath"]
                    })
                else:
                    return JsonResponse({
                        "success": False,
                        "message": "No recorded files found.",
                        "filename": None,
                        "filepath": None
                    })
            except Exception as e:
                logger.error(f"Error adding to processing queue: {str(e)}")
                return JsonResponse({"success": False, "message": "Error during file processing.", "error": str(e)})

        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding error: {str(e)}")
            return JsonResponse({"success": False, "message": "Invalid JSON data.", "error": str(e)})
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return JsonResponse({"success": False, "message": "An error occurred.", "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request method."})


@cache_control(no_store=True, no_cache=True, must_revalidate=True)
@csrf_exempt
def check_device_connections(request):

    global camera_status, mic_status, screen_capture_status
    if request.method == "POST":
        try:
            camera_status = connection_obj.test_rtsp_connection()
            mic_status = connection_obj.test_alsa_connection()
            screen_capture_status = connection_obj.test_video_device()
            
            logger.info(f"Camera status: {camera_status}, Mic status: {mic_status}, Screen capture status: {screen_capture_status}")

            return JsonResponse({
                'camera_status': camera_status,
                'mic_status': mic_status,
                'screen_capture_status': screen_capture_status
            })
        except Exception as e:
            logger.error(f"Error checking device connections: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)


def is_internet_available():
    try:
        # Connect to a well-known public DNS server (Google's DNS)
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False


def get_staff_subject_groups(pin, school_id):
    if not is_internet_available():
        # No internet; directly use local DB
        logger.info("No internet connection. Falling back to local DB.")
        return handle_local_db(pin, school_id)

    # API URL
    api_url = os.getenv('LOGIN_API')
    url = api_url
    
    # Payload for the POST request
    payload = {
        "pin": pin,
        "school_id": school_id
    }
    
    try:
        # Sending the POST request
        response = requests.post(url, json=payload, timeout=5)  # Set a timeout to avoid excessive waiting
        
        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            data = response.json()
            logger.info(f"Response from API: {response.status_code}")# json.dumps(data, indent=4)
            return data
        else:
            # Fall back to local DB if the API fails
            logger.error(f"Failed to get data. Status code: {response.status_code}, \nTrying to hit local DB")
            return handle_local_db(pin, school_id)
    except requests.exceptions.RequestException as e:
        logger.info(f"Error during API call: {e}")
        # No internet connection, use local database instead
        return handle_local_db(pin, school_id)



def handle_local_db(value, school_id):
    try:
        session = get_session(database_url=DATABASE_URL)  # Create a new session for the database interaction
    except Exception as e:
        logger.error(f"Error connecting to local DB: {e}")
        return {'error_message': "Could not access local database"}

    try:
        staff_member = None
        
        # if value and len(value) > 4:
        #     # Retrieve staff details based on RFID
        #     staff_member = get_staff_by_rfid(session, value, school_id)
        # elif value and len(value) == 4:
        #     # Retrieve staff details based on PIN
        #     value = int(value)
        #     staff_member = get_staff_by_pin(session, value, school_id)
        try:
            # Check staff member using the combined RFID or PIN query
            if value:
                staff_member = get_staff_by_rfid_or_pin(session, value, school_id)
        except Exception as e:
            logger.error(f"Error fetching staff member from DB: {e}")
            return {'error_message': "Could not retrieve staff member data"}

        if staff_member:
            logger.info(f"Login successful: {staff_member.first_name} {staff_member.last_name}")
            
            try:
                # Retrieve subject groups for the staff member
                subjects = get_teacher_subject_groups_by_staff(session, staff_member=staff_member)
                subject_groups = []

                for subject in subjects:
                    try:
                        # Access the related SubjectGroup instance
                        subject_group = subject.subject_group

                        # Structure the data like the API response, converting UUIDs to strings
                        subject_groups.append({
                            'class_name': subject_group.class_name,
                            'title': subject_group.title,
                            'is_active': subject_group.is_active,
                            'school_id': str(subject_group.school_id) if isinstance(subject_group.school_id, UUID) else subject_group.school_id,
                            'id': str(subject_group.id) if isinstance(subject_group.id, UUID) else subject_group.id,
                            'subject': subject_group.subject,
                            'is_language_subject': subject_group.is_language_subject,
                            'section': subject_group.section,
                        })
                    except Exception as e:
                        logger.error(f"Error processing subject group data: {e}")
                        # Skip the current subject group and continue processing others
                        continue
                
                logger.info("Subject groups successfully retrieved from local DB")
                
                # Return a similar response format as the API
                return {
                    "first_name": staff_member.first_name,
                    "last_name": staff_member.last_name,
                    "subject_groups": subject_groups
                }
            except Exception as e:
                logger.error(f"Error retrieving subject groups: {e}")
                return {'error_message': "An error occurred while retrieving subject groups"}
        else:
            logger.warning(f"Staff member not found for value: {value}")
            return {'error_message': "Staff member not found."}
    except Exception as e:
        logger.error(f"Error during local DB processing: {e}")
        return {'error_message': "An error occurred while processing the local database"}
    finally:
        try:
            # Always close the session to avoid any connection leaks
            session.close()
        except Exception as e:
            logger.error(f"Error closing the database session: {e}")


@csrf_exempt
def login_page(request):
    error_message = None  # Initialize error_message here
    staff_member = None  # To store the retrieved staff member details

    if request.method == 'POST':
        value = request.POST.get('pin')  # Retrieve the PIN or RFID from the form field
        try:
            if value:
                response = get_staff_subject_groups(value, school_id)
                # logger.info(f"Response of get_staff_subject_groups: {response}")  # Corrected logging
                firstname = response['first_name']
                lastname = response['last_name']
                username = f"{firstname} {lastname}"
                # Extract subject groups
                subject_groups = response['subject_groups']
                if subject_groups:
                    # Store subject groups in session
                    request.session['subject_groups'] = subject_groups
                    request.session['username'] = username
                    logger.info(f"subject group values fetched:{subject_groups}")
                    return render(request, 'subjectcards.html', {
                            'username': username,  # Assuming staff name comes in subjects
                            'subject_groups': subject_groups  # Pass the subjects to the template
                        })
                else :
                    return render(request, 'login_page.html', {'error_message': "No Subjects Assigned"})
            else:
                error_message = "Invalid credentials. Please try again."
        except Exception as e:
            logger.error(f"An error occurred during login: {e}")
            error_message = "Invalid Credentials. Please try again."

    return render(request, 'login_page.html', {'error_message': error_message})


@csrf_exempt
def subjectcards(request):
    # Retrieve subject groups and username from session
    subject_groups = request.session.get('subject_groups', [])
    username = request.session.get('username', '')

    logger.info(f"I am in subjectcards, subject groups are: {subject_groups}")
    logger.info(f"Username is: {username}")

    # Combine context data into one dictionary
    return render(request, 'subjectcards.html', {
        'subject_groups': subject_groups,
        'username': username
    })


@csrf_exempt
def eonpod(request):
    # Render `eonpod.html` template 
    return render(request, 'eonpod.html')