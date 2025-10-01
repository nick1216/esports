#!/bin/bash

# Start the FastAPI application with headless browser support
echo "🚀 Starting FastAPI application (headless mode)..."
exec uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}

