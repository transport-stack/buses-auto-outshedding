import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, mock_open
import json
import pandas as pd 

# Import the FastAPI app instance
from main import app

# Create a TestClient instance
client = TestClient(app)

# --- Fixtures ---

@pytest.fixture
def mock_fleet_api_data():
    """Fixture for mocking the fleet API response."""
    return pd.DataFrame({
        'vehicle_id': ['BUS1', 'BUS2'],
        'depot': ['DEPOT_A', 'DEPOT_B']
    })

@pytest.fixture
def mock_daily_data():
    """Fixture for mocking the daily JSON data file."""
    return {
        'BUS1': {
            'bus_number': 'BUS1',
            'ot': '08:00:00',
            'it': '18:00:00',
            'shift': 'm'
        }
    }

# --- Test Cases ---

def test_health_check():
    """Test the /api/health endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "Automated Depot Management API",
        "version": "1.0.0"
    }

@patch('main.pd.read_json')
def test_get_bus_depot_map_success(mock_read_json, mock_fleet_api_data):
    """Test get_bus_depot_map with a successful API call."""
    from main import get_bus_depot_map
    mock_read_json.return_value = mock_fleet_api_data
    
    bus_depot_map = get_bus_depot_map()
    
    assert bus_depot_map == {'BUS1': 'DEPOT_A', 'BUS2': 'DEPOT_B'}
    mock_read_json.assert_called_once()

@patch('main.pd.read_json', side_effect=Exception("API Error"))
@patch('main.pd.read_csv')
def test_get_bus_depot_map_fallback(mock_read_csv, mock_read_json, mock_fleet_api_data):
    """Test get_bus_depot_map fallback to local CSV when API fails."""
    from main import get_bus_depot_map
    # Mock the CSV data to be returned by pandas
    mock_df = pd.DataFrame({'reg_num': ['BUS1', 'BUS2'], 'depot': ['DEPOT_A', 'DEPOT_B']})
    mock_read_csv.return_value = mock_df

    bus_depot_map = get_bus_depot_map()

    assert bus_depot_map == {'BUS1': 'DEPOT_A', 'BUS2': 'DEPOT_B'}
    mock_read_json.assert_called_once() # Ensure the API was called
    mock_read_csv.assert_called_once_with('./all_buses_delhi.csv') # Ensure the fallback was used


def test_return_data_not_found():
    """Test return_data when the data file does not exist."""
    response = client.get("/get_all_depot_data/2023/01/01")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

@patch("builtins.open", new_callable=mock_open, read_data=json.dumps({"key": "value"}))
def test_return_data_success(mock_file):
    """Test return_data with a valid data file."""
    response = client.get("/get_all_depot_data/2023/01/01")
    assert response.status_code == 200
    assert response.json() == {"key": "value"}

@patch("builtins.open", new_callable=mock_open, read_data="invalid json")
def test_return_data_json_error(mock_file):
    """Test return_data with a corrupted JSON file."""
    response = client.get("/get_all_depot_data/2023/01/01")
    assert response.status_code == 500
    assert "Error parsing data file" in response.json()["detail"]

@patch('main.return_data')
@patch('main.get_bus_depot_map')
def test_get_all_bus_data(mock_get_bus_depot_map, mock_return_data, mock_daily_data):
    """Test the /api/bus_data endpoint."""
    mock_return_data.return_value = mock_daily_data
    mock_get_bus_depot_map.return_value = {'BUS1': 'DEPOT_A'}

    response = client.get("/api/bus_data/2023/01/01")
    
    assert response.status_code == 200
    
    # The response is a list of the values from the dictionary
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]['bus_number'] == 'BUS1'
    assert response_data[0]['depot'] == 'DEPOT_A' # Check that depot info was added

@patch('main.get_bus_depot_map')
@patch('main.return_data')
def test_get_depot_bus_data(mock_return_data, mock_get_bus_depot_map):
    """Test the /api/bus_data/{yyyy}/{mm}/{dd}/{depot}/{shift} endpoint."""
    # Define test data directly to avoid side effects from fixtures
    test_data = {
        'BUS1': {'bus_number': 'BUS1', 'shift': 'm', 'ot': '08:00:00', 'it': '18:00:00'},
        'BUS2': {'bus_number': 'BUS2', 'shift': 'e', 'ot': '09:00:00', 'it': '19:00:00'}
    }
    mock_return_data.return_value = test_data
    mock_get_bus_depot_map.return_value = {'BUS1': 'DEPOT_A', 'BUS2': 'DEPOT_A'}

    # Request data for morning shift at DEPOT_A
    response = client.get("/api/bus_data/2023/01/01/DEPOT_A/m")

    assert response.status_code == 200
    response_data = response.json()
    assert len(response_data) == 1
    assert response_data[0]['bus_number'] == 'BUS1'
    assert response_data[0]['shift'] == 'm'
