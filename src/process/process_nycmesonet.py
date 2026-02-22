"""
NYC Mesonet Zip Processor
=========================
Process NYC Mesonet 5-minute data to standard format.

Put this file in src/process/ and run:
    python process_nycmesonet.py

Input:  src/data/Mesonet/*.zip
Output: src/data/output/mesonet/
"""

import pandas as pd
import zipfile
import sys
import argparse
from pathlib import Path
from io import StringIO

# Simple setup - just import config!
from config_process import MESONET_DIR, OUTPUT_DIR
from config import CONVERSIONS


# =============================================================================
# PROCESSING FUNCTIONS
# =============================================================================

def process_zip(zip_path: str, output_dir: Path, action='normal', add_timestamp=False):
    """Read zip of daily CSVs, process to standard format, output per-station CSV."""
    from datetime import datetime
    
    output_dir = Path(output_dir)
    
    # Check if output exists and handle action
    if output_dir.exists():
        existing_files = [f for f in output_dir.glob("mesonet_*.csv") 
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
    
    # Read all CSVs from zip
    print(f"Reading: {zip_path}")
    all_data = []
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        csv_files = sorted([f for f in zf.namelist() if f.endswith('.csv')])
        print(f"Found {len(csv_files)} CSV files")
        
        for i, fname in enumerate(csv_files):
            with zf.open(fname) as f:
                df = pd.read_csv(StringIO(f.read().decode('utf-8')))
                all_data.append(df)
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(csv_files)}...")
    
    # Combine
    print("Concatenating...")
    df_all = pd.concat(all_data, ignore_index=True)
    
    # =========================================================================
    # IDENTIFY RAW UNITS AND COLUMNS
    # =========================================================================
    
    # Identify columns that need unit conversion (from header)
    inch_cols = [c.split(' [')[0].replace(' ', '_') for c in df_all.columns if '[inch]' in c]
    fahrenheit_cols = [c.split(' [')[0].replace(' ', '_') for c in df_all.columns if '[degF]' in c]
    mph_cols = [c.split(' [')[0].replace(' ', '_') for c in df_all.columns if '[mile/hr]' in c]
    
    # Clean column names (remove units)
    df_all.columns = [c.split(' [')[0].replace(' ', '_') for c in df_all.columns]
    
    # =========================================================================
    # CONVERT TO STANDARD UNITS
    # =========================================================================
    
    # Convert inches to mm
    for col in inch_cols:
        if col in df_all.columns:
            df_all[col] = pd.to_numeric(df_all[col], errors='coerce')
            df_all[col] = CONVERSIONS['inches_to_mm'](df_all[col])
    print(f"Converted {len(inch_cols)} columns from inches to mm")
    
    # Convert °F to °C
    for col in fahrenheit_cols:
        if col in df_all.columns:
            df_all[col] = pd.to_numeric(df_all[col], errors='coerce')
            df_all[col] = CONVERSIONS['fahrenheit_to_celsius'](df_all[col])
    print(f"Converted {len(fahrenheit_cols)} columns from °F to °C")
    
    # Convert mph to m/s
    for col in mph_cols:
        if col in df_all.columns:
            df_all[col] = pd.to_numeric(df_all[col], errors='coerce')
            df_all[col] = CONVERSIONS['mph_to_ms'](df_all[col])
    print(f"Converted {len(mph_cols)} columns from mph to m/s")
    
    # =========================================================================
    # RENAME STANDARD COLUMNS
    # =========================================================================
    
    # Map to standard names where applicable
    rename_map = {}
    if 'temp_2m' in df_all.columns:
        rename_map['temp_2m'] = 'temp'
    if 'precip_incremental' in df_all.columns:
        rename_map['precip_incremental'] = 'precip'
    if 'avg_wind_speed_prop' in df_all.columns:
        rename_map['avg_wind_speed_prop'] = 'wind_speed'
    if 'max_wind_speed_prop' in df_all.columns:
        rename_map['max_wind_speed_prop'] = 'wind_gust'
    if 'wind_direction_prop' in df_all.columns:
        rename_map['wind_direction_prop'] = 'wind_dir'
    
    if rename_map:
        df_all = df_all.rename(columns=rename_map)
        print(f"Renamed columns: {rename_map}")
    
    # =========================================================================
    # PARSE TIME AND EXTRACT METADATA
    # =========================================================================
    
    # Parse datetime (strip timezone abbrev like EST)
    df_all['time'] = df_all['time'].str.replace(r'\s+[A-Z]{2,4}$', '', regex=True)
    df_all['time'] = pd.to_datetime(df_all['time'])
    
    # Extract metadata
    meta_cols = ['station', 'latitude', 'longitude', 'elevation']
    df_meta = df_all[meta_cols].drop_duplicates('station').sort_values('station').reset_index(drop=True)
    
    # Save metadata
    meta_path = output_dir / "mesonet_metadata.csv"
    df_meta.to_csv(meta_path, index=False)
    print(f"Saved: {meta_path}")
    
    # =========================================================================
    # SAVE PER-STATION
    # =========================================================================
    
    data_cols = [c for c in df_all.columns if c not in meta_cols]
    
    for station in df_meta['station']:
        df_station = (
            df_all.loc[df_all['station'] == station, data_cols]
            .sort_values('time')
            .drop_duplicates('time')
            .set_index('time')
        )
        
        station_path = output_dir / f"mesonet_{station}.csv"
        df_station.to_csv(station_path)
        print(f"Saved: {station_path} ({len(df_station):,} rows)")
    
    print("\n✓ Done!")


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    from config_process import DEFAULT_PROCESSING_ACTION_IF_EXISTS
    
    parser = argparse.ArgumentParser(description='Process NYC Mesonet data')
    parser.add_argument('--action', choices=['replace', 'add', 'skip'], 
                       default=DEFAULT_PROCESSING_ACTION_IF_EXISTS,
                       help='Action if files exist: replace (overwrite), add (timestamp), or skip')
    parser.add_argument('zip_path', nargs='?', type=str, help='Path to zip file (optional)')
    parser.add_argument('output_dir', nargs='?', type=str, help='Output directory (optional)')
    args = parser.parse_args()
    
    # Handle skip
    if args.action == 'skip':
        print("Skipping processing (action=skip)")
        sys.exit(0)
    
    output_dir = OUTPUT_DIR / "mesonet"
    
    if args.zip_path:
        zip_path = args.zip_path
    else:
        zip_files = list(MESONET_DIR.glob("*.zip"))
        if not zip_files:
            print(f"Error: No .zip file found in {MESONET_DIR}")
            sys.exit(1)
        zip_path = str(zip_files[0])
    
    if args.output_dir:
        output_dir = Path(args.output_dir)
    
    print("=" * 60)
    print("NYC MESONET PROCESSOR")
    print("=" * 60)
    print(f"Input:  {zip_path}")
    print(f"Output: {output_dir}")
    if args.action == 'replace':
        print(f"Action: Overwriting existing files")
    print()
    
    process_zip(zip_path, output_dir, action=args.action, add_timestamp=False)
