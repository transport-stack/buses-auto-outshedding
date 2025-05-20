import datetime
import time
import json
import os
from pathlib import Path

import requests
import pandas as pd
from geopy.distance import geodesic
from shapely.geometry import Point, Polygon

import depots_data
from config import (
    DATA_DIR, 
    FLEET_API_URL, 
    GPS_DTC_API_URL, 
    GPS_DIMTS_API_URL,
    DUTY_MASTER_API_URL,
    POLLING_INTERVAL,
    DISTANCE_THRESHOLD_OUT,
    DISTANCE_THRESHOLD_IN,
    DATA_MISSING_THRESHOLD
)

# Global variables
bus_ot_it_timings_morning_shift = {}
bus_ot_it_timings_evening_shift = {}
recorded_bus_gps_data = {}
bus_distances_travelled = {}
data_missing_flagged_buses = []
bus_data_timestamps = {}


def load_polygons():
    depot_polygons = depots_data.load_depot_polygons()
    return depot_polygons


def get_bus_depot_map():
    """Fetch bus and depot mapping from the fleet API"""
    global bus_ot_it_timings_morning_shift
    global bus_ot_it_timings_evening_shift
    
    try:
        response = requests.get(FLEET_API_URL)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()
        
        buses = []
        bus_depot_map = {}
        
        for bus in data:
            bus_depot_map[bus['vehicle_id']] = bus['depot']
            buses.append(bus['vehicle_id'])

        # Initialize morning shift data
        bus_ot_it_timings_morning_shift = {
            bus_id: {"bus_number": bus_id, "ot": "", "it": "", "shift": "m"} 
            for bus_id in buses
        }
        
        # Initialize evening shift data
        bus_ot_it_timings_evening_shift = {
            bus_id: {"bus_number": bus_id, "ot": "", "it": "", "shift": "e"} 
            for bus_id in buses
        }

        return bus_depot_map
    
    except Exception as e:
        print(f"Error fetching bus depot map: {e}")
        # Fallback to local file if API fails
        try:
            df = pd.read_csv('./all_buses_delhi.csv')
            buses = list(df['reg_num'])
            depot_ids = list(df['depot'])
            
            bus_depot_map = {buses[i]: depot_ids[i] for i in range(len(buses))}
            
            # Initialize shift data with local file data
            bus_ot_it_timings_morning_shift = {
                bus_id: {"bus_number": bus_id, "ot": "", "it": "", "shift": "m"} 
                for bus_id in buses
            }
            
            bus_ot_it_timings_evening_shift = {
                bus_id: {"bus_number": bus_id, "ot": "", "it": "", "shift": "e"} 
                for bus_id in buses
            }
            
            return bus_depot_map
        except Exception as e2:
            print(f"Error reading local file: {e2}")
            return {}


def get_bus_gps_data():
    """Fetch GPS data for buses from DTC and DIMTS APIs"""
    try:
        # Fetch DTC GPS data
        dtc_response = requests.get(GPS_DTC_API_URL)
        dtc_response.raise_for_status()
        dtc_data = dtc_response.text.split("\n")
        dtc_data = [line.split(',') for line in dtc_data]
        
        # Fetch DIMTS GPS data
        dimts_response = requests.get(GPS_DIMTS_API_URL)
        dimts_response.raise_for_status()
        dimts_data = dimts_response.text.split("\n")
        dimts_data = [line.split(',') for line in dimts_data]
        
        # Combine both datasets
        combined_data = dtc_data + dimts_data
        
        return combined_data
    except Exception as e:
        print(f"Error fetching GPS data: {e}")
        return []


def get_bus_duties():
    """Fetch bus duty assignments from the duty master API"""
    try:
        response = requests.get(DUTY_MASTER_API_URL)
        response.raise_for_status()
        data = response.text.split("\n")
        
        # Skip header row and parse CSV data
        parsed_data = [line.split(',') for line in data[1:] if line]
        
        return parsed_data
    except Exception as e:
        print(f"Error fetching bus duties: {e}")
        return []


