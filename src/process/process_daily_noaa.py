"""
NOAA Daily Data Processor
=========================
Process NOAA daily data to standard format.

Put this file in src/process/ and run:
    python process_daily_noaa.py

Input:  src/data/noaa_asos/daily/417*.csv
Output: src/data/output/noaa_daily/
"""

import pandas as pd
import sys
import argparse
from pathlib import Path

# Simple setup - just import config!
from config_process import NOAA_DAILY_DIR, OUTPUT_DIR
from config import CONVERSIONS


# =============================================================================
# CONFIGURATION
# =============================================================================

STATION_KEYWORDS = {
    'KNYC': ['CENTRAL PARK', 'KNYC'],
    'KJFK': ['JFK', 'JOHN F KENNEDY', 'KJFK'],
    'KLGA': ['LAGUARDIA', 'LGA', 'KLGA'],
}

# Columns to keep (NOAA names -> standard names)
COLUMN_MAP = {
    'DATE': 'time',
    'PRCP': 'precip',           # inches -> mm
    'SNOW': 'snow',             # inches -> mm
    'SNWD': 'snow_depth',       # inches -> mm
    'TMAX': 'temp_max',         # °F -> °C
    'TMIN': 'temp_min',         # °F -> °C
    'TAVG': 'temp',             # °F -> °C (standard temp column)
    'AWND': 'wind_speed',       # mph -> m/s
    'WSF2': 'wind_gust_2min',   # mph -> m/s
    'WSF5': 'wind_gust_5sec',   # mph -> m/s
    'WDF2': 'wind_dir_2min',    # degrees (no conversion)
    'WDF5': 'wind_dir_5sec',    # degrees (no conversion)
}

# Columns to convert
INCH_TO_MM_COLS = ['PRCP', 'SNOW', 'SNWD']
FAHRENHEIT_TO_CELSIUS_COLS = ['TMAX', 'TMIN', 'TAVG']
MPH_TO_MS_COLS = ['AWND', 'WSF2', 'WSF5']


# =============================================================================
# PROCESSING FUNCTIONS
# =============================================================================

def identify_station(row) -> str | None:
    """Identify which target station this row belongs to."""
    name = str(row.get('NAME', '')).upper() if pd.notna(row.get('NAME')) else ''
    station = str(row.get('STATION', '')).upper() if pd.notna(row.get('STATION')) else ''
    
    for code, keywords in STATION_KEYWORDS.items():
        for kw in keywords:
            if kw in name or kw in station:
                return code
    return None


