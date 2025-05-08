# Use lightweight Python base image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp and support libraries
RUN pip install yt-dlp

# Create app directory
WORKDIR /app

# Copy your Flask script and static files
COPY script.py /app/
COPY index.html /app/

# Copy pre-exported cookies.txt (you generate this locally)
COPY cookies.txt /app/

# Expose port Railway expects
EXPOSE 8080

# Run Flask using Gunicorn
CMD ["gunicorn", "script:app", "--timeout", "300", "--workers", "2", "--bind", "0.0.0.0:8080"]