def record_gps_data(recorded_bus_gps: dict):
    """Record GPS data for buses and calculate distances traveled"""
    global recorded_bus_gps_data
    global data_missing_flagged_buses
    global bus_data_timestamps
    global bus_distances_travelled
    
    gps_data = get_bus_gps_data()
    
    for bus_data in gps_data:
        # Ensure we have complete data (14 fields expected in the GPS data)
        if len(bus_data) == 14:
            bus_id = bus_data[2]
            
            try:
                # Extract latitude and longitude
                lat = float(bus_data[0])
                lng = float(bus_data[1])
                current_location = [lat, lng]
                
                # Parse timestamp
                try:
                    current_timestamp = datetime.datetime.strptime(bus_data[5], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    print(f"Invalid timestamp format for bus {bus_id}: {bus_data[5]}")
                    continue
                
                # Initialize data for new bus
                if bus_id not in recorded_bus_gps:
                    recorded_bus_gps[bus_id] = [current_location]
                    bus_distances_travelled[bus_id] = {'bus_no': bus_id, 'dist': 0}
                    bus_data_timestamps[bus_id] = current_timestamp
                else:
                    # Get previous location
                    prev_location = recorded_bus_gps[bus_id][-1]
                    
                    # Check for missing data (gap in timestamps)
                    if bus_id in bus_data_timestamps:
                        time_diff_minutes = (current_timestamp - bus_data_timestamps[bus_id]).total_seconds() / 60
                        
                        if time_diff_minutes > DATA_MISSING_THRESHOLD:
                            if bus_id not in data_missing_flagged_buses:
                                data_missing_flagged_buses.append(bus_id)
                                print(f"Data missing for bus {bus_id} - time gap: {time_diff_minutes:.1f} minutes")
                    
                    # Update timestamp
                    bus_data_timestamps[bus_id] = current_timestamp
                    
                    # Add new location to history
                    recorded_bus_gps[bus_id].append(current_location)
                    
                    # Calculate distance traveled
                    dist_travel = geodesic(prev_location, current_location).km
                    
                    # Update total distance
                    if bus_id in bus_distances_travelled:
                        bus_distances_travelled[bus_id]['dist'] += dist_travel
                    
                    # Limit history to 15 points to avoid excessive memory usage
                    if len(recorded_bus_gps[bus_id]) > 15:
                        del recorded_bus_gps[bus_id][0]
            
            except (ValueError, IndexError) as e:
                print(f"Error processing GPS data for bus {bus_id}: {e}")
                continue


def check_bus_within_depot(position: list, polygon: Polygon):
    p1 = Point(position[0], position[1])
    if p1.within(polygon):
        return True
    else:
        return False


def convert_to_json(data_morning, data_evening):
    final_data = []
    for k in data_morning.keys():
        final_data.append(data_morning[k])
    for k in data_evening.keys():
        final_data.append(data_evening[k])
    dump_data = json.dumps(final_data, indent=4)
    return dump_data


def check_shed_status(bus_depot_map: dict, gps_data, recorded_bus_gps_data, depot_polygons, file, dist_data_file):
    """Check if buses have entered or exited depots and record timestamps"""
    global bus_ot_it_timings_morning_shift
    global bus_ot_it_timings_evening_shift
    
    for bus_data in gps_data:
        # Skip incomplete data
        if len(bus_data) != 14:
            continue
            
        bus_number = bus_data[2]
        
        # Skip buses not in our mapping
        if bus_number not in bus_depot_map:
            continue
            
        # Skip if depot not defined in polygons
        depot_id = bus_depot_map[bus_number]
        if depot_id not in depot_polygons:
            continue
            
        depot_poly = depot_polygons[depot_id]
        
        # Skip if all timings are already recorded for this bus
        if (bus_ot_it_timings_morning_shift[bus_number]["ot"] and 
            bus_ot_it_timings_morning_shift[bus_number]["it"] and 
            bus_ot_it_timings_evening_shift[bus_number]["ot"] and 
            bus_ot_it_timings_evening_shift[bus_number]["it"]):
            continue

        try:
            # Get current location
            current_location = [float(bus_data[0]), float(bus_data[1])]
            
            # Get previous location
            if bus_number in recorded_bus_gps_data and recorded_bus_gps_data[bus_number]:
                prev_location = recorded_bus_gps_data[bus_number][0]
                distance = geodesic(prev_location, current_location).km
            else:
                # Skip if we don't have previous location data
                continue
            
            # Check if bus is within depot
            is_in_depot = check_bus_within_depot(current_location, depot_poly)
            
            # Morning shift - Outshedding (bus leaving depot)
            if not bus_ot_it_timings_morning_shift[bus_number]['ot']:
                if not is_in_depot and distance > DISTANCE_THRESHOLD_OUT:
                    bus_ot_it_timings_morning_shift[bus_number]['ot'] = datetime.datetime.now().strftime(
                        "%Y/%m/%d %H:%M:%S")
                    print(f"Bus {bus_number} left depot {depot_id} (morning shift) at {bus_ot_it_timings_morning_shift[bus_number]['ot']}")
            
            # Morning shift - Inshedding (bus returning to depot)
            elif not bus_ot_it_timings_morning_shift[bus_number]['it']:
                if is_in_depot and distance < DISTANCE_THRESHOLD_IN:
                    bus_ot_it_timings_morning_shift[bus_number]['it'] = datetime.datetime.now().strftime(
                        "%Y/%m/%d %H:%M:%S")
                    print(f"Bus {bus_number} returned to depot {depot_id} (morning shift) at {bus_ot_it_timings_morning_shift[bus_number]['it']}")
            
            # Evening shift - Outshedding
            elif not bus_ot_it_timings_evening_shift[bus_number]['ot']:
                if not is_in_depot and distance > DISTANCE_THRESHOLD_OUT:
                    bus_ot_it_timings_evening_shift[bus_number]['ot'] = datetime.datetime.now().strftime(
                        "%Y/%m/%d %H:%M:%S")
                    print(f"Bus {bus_number} left depot {depot_id} (evening shift) at {bus_ot_it_timings_evening_shift[bus_number]['ot']}")
            
            # Evening shift - Inshedding
            elif not bus_ot_it_timings_evening_shift[bus_number]['it']:
                if is_in_depot and distance < DISTANCE_THRESHOLD_IN:
                    bus_ot_it_timings_evening_shift[bus_number]['it'] = datetime.datetime.now().strftime(
                        "%Y/%m/%d %H:%M:%S")
                    print(f"Bus {bus_number} returned to depot {depot_id} (evening shift) at {bus_ot_it_timings_evening_shift[bus_number]['it']}")
            
            # Handle case where a bus has morning data but no evening data and it's past noon
            # This assumes the morning data is actually evening data
            if (not bus_ot_it_timings_evening_shift[bus_number]['ot'] and 
                bus_ot_it_timings_morning_shift[bus_number]['ot']):
                
                out_time = bus_ot_it_timings_morning_shift[bus_number]['ot'].split(' ')[1].strip()
                if out_time > '12:00:00':
                    # Copy morning data to evening data
                    bus_ot_it_timings_evening_shift[bus_number]['ot'] = bus_ot_it_timings_morning_shift[bus_number]['ot']
                    bus_ot_it_timings_evening_shift[bus_number]['it'] = bus_ot_it_timings_morning_shift[bus_number]['it']
        
        except (ValueError, IndexError) as e:
            print(f"Error processing shed status for bus {bus_number}: {e}")
            continue

    # Prepare data for saving
    json_data = convert_to_json(bus_ot_it_timings_morning_shift, bus_ot_it_timings_evening_shift)
    distance_travelled_data = list(bus_distances_travelled.values())
    distance_travelled_json = json.dumps(distance_travelled_data, indent=4)
    
    # Write data to files
    dist_data_file.write(distance_travelled_json)
    file.write(json_data)


def main():
    """Main function to run the automated depot management system"""
    global recorded_bus_gps_data
    global bus_ot_it_timings_morning_shift
    global bus_ot_it_timings_evening_shift
    global bus_distances_travelled

    print("Starting Automated Depot Management System")
    print(f"Data directory: {DATA_DIR}")
    print(f"Polling interval: {POLLING_INTERVAL} seconds")
    print(f"Distance threshold for outshedding: {DISTANCE_THRESHOLD_OUT} km")
    print(f"Distance threshold for inshedding: {DISTANCE_THRESHOLD_IN} km")
    
    # Ensure data directory exists
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    
    # Initialize data
    iteration = 1
    bus_depot_map = get_bus_depot_map()
    depot_polygons = load_polygons()
    
    # Get current date for filenames
    current_date = datetime.datetime.now()
    f_name = current_date.strftime("%d_%m_%Y") + ".json"
    
    # Try to load existing data for today
    try:
        file_path = Path(DATA_DIR) / f_name
        with open(file_path, "r") as f:
            json_data = json.load(f)

        for data in json_data:
            if data['shift'] == 'm':
                bus_ot_it_timings_morning_shift[data['bus_number']] = {
                    "bus_number": data['bus_number'],
                    'ot': data['ot'], 
                    'it': data['it'], 
                    'shift': 'm'
                }
            else:
                bus_ot_it_timings_evening_shift[data['bus_number']] = {
                    "bus_number": data['bus_number'],
                    'ot': data['ot'], 
                    'it': data['it'], 
                    'shift': 'e'
                }
        print(f"Timings data loaded from {file_path}")

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"No existing timings data found or error loading file: {e}")

    # Try to load existing distance data for today
    try:
        dist_file_path = Path(DATA_DIR) / f"{f_name[:-5]}Distances.json"
        with open(dist_file_path, "r") as f1:
            dist_file_data = json.load(f1)

        for data in dist_file_data:
            bus_distances_travelled[data['bus_no']] = data
        print(f"Distances data loaded from {dist_file_path}")

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"No existing distances data found or error loading file: {e}")

    print("Starting main monitoring loop...")
    
    # Main monitoring loop
    while True:
        try:
            iteration += 1
            start_time = time.time()
            
            # Get GPS data and process it
            gps_data = get_bus_gps_data()
            record_gps_data(recorded_bus_gps_data)

            # Reset filenames at 3 AM for new day
            if datetime.datetime.now().strftime("%H:%M:%S") >= "03:00:00":
                f_name = datetime.datetime.now().strftime("%d_%m_%Y") + ".json"
                print(f"New day detected, switching to new files: {f_name}")

            # Open files for writing
            timings_file_path = Path(DATA_DIR) / f_name
            distances_file_path = Path(DATA_DIR) / f"{f_name[:-5]}Distances.json"
            
            with open(timings_file_path, "w+") as file, open(distances_file_path, "w+") as dist_data_file:
                # Check and record shed status
                check_shed_status(bus_depot_map, gps_data, recorded_bus_gps_data, depot_polygons, file, dist_data_file)
            
            # Calculate execution time and sleep for the remainder of the polling interval
            execution_time = time.time() - start_time
            print(f"Iteration {iteration} completed in {execution_time:.2f} seconds")
            
            sleep_time = max(0.1, POLLING_INTERVAL - execution_time)
            time.sleep(sleep_time)
            
        except KeyboardInterrupt:
            print("\nExiting application...")
            break
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            # Continue running despite errors
            time.sleep(POLLING_INTERVAL)


if __name__ == '__main__':
    main()

# FLag buses --> data nhi aa rha kaafi time tak
# Flag buses --> Stationed at different depots
