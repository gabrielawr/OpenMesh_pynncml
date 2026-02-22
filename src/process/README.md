# Process Folder Overview

The `process/` folder contains scripts that **standardize and unify** raw weather data from multiple sources into a consistent format.

## What It Does (Not)

- ❌ Does NOT fetch or download data
- ❌ Does NOT perform analysis or calculations
- ✅ Works with **already downloaded/raw files**
- ✅ Reformats data into unified standard format
- ✅ Minimal processing (unit conversion only)

## Workflow

```
Raw Data (from different sources)
    ↓
[Process Scripts]
    ↓
Standardized Output Format
```

## Data Sources & Scripts

| Source | Input | Script | Output |
|--------|-------|--------|--------|
| ASOS 1-min | `data/noaa_asos/noaa_asos_1min/raw/*_raw_*.csv` | `process_asos_1min.py` | `output/asos_1min/asos_1min_*.csv` |
| NOAA Daily | `data/noaa_asos/daily/417*.csv` | `process_daily_noaa.py` | `output/noaa_daily/noaa_daily_*.csv` |
| NYC Mesonet | `data/Mesonet/*.zip` | `process_nycmesonet.py` | `output/mesonet/mesonet_*.csv` |

## What Each Script Does

### `process_asos_1min.py`
- Loads raw ASOS CSV files (per station)
- Converts units: °F → °C, knots → m/s, inches → mm
- Parses timestamps to UTC
- Removes duplicates and sorts by time
- Saves per-station CSV with time index

### `process_daily_noaa.py`
- Reads NOAA daily data files (417*.csv)
- Identifies target stations (KNYC, KJFK, KLGA)
- Converts units: °F → °C, mph → m/s, inches → mm
- Saves per-station CSV with time index

### `process_nycmesonet.py`
- Extracts and reads CSVs from zip archive
- Auto-detects column units from headers (`[degF]`, `[inch]`, `[mile/hr]`)
- Converts all to metric
- Saves per-station CSVs + separate metadata file

## Standard Output Format

All outputs follow the same structure:
- **Index**: `time` (datetime, UTC)
- **Columns**: `temp`, `precip`, `wind_speed`, `wind_dir`, `dewpoint`, etc.
- **Units**: Metric (°C, mm, m/s)
- **Format**: CSV with time as index

Example output row:
```
time,temp,precip,wind_speed,wind_dir
2023-08-01 00:00:00,22.5,0.0,3.2,180
```

## Configuration

**Default settings** in `config_process.py`:
- `DEFAULT_PROCESSING_ACTION_IF_EXISTS = 'add'`

**Processing modes:**
- `--action add` (default): Save with timestamp, keep history
- `--action replace`: Overwrite existing files
- `--action skip`: Don't process

## Usage

```bash
# Process all data with default action (add timestamp)
python process_asos_1min.py
python process_daily_noaa.py
python process_nycmesonet.py

# Overwrite existing output
python process_asos_1min.py --action replace

# Skip processing
python process_asos_1min.py --action skip
```

## Key Features

✅ **Minimal Processing**: Only unit conversions, no analysis  
✅ **Unified Format**: All sources output same schema  
✅ **Per-Station Output**: One file per weather station  
✅ **Time Indexed**: Easy to merge/align different sources  
✅ **Lossless**: No data dropped (except exact duplicates)  
✅ **Configurable**: Can override action and paths via arguments