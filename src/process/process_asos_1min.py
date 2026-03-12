"""
ASOS 1-Minute Data Processor
============================
Process raw ASOS 1-minute data to standard format.

Put this file in src/process/ and run:
    python process_asos_1min.py

Input:  src/data/noaa_asos/noaa_asos_1min/raw/*_raw_*.csv
Output: src/data/output/asos_1min/
"""

import pandas as pd
import sys
import argparse
from pathlib import Path

# Simple setup - just import config!
from config_process import ASOS_1MIN_DIR, OUTPUT_DIR
from config import ASOS_COLUMN_MAP, ASOS_CONVERSIONS, CONVERSIONS, map_precip_type


# =============================================================================
# PROCESSING FUNCTIONS
# =============================================================================

def load_raw_data(raw_dir: Path, station_ids: list = None, verbose: bool = True):
    """Load raw ASOS CSV files. Merges multiple files per station (deduplicates by time)."""
    if verbose:
        print(f"Loading raw data from: {raw_dir}")
    
    raw_data = {}
    files = sorted(raw_dir.glob("*_raw_*.csv"))
    
    if not files:
        print(f"  ⚠ No raw files found in {raw_dir}")
        return {}
    
    for fpath in files:
        station_id = fpath.stem.split('_raw_')[0]
        
        if station_ids and station_id not in station_ids:
            continue
        
        df = pd.read_csv(fpath)
        
        if verbose:
            print(f"  ✓ {fpath.name} ({len(df):,} rows)")
        
        if station_id in raw_data:
            raw_data[station_id] = pd.concat([raw_data[station_id], df], ignore_index=True)
        else:
            raw_data[station_id] = df
    
    time_col = 'valid(UTC)' if files and 'valid(UTC)' in raw_data.get(list(raw_data.keys())[0] if raw_data else '', pd.DataFrame()).columns else 'valid'
    for station_id in raw_data:
        df = raw_data[station_id]
        if time_col in df.columns:
            df[time_col] = pd.to_datetime(df[time_col])
            df = df.drop_duplicates(subset=[time_col]).sort_values(time_col).reset_index(drop=True)
            raw_data[station_id] = df
            if verbose:
                print(f"  → {station_id} merged: {len(df):,} unique rows")
    
    if verbose:
        print(f"✓ Loaded {len(raw_data)} stations\n")
    
    return raw_data


def process_station(df: pd.DataFrame, station_id: str) -> pd.DataFrame:
    """
    Process a single station's raw data to standard format.
    
    Conversions applied:
    - Temperature: °F -> °C
    - Wind speed: knots -> m/s
    - Precipitation: inches -> mm
    - Time: parsed to datetime (UTC)
    - Precip type: mapped to standard categories
    """
    out = pd.DataFrame()
    
    # Time (UTC)
    time_col = 'valid(UTC)' if 'valid(UTC)' in df.columns else 'valid'
    out['time'] = pd.to_datetime(df[time_col])
    
    # Temperature: °F -> °C
    if 'tmpf' in df.columns:
        out['temp'] = pd.to_numeric(df['tmpf'], errors='coerce')
        out['temp'] = CONVERSIONS['fahrenheit_to_celsius'](out['temp'])
    
    # Dewpoint: °F -> °C
    if 'dwpf' in df.columns:
        out['dewpoint'] = pd.to_numeric(df['dwpf'], errors='coerce')
        out['dewpoint'] = CONVERSIONS['fahrenheit_to_celsius'](out['dewpoint'])
    
    # Wind speed: knots -> m/s
    if 'sknt' in df.columns:
        out['wind_speed'] = pd.to_numeric(df['sknt'], errors='coerce')
        out['wind_speed'] = CONVERSIONS['knots_to_ms'](out['wind_speed'])
    
    # Wind gust: knots -> m/s
    if 'gust_sknt' in df.columns:
        out['wind_gust'] = pd.to_numeric(df['gust_sknt'], errors='coerce')
        out['wind_gust'] = CONVERSIONS['knots_to_ms'](out['wind_gust'])
    
    # Wind direction (no conversion needed)
    if 'drct' in df.columns:
        out['wind_dir'] = pd.to_numeric(df['drct'], errors='coerce')
    
    # Wind gust direction (no conversion needed)
    if 'gust_drct' in df.columns:
        out['wind_gust_dir'] = pd.to_numeric(df['gust_drct'], errors='coerce')
    
    # Precipitation: inches -> mm
    if 'precip' in df.columns:
        out['precip'] = pd.to_numeric(df['precip'], errors='coerce')
        out['precip'] = CONVERSIONS['inches_to_mm'](out['precip'])
    
    # Precipitation type
    if 'ptype' in df.columns:
        out['precip_type'] = df['ptype'].apply(map_precip_type)
    
    # Sort by time and remove duplicates
    out = out.sort_values('time').drop_duplicates('time').reset_index(drop=True)
    
    return out


