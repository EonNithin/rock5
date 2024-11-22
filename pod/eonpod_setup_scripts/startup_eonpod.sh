#!/bin/bash

# Navigate to the base directory (eonpod-ai)
cd "$HOME/eonpod-ai"

# Perform a git pull to update the repository
echo "Pulling the latest changes from Git..."
if git pull; then
    echo "Successfully pulled the latest changes."
else
    echo "Git pull failed. Continuing with the existing codebase."
fi

# Navigate to the Django project directory
cd "$HOME/eonpod-ai/pod/eonpod" || exit 1

# Check if the Django server is running
if ! lsof -i :8000 | grep LISTEN; then
    echo "Starting Django server..."
    python3 manage.py runserver 8000 &
    SERVER_PID=$!
else
    echo "Django server already running."
fi

# Serve a simple loading page until the server is ready
echo "Displaying loading page..."
chromium-browser --kiosk "file://$HOME/eonpod-ai/pod/eonpod_setup_scripts/loading.html" --disable-pinch --disable-zoom --overscroll-history-navigation=0 &
CHROMIUM_PID=$!

# Wait for the Django server to become accessible
until curl -s http://localhost:8000 > /dev/null; do
    echo "Waiting for server to start..."
    sleep 1
done

# Kill the loading page Chromium instance
echo "Killing loading page..."
kill "$CHROMIUM_PID" 2>/dev/null


# Open the Django app in Chromium in kiosk mode
chromium-browser --kiosk "http://localhost:8000" --disable-pinch --disable-zoom --overscroll-history-navigation=0 &