"""
NOAA ASOS Data Processing Functions
====================================

Fetch and process Automated Surface Observing System (ASOS) data from 
Iowa Environmental Mesonet (IEM) API.

ASOS Precipitation Measurement (from IEM/NOAA):
------------------------------------------------
- p01i = "One hour precipitation from observation time to previous hourly reset"
- Reset occurs at ~51 minutes past each hour (site-dependent)
- In 5-min data, p01i is a RUNNING TOTAL that repeats until next reset
- To get true hourly precip: use ONLY the :51 minute observations
- Values reported in INCHES (converted to mm here)

References:
-----------
- IEM: https://mesonet.agron.iastate.edu/request/download.phtml
- ASOS User's Guide: https://www.weather.gov/asos/

Author: OpenMesh Project
Date: 2025-11-16
"""

import pandas as pd
import numpy as np
import requests
from io import StringIO
from datetime import datetime
from pathlib import Path


# ============================================================================
# STATION CONFIGURATION
# ============================================================================

STATIONS = {
    'KJFK': {
        'name': 'JFK Airport',
        'location': 'Queens, NY',
        'color': '#1f77b4',
        'linestyle': '-'
    },
    'KLGA': {
        'name': 'LaGuardia Airport',
        'location': 'Queens, NY',
        'color': '#ff7f0e',
        'linestyle': '--'
    },
    'KNYC': {
        'name': 'Central Park',
        'location': 'Manhattan, NY',
        'color': '#2ca02c',
        'linestyle': ':'
    }
}


# ============================================================================
# DATA FETCHING
# ============================================================================

def fetch_station_from_iem(station_id, start_date, end_date, resolution='5min', verbose=True):
    """
    Fetch ASOS data from Iowa Environmental Mesonet (IEM) API
    
    Returns DataFrame with 33 columns including:
    - tmpf, dwpf, relh (temperature, dewpoint, humidity)
    - drct, sknt, gust (wind)
    - p01i (precipitation)
    - alti, mslp (pressure)
    - vsby (visibility)
    """
    BASE_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
    
    params = {
        'station': station_id,
        'data': 'all',
        'year1': start_date.year,
        'month1': start_date.month,
        'day1': start_date.day,
        'year2': end_date.year,
        'month2': end_date.month,
        'day2': end_date.day,
        'tz': 'Etc/UTC',
        'format': 'comma',
        'latlon': 'yes',
        'elev': 'yes',
        'missing': 'M',
        'trace': 'T',
    }
    
    if verbose:
        res_str = '5-min' if resolution == '5min' else 'hourly'
        print(f"Fetching {station_id} ({res_str})... ", end='', flush=True)
    
    try:
        response = requests.get(BASE_URL, params=params, timeout=120)
        
        if response.status_code == 200 and len(response.text) > 100:
            df = pd.read_csv(StringIO(response.text), comment='#')
            if verbose:
                print(f"✓ {len(df):,} records, {len(df.columns)} columns")
            return df
        else:
            if verbose:
                print(f"✗ No data")
            return None
            
    except Exception as e:
        if verbose:
            print(f"✗ Error: {e}")
        return None


def fetch_all_stations(station_ids, start_date, end_date, resolution='5min', verbose=True):
    """Fetch data for multiple stations"""
    if verbose:
        print(f"\n{'='*60}")
        print(f"FETCHING DATA ({resolution})")
        print(f"{'='*60}\n")
    
    raw_data = {}
    for station_id in station_ids:
        df = fetch_station_from_iem(station_id, start_date, end_date, resolution, verbose)
        if df is not None and len(df) > 0:
            raw_data[station_id] = df
    
    if verbose:
        print(f"\n✓ Fetched {len(raw_data)}/{len(station_ids)} stations\n")
    
    return raw_data


# ============================================================================
# DATA CONVERSION
# ============================================================================

