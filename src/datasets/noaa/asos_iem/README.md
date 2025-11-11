# ASOS Data Analysis

Analysis toolkit for Automated Surface Observing Station (ASOS) data from NOAA Mesonet.

## Overview

This project provides tools to process, analyze, and visualize 1-minute ASOS weather observations. Download raw data from NOAA and analyze precipitation, temperature, wind, and other meteorological variables.

## Data Source

ASOS data is provided by the Iowa State University Mesonet:
https://mesonet.agron.iastate.edu/request/asos/1min.phtml

## Downloading ASOS Data

### Step-by-step Instructions

1. Visit: https://mesonet.agron.iastate.edu/request/asos/1min.phtml

2. Select your options:
   - **Station**: Choose one or multiple stations (e.g., KJFK for JFK Airport)
   - **Start Date**: Select date range
   - **End Date**: Select end date
   - **Variables**: Choose parameters (Temperature, Precipitation, Wind, etc.)

3. Available variables include:
   - `tmpf`: Air temperature (Fahrenheit)
   - `dwpf`: Dew point (Fahrenheit)
   - `sknt`: Wind speed (knots)
   - `drct`: Wind direction (degrees)
   - `precip`: Precipitation (inches)
   - `pres1`: Altimeter setting (inches Hg)
   - `vsby`: Visibility (statute miles)

4. Request format:
   - Select "Text" format
   - Request will include `valid_time` timestamp

5. Download file:
   - Save as: `[STATION_ID].txt` (e.g., `KJFK.txt`, `KLGA.txt`)
   - Place in same directory

## Installation

### Requirements
- Python 3.7+
- pandas
- matplotlib
- numpy

### Setup

```bash
pip install -r requirements.txt
```

## Project Structure

```
asos_analysis/
├── asos_processor.py    # Core functions
├── README.md            # This file
├── USAGE_GUIDE.md       # Function reference
├── examples.py          # Working examples
└── requirements.txt     # Dependencies
```

## Quick Start

```python
from asos_processor import read_asos_files, analyze_data, print_analysis, plot_variable

# Load data
data = read_asos_files('./data')

# Analyze
for station_id, df in data.items():
    analysis = analyze_data(df, station_id)
    print_analysis(analysis)

# Plot
plot_variable(data, 'tmpf')
```

## Core Functions

### Data Loading
- `read_asos_files(path)` - Load all .txt files from directory

### Filtering
- `filter_by_date_range(df, start_date, end_date)` - Filter by date range

### Analysis
- `analyze_data(df, station_id)` - Statistical analysis
- `print_analysis(dict)` - Pretty-print results
- `get_summary_table(dataframes)` - Summary statistics

### Visualization
- `plot_variable(data, variable, start_date, end_date, save_path)` - Time-series plot
- `compare_stations(data, variable, start_date, end_date, save_path)` - Multi-station comparison

## Common Variables

| Variable | Description | Units |
|----------|-------------|-------|
| `tmpf` | Temperature | Fahrenheit |
| `dwpf` | Dew point | Fahrenheit |
| `sknt` | Wind speed | Knots |
| `drct` | Wind direction | Degrees (0-360) |
| `precip` | Precipitation | Inches |
| `precip_mm` | Precipitation (converted) | Millimeters |
| `pres1` | Altimeter setting | Inches Hg |
| `vsby` | Visibility | Statute miles |

## Data Format

Downloaded files are standard CSV format with columns:
- `valid_time`: UTC timestamp
- Variable columns (depend on selection)

## Examples

See `examples.py` for complete working examples including:
- Single station analysis
- Date range filtering
- Multi-station comparison
- Variable plotting
- Data export

## Notes

- Timestamps are in UTC
- Precipitation is automatically converted from inches to millimeters
- Missing values are handled gracefully
- Multiple stations can be analyzed simultaneously

## License

ASOS data is provided by NOAA. See https://mesonet.agron.iastate.edu/ for terms of use.
