#!/bin/bash
# Setup script for Automated Depot Management System

echo "Setting up Automated Depot Management System..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo ".env file created. Please review and update the settings as needed."
else
    echo ".env file already exists."
fi

# Create data directory if it doesn't exist
if [ ! -d "data" ]; then
    echo "Creating data directory..."
    mkdir -p data
    echo "Data directory created."
else
    echo "Data directory already exists."
fi

echo "Setup complete! You can now run the system using:"
echo "  python run.py tracker  # To run the tracking system"
echo "  python run.py api      # To run the API server"
echo "  python run.py all      # To run both components"
