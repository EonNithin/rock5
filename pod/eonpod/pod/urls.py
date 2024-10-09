from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from pod.views import login_page, eonpod, check_device_connections, ai_chatpage, start_recording_view, stop_recording_view, pause_recording_view, resume_recording_view, video_stream

urlpatterns = [
    path('', login_page, name='login_page'),
    path('login_page/', login_page, name='login_page'),
    path('eonpod/', eonpod, name='eonpod'),
    path('check_device_connections/', check_device_connections, name='check_device_connections'),
    path('ai_chatpage/', ai_chatpage, name='ai_chatpage'),
    # path('generate_response/', generate_response, name='generate_response'),
    # path('update_recording_status/', update_recording_status, name='update_recording_status'),
    # path('update_streaming_status/', update_streaming_status, name='update_streaming_status'),
    # path('get_latest_mp4_filepath/', get_latest_mp4_filepath, name='get_latest_recording'),
    path('start_recording_view/', start_recording_view, name='start_recording'),
    path('stop_recording_view/', stop_recording_view, name='stop_recording'),
    path('video_stream', video_stream, name = "video_stream"),
    path('pause_recording_view/', pause_recording_view, name='pause_recording_view'),
    path('resume_recording_view/', resume_recording_view, name='resume_recording_view'),
    # Add other URL patterns as needed
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
