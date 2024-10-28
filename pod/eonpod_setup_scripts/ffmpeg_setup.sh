#!/bin/bash

# Function to display status messages
echo_status() {
    echo -e "\n[STATUS] $1\n"
}

# Update package lists and remove any existing ffmpeg installation
echo_status "Removing any existing FFmpeg installation"
sudo apt-get remove --purge -y ffmpeg

# Clean up after removal
sudo apt-get autoremove -y
sudo apt-get autoclean

# Install cmake
echo_status "Installing cmake"
sudo apt-get install -y cmake

# Update package lists and install required packages
echo_status "Updating package lists and installing build-essential, pkg-config, git"
sudo apt-get update
sudo apt-get install -y build-essential pkg-config git yasm libdrm-dev libudev-dev

# Install git (in case it's not installed already)
echo_status "Installing git"
sudo apt-get install -y git

# Clone and build MPP (Rockchip Media Process Platform)
echo_status "Cloning and building MPP from rockchip-linux"
git clone https://github.com/rockchip-linux/mpp.git
cd mpp

# Build and install MPP
echo_status "Building MPP with cmake"
cmake -DRKPLATFORM=ON -DHAVE_DRM=ON -DHAVE_LINUX=ON -DCMAKE_INSTALL_PREFIX=/usr .
make -j$(nproc)

echo_status "Installing MPP"
sudo make install

# Return to the home directory
cd ~

sudo apt install ffmpeg

echo_status "Setup completed successfully!"

