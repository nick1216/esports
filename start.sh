#!/bin/bash

# Start Xvfb (virtual display for headless browser)
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1920x1080x24 &
sleep 2

# Wait for Xvfb to be ready
echo "Waiting for Xvfb to be ready..."
while ! xdpyinfo -display :99 >/dev/null 2>&1; do
    sleep 1
done

echo "Xvfb is ready!"

# Start the FastAPI application
echo "Starting FastAPI application..."
exec uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}

