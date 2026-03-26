# Use a highly compressed, lightweight Python image to save disk space
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your main.py server code into the container
COPY . .

# Expose the port your FastAPI server uses
EXPOSE 8000

# The command to start the server when the container runs
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]