def process_all_stations(raw_data: dict, verbose: bool = True) -> dict:
    """Process all stations to standard format."""
    if verbose:
        print("Processing to standard format...")
    
    processed = {}
    for station_id, df in raw_data.items():
        processed[station_id] = process_station(df, station_id)
        if verbose:
            n = len(processed[station_id])
            precip_sum = processed[station_id]['precip'].sum()
            print(f"  {station_id}: {n:,} rows, total precip = {precip_sum:.1f} mm")
    
    if verbose:
        print("✓ Processing complete\n")
    
    return processed


def save_processed(processed_data: dict, output_dir: Path, add_timestamp: bool = False, verbose: bool = True):
    """Save processed data to CSV files."""
    from datetime import datetime
    
    # Check if files already exist
    if output_dir.exists():
        existing_files = [f for f in output_dir.glob("asos_1min_*.csv") 
                         if 'metadata' not in f.name.lower()]
        if existing_files:
            # Create timestamped subfolder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = output_dir / timestamp
            if verbose:
                print(f"Files exist in output directory. Saving to timestamped folder: {output_dir}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if verbose:
        print(f"Saving to: {output_dir}")
    
    for station_id, df in processed_data.items():
        out_path = output_dir / f"asos_1min_{station_id}.csv"
        df.set_index('time').to_csv(out_path)
        if verbose:
            print(f"  ✓ {out_path.name} ({len(df):,} rows)")
    
    if verbose:
        print("✓ Save complete\n")


def check_format(processed_data: dict, verbose: bool = True) -> bool:
    """Check if processed data matches standard format."""
    required_cols = ['time', 'temp', 'dewpoint', 'wind_speed', 'wind_dir', 'precip']
    
    if verbose:
        print("Checking format...")
    
    all_valid = True
    for station_id, df in processed_data.items():
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            print(f"  ✗ {station_id}: missing columns {missing}")
            all_valid = False
        else:
            if verbose:
                print(f"  ✓ {station_id}: OK")
    
    if verbose:
        status = "✓ All valid" if all_valid else "✗ Format issues found"
        print(f"{status}\n")
    
    return all_valid


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main processing pipeline."""
    from config_process import DEFAULT_PROCESSING_ACTION_IF_EXISTS
    
    parser = argparse.ArgumentParser(description='Process ASOS 1-minute data')
    parser.add_argument('--action', choices=['replace', 'add', 'skip'], 
                       default=DEFAULT_PROCESSING_ACTION_IF_EXISTS,
                       help='Action if files exist: replace (overwrite), add (timestamp), or skip')
    args = parser.parse_args()
    
    # Handle skip
    if args.action == 'skip':
        print("Skipping processing (action=skip)")
        return
    
    raw_dir = ASOS_1MIN_DIR / "raw"
    output_dir = OUTPUT_DIR / "asos_1min"
    
    print("=" * 60)
    print("ASOS 1-MINUTE DATA PROCESSOR")
    print("=" * 60)
    print(f"Input:  {raw_dir}")
    print(f"Output: {output_dir}")
    if args.action == 'replace':
        print(f"Action: Overwriting existing files")
    print()
    
    raw_data = load_raw_data(raw_dir)
    if not raw_data:
        print("No data to process.")
        return
    
    processed_data = process_all_stations(raw_data)
    check_format(processed_data)
    save_processed(processed_data, output_dir, add_timestamp=False)
    
    print("=" * 60)
    print("✓ DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
