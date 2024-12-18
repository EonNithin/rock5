#!/bin/bash

# Function to check if Python 3.10 is installed
check_python() {
    if command -v python3.10 &> /dev/null; then
        echo "Python 3.10 is already installed."
    else
        echo "Python 3.10 is not installed. Installing it now..."
        sudo apt-get update
        sudo apt-get install -y software-properties-common
        sudo add-apt-repository -y ppa:deadsnakes/ppa
        sudo apt-get update
        sudo apt-get install -y python3.10 python3.10-venv python3.10-dev
        echo "Python 3.10 installed successfully."
    fi
}

# Function to check and install pip for Python 3.10
check_pip() {
    if command -v pip3 &> /dev/null; then
        echo "pip for Python 3.10 is already installed."
    else
        echo "pip for Python 3.10 is not installed. Installing it now..."
        sudo apt-get update
        sudo apt-get install -y python3-pip
        echo "pip installed successfully."
    fi
}


# Call the function to check and install Python 3.10
check_python

# Call the function to check and install pip for Python 3.10
check_pip


# Variables
REPO_URL="https://github.com/EonNithin/rock5.git"  # Your GitHub repository URL
PROJECT_DIR="$HOME/eonpod"  # Your project directory path
REQUIREMENTS_FILE="$PROJECT_DIR/pod/eonpod/requirements.txt"

# Step 1: Create project directory if it doesn't exist
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Directory $PROJECT_DIR does not exist. Creating it..."
    mkdir -p "$PROJECT_DIR"
else
    echo "Directory $PROJECT_DIR already exists."
fi

# Step 2: Clone the repository or pull latest changes if it already exists
cd "$PROJECT_DIR" || exit
if [ -d ".git" ]; then
    echo "Repository already exists. Pulling the latest changes..."
    git pull
else
    echo "Cloning repository from $REPO_URL on branch eonpod..."
    git clone -b eonpod "$REPO_URL" "$PROJECT_DIR"
    cd "$PROJECT_DIR" || exit
fi

# Step 3: Install portaudio for pyaudio
echo "Installing portaudio..."
sudo apt-get update
sudo apt-get install -y portaudio19-dev

# Step 4: Check for requirements.txt and install dependencies
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Found requirements.txt, installing dependencies..."

    echo "Installing requirements..."
    pip install --upgrade pip
    pip install -r "$REQUIREMENTS_FILE"
else
    echo "requirements.txt not found, skipping dependency installation."
fi

echo "Setup complete."