#!/usr/bin/env python3
"""
Run script for Automated Depot Management System.
This script provides a simple interface to run either the tracker or the API server.
"""
import os
import sys
import argparse
import subprocess
from pathlib import Path

def setup_environment():
    """Ensure the environment is properly set up."""
    # Check if .env file exists
    if not Path('.env').exists():
        if Path('.env.example').exists():
            print("No .env file found. Creating one from .env.example...")
            with open('.env.example', 'r') as example_file:
                with open('.env', 'w') as env_file:
                    env_file.write(example_file.read())
            print(".env file created. Please review and update the settings as needed.")
        else:
            print("Warning: No .env or .env.example file found.")
    
    # Ensure data directory exists
    data_dir = Path('./data')
    data_dir.mkdir(exist_ok=True)
    
    # Check if required packages are installed
    try:
        import uvicorn
        import fastapi
        import pandas
        import geopy
        import shapely
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)

def run_tracker():
    """Run the bus tracking system."""
    print("Starting the Automated Depot Management tracking system...")
    try:
        subprocess.run([sys.executable, "automatic_outshed.py"], check=True)
    except KeyboardInterrupt:
        print("\nTracking system stopped.")
    except Exception as e:
        print(f"Error running tracking system: {e}")

def run_api(host="127.0.0.1", port=8000):
    """Run the API server."""
    print(f"Starting the API server at http://{host}:{port}...")
    try:
        import uvicorn
        uvicorn.run("main:app", host=host, port=port, reload=True)
    except KeyboardInterrupt:
        print("\nAPI server stopped.")
    except Exception as e:
        print(f"Error running API server: {e}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run Automated Depot Management System")
    parser.add_argument("component", choices=["tracker", "api", "all"], 
                        help="Component to run: tracker, api, or all")
    parser.add_argument("--host", default="127.0.0.1", 
                        help="Host for the API server (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, 
                        help="Port for the API server (default: 8000)")
    
    args = parser.parse_args()
    
    # Setup environment
    setup_environment()
    
    # Run the requested component
    if args.component == "tracker":
        run_tracker()
    elif args.component == "api":
        run_api(args.host, args.port)
    elif args.component == "all":
        # This is a simple implementation - in production, you'd want to use multiprocessing
        print("Running both tracker and API server...")
        print("Note: For production use, it's recommended to run these in separate processes.")
        print("Starting API server first...")
        import threading
        api_thread = threading.Thread(target=run_api, args=(args.host, args.port))
        api_thread.daemon = True
        api_thread.start()
        
        # Give the API server a moment to start
        import time
        time.sleep(2)
        
        # Run the tracker in the main thread
        run_tracker()

if __name__ == "__main__":
    main()
