FROM python:3.10-slim
WORKDIR /app

# Install system dependencies required for Headless OpenCV and MediaPipe
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose the Flask port
EXPOSE 5001

CMD ["python", "ai_server.py"]
