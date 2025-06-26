from typing import Union, List, Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import pandas as pd
import os
from pathlib import Path

# Import configuration
from config import DATA_DIR, FLEET_API_URL
import depots_data

app = FastAPI(
    title="Automated Depot Management API",
    description="API for tracking bus outshedding and inshedding times",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Set up templates
templates = Jinja2Templates(directory="templates")

# Create static directory if it doesn't exist
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")


def get_bus_depot_map():
    """Fetch bus and depot mapping from the fleet API"""
    try:
        df = pd.read_json(FLEET_API_URL)
        buses, depot_id = list(df['vehicle_id']), list(df['depot'])
        bus_depot_map = {buses[i]: depot_id[i] for i in range(len(buses))}
        return bus_depot_map
    except Exception as e:
        print(f"Error fetching bus depot map: {e}")
        # Fallback to local file if API fails
        try:
            df = pd.read_csv('./all_buses_delhi.csv')
            buses, depot_id = list(df['reg_num']), list(df['depot'])
            return {buses[i]: depot_id[i] for i in range(len(buses))}
        except Exception as e2:
            print(f"Error reading local file: {e2}")
            return {}


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Serve the main dashboard"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/health")
def health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "service": "Automated Depot Management API",
        "version": "1.0.0"
    }


@app.get("/get_all_depot_data/{yyyy}/{mm}/{dd}")
def return_data(dd: str, mm: str, yyyy: str):
    """Return all depot data for a specific date"""
    file_path = Path(DATA_DIR) / f"{dd}_{mm}_{yyyy}.json"
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Data for {dd}/{mm}/{yyyy} not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Error parsing data file for {dd}/{mm}/{yyyy}")

def _enrich_data_with_depot_info(data: dict) -> list:
    """Helper function to add depot information to bus data."""
    bus_depot_map = get_bus_depot_map()
    enriched_values = list(data.values())
    for bus in enriched_values:
        bus['depot'] = bus_depot_map.get(bus['bus_number'], 'Unknown')
    return enriched_values


@app.get("/api/bus_data/{yyyy}/{mm}/{dd}")
def get_all_bus_data(yyyy: str, mm: str, dd: str):
    """API endpoint for the dashboard to get all bus data for a specific date"""
    try:
        data = return_data(dd, mm, yyyy)
        return _enrich_data_with_depot_info(data)
    except HTTPException as e:
        if e.status_code == 404:
            return []
        raise


@app.get("/get_depot_data/{yyyy}/{mm}/{dd}/{depot}/{shift}")
def return_depot_data(dd: str, mm: str, yyyy: str, depot: str, shift: str):
    """Return data for a specific depot and shift on a specific date"""
    data = return_data(dd, mm, yyyy)
    enriched_data = _enrich_data_with_depot_info(data)

    # Normalize shift parameter
    shift = 'm' if shift.lower() in ['morning', 'm'] else 'e'

    depot_data = [
        bus for bus in enriched_data
        if bus.get('depot') == depot and bus.get('shift') == shift
    ]

    if not depot_data:
        raise HTTPException(status_code=404, detail=f"No data found for {depot} during {shift} shift on {dd}/{mm}/{yyyy}")

    return depot_data

@app.get("/api/bus_data/{yyyy}/{mm}/{dd}/{depot}/{shift}")
def get_depot_bus_data(yyyy: str, mm: str, dd: str, depot: str, shift: str):
    """API endpoint for the dashboard to get bus data for a specific depot and shift"""
    try:
        data = return_depot_data(dd, mm, yyyy, depot, shift)
        
        # Add depot information to each entry
        for entry in data:
            entry['depot'] = depot
            
        return data
    except HTTPException as e:
        if e.status_code == 404:
            return []
        raise


@app.get("/depot_table_data/{yyyy}/{mm}/{dd}/{depot}/{shift}", response_class=HTMLResponse)
def make_table(dd: str, mm: str, yyyy: str, depot: str, shift: str):
    """Return HTML table of depot data for a specific depot and shift on a specific date"""
    try:
        depot_data = return_depot_data(dd, mm, yyyy, depot, shift)
        
        if not depot_data:
            return f"<p>No data available for depot {depot} on {dd}/{mm}/{yyyy} for {'morning' if shift == 'm' else 'evening'} shift</p>"
        
        df = pd.DataFrame()
        bus_no = [entry['bus_number'] for entry in depot_data]
        inshed_times = [entry['it'] for entry in depot_data]
        outshed_times = [entry['ot'] for entry in depot_data]

        df['Bus Number'] = bus_no
        df['Outshed Times'] = outshed_times
        df['Inshed Times'] = inshed_times

        return df.to_html(table_id="depot-data", classes="table table-striped table-hover")
    except Exception as e:
        return f"<p>Error generating table: {str(e)}</p>"


@app.get("/bus_distances/{yyyy}/{mm}/{dd}", response_class=HTMLResponse)
def return_distance_travelled(dd: str, mm: str, yyyy: str):
    """Return HTML table of distances traveled by buses on a specific date"""
    file_path = Path(DATA_DIR) / f"{dd}_{mm}_{yyyy}Distances.json"
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)

        bus_no = [entry['bus_no'] for entry in data]
        distances = [entry['dist'] for entry in data]

        df = pd.DataFrame()
        df['bus_number'] = bus_no
        df['Distance Travelled'] = distances

        return df.to_html()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Distance data for {dd}/{mm}/{yyyy} not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Error parsing distance data file for {dd}/{mm}/{yyyy}")


@app.get("/api/depots")
def get_depots() -> List[Dict[str, str]]:
    """Return a list of all depots for the dashboard"""
    try:
        # Get depot IDs from the depot_id_name_map in depots_data.py
        depot_ids = list(depots_data.depot_id_name_map.keys())
        
        # Format as a list of objects with id and name
        depots = []
        for depot_id in depot_ids:
            # Convert depot ID to a more readable name
            name = depot_id.upper().replace('-', ' ')
            depots.append({"id": depot_id, "name": name})
            
        # Sort by name
        depots.sort(key=lambda x: x["name"])
        
        return depots
    except Exception as e:
        print(f"Error getting depots: {e}")
        return []


@app.get("/api/stats")
def get_stats():
    """Get system statistics"""
    try:
        # Get the current date
        today = datetime.now().strftime("%d_%m_%Y")
        file_path = Path(DATA_DIR) / f"{today}.json"
        
        if not file_path.exists():
            return {
                "total_buses": 0,
                "active_buses": 0,
                "completed_trips": 0,
                "in_progress_trips": 0
            }
        
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        total_buses = len(data)
        completed_trips = sum(1 for bus in data if bus.get('ot') and bus.get('it'))
        in_progress_trips = sum(1 for bus in data if bus.get('ot') and not bus.get('it'))
        active_buses = completed_trips + in_progress_trips
        
        return {
            "total_buses": total_buses,
            "active_buses": active_buses,
            "completed_trips": completed_trips,
            "in_progress_trips": in_progress_trips
        }
    except Exception as e:
        print(f"Error getting stats: {e}")
        return {
            "total_buses": 0,
            "active_buses": 0,
            "completed_trips": 0,
            "in_progress_trips": 0
        }
