# Weather Underground PWS Data Fetcher

A modular Python system for fetching weather data from Weather Underground Personal Weather Stations (PWS).

## 📁 File Structure

```
your_project/
├── wu_functions.py    # All API functions and utilities
├── main.py            # Main configuration and execution script
├── output/            # Output directory (created automatically)
│   ├── current_conditions_*.json
│   ├── hourly_history_*.json
│   ├── daily_summary_*.json
│   └── weather_data_*.json
└── README.md          # This file
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install requests
```

### 2. Configure Settings
Edit `main.py` and update:

```python
# Your API Key
API_KEY = 'your_api_key_here'

# Station IDs
STATION_IDS = [
    'KNYNEWYO1127',
    'KNYNEWYO2197',
    # Add more stations...
]

# Date Range
START_DATE = datetime(2024, 9, 25)
END_DATE = datetime(2024, 10, 1)
```

### 3. Run
```bash
python main.py
```

## ⚙️ Configuration Options

### Date Ranges

**Option 1: Specific Dates**
```python
START_DATE = datetime(2024, 9, 25)  # Year, Month, Day
END_DATE = datetime(2024, 10, 1)
```

**Option 2: Relative Dates**
```python
START_DATE = datetime.now() - timedelta(days=7)  # Last 7 days
END_DATE = datetime.now()

START_DATE = datetime.now() - timedelta(days=30)  # Last 30 days
END_DATE = datetime.now()
```

### Units

```python
UNITS = 'e'  # English: °F, mph, inches
UNITS = 'm'  # Metric: °C, km/h, mm
```

### Multiple Stations

```python
STATION_IDS = [
    'KNYNEWYO1127',
    'KNYNEWYO2197',
    'KCASANDI123',
    'KTXAUSTI456',
]
```

### Output Options

```python
OUTPUT_OPTIONS = {
    'save_combined': True,       # One file with all stations
    'save_individual': True,     # Separate file per station
    'save_by_type': True,        # Files by data type (current/hourly/daily)
    'print_summary': True,       # Print to console
}
```

## 📊 Available Parameters

### Current Observation Parameters
- `stationID` - Station ID
- `obsTimeLocal` - Observation Time (Local)
- `neighborhood` - Neighborhood
- `humidity` - Humidity (%)
- `winddir` - Wind Direction (degrees)
- `uv` - UV Index
- `solarRadiation` - Solar Radiation (W/m²)

### Imperial Unit Parameters
- `temp` - Temperature (°F)
- `heatIndex` - Heat Index (°F)
- `dewpt` - Dew Point (°F)
- `windChill` - Wind Chill (°F)
- `windSpeed` - Wind Speed (mph)
- `windGust` - Wind Gust (mph)
- `pressure` - Pressure (in)
- `precipRate` - Precipitation Rate (in/hr)
- `precipTotal` - Precipitation Total (in)

### Metric Unit Parameters
Same parameters but in metric units (°C, km/h, mm, mb)

## 📦 Output Files

### Combined File
```json
{
  "KNYNEWYO1127": {
    "station_id": "KNYNEWYO1127",
    "current": { ... },
    "hourly": { ... },
    "daily": { ... },
    "fetch_time": "2024-10-01T10:30:00"
  },
  "KNYNEWYO2197": { ... }
}
```

### By Type Files
- `current_conditions_*.json` - Latest observations from all stations
- `hourly_history_*.json` - Hourly data from all stations
- `daily_summary_*.json` - Daily summaries from all stations

### Individual Station Files
- `weather_data_KNYNEWYO1127_*.json` - All data for single station

## 🔍 API Limitations

- **Hourly Data**: Maximum 7 days
- **Daily Summary**: Maximum 7-30 days (depending on endpoint)
- **Rate Limits**: Depends on your API key type

## 🛠️ Functions in `wu_functions.py`

### Data Fetching
- `get_current_conditions()` - Fetch current weather
- `get_hourly_history()` - Fetch hourly historical data
- `get_daily_summary()` - Fetch daily summaries
- `fetch_all_data()` - Fetch everything for multiple stations

### Utilities
- `save_to_json()` - Save data to JSON file
- `print_available_parameters()` - Display all available parameters
- `validate_date_range()` - Validate and adjust date ranges
- `print_current_summary()` - Print current conditions summary

## 💡 Usage Examples

### Example 1: Last 7 Days, Single Station
```python
API_KEY = 'your_key'
STATION_IDS = ['KNYNEWYO1127']
START_DATE = datetime.now() - timedelta(days=7)
END_DATE = datetime.now()
UNITS = 'e'
```

### Example 2: Multiple Stations, Specific Date Range
```python
API_KEY = 'your_key'
STATION_IDS = ['KNYNEWYO1127', 'KNYNEWYO2197', 'KCASANDI123']
START_DATE = datetime(2024, 9, 1)
END_DATE = datetime(2024, 9, 30)
UNITS = 'm'  # Metric units
```

### Example 3: Current Conditions Only
```python
FETCH_OPTIONS = {
    'current': True,
    'hourly': False,
    'daily': False,
}
```

## 🔗 Resources

- [Weather Underground PWS Dashboard](https://www.wunderground.com/dashboard/pws/)
- [WU API Keys](https://www.wunderground.com/member/api-keys)
- [PWS Network](https://www.wunderground.com/pws/overview)

## ⚠️ Troubleshooting

1. **"No module named 'requests'"**
   ```bash
   pip install requests
   ```

2. **"No observations found"**
   - Check if station is active
   - Verify station ID is correct
   - Ensure station is reporting data

3. **API Key Issues**
   - Verify key at: https://www.wunderground.com/member/api-keys
   - Ensure key has PWS API access enabled

4. **Date Range Too Large**
   - Hourly data limited to 7 days
   - Use daily summaries for longer ranges