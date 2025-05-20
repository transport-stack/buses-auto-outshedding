# Automated Depot Management

A system for tracking bus outshedding and inshedding times at transit depots. This project monitors when buses exit and enter depots, records the times, and calculates distances traveled.

## Features

- Automated detection of bus outshedding (exiting depot) and inshedding (entering depot) times
- Morning and evening shift tracking
- Distance traveled calculation for each bus
- REST API for accessing recorded data
- Web interface for viewing depot data in tabular format
- Support for multiple depots with geofencing

## Prerequisites

- Python 3.7+
- pip (Python package manager)

## Installation

### Automatic Setup (Recommended)

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/automated-depot-management.git
   cd automated-depot-management
   ```

2. Run the setup script:

   ```bash
   ./setup.sh
   ```

   This script will:
   - Create a virtual environment
   - Install all dependencies
   - Set up environment variables from .env.example
   - Set up the data directory

3. Edit the `.env` file with your specific configuration:
   - Update API URLs if needed
   - Configure data directory path

### Manual Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/automated-depot-management.git
   cd automated-depot-management
   ```

2. Create a virtual environment (recommended):

      ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:

      ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:

   ```bash
   cp .env.example .env
   ```
   
5. Edit the `.env` file with your specific configuration

6. Create a data directory:

   ```bash
   mkdir -p data
   ```

## Usage

The application can be run in three modes:

### Using the Run Script (Recommended)

The project includes a convenient run script that can start either the tracker, the API server, or both:

```bash
# Run the tracking system only
python run.py tracker

# Run the API server only
python run.py api

# Run both the tracker and API server
python run.py all

# Run the API server on a specific host and port
python run.py api --host 0.0.0.0 --port 8080
```

### Manual Execution

#### Running the Outshedding/Inshedding Tracker

```bash
python automatic_outshed.py
```

This will start the tracking process that:

- Polls GPS data from the configured APIs
- Detects when buses enter or exit depot boundaries
- Records timestamps for these events
- Calculates distances traveled
- Saves data to JSON files in the configured data directory

#### Starting the API Server

```bash
uvicorn main:app --reload
```

This starts the FastAPI server that provides access to the recorded data.

### API Endpoints

- `GET /`: Basic health check
- `GET /get_all_depot_data/{yyyy}/{mm}/{dd}`: Get all depot data for a specific date
- `GET /get_depot_data/{yyyy}/{mm}/{dd}/{depot}/{shift}`: Get data for a specific depot and shift
- `GET /depot_table_data/{yyyy}/{mm}/{dd}/{depot}/{shift}`: Get HTML table of depot data
- `GET /bus_distances/{yyyy}/{mm}/{dd}`: Get distances traveled by buses on a specific date

## Project Structure

- `automatic_outshed.py`: Main script for tracking bus movements and recording shed times
- `main.py`: FastAPI server for accessing the recorded data
- `depots_data.py`: Contains polygon definitions for all depot boundaries
- `data/`: Directory where recorded data is stored
- `Distance/`: Contains modules for distance calculation
- `.env`: Configuration file for environment variables
- `requirements.txt`: Python dependencies

## Data Sources and Formats

The Automated Depot Management system relies on several data sources to track bus movements and calculate outshedding/inshedding times. Understanding these data sources and their formats is crucial for the system to work properly.

### Input Data Sources

#### 1. Fleet Information API

**Purpose**: Provides information about all buses and their assigned depots.

**Default URL**: Configured in the `.env` file

**Expected Format**: JSON array of objects with the following structure:

```json
[
  {
    "vehicle_id": "DL1PC1234",  // Bus registration number
    "depot": "rhd-1"          // Depot ID where the bus is assigned
  },
  ...
]
```

**Configuration**: Set via `FLEET_API_URL` in the `.env` file.

#### 2. GPS Data APIs

**Purpose**: Provides real-time GPS positions of buses.

**Default URLs**: Configured in the `.env` file for both DTC and DIMTS buses

**Expected Format**: CSV text with the following columns:

```csv
latitude,longitude,bus_number,speed,heading,timestamp,other_fields...
```

Example:

```csv
28.6139,77.2090,DL1PC1234,45,270,2025-05-19 14:30:00,...
```

**Configuration**: Set via `GPS_DTC_API_URL` and `GPS_DIMTS_API_URL` in the `.env` file.

#### 3. Duty Master API

**Purpose**: Provides information about bus duty assignments.

**Default URL**: Configured in the `.env` file

**Expected Format**: CSV text with header row and the following columns:

```csv
bus_number,duty_number,route,shift,depot,date,...
```

**Configuration**: Set via `DUTY_MASTER_API_URL` in the `.env` file.

#### 4. Depot Boundaries

**Purpose**: Defines the geographical boundaries of each depot as polygons.

**Source**: Defined in `depots_data.py` as coordinate arrays for each depot.

**Format**: Python dictionary mapping depot IDs to arrays of [latitude, longitude] coordinates.

### Generated Data Files

The system generates and maintains two types of JSON files in the data directory:

#### 1. Daily Timing Data: `DD_MM_YYYY.json`

**Purpose**: Contains outshedding and inshedding times for each bus.

**Format**:

```json
[
  {
    "bus_number": "DL1PC1234",
    "ot": "2025/05/19 08:15:30",  // Outshed time (when bus left depot)
    "it": "2025/05/19 18:45:22",  // Inshed time (when bus returned to depot)
    "shift": "m"                  // Shift: "m" for morning, "e" for evening
  },
  ...
]
```

#### 2. Distance Data: `DD_MM_YYYYDistances.json`

**Purpose**: Contains the total distance traveled by each bus.

**Format**:

```json
[
  {
    "bus_no": "DL1PC1234",
    "dist": 145.8              // Distance traveled in kilometers
  },
  ...
]
```

### Fallback Data

If the Fleet API is unavailable, the system can fall back to a local CSV file:

**File**: `all_buses_delhi.csv`

**Format**: CSV with the following columns:

```csv
reg_num,depot,...
```

Where `reg_num` is the bus registration number and `depot` is the depot ID.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is open source and available under the [MIT License](LICENSE).
