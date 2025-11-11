"""
Weather Data Analysis Tools
Analyze and visualize fetched weather data
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import statistics


def load_json_file(filepath: str) -> Optional[Dict]:
    """Load data from JSON file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None


def get_latest_file(directory: str, pattern: str) -> Optional[str]:
    """Get the most recent file matching pattern in directory"""
    try:
        files = [f for f in os.listdir(directory) if pattern in f and f.endswith('.json')]
        if not files:
            return None
        files.sort(reverse=True)
        return os.path.join(directory, files[0])
    except Exception as e:
        print(f"Error finding files: {e}")
        return None


def extract_temperature_series(data: Dict, station_id: str, units: str = 'e') -> List[tuple]:
    """
    Extract temperature time series from hourly data

    Returns:
        List of (datetime, temperature) tuples
    """
    temp_series = []

    if station_id not in data:
        return temp_series

    hourly = data[station_id].get('hourly', {})
    observations = hourly.get('observations', [])

    unit_type = 'imperial' if units == 'e' else 'metric'

    for obs in observations:
        time_str = obs.get('obsTimeLocal', '')
        if time_str:
            dt = datetime.strptime(time_str[:19], '%Y-%m-%d %H:%M:%S')
            temp = obs.get(unit_type, {}).get('temp')
            if temp is not None:
                temp_series.append((dt, temp))

    return sorted(temp_series, key=lambda x: x[0])


def calculate_statistics(data: Dict, station_id: str, parameter: str,
                         units: str = 'e') -> Dict[str, float]:
    """
    Calculate statistics for a specific parameter

    Args:
        data: Loaded JSON data
        station_id: Station ID
        parameter: Parameter name (e.g., 'temp', 'humidity', 'windSpeed')
        units: 'e' or 'm'

    Returns:
        Dictionary with min, max, mean, median, std
    """
    values = []

    if station_id not in data:
        return {}

    hourly = data[station_id].get('hourly', {})
    observations = hourly.get('observations', [])

    unit_type = 'imperial' if units == 'e' else 'metric'

    for obs in observations:
        # Check if parameter is in unit measurements or root level
        if parameter in ['humidity', 'uv', 'winddir', 'solarRadiation']:
            value = obs.get(parameter)
        else:
            value = obs.get(unit_type, {}).get(parameter)

        if value is not None:
            values.append(value)

    if not values:
        return {}

    stats = {
        'count': len(values),
        'min': min(values),
        'max': max(values),
        'mean': statistics.mean(values),
        'median': statistics.median(values),
    }

    if len(values) > 1:
        stats['stdev'] = statistics.stdev(values)

    return stats


def compare_stations(data: Dict, parameter: str, units: str = 'e') -> Dict[str, Dict]:
    """
    Compare a parameter across all stations

    Args:
        data: Loaded JSON data with multiple stations
        parameter: Parameter to compare (e.g., 'temp', 'humidity')
        units: 'e' or 'm'

    Returns:
        Dictionary with statistics for each station
    """
    comparison = {}

    for station_id in data.keys():
        stats = calculate_statistics(data, station_id, parameter, units)
        if stats:
            comparison[station_id] = stats

    return comparison


