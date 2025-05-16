# Dockerfile
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y ffmpeg libstdc++6 libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["gunicorn", "--timeout", "1200", "--workers", "2", "--bind", "0.0.0.0:8080", "script:app"]
