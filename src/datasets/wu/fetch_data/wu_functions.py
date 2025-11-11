"""
Weather Underground PWS API Functions
Contains all functions for fetching and processing weather data
"""

import requests
from datetime import datetime, timedelta
import json
import os
from typing import Dict, List, Optional, Tuple

# Base URL for Weather Underground PWS API
BASE_URL = "https://api.weather.com/v2/pws"

# All available parameters in WU PWS API responses
CURRENT_PARAMS = {
    'stationID': 'Station ID',
    'obsTimeUtc': 'Observation Time (UTC)',
    'obsTimeLocal': 'Observation Time (Local)',
    'neighborhood': 'Neighborhood',
    'softwareType': 'Software Type',
    'country': 'Country',
    'solarRadiation': 'Solar Radiation (W/m²)',
    'lon': 'Longitude',
    'realtimeFrequency': 'Realtime Frequency',
    'epoch': 'Epoch Time',
    'lat': 'Latitude',
    'uv': 'UV Index',
    'winddir': 'Wind Direction (degrees)',
    'humidity': 'Humidity (%)',
    'qcStatus': 'QC Status'
}

IMPERIAL_PARAMS = {
    'temp': 'Temperature (°F)',
    'heatIndex': 'Heat Index (°F)',
    'dewpt': 'Dew Point (°F)',
    'windChill': 'Wind Chill (°F)',
    'windSpeed': 'Wind Speed (mph)',
    'windGust': 'Wind Gust (mph)',
    'pressure': 'Pressure (in)',
    'precipRate': 'Precipitation Rate (in/hr)',
    'precipTotal': 'Precipitation Total (in)',
    'elev': 'Elevation (ft)'
}

METRIC_PARAMS = {
    'temp': 'Temperature (°C)',
    'heatIndex': 'Heat Index (°C)',
    'dewpt': 'Dew Point (°C)',
    'windChill': 'Wind Chill (°C)',
    'windSpeed': 'Wind Speed (km/h)',
    'windGust': 'Wind Gust (km/h)',
    'pressure': 'Pressure (mb)',
    'precipRate': 'Precipitation Rate (mm/hr)',
    'precipTotal': 'Precipitation Total (mm)',
    'elev': 'Elevation (m)'
}


