"""
Configuration file for NOAA ASOS 5-minute data fetching

Defines target stations, date ranges, and paths for data processing.
"""

from datetime import datetime
from pathlib import Path

# ==============================================================================
# TARGET STATIONS
# ==============================================================================
# NYC area ASOS stations providing coverage for Manhattan and Brooklyn

STATIONS = {
    'KNYC': {
        'name': 'New York City Central Park',
        'wban': '94728',
        'location': 'Manhattan',
        'lat': 40.7789,
        'lon': -73.9692,
        'elevation_ft': 154
    },
    'KJFK': {
        'name': 'John F Kennedy International Airport',
        'wban': '94789',
        'location': 'Queens (serves Brooklyn)',
        'lat': 40.6398,
        'lon': -73.7789,
        'elevation_ft': 13
    },
    'KLGA': {
        'name': 'LaGuardia Airport',
        'wban': '14732',
        'location': 'Queens (serves Brooklyn)',
        'lat': 40.7769,
        'lon': -73.8740,
        'elevation_ft': 21
    }
}

# ==============================================================================
# DATE RANGE
# ==============================================================================
# Define the time period for data fetching
# Format: YYYY-MM-DD

START_DATE = datetime(2024, 1, 1)  # Default start date
END_DATE = datetime(2024, 12, 31)  # Default end date

# ==============================================================================
# DATA SOURCE
# ==============================================================================
# NOAA NCEI ASOS 5-minute data base URL
BASE_URL = "https://www.ncei.noaa.gov/data/automated-surface-observing-system-five-minute/access"

# File naming convention: {WBAN}{STATION_ID}{YYYYMM}.dat
# Example: 64010KJFK202401.dat

# ==============================================================================
# PATHS
# ==============================================================================
# Directory structure for data storage

# Base directory (relative to project root)
DATA_DIR = Path("data/noaa/asos")

# Subdirectories
RAW_DATA_DIR = DATA_DIR / "raw"  # Original .dat files
PROCESSED_DATA_DIR = DATA_DIR / "processed"  # Cleaned CSV/Parquet files
LOGS_DIR = DATA_DIR / "logs"  # Download and processing logs

# Ensure directories exist
for dir_path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# PROCESSING OPTIONS
# ==============================================================================

# Output format for processed data
OUTPUT_FORMAT = "csv"  # Options: 'csv', 'parquet'

# Quality control thresholds
QC_PARAMS = {
    'temp_min': -50,  # Minimum valid temperature (°C)
    'temp_max': 50,   # Maximum valid temperature (°C)
    'pressure_min': 900,  # Minimum valid pressure (hPa)
    'pressure_max': 1100,  # Maximum valid pressure (hPa)
    'wind_speed_max': 100,  # Maximum valid wind speed (mph)
}

# Missing data codes from ASOS
MISSING_CODES = ['M', 'MM', 'MMM', '/', '']

# ==============================================================================
# LOGGING
# ==============================================================================

LOG_LEVEL = "INFO"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
