"""
ASOS Data Processing Functions

Contains stable functions for processing and comparing ASOS and Snow data.
Focus on precipitation (PRCP) comparison and analysis.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import Counter


# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

STATION_CODES = {
    'KNYC': 'Central Park',
    'KJFK': 'JFK Airport',
    'KLGA': 'LaGuardia Airport'
}


# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

def load_asos_5min_data(station_id, data_dir):
    """
    Load all ASOS 5-minute CSV files for a station and combine them.
    
    Parameters:
    -----------
    station_id : str
        Station code (e.g., 'KJFK', 'KNYC', 'KLGA')
    data_dir : Path
        Directory containing ASOS CSV files
        
    Returns:
    --------
    pd.DataFrame
        Combined dataframe with all 5-minute data for the station
    """
    # Find all CSV files for this station
    station_files = list(data_dir.glob(f'{station_id}_*.csv'))
    
    if len(station_files) == 0:
        print(f"⚠ No files found for {station_id}")
        return None
    
    print(f"\nLoading {station_id}:")
    print(f"  Found {len(station_files)} file(s)")
    
    # Load and combine all files
    dfs = []
    for filepath in sorted(station_files):
        try:
            df = pd.read_csv(filepath, low_memory=False)
            print(f"    {filepath.name}: {len(df):,} rows")
            dfs.append(df)
        except Exception as e:
            print(f"    ⚠ Error reading {filepath.name}: {e}")
    
    if len(dfs) == 0:
        return None
    
    # Combine all dataframes
    df_combined = pd.concat(dfs, ignore_index=True)
    
    # Convert datetime to datetime type
    if 'datetime' in df_combined.columns:
        df_combined['datetime'] = pd.to_datetime(df_combined['datetime'], errors='coerce')
        df_combined = df_combined.sort_values('datetime').reset_index(drop=True)
    
    print(f"  ✓ Combined: {len(df_combined):,} total rows")
    print(f"  Date range: {df_combined['datetime'].min()} to {df_combined['datetime'].max()}")
    
    return df_combined


def load_snow_daily_data(snow_data_dir):
    """
    Load processed snow daily data (contains PRCP/precipitation column).
    
    Parameters:
    -----------
    snow_data_dir : Path
        Directory containing snow_data_processed.csv
        
    Returns:
    --------
    pd.DataFrame
        Snow daily data with PRCP (precipitation) column
    """
    snow_file = snow_data_dir / 'snow_data_processed.csv'
    
    if not snow_file.exists():
        print(f"⚠ Snow data file not found: {snow_file}")
        return None
    
    df_snow = pd.read_csv(snow_file)
    df_snow['DATE'] = pd.to_datetime(df_snow['DATE'])
    
    print(f"\n✓ Loaded snow data: {len(df_snow):,} rows")
    print(f"  Date range: {df_snow['DATE'].min().date()} to {df_snow['DATE'].max().date()}")
    print(f"  Stations: {', '.join(sorted(df_snow['station_code'].unique()))}")
    
    # Highlight PRCP column
    if 'PRCP' in df_snow.columns:
        prcp_days = df_snow[df_snow['PRCP'] > 0]
        print(f"  ✓ Contains PRCP (precipitation): {len(prcp_days):,} days with rain")
        print(f"    Total PRCP: {df_snow['PRCP'].sum():.2f} mm across all stations")
    
    return df_snow


# ============================================================================
# DATA PROCESSING FUNCTIONS
# ============================================================================

def aggregate_asos_5min_to_daily_prcp(df_5min, station_id):
    """
    Aggregate ASOS 5-minute precipitation data to daily totals.
    
    **Precipitation**: Sums `precip_mm` to get daily totals (renamed to PRCP).
    This daily PRCP will be compared with Snow data PRCP.
    
    Parameters:
    -----------
    df_5min : pd.DataFrame
        5-minute ASOS data
    station_id : str
        Station code
        
    Returns:
    --------
    pd.DataFrame
        Daily aggregated precipitation data with columns: DATE, station_code, PRCP
    """
    if df_5min is None or len(df_5min) == 0:
        return None
    
    if 'precip_mm' not in df_5min.columns:
        print(f"⚠ 'precip_mm' column not found for {station_id}")
        return None
    
    # Create date column (remove time, keep date only)
    df_5min = df_5min.copy()
    df_5min['DATE'] = pd.to_datetime(df_5min['datetime']).dt.date
    df_5min['DATE'] = pd.to_datetime(df_5min['DATE'])
    
    # Aggregate precipitation to daily (sum)
    df_daily = df_5min.groupby('DATE')['precip_mm'].sum().reset_index()
    df_daily = df_daily.rename(columns={'precip_mm': 'PRCP'})
    
    # Add station code
    df_daily['station_code'] = station_id
    
    # Reorder columns
    df_daily = df_daily[['DATE', 'station_code', 'PRCP']]
    
    return df_daily


def process_prcp_data_comparison(asos_5min_data, df_snow_daily, start_date=None, end_date=None):
    """
    Process and compare PRCP (precipitation) data from ASOS 5-minute and Snow daily sources.
    
    **Comparison Logic:**
    - ASOS: Sum all 5-minute `precip_mm` values to get daily total
    - Snow: Use daily `PRCP` value directly
    - **Expected:** Daily PRCP totals should match (+- measurement differences) 
      since both measure the same thing (precipitation)
    
    Creates summary dataframes for comparison:
    1. Daily comparison: ASOS daily (sum of 5-min) vs Snow daily PRCP
    2. Summary statistics: Agreement metrics between sources
    
    Parameters:
    -----------
    asos_5min_data : dict
        Dictionary of 5-minute ASOS data by station {station_id: df}
    df_snow_daily : pd.DataFrame
        Daily snow data with PRCP column (contains precipitation measurements)
    start_date : str or datetime, optional
        Start date for filtering
    end_date : str or datetime, optional
        End date for filtering
        
    Returns:
    --------
    dict
        Dictionary containing:
        - 'daily_comparison': DataFrame with DATE, station_code, ASOS_PRCP, Snow_PRCP, Difference
        - 'summary': DataFrame with summary statistics per station (agreement metrics)
    """
    # Convert dates
    if start_date:
        start_date = pd.to_datetime(start_date)
    if end_date:
        end_date = pd.to_datetime(end_date)
    
    # Aggregate ASOS 5-minute to daily
    asos_daily_list = []
    for station_id, df_5min in asos_5min_data.items():
        df_daily = aggregate_asos_5min_to_daily_prcp(df_5min, station_id)
        if df_daily is not None:
            # Filter by date range
            if start_date:
                df_daily = df_daily[df_daily['DATE'] >= start_date]
            if end_date:
                df_daily = df_daily[df_daily['DATE'] <= end_date]
            asos_daily_list.append(df_daily)
    
    if len(asos_daily_list) == 0:
        print("⚠ No ASOS daily data processed")
        return None
    
    # Combine ASOS daily data
    df_asos_daily = pd.concat(asos_daily_list, ignore_index=True)
    
    # Prepare Snow data
    df_snow = df_snow_daily.copy()
    if start_date:
        df_snow = df_snow[df_snow['DATE'] >= start_date]
    if end_date:
        df_snow = df_snow[df_snow['DATE'] <= end_date]
    
    # Merge ASOS and Snow data on DATE and station_code
    df_comparison = pd.merge(
        df_asos_daily[['DATE', 'station_code', 'PRCP']],
        df_snow[['DATE', 'station_code', 'PRCP']],
        on=['DATE', 'station_code'],
        how='outer',
        suffixes=('_ASOS', '_Snow')
    )
    
    # Rename columns
    df_comparison = df_comparison.rename(columns={
        'PRCP_ASOS': 'ASOS_PRCP',
        'PRCP_Snow': 'Snow_PRCP'
    })
    
    # Calculate difference
    df_comparison['Difference'] = df_comparison['ASOS_PRCP'] - df_comparison['Snow_PRCP']
    df_comparison['Abs_Difference'] = df_comparison['Difference'].abs()
    
    # Sort by date
    df_comparison = df_comparison.sort_values(['station_code', 'DATE']).reset_index(drop=True)
    
    # Create summary statistics
    summary_list = []
    for station_id in df_comparison['station_code'].unique():
        df_station = df_comparison[df_comparison['station_code'] == station_id]
        
        # Get overlapping dates (where both have data)
        df_overlap = df_station[df_station['ASOS_PRCP'].notna() & df_station['Snow_PRCP'].notna()]
        
        summary_list.append({
            'station_code': station_id,
            'Total_Days_ASOS': df_station['ASOS_PRCP'].notna().sum(),
            'Total_Days_Snow': df_station['Snow_PRCP'].notna().sum(),
            'Overlapping_Days': len(df_overlap),
            'ASOS_Total_Prcp': df_station['ASOS_PRCP'].sum(),
            'Snow_Total_Prcp': df_station['Snow_PRCP'].sum(),
            'ASOS_Mean_Daily': df_station['ASOS_PRCP'].mean(),
            'Snow_Mean_Daily': df_station['Snow_PRCP'].mean(),
            'Mean_Difference': df_overlap['Difference'].mean() if len(df_overlap) > 0 else np.nan,
            'RMSE': np.sqrt((df_overlap['Difference']**2).mean()) if len(df_overlap) > 0 else np.nan,
            'Correlation': df_overlap['ASOS_PRCP'].corr(df_overlap['Snow_PRCP']) if len(df_overlap) > 0 else np.nan
        })
    
    df_summary = pd.DataFrame(summary_list)
    
    return {
        'daily_comparison': df_comparison,
        'summary': df_summary
    }


# ============================================================================
# COMPARISON FUNCTIONS
# ============================================================================

def compare_prcp_daily_vs_5min(comparison_dict, station_id=None):
    """
    Get PRCP comparison data: ASOS daily sum (from 5-min) vs Snow daily PRCP.
    
    **Note:** Both should measure the same thing (precipitation), so values should match.
    
    Parameters:
    -----------
    comparison_dict : dict
        Output from process_prcp_data_comparison()
    station_id : str, optional
        Specific station to analyze. If None, returns all stations.
        
    Returns:
    --------
    pd.DataFrame
        Comparison data for days with both ASOS and Snow PRCP data
        Columns: DATE, station_code, ASOS_PRCP, Snow_PRCP, Difference
    """
    df_comparison = comparison_dict['daily_comparison']
    
    if station_id:
        df_comparison = df_comparison[df_comparison['station_code'] == station_id]
    
    # Filter to days with data from both sources
    df_both = df_comparison[
        df_comparison['ASOS_PRCP'].notna() & 
        df_comparison['Snow_PRCP'].notna()
    ].copy()
    
    return df_both


# ============================================================================
# PLOTTING FUNCTIONS
# ============================================================================

def plot_accumulated_prcp(comparison_dict, start_date=None, end_date=None, 
                         stations=None, figsize=(16, 10)):
    """
    Plot accumulated precipitation: ASOS (5-min sum) vs Snow Daily PRCP.
    
    **Expected Result:** Lines should track closely since both measure precipitation.
    Differences may indicate:
    - Measurement timing differences
    - Sensor calibration differences
    - Missing data in one source
    
    Parameters:
    -----------
    comparison_dict : dict
        Output from process_prcp_data_comparison()
    start_date : str or datetime, optional
        Start date for plotting
    end_date : str or datetime, optional
        End date for plotting
    stations : list, optional
        List of station codes. If None, plots all stations.
    figsize : tuple, optional
        Figure size (width, height)
        
    Returns:
    --------
    fig, axes : matplotlib figure and axes objects
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    
    df_comparison = comparison_dict['daily_comparison'].copy()
    
    # Filter by date range
    if start_date:
        start_date = pd.to_datetime(start_date)
        df_comparison = df_comparison[df_comparison['DATE'] >= start_date]
    if end_date:
        end_date = pd.to_datetime(end_date)
        df_comparison = df_comparison[df_comparison['DATE'] <= end_date]
    
    # Filter by stations
    if stations:
        df_comparison = df_comparison[df_comparison['station_code'].isin(stations)]
    
    # Get unique stations
    unique_stations = sorted(df_comparison['station_code'].unique())
    
    if len(unique_stations) == 0:
        print("⚠ No data to plot")
        return None, None
    
    # Create figure
    fig, axes = plt.subplots(len(unique_stations), 1, figsize=figsize)
    if len(unique_stations) == 1:
        axes = [axes]
    
    for idx, station_id in enumerate(unique_stations):
        ax = axes[idx]
        df_station = df_comparison[df_comparison['station_code'] == station_id].sort_values('DATE')
        
        # Calculate cumulative sums
        df_station = df_station.copy()
        df_station['ASOS_Accumulated'] = df_station['ASOS_PRCP'].fillna(0).cumsum()
        df_station['Snow_Accumulated'] = df_station['Snow_PRCP'].fillna(0).cumsum()
        
        # Plot accumulated precipitation
        ax.plot(df_station['DATE'], df_station['ASOS_Accumulated'], 
               label='ASOS (5-min sum)', linewidth=2.5, alpha=0.9, color='blue')
        ax.plot(df_station['DATE'], df_station['Snow_Accumulated'], 
               label='Snow Daily PRCP', linewidth=2.5, alpha=0.9, color='red', linestyle='--')
        
        # Formatting
        station_name = STATION_CODES.get(station_id, station_id)
        ax.set_title(f'{station_id} ({station_name}) - Accumulated Precipitation', 
                    fontsize=12, fontweight='bold')
        ax.set_ylabel('Accumulated PRCP (mm)', fontsize=10)
        ax.legend(loc='upper left', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='x', rotation=45)
        
        # Format x-axis dates
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        
        # Add total values in text box
        asos_total = df_station['ASOS_PRCP'].sum()
        snow_total = df_station['Snow_PRCP'].sum()
        diff_total = asos_total - snow_total
        summary_text = f'Total ASOS: {asos_total:.1f} mm\\n'
        summary_text += f'Total Snow: {snow_total:.1f} mm\\n'
        summary_text += f'Difference: {diff_total:.1f} mm'
        ax.text(0.02, 0.98, summary_text, transform=ax.transAxes,
               verticalalignment='top', fontsize=9,
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    axes[-1].set_xlabel('Date', fontsize=10)
    
    # Overall title
    period_str = ""
    if start_date and end_date:
        period_str = f"\\n{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    fig.suptitle(f'Accumulated Precipitation: ASOS (5-min sum) vs Snow Daily PRCP{period_str}', 
                fontsize=14, fontweight='bold')
    plt.tight_layout()
    
    return fig, axes

