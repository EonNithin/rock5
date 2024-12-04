#!/bin/bash

# Serve a simple loading page until the server is ready
echo "Displaying loading page..."
chromium-browser --kiosk "file://$HOME/eonpod-ai/pod/eonpod_setup_scripts/loading.html" --disable-pinch --disable-zoom --overscroll-history-navigation=0 &
CHROMIUM_PID=$!

# Navigate to the base directory (eonpod-ai)
cd "$HOME/eonpod-ai"

# Stash any local changes
echo "Stashing local changes..."
if git stash; then
    echo "Successfully stashed local changes."
else
    echo "No local changes to stash, or stash operation failed."
fi

# Perform a git pull to update the repository
echo "Pulling the latest changes from Git..."
if git pull; then
    echo "Successfully pulled the latest changes."
else
    echo "Git pull failed. Continuing with the existing codebase."
fi



# Run PostgreSQL commands to drop specific tables
echo "Running PostgreSQL commands..."
psql postgresql://learneon_dev:12345@localhost:5432/local_eonpod_db <<EOF
DROP TABLE IF EXISTS school CASCADE;
DROP TABLE IF EXISTS staff CASCADE;
DROP TABLE IF EXISTS subject_group CASCADE;
DROP TABLE IF EXISTS teacher_subject_groups CASCADE;
EOF

if [ $? -eq 0 ]; then
    echo "PostgreSQL commands executed successfully."
else
    echo "Failed to execute PostgreSQL commands. Check database connectivity and syntax."
    exit 1
fi

# Execute the shell script to set up the database
echo "Executing database setup script..."
DB_SETUP_SCRIPT="$HOME/eonpod-ai/pod/eonpod_setup_scripts/local DB Setup scripts/create_tables_in_DB.sh"
if [ -f "$DB_SETUP_SCRIPT" ]; then
    chmod +x "$DB_SETUP_SCRIPT"
    "$DB_SETUP_SCRIPT"
    if [ $? -eq 0 ]; then
        echo "Database setup script executed successfully."
    else
        echo "Database setup script execution failed."
        exit 1
    fi
else
    echo "Database setup script not found: $DB_SETUP_SCRIPT"
    exit 1
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

# Wait for the Django server to become accessible
until curl -s http://localhost:8000 > /dev/null; do
    echo "Waiting for server to start..."
    sleep 5
done

# Kill the loading page Chromium instance
echo "Killing loading page..."
kill "$CHROMIUM_PID" 2>/dev/null


# Open the Django app in Chromium in kiosk mode
chromium-browser --kiosk "http://localhost:8000" --disable-pinch --disable-zoom --overscroll-history-navigation=0 &