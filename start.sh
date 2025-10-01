#!/bin/bash

# Start Xvfb (virtual display for non-headless browser)
echo "🖥️  Starting Xvfb virtual display..."
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!
sleep 2

# Export DISPLAY variable
export DISPLAY=:99

# Wait for Xvfb to be ready
echo "⏳ Waiting for Xvfb to be ready..."
for i in {1..10}; do
    if xdpyinfo -display :99 >/dev/null 2>&1; then
        echo "✅ Xvfb is ready on display :99"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "⚠️  Warning: Xvfb check timed out, proceeding anyway..."
    fi
    sleep 1
done

# Verify display
echo "🔍 Current DISPLAY: $DISPLAY"

# Start the FastAPI application
echo "🚀 Starting FastAPI application..."
exec uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}

