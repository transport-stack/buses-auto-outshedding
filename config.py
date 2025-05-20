"""
Configuration module for the Automated Depot Management system.
Loads environment variables from .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API URLs
FLEET_API_URL = os.getenv("FLEET_API_URL", "https://depot.chartr.in/all_fleet/")
GPS_DTC_API_URL = os.getenv("GPS_DTC_API_URL", "https://gpsfeed.chartr.in/combined_gps_positions_dtc.txt")
GPS_DIMTS_API_URL = os.getenv("GPS_DIMTS_API_URL", "https://gpsfeed.chartr.in/combined_gps_positions_dimts.txt")
DUTY_MASTER_API_URL = os.getenv("DUTY_MASTER_API_URL", "https://gpsfeed.chartr.in/depot_tool_duty_master.txt")

# Data Storage
DATA_DIR = os.getenv("DATA_DIR", "./data/")

# Ensure data directory exists
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

# Application Settings
POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "10"))  # Time in seconds between GPS data polling
DISTANCE_THRESHOLD_OUT = float(os.getenv("DISTANCE_THRESHOLD_OUT", "0.3"))  # Distance in km to consider a bus has left depot
DISTANCE_THRESHOLD_IN = float(os.getenv("DISTANCE_THRESHOLD_IN", "0.05"))  # Distance in km to consider a bus has entered depot
DATA_MISSING_THRESHOLD = int(os.getenv("DATA_MISSING_THRESHOLD", "360"))  # Time in minutes to flag missing data
