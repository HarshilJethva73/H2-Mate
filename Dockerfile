# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install ffmpeg and other dependencies
RUN apt-get update && apt-get install -y ffmpeg libstdc++ libffi-dev && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8080 available to the world outside this container
EXPOSE 8080

# Define environment variable for Flask
ENV FLASK_APP=script.py

# Run the application
CMD ["gunicorn", "script:app", "--bind", "0.0.0.0:8080"]
