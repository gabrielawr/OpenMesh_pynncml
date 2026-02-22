"""
Configuration: All data paths and settings
Auto-detects project root. Set MANUAL_BASE_PATH to override.
"""

from pathlib import Path


# =============================================================================
# MANUAL OVERRIDE
# =============================================================================
MANUAL_BASE_PATH = None  # e.g. "/path/to/OpenMesh_pynncml"


# =============================================================================
# AUTO-DETECT PROJECT ROOT
# =============================================================================
def get_base_path() -> Path:
    """Auto-detect project root by looking for 'src' or 'dataset' folder."""
    if MANUAL_BASE_PATH:
        return Path(MANUAL_BASE_PATH)
    
    current = Path(__file__).resolve()
    for parent in [current.parent] + list(current.parents):
        if (parent / "src").exists() or (parent / "dataset").exists():
            return parent
        if parent.name == "OpenMesh_pynncml":
            return parent
    
    raise ValueError(f"Could not find project root. Set MANUAL_BASE_PATH in config.py")


BASE_PATH = get_base_path()


# =============================================================================
# NEW DATASETS (NetCDF) - REQUIRED FOR ANALYSIS
# =============================================================================
DATASET_DIR = BASE_PATH / "dataset"
WEATHER_STATIONS_DIR = DATASET_DIR / "weather stations"
LINKS_DIR = DATASET_DIR / "links"

# PWS Data (sample or full)
PWS_SAMPLE_FILE = WEATHER_STATIONS_DIR / "pws_opensense_sample_jan.nc"
PWS_FULL_FILE = WEATHER_STATIONS_DIR / "pws_opensense_os.nc"
PWS_METADATA_FILE = WEATHER_STATIONS_DIR / "pws_metadata.csv"

# Links Data (OpenMesh CML)
LINKS_FILE = LINKS_DIR / "ds_openmesh.nc"
LINKS_METADATA_FILE = LINKS_DIR / "links_metadata.csv"

# Fallback: extracted from Zenodo
EXTRACTED_DIR = BASE_PATH / "src" / "data" / "openmesh" / "extracted" / "dataset"
EXTRACTED_WEATHER_STATIONS_DIR = EXTRACTED_DIR / "weather stations"
EXTRACTED_LINKS_DIR = EXTRACTED_DIR / "links"


# =============================================================================
# RAW DATA DIRECTORIES - OPTIONAL (only if processing manually)
# =============================================================================
SRC_DIR = BASE_PATH / "src"
DATA_DIR = SRC_DIR / "data"

MESONET_RAW_DIR = DATA_DIR / "Mesonet"
NOAA_ASOS_RAW_DIR = DATA_DIR / "noaa_asos"
WU_PWS_DIR = DATA_DIR / "wu_pws"
SNOW_DIR = DATA_DIR / "snow_analysis"

# Backward compatibility aliases (used by some processing scripts)
NOAA_DIR = NOAA_ASOS_RAW_DIR
MESONET_DIR = MESONET_RAW_DIR
NOAA_DAILY_DIR = NOAA_DIR / "daily"  # Input directory for daily NOAA files


# =============================================================================
# PROCESSED DATA (CSV) - REQUIRED FOR FULL ANALYSIS
# =============================================================================
OUTPUT_DIR = DATA_DIR / "output"

# Processed output (from run_all_processors.ipynb)
ASOS_1MIN_OUTPUT_DIR = OUTPUT_DIR / "asos_1min"
NOAA_DAILY_OUTPUT_DIR = OUTPUT_DIR / "noaa_daily"
MESONET_OUTPUT_DIR = OUTPUT_DIR / "mesonet"

# Raw data directories (for processing)
ASOS_1MIN_DIR = NOAA_ASOS_RAW_DIR / "noaa_asos_1min"

# Fetch directories
FETCH_DIR = SRC_DIR / "fetch_data"
ASOS_FETCH_DIR = FETCH_DIR / "noaa_asos"
OPENMESH_FETCH_DIR = FETCH_DIR / "openmesh"


# =============================================================================
# PROCESSING DIRECTORIES
# =============================================================================
PROCESS_DIR = SRC_DIR / "process"


# =============================================================================
# DATA SEARCH PRIORITIES
# =============================================================================
# Try PWS files in this order
PWS_SEARCH_FILES = [
    PWS_SAMPLE_FILE,
    PWS_FULL_FILE,
    EXTRACTED_WEATHER_STATIONS_DIR / "pws_opensense_sample_jan.nc",
    EXTRACTED_WEATHER_STATIONS_DIR / "pws_opensense_os.nc",
]

# Try ASOS directories in this order
ASOS_SEARCH_DIRS = [
    ASOS_1MIN_OUTPUT_DIR,
    DATA_DIR / "noaa_asos" / "noaa_asos_1min",
]


# =============================================================================
# VARIABLE MAPPING (standard names)
# =============================================================================
VARIABLE_MAPPING = {
    # Precipitation
    'rainfall_rate': ['rainfall_rate', 'rain_rate', 'RR'],
    'rainfall_amount': ['rainfall_amount', 'rain_amount', 'rain_mm'],
    
    # Temperature & Humidity
    'temperature': ['temperature', 'temp', 'T'],
    'relative_humidity': ['relative_humidity', 'humidity', 'RH'],
    
    # Wind
    'wind_velocity': ['wind_velocity', 'wind_speed', 'WS'],
    'wind_direction': ['wind_direction', 'wd', 'WD'],
    
    # Pressure
    'air_pressure': ['air_pressure', 'pressure', 'P'],
    
    # Snow (optional)
    'snow_depth': ['snow_depth', 'snow'],
    'snow_rate': ['snow_rate'],
}

UNIT_MAP = {
    'rainfall_rate': 'mm/min',
    'rainfall_amount': 'mm',
    'temperature': '°C',
    'relative_humidity': '%',
    'wind_velocity': 'm/s',
    'wind_direction': '°',
    'air_pressure': 'hPa',
    'snow_depth': 'cm',
    'snow_rate': 'cm/hr',
}


# =============================================================================
# ANALYSIS DEFAULTS
# =============================================================================
DEFAULT_START_DATE = '2024-01-01'
DEFAULT_END_DATE = '2024-01-31'
USE_SAMPLE_BY_DEFAULT = True

PLOT_DPI = 150
PLOT_FIGSIZE_SINGLE = (16, 6)
PLOT_FIGSIZE_MULTI = (16, 4)