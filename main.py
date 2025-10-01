"""
Esports EV Finder - Main Entry Point

This is the main entry point for the Esports EV Finder application.
It starts the FastAPI server which serves both the API and the web interface.

Usage:
    python main.py

The application will be available at:
    - Web Interface: http://localhost:8000
    - API Documentation: http://localhost:8000/docs
"""

import uvicorn
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("=" * 60)
    print("🎮 Esports EV Finder")
    print("=" * 60)
    print("\nStarting server...")
    print("Web Interface: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("\nPress CTRL+C to stop the server\n")
    print("=" * 60)
    
    # Run the FastAPI application
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
