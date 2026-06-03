#!/usr/bin/env python3
"""
Project Vyom - Web-based Ground Control Station Startup Script
Starts the modern web-based ground control station
"""

import sys
import os
import subprocess
import webbrowser
import time
import argparse
from pathlib import Path

def main():
    """Main startup function"""
    parser = argparse.ArgumentParser(description="Project Vyom Ground Control Station")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    # Get the directory containing this script
    script_dir = Path(__file__).parent
    web_gui_dir = script_dir / "web_gui"
    
    print("Starting Project Vyom Ground Control Station...")
    print(f"Working directory: {script_dir}")
    print(f"Web GUI directory: {web_gui_dir}")
    
    # Check if web_gui directory exists
    if not web_gui_dir.exists():
        print(f"ERROR: Web GUI directory not found: {web_gui_dir}")
        print("Please ensure the web_gui folder exists with index.html")
        sys.exit(1)
    
    # Check if index.html exists
    index_file = web_gui_dir / "index.html"
    if not index_file.exists():
        print(f"ERROR: index.html not found: {index_file}")
        sys.exit(1)
    
    # Install required packages if needed
    try:
        import fastapi
        import uvicorn
        print("SUCCESS: FastAPI and Uvicorn are available")
    except ImportError:
        print("Installing required packages...")
        subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn[standard]", "websockets"], check=True)
        print("SUCCESS: Packages installed successfully")
    
    # Start the web server
    print(f"Starting web server on http://{args.host}:{args.port}")
    print("Ground Control Station will be available in your browser")
    print("Press Ctrl+C to stop the server")
    
    # Open browser if requested
    if not args.no_browser:
        def open_browser():
            time.sleep(2)  # Wait for server to start
            webbrowser.open(f"http://{args.host}:{args.port}")
        
        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
    
    try:
        # Change to the script directory and start the server
        os.chdir(script_dir)
        
        # Start the server
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "web_server:app",
            "--host", args.host,
            "--port", str(args.port)
        ] + (["--reload"] if args.reload else []))
        
    except KeyboardInterrupt:
        print("\nGround Control Station stopped by user")
    except Exception as e:
        print(f"ERROR: Error starting Ground Control Station: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