def find_extremes(data: Dict, station_id: str, units: str = 'e') -> Dict[str, Dict]:
    """
    Find extreme values (hottest, coldest, windiest, etc.)

    Returns:
        Dictionary with extreme observations
    """
    if station_id not in data:
        return {}

    hourly = data[station_id].get('hourly', {})
    observations = hourly.get('observations', [])

    if not observations:
        return {}

    unit_type = 'imperial' if units == 'e' else 'metric'

    extremes = {
        'hottest': None,
        'coldest': None,
        'windiest': None,
        'highest_pressure': None,
        'lowest_pressure': None,
        'most_humid': None,
        'least_humid': None,
    }

    max_temp = float('-inf')
    min_temp = float('inf')
    max_wind = float('-inf')
    max_pressure = float('-inf')
    min_pressure = float('inf')
    max_humidity = float('-inf')
    min_humidity = float('inf')

    for obs in observations:
        measurements = obs.get(unit_type, {})

        # Temperature
        temp = measurements.get('temp')
        if temp is not None:
            if temp > max_temp:
                max_temp = temp
                extremes['hottest'] = {
                    'time': obs.get('obsTimeLocal'),
                    'value': temp,
                    'unit': '°F' if units == 'e' else '°C'
                }
            if temp < min_temp:
                min_temp = temp
                extremes['coldest'] = {
                    'time': obs.get('obsTimeLocal'),
                    'value': temp,
                    'unit': '°F' if units == 'e' else '°C'
                }

        # Wind
        wind = measurements.get('windSpeed')
        if wind is not None and wind > max_wind:
            max_wind = wind
            extremes['windiest'] = {
                'time': obs.get('obsTimeLocal'),
                'value': wind,
                'unit': 'mph' if units == 'e' else 'km/h'
            }

        # Pressure
        pressure = measurements.get('pressure')
        if pressure is not None:
            if pressure > max_pressure:
                max_pressure = pressure
                extremes['highest_pressure'] = {
                    'time': obs.get('obsTimeLocal'),
                    'value': pressure,
                    'unit': 'in' if units == 'e' else 'mb'
                }
            if pressure < min_pressure:
                min_pressure = pressure
                extremes['lowest_pressure'] = {
                    'time': obs.get('obsTimeLocal'),
                    'value': pressure,
                    'unit': 'in' if units == 'e' else 'mb'
                }

        # Humidity
        humidity = obs.get('humidity')
        if humidity is not None:
            if humidity > max_humidity:
                max_humidity = humidity
                extremes['most_humid'] = {
                    'time': obs.get('obsTimeLocal'),
                    'value': humidity,
                    'unit': '%'
                }
            if humidity < min_humidity:
                min_humidity = humidity
                extremes['least_humid'] = {
                    'time': obs.get('obsTimeLocal'),
                    'value': humidity,
                    'unit': '%'
                }

    return extremes


def export_to_csv(data: Dict, station_id: str, output_file: str,
                  units: str = 'e') -> bool:
    """
    Export hourly data to CSV format

    Args:
        data: Loaded JSON data
        station_id: Station ID
        output_file: Output CSV filename
        units: 'e' or 'm'

    Returns:
        True if successful
    """
    try:
        import csv

        if station_id not in data:
            print(f"Station {station_id} not found in data")
            return False

        hourly = data[station_id].get('hourly', {})
        observations = hourly.get('observations', [])

        if not observations:
            print("No observations to export")
            return False

        unit_type = 'imperial' if units == 'e' else 'metric'

        # Define columns
        columns = [
            'datetime',
            'temp',
            'humidity',
            'dewpt',
            'windSpeed',
            'windGust',
            'winddir',
            'pressure',
            'precipRate',
            'precipTotal',
            'uv',
            'solarRadiation'
        ]

        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns)
            writer.writeheader()

            for obs in observations:
                measurements = obs.get(unit_type, {})
                row = {
                    'datetime': obs.get('obsTimeLocal', ''),
                    'temp': measurements.get('temp', ''),
                    'humidity': obs.get('humidity', ''),
                    'dewpt': measurements.get('dewpt', ''),
                    'windSpeed': measurements.get('windSpeed', ''),
                    'windGust': measurements.get('windGust', ''),
                    'winddir': obs.get('winddir', ''),
                    'pressure': measurements.get('pressure', ''),
                    'precipRate': measurements.get('precipRate', ''),
                    'precipTotal': measurements.get('precipTotal', ''),
                    'uv': obs.get('uv', ''),
                    'solarRadiation': obs.get('solarRadiation', ''),
                }
                writer.writerow(row)

        print(f"✓ Data exported to {output_file}")
        return True

    except Exception as e:
        print(f"Error exporting to CSV: {e}")
        return False