def convert_to_standard_format(df, station_id):
    """Convert IEM format to metric units"""
    df = df.copy()
    standard = pd.DataFrame()
    
    standard['datetime'] = pd.to_datetime(df['valid'])
    standard['station_id'] = station_id
    
    # Temperature: F to C
    if 'tmpf' in df.columns:
        standard['temp_c'] = pd.to_numeric(df['tmpf'], errors='coerce')
        standard['temp_c'] = (standard['temp_c'] - 32) * 5/9
    
    # Dewpoint: F to C
    if 'dwpf' in df.columns:
        standard['dewpoint_c'] = pd.to_numeric(df['dwpf'], errors='coerce')
        standard['dewpoint_c'] = (standard['dewpoint_c'] - 32) * 5/9
    
    # Wind: knots to m/s
    if 'sknt' in df.columns:
        standard['wind_speed_ms'] = pd.to_numeric(df['sknt'], errors='coerce') * 0.51444
    
    if 'drct' in df.columns:
        standard['wind_dir_deg'] = pd.to_numeric(df['drct'], errors='coerce')
    
    # Pressure: inHg to hPa
    if 'alti' in df.columns:
        standard['pressure_hpa'] = pd.to_numeric(df['alti'], errors='coerce') * 33.8639
    
    # Visibility
    if 'vsby' in df.columns:
        standard['visibility_mi'] = pd.to_numeric(df['vsby'], errors='coerce')
    
    # Precipitation: inches to mm
    if 'p01i' in df.columns:
        precip = df['p01i'].replace('T', '0.001')
        standard['precip_mm'] = pd.to_numeric(precip, errors='coerce') * 25.4
    
    # Wind gust: knots to m/s
    if 'gust' in df.columns:
        standard['wind_gust_ms'] = pd.to_numeric(df['gust'], errors='coerce') * 0.51444
    
    # Humidity
    if 'relh' in df.columns:
        standard['humidity_pct'] = pd.to_numeric(df['relh'], errors='coerce')
    
    return standard.sort_values('datetime').reset_index(drop=True)


def process_all_stations(raw_data, verbose=True):
    """Convert all stations to standard format"""
    if verbose:
        print("Processing data...\n")
    
    processed_data = {}
    for station_id, df_raw in raw_data.items():
        df_std = convert_to_standard_format(df_raw, station_id)
        processed_data[station_id] = df_std
        
        if verbose:
            station_name = STATIONS.get(station_id, {}).get('name', station_id)
            print(f"{station_id} - {station_name}:")
            print(f"  Records: {len(df_std):,}")
            
            if 'precip_mm' in df_std.columns:
                precip_valid = df_std['precip_mm'].notna().sum()
                precip_rain = (df_std['precip_mm'] > 0).sum()
                print(f"  Precipitation: {precip_valid:,} valid, {precip_rain:,} with rain")
            print()
    
    if verbose:
        print("✓ Processing complete\n")
    
    return processed_data


# ============================================================================
# PRECIPITATION ANALYSIS
# ============================================================================

def compute_precip_increments(processed_data):
    """
    Compute TRUE 5-minute precipitation increments.
    
    ASOS p01i is a running hourly total that resets at ~:51.
    To get actual rainfall per 5-min interval:
    - Compute diff between consecutive observations
    - When diff < 0, it means hourly reset occurred → use the new value as-is
    
    Parameters
    ----------
    processed_data : dict
        Dictionary of processed DataFrames {station_id: df}
        
    Returns
    -------
    dict
        Same structure with 'precip_mm' replaced by true 5-min increments
    """
    result = {}
    
    for station_id, df in processed_data.items():
        df_out = df.copy()
        df_out['datetime'] = pd.to_datetime(df_out['datetime'])
        df_out = df_out.sort_values('datetime').reset_index(drop=True)
        
        if 'precip_mm' in df_out.columns:
            # Compute difference between consecutive readings
            precip_raw = df_out['precip_mm'].fillna(0)
            precip_diff = precip_raw.diff()
            
            # First row: use raw value
            precip_diff.iloc[0] = precip_raw.iloc[0]
            
            # Negative diff = hourly reset occurred → use raw value (new hour's accumulation)
            reset_mask = precip_diff < 0
            precip_diff[reset_mask] = precip_raw[reset_mask]
            
            df_out['precip_mm'] = precip_diff
        
        result[station_id] = df_out
    
    return result


def compute_accumulated_rainfall(df, start_date=None, end_date=None):
    """
    Compute cumulative precipitation from 5-min increment data.
    
    This version works with increment data (where precip_mm is per 5-minute interval).
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with datetime and precip_mm columns (increments, not running totals)
    start_date : datetime, optional
        Start date for filtering
    end_date : datetime, optional
        End date for filtering
        
    Returns
    -------
    pd.DataFrame
        DataFrame with datetime, precip_mm, and accumulated_mm columns
    """
    df_accum = df[['datetime', 'precip_mm']].copy()
    df_accum['datetime'] = pd.to_datetime(df_accum['datetime'])
    
    # Filter date range
    if start_date:
        df_accum = df_accum[df_accum['datetime'] >= pd.to_datetime(start_date)]
    if end_date:
        df_accum = df_accum[df_accum['datetime'] <= pd.to_datetime(end_date)]
    
    df_accum = df_accum.copy()
    df_accum['precip_mm'] = df_accum['precip_mm'].fillna(0)
    df_accum['accumulated_mm'] = df_accum['precip_mm'].cumsum()
    
    return df_accum.reset_index(drop=True)


