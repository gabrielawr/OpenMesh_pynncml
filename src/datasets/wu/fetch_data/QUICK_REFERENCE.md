# Weather Underground PWS - Quick Reference

## 🚀 Setup & Installation

```bash
# Install required packages
pip install requests

# Install optional packages (for visualization)
pip install matplotlib

# Verify setup
python setup.py
```

## 📋 File Overview

| File | Purpose |
|------|---------|
| `wu_functions.py` | Core API functions |
| `main.py` | Data fetching (configure & run) |
| `data_analysis.py` | Analysis functions |
| `analyze.py` | Run analysis |
| `visualize.py` | Create plots |
| `setup.py` | Verify installation |

## ⚡ Quick Commands

```bash
# Fetch weather data
python main.py

# Analyze data (automated)
python analyze.py

# Analyze data (interactive menu)
python analyze.py --interactive

# Create visualizations
python visualize.py

# Check setup
python setup.py
```

## 🔧 Configuration Snippets

### Last 7 Days, Single Station
```python
# In main.py
API_KEY = 'your_api_key'
STATION_IDS = ['KNYNEWYO1127']
START_DATE = datetime.now() - timedelta(days=7)
END_DATE = datetime.now()
UNITS = 'e'
```

### Multiple Stations
```python
STATION_IDS = [
    'KNYNEWYO1127',
    'KNYNEWYO2197',
    'KCASANDI123',
]
```

### Specific Date Range
```python
START_DATE = datetime(2024, 9, 1)
END_DATE = datetime(2024, 9, 30)
```

### Metric Units
```python
UNITS = 'm'  # Celsius, km/h, mm
```

## 📊 Common Parameters

### Temperature
- `temp` - Current temperature
- `tempHigh` - Daily high (in daily summary)
- `tempLow` - Daily low (in daily summary)
- `tempAvg` - Daily average (in daily summary)
- `heatIndex` - Heat index
- `windChill` - Wind chill
- `dewpt` - Dew point

### Wind
- `windSpeed` - Wind speed
- `windGust` - Wind gust
- `winddir` - Wind direction (degrees)

### Precipitation
- `precipRate` - Current precipitation rate
- `precipTotal` - Total precipitation

### Other
- `humidity` - Relative humidity (%)
- `pressure` - Barometric pressure
- `uv` - UV index
- `solarRadiation` - Solar radiation (W/m²)

## 📦 Output Files

```
output/
├── weather_data_all_stations_*.json    # All data combined
├── weather_data_STATIONID_*.json       # Per station
├── current_conditions_*.json           # Current only
├── hourly_history_*.json               # Hourly only
├── daily_summary_*.json                # Daily only
├── STATIONID_data.csv                  # CSV export
└── plots/
    ├── STATIONID_temperature_timeline.png
    ├── STATIONID_multi_parameter.png
    ├── STATIONID_daily_summary.png
    ├── STATIONID_wind_rose.png
    └── comparison_*.png
```

## 🐍 Python Code Snippets

### Load Data
```python
from data_analysis import load_json_file

data = load_json_file('output/hourly_history_*.json')
```

### Calculate Statistics
```python
from data_analysis import calculate_statistics

stats = calculate_statistics(data, 'KNYNEWYO1127', 'temp', 'e')
print(f"Average: {stats['mean']:.1f}°F")
print(f"Range: {stats['min']:.1f} to {stats['max']:.1f}°F")
```

### Compare Stations
```python
from data_analysis import compare_stations

comparison = compare_stations(data, 'temp', 'e')
for station, stats in comparison.items():
    print(f"{station}: {stats['mean']:.1f}°F avg")
```

### Find Extremes
```python
from data_analysis import find_extremes

extremes = find_extremes(data, 'KNYNEWYO1127', 'e')
print(f"Hottest: {extremes['hottest']['value']}°F")
print(f"Coldest: {extremes['coldest']['value']}°F")
```

### Export to CSV
```python
from data_analysis import export_to_csv

export_to_csv(data, 'KNYNEWYO1127', 'my_data.csv', 'e')
```

### Extract Temperature Series
```python
from data_analysis import extract_temperature_series

temps = extract_temperature_series(data, 'KNYNEWYO1127', 'e')
# Returns list of (datetime, temperature) tuples
```

## 🔍 API Endpoints

```python
BASE_URL = "https://api.weather.com/v2/pws"

# Current conditions
GET /observations/current
  ?stationId=KNYNEWYO1127
  &format=json
  &units=e
  &apiKey=YOUR_KEY

# Hourly history (7 days)
GET /observations/hourly/7day
  ?stationId=KNYNEWYO1127
  &format=json
  &units=e
  &apiKey=YOUR_KEY

# Daily summary (7 days)
GET /dailysummary/7day
  ?stationId=KNYNEWYO1127
  &format=json
  &units=e
  &apiKey=YOUR_KEY
```

## 🌐 Important URLs

- **API Keys**: https://www.wunderground.com/member/api-keys
- **Find Stations**: https://www.wunderground.com/wundermap
- **Your Dashboard**: https://www.wunderground.com/dashboard/pws/YOURSTATIONID
- **WU Community**: https://community.wunderground.com/

## 🐛 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| "No module named 'requests'" | `pip install requests` |
| "No observations found" | Check station ID and verify station is active |
| "401 error" | Invalid API key - check at wunderground.com |
| "404 error" | Station ID not found - verify spelling |
| Limited data | API limits: 7 days hourly, some stations don't report all parameters |
| "matplotlib not available" | `pip install matplotlib` |

## 📝 Interactive Analysis Menu

```
1. View summary report for a station
2. Compare all stations  
3. Find extreme values
4. Calculate statistics for a parameter
5. Export station data to CSV
6. Exit
```

## 💡 Pro Tips

1. **Fetch once, analyze many times** - JSON files can be reanalyzed without re-fetching
2. **Use CSV exports** for Excel/Pandas/R
3. **Check station quality** - Not all stations report all parameters
4. **Batch date ranges** - For >7 days hourly, fetch in chunks
5. **Use daily summaries** for longer historical periods
6. **Cache API responses** to avoid rate limits
7. **Check QC status** - Some observations may be flagged

## 🔐 Security Note

```python
# DON'T commit API keys to git
# Create config.py (add to .gitignore)
# config.py
API_KEY = 'your_secret_key'

# main.py
from config import API_KEY
```

## 📚 Learn More

- Full documentation: `COMPLETE_GUIDE.md`
- Basic usage: `README.md`
- Run setup check: `python setup.py`

---

**Quick Start:** Configure `main.py` → Run `python main.py` → Run `python analyze.py` → Done! 🎉