def process_noaa_daily(input_dir: Path, output_dir: Path, action='normal', add_timestamp=False):
    """Process NOAA daily files into per-station CSVs."""
    from datetime import datetime
    
    # Check if output exists and handle action
    if output_dir.exists():
        existing_files = [f for f in output_dir.glob("noaa_daily_*.csv") 
                         if 'metadata' not in f.name.lower()]
        if existing_files:
            if action == 'skip':
                print(f"Output files exist ({len(existing_files)} files). Skipping (action=skip).")
                return
            elif action == 'replace':
                print(f"Output files exist ({len(existing_files)} files). Will overwrite (action=replace).")
            else:
                # Default: create timestamped subfolder
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = output_dir / timestamp
                print(f"Output files exist ({len(existing_files)} files). Saving to timestamped folder: {output_dir}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find 417*.csv files
    files = sorted(input_dir.glob('417*.csv'))
    if not files:
        print(f"Error: No 417*.csv files found in {input_dir}")
        sys.exit(1)
    
    print(f"Found {len(files)} files: {[f.name for f in files]}")
    
    # Read and combine
    dfs = []
    for f in files:
        df = pd.read_csv(f, low_memory=False)
        print(f"  {f.name}: {len(df):,} rows")
        dfs.append(df)
    
    df_all = pd.concat(dfs, ignore_index=True)
    print(f"Combined: {len(df_all):,} rows")
    
    # Identify target stations
    df_all['station_code'] = df_all.apply(identify_station, axis=1)
    df_filtered = df_all[df_all['station_code'].notna()].copy()
    print(f"Filtered to target stations: {len(df_filtered):,} rows")
    
    if len(df_filtered) == 0:
        print("Error: No target stations found")
        sys.exit(1)
    
    # Parse datetime
    df_filtered['DATE'] = pd.to_datetime(df_filtered['DATE'], errors='coerce')
    
    # =========================================================================
    # CONVERT TO STANDARD UNITS
    # =========================================================================
    
    # Convert inches to mm
    for col in INCH_TO_MM_COLS:
        if col in df_filtered.columns:
            df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')
            df_filtered[col] = CONVERSIONS['inches_to_mm'](df_filtered[col])
    print(f"Converted {len(INCH_TO_MM_COLS)} columns from inches to mm")
    
    # Convert °F to °C
    for col in FAHRENHEIT_TO_CELSIUS_COLS:
        if col in df_filtered.columns:
            df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')
            df_filtered[col] = CONVERSIONS['fahrenheit_to_celsius'](df_filtered[col])
    print(f"Converted {len(FAHRENHEIT_TO_CELSIUS_COLS)} columns from °F to °C")
    
    # Convert mph to m/s
    for col in MPH_TO_MS_COLS:
        if col in df_filtered.columns:
            df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')
            df_filtered[col] = CONVERSIONS['mph_to_ms'](df_filtered[col])
    print(f"Converted {len(MPH_TO_MS_COLS)} columns from mph to m/s")
    
    # =========================================================================
    # SELECT AND RENAME COLUMNS
    # =========================================================================
    
    keep_cols = ['DATE', 'station_code'] + [c for c in COLUMN_MAP.keys() if c in df_filtered.columns and c != 'DATE']
    df_out = df_filtered[keep_cols].copy()
    
    # Rename columns
    rename_map = {k: v for k, v in COLUMN_MAP.items() if k in df_out.columns}
    rename_map['station_code'] = 'station'
    df_out = df_out.rename(columns=rename_map)
    
    # Remove duplicates and sort
    df_out = df_out.drop_duplicates(subset=['time', 'station'], keep='first')
    df_out = df_out.sort_values(['station', 'time'])
    
    # =========================================================================
    # SAVE PER-STATION
    # =========================================================================
    
    stations = sorted(df_out['station'].unique())
    for station in stations:
        df_station = df_out[df_out['station'] == station].drop(columns=['station']).set_index('time')
        station_path = output_dir / f'noaa_daily_{station}.csv'
        df_station.to_csv(station_path)
        print(f"Saved: {station_path} ({len(df_station):,} rows)")
    
    print("\n✓ Done!")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    from config_process import DEFAULT_PROCESSING_ACTION_IF_EXISTS
    
    parser = argparse.ArgumentParser(description='Process NOAA daily data')
    parser.add_argument('--action', choices=['replace', 'add', 'skip'], 
                       default=DEFAULT_PROCESSING_ACTION_IF_EXISTS,
                       help='Action if files exist: replace (overwrite), add (timestamp), or skip')
    parser.add_argument('input_dir', nargs='?', type=str, help='Input directory (optional)')
    parser.add_argument('output_dir', nargs='?', type=str, help='Output directory (optional)')
    args = parser.parse_args()
    
    # Handle skip
    if args.action == 'skip':
        print("Skipping processing (action=skip)")
        sys.exit(0)
    
    output_dir = OUTPUT_DIR / "noaa_daily"
    
    if args.input_dir:
        input_dir = Path(args.input_dir)
    else:
        input_dir = NOAA_DAILY_DIR
    
    if args.output_dir:
        output_dir = Path(args.output_dir)
    
    # Check for existing files when running directly (not from notebook)
    if output_dir.exists():
        existing_files = [f for f in output_dir.glob("noaa_daily_*.csv") 
                         if 'metadata' not in f.name.lower()]
        if existing_files and args.action == DEFAULT_PROCESSING_ACTION_IF_EXISTS:
            # If using default action and files exist, prompt user
            print(f"\n⚠ Files exist ({len(existing_files)} files) in {output_dir}")
            while True:
                response = input("  [r]eplace, [a]dd, or [s]kip? (r/a/s): ").strip().lower()
                if response in ['r', 'replace']:
                    args.action = 'replace'
                    break
                elif response in ['a', 'add']:
                    args.action = 'add'
                    break
                elif response in ['s', 'skip']:
                    print("  → Skipping processing")
                    sys.exit(0)
                else:
                    print("  Invalid. Enter 'r', 'a', or 's'.")
    
    print("=" * 60)
    print("NOAA DAILY PROCESSOR")
    print("=" * 60)
    print(f"Input:  {input_dir}")
    print(f"Output: {output_dir}")
    if args.action == 'replace':
        print(f"Action: Overwriting existing files")
    print()
    
    process_noaa_daily(input_dir, output_dir, action=args.action, add_timestamp=False)
