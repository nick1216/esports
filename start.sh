#!/bin/bash
# Startup script for Render deployment

# Start Xvfb in the background
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &

# Wait for Xvfb to be ready
sleep 2

# Start the FastAPI application
exec uvicorn api:app --host 0.0.0.0 --port 8000

