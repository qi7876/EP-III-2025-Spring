FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    # Set timezone if needed, e.g., for logging timestamps
    TZ=Etc/UTC \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
# - libzmq3-dev: For pyzmq native extension compilation
# - libgl1: Common dependency for OpenCV (even headless)
# - libglib2.0-0: Another common dependency
# - Optional: libv4l-dev for camera access potential (might be needed depending on host OS/setup)
# - ca-certificates: For potential HTTPS requests if added later
RUN apt-get update && apt-get install -y --no-install-recommends \
    libzmq3-dev \
    libgl1 \
    libglib2.0-0 \
    # Uncomment the next line if camera issues arise, might help
    # libv4l-dev \
    ca-certificates \
    # Clean up apt cache to reduce image size
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Using --no-cache-dir reduces image size slightly
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code (app.py, templates/, static/)
# into the working directory (/app)
COPY . .

# No EXPOSE needed if using --net=host
# If not using --net=host, you would uncomment and expose like this:
# EXPOSE 5000/tcp      # Default Flask port
# EXPOSE 30001/udp     # Discovery port
# EXPOSE ZMQ_PORT/tcp  # ZMQ port - problematic as it can be dynamic

# Define the command to run the application
# Using list form is generally preferred for CMD
# Allows passing arguments like --flask-port or --zmq-port during `docker run`
CMD ["python", "app.py"]