def get_current_conditions(api_key: str, station_id: str, units: str = 'e') -> Optional[Dict]:
    """
    Fetch current weather conditions for a station

    Args:
        api_key: Weather Underground API key
        station_id: Station ID (e.g., 'KNYNEWYO1127')
        units: 'e' for English, 'm' for metric

    Returns:
        Dictionary with current conditions or None if error
    """
    url = f"{BASE_URL}/observations/current"
    params = {
        'stationId': station_id,
        'format': 'json',
        'units': units,
        'apiKey': api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'observations' in data and len(data['observations']) > 0:
            return data
        else:
            print(f"No observations found for station {station_id}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching current conditions for {station_id}: {e}")
        return None


def get_hourly_history(api_key: str, station_id: str, start_date: datetime,
                       end_date: datetime, units: str = 'e') -> Optional[Dict]:
    """
    Fetch hourly historical observations (max 7 days)

    Args:
        api_key: Weather Underground API key
        station_id: Station ID
        start_date: Start datetime
        end_date: End datetime
        units: 'e' for English, 'm' for metric

    Returns:
        Dictionary with hourly observations or None if error
    """
    url = f"{BASE_URL}/observations/hourly/7day"
    params = {
        'stationId': station_id,
        'format': 'json',
        'units': units,
        'apiKey': api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'observations' in data:
            # Filter by date range
            observations = data['observations']
            filtered_obs = []

            for obs in observations:
                obs_time = datetime.strptime(obs['obsTimeLocal'][:19], '%Y-%m-%d %H:%M:%S')
                if start_date <= obs_time <= end_date:
                    filtered_obs.append(obs)

            data['observations'] = filtered_obs
            return data
        else:
            print(f"No observations found for station {station_id}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching hourly history for {station_id}: {e}")
        return None


def get_daily_summary(api_key: str, station_id: str, num_days: int = 7,
                      units: str = 'e') -> Optional[Dict]:
    """
    Fetch daily summary (max 7 days)

    Args:
        api_key: Weather Underground API key
        station_id: Station ID
        num_days: Number of days (1-7)
        units: 'e' for English, 'm' for metric

    Returns:
        Dictionary with daily summaries or None if error
    """
    # API endpoint supports 7day, 30day
    endpoint = '7day' if num_days <= 7 else '30day'
    url = f"{BASE_URL}/dailysummary/{endpoint}"

    params = {
        'stationId': station_id,
        'format': 'json',
        'units': units,
        'apiKey': api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'summaries' in data:
            # Limit to requested number of days
            data['summaries'] = data['summaries'][:num_days]
            return data
        else:
            print(f"No summary data found for station {station_id}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching daily summary for {station_id}: {e}")
        return None


def fetch_all_data(api_key: str, station_ids: List[str], start_date: datetime,
                   end_date: datetime, units: str = 'e',
                   fetch_options: Dict = None) -> Dict[str, Dict]:
    """
    Fetch all available data for multiple stations

    Args:
        api_key: Weather Underground API key
        station_ids: List of station IDs
        start_date: Start datetime for historical data
        end_date: End datetime for historical data
        units: 'e' for English, 'm' for metric
        fetch_options: Dict specifying what to fetch (current, rapid, hourly, daily)

    Returns:
        Dictionary with all data organized by station
    """
    if fetch_options is None:
        fetch_options = {'current': True, 'rapid': True, 'hourly': True, 'daily': True}

    all_data = {}

    for station_id in station_ids:
        print(f"\n{'=' * 60}")
        print(f"Fetching data for station: {station_id}")
        print(f"{'=' * 60}")

        station_data = {
            'station_id': station_id,
            'current': None,
            'rapid': None,
            'hourly': None,
            'daily': None,
            'fetch_time': datetime.now().isoformat()
        }

        # Calculate date range (needed for hourly and daily)
        days_diff = (end_date - start_date).days

        # Fetch current conditions
        if fetch_options.get('current', True):
            print(f"  → Fetching current conditions...")
            current = get_current_conditions(api_key, station_id, units)
            if current:
                station_data['current'] = current
                print(f"    ✓ Current conditions fetched")

        # Fetch rapid history (high resolution - last 24 hours)
        if fetch_options.get('rapid', True):
            print(f"  → Fetching rapid history (high resolution, last 24h)...")
            rapid = get_rapid_history(api_key, station_id, units)
            if rapid:
                station_data['rapid'] = rapid
                obs_count = len(rapid.get('observations', []))
                print(f"    ✓ Rapid history fetched ({obs_count} observations)")
                # Fetch historical data (hourly resolution for date range)
                if fetch_options.get('rapid', True):
                    # Check if date range is within 31 days
                    if days_diff > 31:
                        print(f"  ⚠ Historical data limited to 31 days (requested {days_diff} days)")
                        hist_start = end_date - timedelta(days=31)
                    else:
                        hist_start = start_date

                    print(f"  → Fetching historical hourly data ({hist_start.date()} to {end_date.date()})...")
                    historical = get_historical_data(api_key, station_id, hist_start, end_date, units, 'hourly')
                    if historical:
                        station_data['rapid'] = historical
                        obs_count = len(historical.get('observations', []))
                        print(f"    ✓ Historical data fetched ({obs_count} hourly observations)")


        # Fetch hourly history (limited to 7 days by API)
        if fetch_options.get('hourly', True):
            if days_diff > 7:
                print(f"  ⚠ Hourly data limited to last 7 days (requested {days_diff} days)")
                hourly_start = end_date - timedelta(days=7)
            else:
                hourly_start = start_date

            print(f"  → Fetching hourly history ({hourly_start.date()} to {end_date.date()})...")
            hourly = get_hourly_history(api_key, station_id, hourly_start, end_date, units)
            if hourly:
                station_data['hourly'] = hourly
                obs_count = len(hourly.get('observations', []))
                print(f"    ✓ Hourly history fetched ({obs_count} observations)")

        # Fetch daily summary
        if fetch_options.get('daily', True):
            summary_days = min(days_diff, 7)
            print(f"  → Fetching daily summary ({summary_days} days)...")
            daily = get_daily_summary(api_key, station_id, summary_days, units)
            if daily:
                station_data['daily'] = daily
                summary_count = len(daily.get('summaries', []))
                print(f"    ✓ Daily summary fetched ({summary_count} days)")

        all_data[station_id] = station_data

    return all_data


def save_to_json(data: Dict, filename: str, output_dir: str = 'output') -> bool:
    """
    Save data to a JSON file

    Args:
        data: Data to save
        filename: Output filename
        output_dir: Output directory (default: 'output')

    Returns:
        True if successful, False otherwise
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✓ Data saved to {filepath}")
        return True

    except Exception as e:
        print(f"✗ Error saving to file: {e}")
        return False


def print_current_summary(data: Dict, units: str = 'e'):
    """Print a summary of current conditions"""
    if not data or 'observations' not in data:
        return

    obs = data['observations'][0]
    unit_type = 'imperial' if units == 'e' else 'metric'
    measurements = obs.get(unit_type, {})

    print(f"\n  Station: {obs.get('stationID', 'N/A')}")
    print(f"  Time: {obs.get('obsTimeLocal', 'N/A')}")
    print(f"  Temperature: {measurements.get('temp', 'N/A')}°{'F' if units == 'e' else 'C'}")
    print(f"  Humidity: {obs.get('humidity', 'N/A')}%")
    print(f"  Wind Speed: {measurements.get('windSpeed', 'N/A')} {'mph' if units == 'e' else 'km/h'}")
    print(f"  Pressure: {measurements.get('pressure', 'N/A')} {'in' if units == 'e' else 'mb'}")


def get_all_available_parameters() -> Dict[str, Dict[str, str]]:
    """
    Get all available parameters that can be read from the API

    Returns:
        Dictionary containing all parameter categories
    """
    return {
        'current_observation': CURRENT_PARAMS,
        'imperial_units': IMPERIAL_PARAMS,
        'metric_units': METRIC_PARAMS
    }


def print_available_parameters():
    """Print all available parameters"""
    params = get_all_available_parameters()

    print("\n" + "=" * 60)
    print("AVAILABLE WEATHER PARAMETERS")
    print("=" * 60)

    print("\n📊 CURRENT OBSERVATION PARAMETERS:")
    for key, label in params['current_observation'].items():
        print(f"  • {key:20} → {label}")

    print("\n🇺🇸 IMPERIAL UNIT PARAMETERS:")
    for key, label in params['imperial_units'].items():
        print(f"  • {key:20} → {label}")

    print("\n🌍 METRIC UNIT PARAMETERS:")
    for key, label in params['metric_units'].items():
        print(f"  • {key:20} → {label}")

    print("\n" + "=" * 60)


def validate_date_range(start_date: datetime, end_date: datetime) -> Tuple[datetime, datetime]:
    """
    Validate and adjust date range

    Args:
        start_date: Start datetime
        end_date: End datetime

    Returns:
        Tuple of validated (start_date, end_date)
    """
    now = datetime.now()

    # Ensure end_date is not in the future
    if end_date > now:
        print(f"⚠ End date adjusted from {end_date} to {now} (cannot be in future)")
        end_date = now

    # Ensure start_date is before end_date
    if start_date >= end_date:
        print(f"⚠ Start date must be before end date")
        start_date = end_date - timedelta(days=7)

    # Warn if range is too large
    days_diff = (end_date - start_date).days
    if days_diff > 30:
        print(f"⚠ Warning: {days_diff} days requested. Hourly data limited to 7 days.")

    return start_date, end_date


def get_rapid_history(api_key: str, station_id: str, units: str = 'e') -> Optional[Dict]:
    """
    Fetch rapid history - high resolution data for last 24 hours (5-10 minute intervals)

    Args:
        api_key: Weather Underground API key
        station_id: Station ID
        units: 'e' for English, 'm' for metric

    Returns:
        Dictionary with rapid history observations or None if error
    """
    url = f"{BASE_URL}/observations/all/1day"
    params = {
        'stationId': station_id,
        'format': 'json',
        'units': units,
        'apiKey': api_key
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'observations' in data:
            return data
        else:
            print(f"No rapid history found for station {station_id}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching rapid history for {station_id}: {e}")
        return None


def get_historical_data(api_key: str, station_id: str, start_date: datetime,
                        end_date: datetime, units: str = 'e',
                        data_type: str = 'hourly') -> Optional[Dict]:
    """
    Fetch historical data for a date range (max 31 days)

    Args:
        api_key: Weather Underground API key
        station_id: Station ID
        start_date: Start datetime
        end_date: End datetime
        units: 'e' for English, 'm' for metric
        data_type: 'hourly', 'all', or 'daily'

    Returns:
        Dictionary with historical observations or None if error
    """
    url = f"{BASE_URL}/history/{data_type}"

    # Format dates as YYYYMMDD
    start_str = start_date.strftime('%Y%m%d')
    end_str = end_date.strftime('%Y%m%d')

    params = {
        'stationId': station_id,
        'format': 'json',
        'units': units,
        'startDate': start_str,
        'endDate': end_str,
        'apiKey': api_key
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if 'observations' in data:
            return data
        else:
            print(f"No historical data found for {station_id}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching historical data for {station_id}: {e}")
        return None