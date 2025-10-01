#!/bin/bash
# Cron job script for CS500 scraper
# This runs the scraper with Xvfb for headless browser support

# Start Xvfb in the background
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
XVFB_PID=$!

# Wait for Xvfb to be ready
sleep 2

# Set display variable
export DISPLAY=:99

# Run the scraper
python run_cs500_scraper.py

# Clean up
kill $XVFB_PID 2>/dev/null || true

