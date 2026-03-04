"""
Data Conventions Configuration
==============================
Defines standard column names, units, and conversion factors for all weather datasets.

All processed data should follow these conventions for consistency across:
- ASOS 1-minute data
- NYC Mesonet 5-minute data  
- NOAA Daily data
- Any future data sources

Usage:
    from config import STANDARD_COLUMNS, CONVERSIONS, ASOS_COLUMN_MAP, etc.
"""


# =============================================================================
# STANDARD COLUMN NAMES AND UNITS
# =============================================================================

STANDARD_COLUMNS = {
    # Time (always UTC)
    'time': {
        'unit': 'UTC datetime',
        'description': 'Timestamp in UTC',
    },
    
    # Temperature
    'temp': {
        'unit': '°C',
        'description': 'Air temperature (surface/2m)',
    },
    'dewpoint': {
        'unit': '°C', 
        'description': 'Dewpoint temperature',
    },
    
    # Wind
    'wind_speed': {
        'unit': 'm/s',
        'description': 'Average wind speed',
    },
    'wind_gust': {
        'unit': 'm/s',
        'description': 'Wind gust (max speed)',
    },
    'wind_dir': {
        'unit': 'degrees',
        'description': 'Wind direction (0-360, from)',
    },
    
    # Precipitation
    'precip': {
        'unit': 'mm',
        'description': 'Precipitation amount (incremental)',
    },
    'precip_type': {
        'unit': 'category',
        'description': 'Precipitation type (rain/snow/etc)',
        'categories': ['dry', 'rain', 'snow', 'mixed', 'unknown'],
    },
    
    # Station
    'station': {
        'unit': 'string',
        'description': 'Station identifier',
    },
}

# Source-specific columns (not standardized, keep original names)
SOURCE_SPECIFIC_COLUMNS = {
    'mesonet': [
        'temp_9m', 'apparent_temperature', 'relative_humidity',
        'precip_local', 'precip_max_intensity', 'precip_1hr',
        'avg_wind_speed_prop', 'avg_wind_speed_sonic', 'avg_wind_speed_merge',
        'max_wind_speed_prop', 'max_wind_speed_sonic', 'max_wind_speed_merge',
        'wind_direction_prop', 'wind_direction_sonic', 'wind_direction_merge',
        'wind_speed_stddev_prop', 'wind_speed_stddev_sonic', 'wind_speed_stddev_merge',
        'wind_direction_stddev_prop', 'wind_direction_stddev_sonic', 'wind_direction_stddev_merge',
        'solar_insolation', 'station_pressure', 'snow_depth',
        'frozen_soil_05cm', 'frozen_soil_25cm', 'frozen_soil_50cm',
        'soil_temp_05cm', 'soil_temp_25cm', 'soil_temp_50cm',
        'soil_moisture_05cm', 'soil_moisture_25cm', 'soil_moisture_50cm',
    ],
    'asos': [
        'precip_category',  # simplified precip type
    ],
    'noaa_daily': [
        'temp_max', 'temp_min', 'temp_avg',
        'snow_depth', 'snow_depth_accumulated',
    ],
}


# =============================================================================
# CONVERSION FACTORS
# =============================================================================

CONVERSIONS = {
    # Temperature
    'fahrenheit_to_celsius': lambda f: (f - 32) * 5 / 9,
    'celsius_to_fahrenheit': lambda c: c * 9 / 5 + 32,
    
    # Wind speed
    'knots_to_ms': lambda kt: kt * 0.51444,
    'mph_to_ms': lambda mph: mph * 0.44704,
    'ms_to_knots': lambda ms: ms / 0.51444,
    'ms_to_mph': lambda ms: ms / 0.44704,
    
    # Precipitation
    'inches_to_mm': lambda inch: inch * 25.4,
    'mm_to_inches': lambda mm: mm / 25.4,
}


# =============================================================================
# COLUMN MAPPINGS (raw -> standard)
# =============================================================================

# ASOS 1-minute raw columns -> standard
ASOS_COLUMN_MAP = {
    'valid(UTC)': 'time',
    'tmpf': 'temp',           # °F -> °C
    'dwpf': 'dewpoint',       # °F -> °C
    'sknt': 'wind_speed',     # knots -> m/s
    'gust_sknt': 'wind_gust', # knots -> m/s
    'drct': 'wind_dir',       # degrees (no conversion)
    'precip': 'precip',       # inches -> mm
    'ptype': 'precip_type',   # category mapping
}