def print_summary_report(data: Dict, station_id: str, units: str = 'e'):
    """Print a comprehensive summary report for a station"""

    if station_id not in data:
        print(f"Station {station_id} not found")
        return

    station_data = data[station_id]

    print("\n" + "=" * 70)
    print(f"WEATHER SUMMARY REPORT: {station_id}")
    print("=" * 70)

    # Current conditions
    current = station_data.get('current', {})
    if current and 'observations' in current:
        obs = current['observations'][0]
        unit_type = 'imperial' if units == 'e' else 'metric'
        measurements = obs.get(unit_type, {})

        print("\n📍 CURRENT CONDITIONS")
        print(f"  Time: {obs.get('obsTimeLocal', 'N/A')}")
        print(f"  Location: {obs.get('neighborhood', 'N/A')}")
        print(f"  Temperature: {measurements.get('temp', 'N/A')}°{'F' if units == 'e' else 'C'}")
        print(f"  Feels Like: {measurements.get('heatIndex', 'N/A')}°{'F' if units == 'e' else 'C'}")
        print(f"  Humidity: {obs.get('humidity', 'N/A')}%")
        print(
            f"  Wind: {measurements.get('windSpeed', 'N/A')} {'mph' if units == 'e' else 'km/h'} from {obs.get('winddir', 'N/A')}°")
        print(f"  Pressure: {measurements.get('pressure', 'N/A')} {'in' if units == 'e' else 'mb'}")

    # Statistics
    hourly = station_data.get('hourly', {})
    if hourly and 'observations' in hourly:
        obs_count = len(hourly['observations'])
        print(f"\n📊 STATISTICS ({obs_count} observations)")

        # Temperature stats
        temp_stats = calculate_statistics(data, station_id, 'temp', units)
        if temp_stats:
            print(f"\n  🌡️  Temperature:")
            print(
                f"    Range: {temp_stats['min']:.1f}°{'F' if units == 'e' else 'C'} to {temp_stats['max']:.1f}°{'F' if units == 'e' else 'C'}")
            print(f"    Average: {temp_stats['mean']:.1f}°{'F' if units == 'e' else 'C'}")
            print(f"    Median: {temp_stats['median']:.1f}°{'F' if units == 'e' else 'C'}")

        # Humidity stats
        humidity_stats = calculate_statistics(data, station_id, 'humidity', units)
        if humidity_stats:
            print(f"\n  💧 Humidity:")
            print(f"    Range: {humidity_stats['min']:.0f}% to {humidity_stats['max']:.0f}%")
            print(f"    Average: {humidity_stats['mean']:.1f}%")

        # Wind stats
        wind_stats = calculate_statistics(data, station_id, 'windSpeed', units)
        if wind_stats:
            print(f"\n  💨 Wind Speed:")
            print(f"    Range: {wind_stats['min']:.1f} to {wind_stats['max']:.1f} {'mph' if units == 'e' else 'km/h'}")
            print(f"    Average: {wind_stats['mean']:.1f} {'mph' if units == 'e' else 'km/h'}")

        # Extremes
        print(f"\n🏆 EXTREME VALUES:")
        extremes = find_extremes(data, station_id, units)
        for key, value in extremes.items():
            if value:
                label = key.replace('_', ' ').title()
                print(f"  {label}: {value['value']} {value['unit']} at {value['time'][:19]}")

    # Daily summary
    daily = station_data.get('daily', {})
    if daily and 'summaries' in daily:
        print(f"\n📅 DAILY SUMMARY")
        for summary in daily['summaries'][:7]:  # Show up to 7 days
            unit_type = 'imperial' if units == 'e' else 'metric'
            measurements = summary.get(unit_type, {})
            date = summary.get('obsTimeLocal', '')[:10]
            print(f"\n  {date}:")
            print(f"    High: {measurements.get('tempHigh', 'N/A')}°{'F' if units == 'e' else 'C'}")
            print(f"    Low: {measurements.get('tempLow', 'N/A')}°{'F' if units == 'e' else 'C'}")
            print(f"    Precipitation: {measurements.get('precipTotal', 'N/A')} {'in' if units == 'e' else 'mm'}")

    print("\n" + "=" * 70)