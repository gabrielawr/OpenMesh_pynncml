# Weather Underground PWS Complete System Guide

## 📚 Table of Contents
1. [Overview](#overview)
2. [Installation](#installation)
3. [File Structure](#file-structure)
4. [Quick Start](#quick-start)
5. [Detailed Usage](#detailed-usage)
6. [All Available Parameters](#all-available-parameters)
7. [Advanced Features](#advanced-features)
8. [Examples](#examples)
9. [Troubleshooting](#troubleshooting)

---

## Overview

A complete Python system for fetching, analyzing, and visualizing weather data from Weather Underground Personal Weather Stations (PWS).

### Features
- ✅ Fetch current conditions, hourly history, and daily summaries
- ✅ Support for multiple stations simultaneously
- ✅ Flexible date ranges (specific or relative)
- ✅ Both English and Metric units
- ✅ Statistical analysis and comparisons
- ✅ CSV export for further processing
- ✅ Beautiful visualizations (with matplotlib)
- ✅ Interactive analysis mode

---

## Installation

### 1. Required Packages
```bash
# Core functionality (required)
pip install requests

# For analysis and visualization (optional but recommended)
pip install matplotlib
```

### 2. Get Your API Key
1. Go to https://www.wunderground.com/member/api-keys
2. Register/login to your Weather Underground account
3. Create an API key for PWS access
4. Copy your API key

### 3. Find Your Station ID
- Visit: https://www.wunderground.com/wundermap
- Find your station or search for nearby stations
- Station IDs look like: `KNYNEWYO1127`

---


## File Structure

```
your_project/
├── wu_functions.py        # Core API functions
├── main.py                # Main data fetching script
├── data_analysis.py       # Analysis tools
├── analyze.py             # Analysis runner
├── visualize.py           # Visualization generator
├── output/                # Output directory (auto-created)
│   ├── *.json            # JSON data files
│   ├── *.csv             # CSV exports
│   └── plots/            # Generated visualizations
├── README.md              # Basic usage
└── COMPLETE_GUIDE.md      # This file
```

---

## Quick Start

### Step 1: Fetch Data
Edit `main.py`:
```python
API_KEY = 'your_api_key_here'
STATION_IDS = ['KNYNEWYO1127', 'KNYNEWYO2197']
START_DATE = datetime.now() - timedelta(days=7)
END_DATE = datetime.now()
```

Run:
```bash
python main.py
```

### Step 2: Analyze Data
```bash
# Automated analysis
python analyze.py

# Interactive mode
python analyze.py --interactive
```

### Step 3: Create Visualizations
```bash
python visualize.py
```

---

## Detailed Usage

### 1. Data Fetching (`main.py`)

#### Basic Configuration
```python
# Single station, last 7 days
API_KEY = 'your_key'
STATION_IDS = ['KNYNEWYO1127']
START_DATE = datetime.now() - timedelta(days=7)
END_DATE = datetime.now()
UNITS = 'e'  # English units
```

#### Multiple Stations
```python
STATION_IDS = [
    'KNYNEWYO1127',
    'KNYNEWYO2197',
    'KCASANDI123',
    'KTXAUSTI456',
]
```

#### Specific Date Range
```python
START_DATE = datetime(2024, 9, 1)   # September 1, 2024
END_DATE = datetime(2024, 9, 30)    # September 30, 2024
```

#### Output Options
```python
OUTPUT_OPTIONS = {
    'save_combined': True,       # All stations in one file
    'save_individual': True,     # Separate files per station
    'save_by_type': True,        # By data type (current/hourly/daily)
    'print_summary': True,       # Console summary
}
```

### 2. Data Analysis (`analyze.py`)

#### Automated Analysis
Runs all configured analyses:
```bash
python analyze.py
```

Features:
- Summary reports for each station
- Statistical calculations (min, max, mean, median, stdev)
- Multi-station comparisons
- Extreme value detection
- CSV exports

#### Interactive Mode
```bash
python analyze.py --interactive
```

Interactive menu options:
1. View summary report for a station
2. Compare all stations
3. Find extreme values
4. Calculate statistics for a parameter
5. Export station data to CSV
6. Exit

#### Configuration
```python
ANALYSIS_OPTIONS = {
    'summary_report': True,
    'station_comparison': True,
    'export_csv': True,
    'temperature_analysis': True,
}
```

### 3. Visualization (`visualize.py`)

Generates:
- Temperature timeline plots
- Multi-parameter plots (temp, humidity, pressure, wind)
- Daily high/low summaries
- Wind rose diagrams
- Station comparison plots

```bash
python visualize.py
```

Configuration:
```python
PLOT_STYLE = 'seaborn-v0_8-darkgrid'  # Plot style
FIGURE_SIZE = (12, 6)                  # Figure dimensions
DPI = 100                              # Resolution
```

---

## All Available Parameters

### Current Observation Parameters
```python
{
    'stationID': 'Station ID',
    'obsTimeLocal': 'Observation Time (Local)',
    'obsTimeUtc': 'Observation Time (UTC)',
    'neighborhood': 'Neighborhood Name',
    'softwareType': 'Software Type',
    'country': 'Country Code',
    'solarRadiation': 'Solar Radiation (W/m²)',
    'lon': 'Longitude',
    'lat': 'Latitude',
    'uv': 'UV Index',
    'winddir': 'Wind Direction (degrees)',
    'humidity': 'Humidity (%)',
    'qcStatus': 'Quality Control Status'
}
```

### Imperial Unit Parameters (units='e')
```python
{
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
```

### Metric Unit Parameters (units='m')
```python
{
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
```

### Daily Summary Parameters
```python
{
    'tempHigh': 'High Temperature',
    'tempLow': 'Low Temperature',
    'tempAvg': 'Average Temperature',
    'windspeedHigh': 'Highest Wind Speed',
    'windspeedLow': 'Lowest Wind Speed',
    'windspeedAvg': 'Average Wind Speed',
    'pressureMax': 'Maximum Pressure',
    'pressureMin': 'Minimum Pressure',
    'precipRate': 'Precipitation Rate',
    'precipTotal': 'Total Precipitation'
}
```

---

## Advanced Features

### 1. Using Functions Programmatically

#### Import and Use Functions
```python
from wu_functions import get_current_conditions, fetch_all_data
from data_analysis import calculate_statistics, compare_stations
from datetime import datetime, timedelta

# Fetch data
api_key = 'your_key'
station_ids = ['KNYNEWYO1127']
start = datetime.now() - timedelta(days=7)
end = datetime.now()

data = fetch_all_data(api_key, station_ids, start, end, units='e')

# Analyze
stats = calculate_statistics(data, 'KNYNEWYO1127', 'temp', 'e')
print(f"Average temperature: {stats['mean']:.1f}°F")
```

### 2. Custom Analysis Scripts

#### Example: Find Rainy Days
```python
from data_analysis import load_json_file

data = load_json_file('output/hourly_history_20241001_120000.json')

for station_id, station_data in data.items():
    hourly = station_data.get('hourly', {})
    rainy_hours = 0
    
    for obs in hourly.get('observations', []):
        precip = obs.get('imperial', {}).get('precipRate', 0)
        if precip > 0:
            rainy_hours += 1
    
    print(f"{station_id}: {rainy_hours} hours with precipitation")
```

#### Example: Temperature Trends
```python
from data_analysis import extract_temperature_series

temp_series = extract_temperature_series(data, 'KNYNEWYO1127', 'e')

# Calculate warming/cooling trend
if len(temp_series) > 1:
    first_temp = temp_series[0][1]
    last_temp = temp_series[-1][1]
    change = last_temp - first_temp
    
    print(f"Temperature change: {change:+.1f}°F")
```

### 3. Batch Processing Multiple Date Ranges

```python
from datetime import datetime, timedelta
from wu_functions import fetch_all_data, save_to_json

api_key = 'your_key'
stations = ['KNYNEWYO1127']

# Fetch data for each month of 2024
for month in range(1, 13):
    start = datetime(2024, month, 1)
    if month == 12:
        end = datetime(2024, 12, 31)
    else:
        end = datetime(2024, month + 1, 1) - timedelta(days=1)
    
    print(f"Fetching data for {start.strftime('%B %Y')}...")
    data = fetch_all_data(api_key, stations, start, end, 'e')
    
    filename = f'weather_2024_{month:02d}.json'
    save_to_json(data, filename, 'output/monthly')
```

---

## Examples

### Example 1: Monitor Your Home Weather Station
```python
# main.py configuration
API_KEY = 'your_key'
STATION_IDS = ['KNYNEWYO1127']  # Your station
START_DATE = datetime.now() - timedelta(days=1)  # Last 24 hours
END_DATE = datetime.now()
UNITS = 'e'
```

### Example 2: Compare Multiple Stations in Your Area
```python
# main.py configuration
STATION_IDS = [
    'KNYNEWYO1127',
    'KNYNEWYO2197',
    'KNYNEWYO3456',
]
START_DATE = datetime.now() - timedelta(days=7)
END_DATE = datetime.now()

# Then run:
# python main.py
# python analyze.py  # See comparisons
# python visualize.py  # See comparison charts
```

### Example 3: Historical Data Analysis
```python
# Get data for entire September 2024
START_DATE = datetime(2024, 9, 1)
END_DATE = datetime(2024, 9, 30)
STATION_IDS = ['KNYNEWYO1127']

# Run main.py, then analyze
```

### Example 4: Export to CSV for Excel/Pandas
```python
from data_analysis import load_json_file, export_to_csv

data = load_json_file('output/hourly_history_20241001.json')
export_to_csv(data, 'KNYNEWYO1127', 'my_station_data.csv', 'e')

# Now open in Excel or use with pandas:
import pandas as pd
df = pd.read_csv('output/my_station_data.csv')
print(df.describe())
```

---

## Troubleshooting

### Common Issues

#### 1. "ModuleNotFoundError: No module named 'requests'"
**Solution:**
```bash
pip install requests
```

#### 2. "No observations found for station"
**Possible causes:**
- Station is not active
- Station ID is incorrect
- Station is not reporting data

**Solutions:**
- Check station at: `https://www.wunderground.com/dashboard/pws/YOURSTATIONID`
- Verify station ID is correct (case-sensitive)
- Try a different date range

#### 3. "Error fetching data: 401"
**Cause:** Invalid API key

**Solutions:**
- Verify API key at: https://www.wunderground.com/member/api-keys
- Ensure key has PWS API access enabled
- Check for typos in the key

#### 4. "Error fetching data: 404"
**Cause:** Station ID not found

**Solutions:**
- Double-check station ID spelling
- Verify station exists on wunderground.com
- Try searching for the station on the map

#### 5. Limited Data Returned
**API Limitations:**
- Hourly data: Maximum 7 days
- Daily summary: Maximum 7-30 days
- Some stations may not report all parameters

**Solutions:**
- For longer historical data, fetch in 7-day chunks
- Check if station supports the parameters you need
- Consider using daily summaries for longer periods

#### 6. "matplotlib not available"
**Solution:**
```bash
pip install matplotlib
```

#### 7. Date Range Issues
**Problem:** Requested date range too large

**Solutions:**
```python
# For hourly data, limit to 7 days
START_DATE = datetime.now() - timedelta(days=7)
END_DATE = datetime.now()

# For longer periods, use daily summaries
# or fetch in chunks
```

---

## API Rate Limits

Weather Underground may impose rate limits on API requests. Best practices:

1. **Cache data locally** - Don't fetch the same data repeatedly
2. **Use appropriate date ranges** - Don't request more than needed
3. **Batch requests** - Fetch multiple stations in one run
4. **Schedule wisely** - If automating, space out requests

Example for automated hourly updates:
```python
import time
import schedule

def fetch_latest():
    """Fetch last hour of data"""
    start = datetime.now() - timedelta(hours=1)
    end = datetime.now()
    data = fetch_all_data(API_KEY, STATION_IDS, start, end)
    save_to_json(data, f'latest_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')

# Run every hour
schedule.every().hour.at(":05").do(fetch_latest)

while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## Data Format Examples

### JSON Output Structure

#### Combined File (all stations)
```json
{
  "KNYNEWYO1127": {
    "station_id": "KNYNEWYO1127",
    "current": {
      "observations": [{
        "stationID": "KNYNEWYO1127",
        "obsTimeLocal": "2024-10-01 12:00:00",
        "neighborhood": "Upper West Side",
        "imperial": {
          "temp": 72.5,
          "humidity": 65,
          "pressure": 30.12,
          "windSpeed": 8.5
        }
      }]
    },
    "hourly": {
      "observations": [...]
    },
    "daily": {
      "summaries": [...]
    },
    "fetch_time": "2024-10-01T12:30:00"
  },
  "KNYNEWYO2197": {...}
}
```

#### CSV Export Format
```csv
datetime,temp,humidity,dewpt,windSpeed,windGust,winddir,pressure,precipRate,precipTotal,uv,solarRadiation
2024-10-01 12:00:00,72.5,65,58.3,8.5,12.1,180,30.12,0.0,0.0,5,650
2024-10-01 13:00:00,73.2,63,57.9,9.2,13.5,185,30.11,0.0,0.0,6,720
```

---

## Best Practices

### 1. Data Management
```python
# Organize by date
output/
  ├── 2024-09/
  │   ├── weather_data_20240901.json
  │   └── weather_data_20240930.json
  └── 2024-10/
      └── weather_data_20241001.json

# Keep raw and processed data separate
output/
  ├── raw/          # Original JSON from API
  ├── processed/    # CSV exports
  └── plots/        # Visualizations
```

### 2. Error Handling
```python
from wu_functions import get_current_conditions

def safe_fetch(api_key, station_id):
    """Fetch with retry logic"""
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            data = get_current_conditions(api_key, station_id)
            if data:
                return data
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    
    return None
```

### 3. Configuration Management
```python
# config.py - Keep sensitive data separate
API_KEY = 'your_api_key'
STATIONS = {
    'home': 'KNYNEWYO1127',
    'office': 'KNYNEWYO2197',
    'cabin': 'KCASANDI123'
}

# main.py - Import config
from config import API_KEY, STATIONS

STATION_IDS = list(STATIONS.values())
```

### 4. Logging
```python
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('weather_fetch.log'),
        logging.StreamHandler()
    ]
)

# Use in functions
logging.info(f"Fetching data for {station_id}")
logging.error(f"Failed to fetch: {error}")
```

---

## Advanced Use Cases

### 1. Weather Alert System
```python
def check_for_alerts(data, station_id):
    """Check for extreme conditions"""
    current = data[station_id]['current']['observations'][0]
    temp = current['imperial']['temp']
    wind = current['imperial']['windSpeed']
    
    alerts = []
    
    if temp > 95:
        alerts.append(f"⚠️ HEAT WARNING: {temp}°F")
    elif temp < 20:
        alerts.append(f"❄️ COLD WARNING: {temp}°F")
    
    if wind > 25:
        alerts.append(f"💨 HIGH WIND: {wind} mph")
    
    return alerts
```

### 2. Data Quality Checks
```python
def validate_data(observations):
    """Check data quality"""
    issues = []
    
    for obs in observations:
        temp = obs.get('imperial', {}).get('temp')
        humidity = obs.get('humidity')
        
        # Check for unrealistic values
        if temp and (temp < -50 or temp > 150):
            issues.append(f"Suspicious temp: {temp}°F")
        
        if humidity and (humidity < 0 or humidity > 100):
            issues.append(f"Invalid humidity: {humidity}%")
        
        # Check for missing data
        if temp is None:
            issues.append("Missing temperature")
    
    return issues
```

### 3. Automated Reporting
```python
def generate_daily_report(data, station_id):
    """Generate daily weather summary"""
    from data_analysis import calculate_statistics, find_extremes
    
    stats = calculate_statistics(data, station_id, 'temp', 'e')
    extremes = find_extremes(data, station_id, 'e')
    
    report = f"""
    DAILY WEATHER REPORT - {station_id}
    Date: {datetime.now().strftime('%Y-%m-%d')}
    
    Temperature:
      High: {extremes['hottest']['value']}°F at {extremes['hottest']['time']}
      Low: {extremes['coldest']['value']}°F at {extremes['coldest']['time']}
      Average: {stats['mean']:.1f}°F
    
    Wind:
      Max: {extremes['windiest']['value']} mph at {extremes['windiest']['time']}
    
    Humidity:
      High: {extremes['most_humid']['value']}%
      Low: {extremes['least_humid']['value']}%
    """
    
    return report

# Email the report
def email_report(report, recipient):
    import smtplib
    from email.mime.text import MIMEText
    
    msg = MIMEText(report)
    msg['Subject'] = f"Daily Weather Report - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = 'weather@yourdomain.com'
    msg['To'] = recipient
    
    # Send email (configure your SMTP settings)
    # s = smtplib.SMTP('localhost')
    # s.send_message(msg)
    # s.quit()
```

---

## Integration Examples

### With Pandas
```python
import pandas as pd
from data_analysis import load_json_file

# Load and convert to DataFrame
data = load_json_file('output/hourly_history.json')
observations = data['KNYNEWYO1127']['hourly']['observations']

# Extract to DataFrame
df = pd.DataFrame([{
    'datetime': pd.to_datetime(obs['obsTimeLocal']),
    'temp': obs['imperial']['temp'],
    'humidity': obs['humidity'],
    'pressure': obs['imperial']['pressure'],
    'wind': obs['imperial']['windSpeed']
} for obs in observations])

# Analysis with pandas
print(df.describe())
print(df.corr())

# Resample to different frequencies
df_daily = df.resample('D', on='datetime').mean()
```

### With SQLite Database
```python
import sqlite3
import json

def save_to_database(data, db_path='weather.db'):
    """Save weather data to SQLite database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            station_id TEXT,
            datetime TEXT,
            temp REAL,
            humidity REAL,
            pressure REAL,
            wind_speed REAL,
            wind_dir INTEGER
        )
    ''')
    
    # Insert data
    for station_id, station_data in data.items():
        hourly = station_data.get('hourly', {})
        for obs in hourly.get('observations', []):
            cursor.execute('''
                INSERT INTO observations 
                (station_id, datetime, temp, humidity, pressure, wind_speed, wind_dir)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                station_id,
                obs['obsTimeLocal'],
                obs['imperial']['temp'],
                obs['humidity'],
                obs['imperial']['pressure'],
                obs['imperial']['windSpeed'],
                obs['winddir']
            ))
    
    conn.commit()
    conn.close()
```

---

## Resources

### Official Documentation
- [Weather Underground PWS API](https://docs.google.com/document/d/1eKCnKXI9xnoMGRRzOL1xPCBihNV2rOet08qpE_gArAY/edit)
- [PWS Dashboard](https://www.wunderground.com/dashboard/pws/)
- [API Keys](https://www.wunderground.com/member/api-keys)

### Python Libraries
- [Requests](https://docs.python-requests.org/)
- [Matplotlib](https://matplotlib.org/)
- [Pandas](https://pandas.pydata.org/)

### Community
- [Weather Underground Community](https://community.wunderground.com/)

---

## License & Disclaimer

This code is provided as-is for educational and personal use. Make sure to:
- Comply with Weather Underground's Terms of Service
- Respect API rate limits
- Not redistribute API keys
- Use data responsibly

---

## Support & Contributing

For issues or questions:
1. Check this guide first
2. Review the troubleshooting section
3. Check Weather Underground's API documentation
4. Verify your API key and station IDs

Happy weather monitoring! 🌤️📊