ASOS_CONVERSIONS = {
    'temp': 'fahrenheit_to_celsius',
    'dewpoint': 'fahrenheit_to_celsius',
    'wind_speed': 'knots_to_ms',
    'wind_gust': 'knots_to_ms',
    'precip': 'inches_to_mm',
}

# NYC Mesonet raw columns -> standard
MESONET_COLUMN_MAP = {
    'time': 'time',
    'temp_2m': 'temp',              # already °F in raw, convert to °C
    'dewpoint': 'dewpoint',         # already °F in raw, convert to °C
    'avg_wind_speed_prop': 'wind_speed',   # mph -> m/s
    'max_wind_speed_prop': 'wind_gust',    # mph -> m/s
    'wind_direction_prop': 'wind_dir',     # degrees (no conversion)
    'precip_incremental': 'precip',        # inches -> mm
}

MESONET_CONVERSIONS = {
    'temp': 'fahrenheit_to_celsius',
    'dewpoint': 'fahrenheit_to_celsius',
    'wind_speed': 'mph_to_ms',
    'wind_gust': 'mph_to_ms',
    'precip': 'inches_to_mm',
}

# NOAA Daily raw columns -> standard
NOAA_DAILY_COLUMN_MAP = {
    'DATE': 'time',
    'TAVG': 'temp',           # °F -> °C (if available)
    'AWND': 'wind_speed',     # mph -> m/s
    'PRCP': 'precip',         # inches -> mm
}

NOAA_DAILY_CONVERSIONS = {
    'temp': 'fahrenheit_to_celsius',
    'wind_speed': 'mph_to_ms',
    'precip': 'inches_to_mm',
}


# =============================================================================
# PRECIP TYPE MAPPING
# =============================================================================

# ASOS ptype codes -> standard categories
PRECIP_TYPE_MAP = {
    # Dry
    'NP': 'dry',
    # Rain
    'R': 'rain', 'R+': 'rain', 'R-': 'rain',
    # Snow  
    'S': 'snow', 'S+': 'snow', 'S-': 'snow',
    # Mixed/Unknown
    'P': 'unknown', 'P?': 'unknown',
    'M': 'unknown',
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def convert_column(series, conversion_name):
    """Apply a conversion to a pandas Series."""
    import pandas as pd
    if conversion_name not in CONVERSIONS:
        raise ValueError(f"Unknown conversion: {conversion_name}")
    return pd.to_numeric(series, errors='coerce').apply(CONVERSIONS[conversion_name])


def convert_temperature(series, from_unit='fahrenheit'):
    """Convert temperature series to Celsius."""
    if from_unit == 'fahrenheit':
        return convert_column(series, 'fahrenheit_to_celsius')
    elif from_unit == 'celsius':
        return series
    else:
        raise ValueError(f"Unknown temperature unit: {from_unit}")


def convert_wind_speed(series, from_unit='knots'):
    """Convert wind speed series to m/s."""
    if from_unit == 'knots':
        return convert_column(series, 'knots_to_ms')
    elif from_unit == 'mph':
        return convert_column(series, 'mph_to_ms')
    elif from_unit == 'ms':
        return series
    else:
        raise ValueError(f"Unknown wind speed unit: {from_unit}")


def convert_precip(series, from_unit='inches'):
    """Convert precipitation series to mm."""
    if from_unit == 'inches':
        return convert_column(series, 'inches_to_mm')
    elif from_unit == 'mm':
        return series
    else:
        raise ValueError(f"Unknown precipitation unit: {from_unit}")


def map_precip_type(ptype):
    """Map raw precip type code to standard category."""
    import pandas as pd
    if pd.isna(ptype) or ptype in ['', 'nan', 'None']:
        return 'unknown'
    ptype_str = str(ptype).strip()
    return PRECIP_TYPE_MAP.get(ptype_str, 'unknown')


# =============================================================================
# PRINT CONVENTIONS (for reference)
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("STANDARD DATA CONVENTIONS")
    print("=" * 60)
    print("\nStandard Columns:")
    for col, info in STANDARD_COLUMNS.items():
        print(f"  {col:15} [{info['unit']:12}] - {info['description']}")
    
    print("\n" + "=" * 60)
    print("Run this file to see all conventions")

