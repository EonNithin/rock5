#!/bin/bash

# Navigate to the Django project directory
cd "$HOME/eonpod-ai/pod/eonpod" || exit

# Check if port 8000 is in use (Django server running)
if ! lsof -i :8000; then
    # Start the Django server in the background if not running
    exec python3 manage.py runserver 8000 &
    sleep 3
fi

# Kill any existing Chromium instance in kiosk mode
pkill -f "chromium-browser --kiosk" 2>/dev/null

sleep 3 

# Open Chromium in kiosk mode pointing to localhost
exec chromium-browser --kiosk "http://localhost:8000" --disable-pinch --overscroll-history-navigation=0

