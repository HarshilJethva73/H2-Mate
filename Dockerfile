# Dockerfile
FROM python:3.11-slim

# Install required system packages for ffmpeg and libraries
RUN apt-get update \
    && apt-get install -y ffmpeg libstdc++6 libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY script.py index.html cookies.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir flask flask-cors yt_dlp gunicorn

EXPOSE 8080
CMD ["gunicorn", "--timeout", "1200", "--workers", "2", "--bind", "0.0.0.0:8080", "script:app"]
