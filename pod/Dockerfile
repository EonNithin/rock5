# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /eonpod


# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libyaml-dev \
    pkg-config \
    libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y ffmpeg

# Upgrade pip, setuptools, and wheel
RUN pip install --upgrade pip setuptools wheel

# Install Cython
RUN pip install Cython

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt /eonpod/

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy the rest of your application code
COPY /pod/eonpod /eonpod/

# Expose the port on which the Django app will run
EXPOSE 8000

# Set environment variables for Django
ENV PYTHONUNBUFFERED=1

# Run the Django development server
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]