def compute_accumulated_rainfall_legacy(df, resolution='5min'):
    """
    Compute cumulative precipitation (legacy method using :51 minute observations).
    
    For 5-minute data: p01i represents "precipitation in the past hour" and is reported
    at each 5-minute observation. The same hour's precipitation value repeats multiple times.
    We use only the :51 minute observations (full hourly reports) to avoid double-counting.
    
    For hourly data: p01i is already per-hour precipitation, so we can sum directly.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with datetime and precip_mm columns (running totals from raw data)
    resolution : str
        '5min' or 'hourly'
        
    Returns
    -------
    pd.DataFrame
        DataFrame with datetime, precip_mm, and accumulated_mm columns
    """
    df_accum = df[['datetime', 'precip_mm']].copy()
    df_accum['datetime'] = pd.to_datetime(df_accum['datetime'])
    
    if resolution == '5min':
        # Use only :51 minute observations (full hourly reports)
        # These represent the precipitation that fell in the complete hour ending at :51
        df_accum['minute'] = df_accum['datetime'].dt.minute
        df_hourly = df_accum[df_accum['minute'] == 51].copy()
        df_hourly = df_hourly[['datetime', 'precip_mm']].copy()
        df_hourly['precip_mm'] = df_hourly['precip_mm'].fillna(0)
        
        # Compute cumulative sum (values are per-hour, not cumulative)
        df_hourly['accumulated_mm'] = df_hourly['precip_mm'].cumsum()
        
        return df_hourly[['datetime', 'precip_mm', 'accumulated_mm']]
    else:
        # For hourly data, p01i is already per-hour precipitation
        df_accum = df_accum.set_index('datetime')
        df_accum['precip_mm'] = df_accum['precip_mm'].fillna(0)
        df_accum['accumulated_mm'] = df_accum['precip_mm'].cumsum()
        return df_accum.reset_index()[['datetime', 'precip_mm', 'accumulated_mm']]


def compute_accumulated_for_all_stations(processed_data, start_date=None, end_date=None, resolution=None):
    """
    Compute accumulated rainfall for all stations.
    
    Parameters
    ----------
    processed_data : dict
        Dictionary of processed DataFrames {station_id: df}
        If data has been processed with compute_precip_increments, use start_date/end_date
        Otherwise, use resolution for legacy method
    start_date : datetime, optional
        Start date for filtering (used with increment data)
    end_date : datetime, optional
        End date for filtering (used with increment data)
    resolution : str, optional
        Resolution for legacy method ('5min' or 'hourly')
        
    Returns
    -------
    dict
        Dictionary of accumulated rainfall DataFrames {station_id: df}
    """
    accumulated_data = {}
    for station_id, df in processed_data.items():
        if 'precip_mm' in df.columns:
            if resolution is not None:
                # Legacy method: use :51 minute observations
                accumulated_data[station_id] = compute_accumulated_rainfall_legacy(df, resolution=resolution)
            else:
                # New method: use increment data
                accumulated_data[station_id] = compute_accumulated_rainfall(df, start_date, end_date)
    return accumulated_data


# ============================================================================
# FILE I/O
# ============================================================================

def save_processed_data(processed_data, output_dir, start_date, end_date, resolution='5min'):
    """Save processed data to CSV"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\nSaving data...")
    
    # Individual files
    for station_id, df in processed_data.items():
        filename = f"{station_id}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{resolution}.csv"
        df.to_csv(output_dir / filename, index=False)
        print(f"  ✓ {filename}")
    
    # Combined file
    combined = pd.concat(processed_data.values(), ignore_index=True)
    combined = combined.sort_values(['station_id', 'datetime']).reset_index(drop=True)
    combined_filename = f"ALL_STATIONS_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{resolution}.csv"
    combined.to_csv(output_dir / combined_filename, index=False)
    print(f"  ✓ {combined_filename}")
    
    print(f"\n✓ Saved to: {output_dir}\n")
