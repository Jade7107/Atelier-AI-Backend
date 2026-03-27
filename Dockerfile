# Use a highly compressed, lightweight Python image to save disk space
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the AI model during the Docker build to prevent timeouts
RUN python -c "from rembg import new_session; new_session('u2netp')"

# Copy your main.py server code into the container
COPY . .

# Expose the port your FastAPI server uses
EXPOSE 8000

# The command to start the server when the container runs
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}