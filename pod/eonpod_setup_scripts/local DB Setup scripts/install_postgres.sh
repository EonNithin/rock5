#!/bin/bash

PASSWORD="12345"  # Replace with your actual password

# Install PostgreSQL and necessary packages
echo "Installing PostgreSQL..."
echo $PASSWORD | sudo -S apt update && echo $PASSWORD | sudo -S apt install -y postgresql postgresql-client

if [ $? -eq 0 ]; then
    echo "PostgreSQL installed successfully."

    # Start PostgreSQL service
    echo "Starting PostgreSQL service..."
    echo $PASSWORD | sudo -S systemctl start postgresql
    if [ $? -eq 0 ]; then
        echo "PostgreSQL service started successfully."
        
        # Enable PostgreSQL service
        echo "Enabling PostgreSQL service to start on boot..."
        echo $PASSWORD | sudo -S systemctl enable postgresql
        if [ $? -eq 0 ]; then
            echo "PostgreSQL service enabled to start on boot successfully."
        else
            echo "Failed to enable PostgreSQL service to start on boot."
        fi
    else
        echo "Failed to start PostgreSQL service."
    fi
else
    echo "Failed to install PostgreSQL."
fi

# Check PostgreSQL version
echo "Checking PostgreSQL version..."
psql --version
