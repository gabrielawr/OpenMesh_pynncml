"""
ASOS Data Processor
Processes Automated Surface Observing Station (ASOS) data from NOAA.

This module provides functions to:
- Load ASOS .txt files from NOAA Mesonet
- Filter data by date range
- Perform statistical analysis
- Generate visualizations
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, Tuple, Optional
import numpy as np


def read_asos_files(data_path: str) -> Dict[str, pd.DataFrame]:
    """
    Load all ASOS .txt files from a directory.
    
    Parameters
    ----------
    data_path : str
        Path to directory containing ASOS .txt files
    
    Returns
    -------
    Dict[str, pd.DataFrame]
        Dictionary with station IDs as keys and processed DataFrames as values
    
    Raises
    ------
    FileNotFoundError
        If no .txt files found in specified directory
    """
    
    data_directory = Path(data_path)
    dataframes = {}
    
    txt_files = list(data_directory.glob('*.txt'))
    
    if not txt_files:
        raise FileNotFoundError(f"No .txt files found in {data_path}")
    
    print(f"Found {len(txt_files)} file(s)\n")
    
    for file_path in txt_files:
        try:
            df = pd.read_csv(file_path)
            
            # Get station ID from filename
            station_id = file_path.stem
            
            # Convert valid_time to datetime
            if 'valid_time' in df.columns:
                df['valid_time'] = pd.to_datetime(df['valid_time'])
            
            # Convert precip from inches to mm if present
            if 'precip' in df.columns:
                df['precip_mm'] = pd.to_numeric(df['precip'], errors='coerce') * 25.4
            
            dataframes[station_id] = df
            
            print(f"Loaded: {station_id}")
            print(f"  Records: {len(df)}")
            print(f"  Columns: {list(df.columns)[:5]}...")
            print(f"  Date range: {df['valid_time'].min()} to {df['valid_time'].max()}\n")
            
        except Exception as e:
            print(f"Error processing {file_path.name}: {str(e)}\n")
    
    return dataframes


def filter_by_date_range(df: pd.DataFrame, 
                        start_date: Optional[str] = None, 
                        end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Filter DataFrame by date range.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with 'valid_time' column
    start_date : str, optional
        Start date (format: 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS')
    end_date : str, optional
        End date (format: 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS')
    
    Returns
    -------
    pd.DataFrame
        Filtered DataFrame
    """
    
    filtered = df.copy()
    
    if start_date:
        start_dt = pd.to_datetime(start_date)
        filtered = filtered[filtered['valid_time'] >= start_dt]
    
    if end_date:
        end_dt = pd.to_datetime(end_date)
        filtered = filtered[filtered['valid_time'] <= end_dt]
    
    return filtered


def analyze_data(df: pd.DataFrame, station_id: str) -> Dict:
    """
    Generate comprehensive statistical analysis of ASOS data.
    
    Parameters
    ----------
    df : pd.DataFrame
        ASOS DataFrame
    station_id : str
        Station identifier for reporting
    
    Returns
    -------
    Dict
        Dictionary containing statistics for all numeric columns
    """
    
    analysis = {
        'station': station_id,
        'total_records': len(df),
        'date_range': f"{df['valid_time'].min()} to {df['valid_time'].max()}",
    }
    
    # Analyze each numeric column
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    
    for col in numeric_cols:
        data = df[col].dropna()
        
        if len(data) > 0:
            analysis[f'{col}_count'] = len(data)
            analysis[f'{col}_mean'] = data.mean()
            analysis[f'{col}_min'] = data.min()
            analysis[f'{col}_max'] = data.max()
            analysis[f'{col}_std'] = data.std()
    
    return analysis


def print_analysis(analysis: Dict) -> None:
    """
    Pretty-print analysis results.
    
    Parameters
    ----------
    analysis : Dict
        Dictionary from analyze_data()
    """
    
    print("=" * 75)
    print(f"ANALYSIS: {analysis['station']}")
    print("=" * 75)
    print(f"Records: {analysis['total_records']}")
    print(f"Date range: {analysis['date_range']}")
    print("-" * 75)
    
    for key, value in analysis.items():
        if key not in ['station', 'total_records', 'date_range']:
            if isinstance(value, (int, float)):
                print(f"{key:30s}: {value:12.2f}")
            else:
                print(f"{key:30s}: {value}")
    
    print("=" * 75 + "\n")


def plot_variable(dataframes: Dict[str, pd.DataFrame], 
                 variable: str,
                 start_date: Optional[str] = None,
                 end_date: Optional[str] = None,
                 save_path: Optional[str] = None) -> None:
    """
    Create time-series plot for specified variable.
    
    Parameters
    ----------
    dataframes : Dict[str, pd.DataFrame]
        Dictionary of station DataFrames
    variable : str
        Variable name to plot (e.g., 'tmpf', 'precip_mm', 'sknt')
    start_date : str, optional
        Start date filter
    end_date : str, optional
        End date filter
    save_path : str, optional
        Path to save figure (PNG, PDF, etc.)
    """
    
    num_stations = len(dataframes)
    fig, axes = plt.subplots(num_stations, 1, figsize=(14, 4 * num_stations))
    
    if num_stations == 1:
        axes = [axes]
    
    for idx, (station_id, df) in enumerate(dataframes.items()):
        data = df.copy()
        
        # Apply date filter
        if start_date or end_date:
            data = filter_by_date_range(data, start_date, end_date)
        
        # Check if variable exists
        if variable not in data.columns:
            axes[idx].text(0.5, 0.5, f'Variable "{variable}" not found',
                          ha='center', va='center', transform=axes[idx].transAxes)
            axes[idx].set_title(f"{station_id} - {variable} (not available)")
            continue
        
        # Plot
        valid_data = data[['valid_time', variable]].dropna()
        
        if len(valid_data) > 0:
            axes[idx].plot(valid_data['valid_time'], valid_data[variable],
                          marker='o', linestyle='-', linewidth=1.5, 
                          markersize=3, color='steelblue')
            axes[idx].grid(True, alpha=0.3)
            axes[idx].tick_params(axis='x', rotation=45)
            
            # Add statistics
            mean_val = valid_data[variable].mean()
            min_val = valid_data[variable].min()
            max_val = valid_data[variable].max()
            
            axes[idx].text(0.02, 0.98, 
                          f'Mean: {mean_val:.1f} | Min: {min_val:.1f} | Max: {max_val:.1f}',
                          transform=axes[idx].transAxes,
                          verticalalignment='top',
                          bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                          fontsize=9)
        
        axes[idx].set_title(f"{station_id} - {variable}", fontweight='bold')
        axes[idx].set_xlabel('Time')
        axes[idx].set_ylabel(variable)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved: {save_path}")
    
    plt.show()


def compare_stations(dataframes: Dict[str, pd.DataFrame], 
                    variable: str,
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None,
                    save_path: Optional[str] = None) -> None:
    """
    Create comparison plot of single variable across multiple stations.
    
    Parameters
    ----------
    dataframes : Dict[str, pd.DataFrame]
        Dictionary of station DataFrames
    variable : str
        Variable to compare
    start_date : str, optional
        Start date filter
    end_date : str, optional
        End date filter
    save_path : str, optional
        Path to save figure
    """
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    for station_id, df in dataframes.items():
        data = df.copy()
        
        if start_date or end_date:
            data = filter_by_date_range(data, start_date, end_date)
        
        if variable in data.columns:
            valid_data = data[['valid_time', variable]].dropna()
            ax.plot(valid_data['valid_time'], valid_data[variable],
                   marker='o', linestyle='-', linewidth=1.5, markersize=3,
                   label=station_id, alpha=0.7)
    
    ax.set_title(f"Comparison: {variable}", fontweight='bold', fontsize=14)
    ax.set_xlabel('Time')
    ax.set_ylabel(variable)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved: {save_path}")
    
    plt.show()


def get_summary_table(dataframes: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Generate summary statistics table for all stations.
    
    Parameters
    ----------
    dataframes : Dict[str, pd.DataFrame]
        Dictionary of station DataFrames
    
    Returns
    -------
    pd.DataFrame
        Summary table with station statistics
    """
    
    summary_data = []
    
    for station_id, df in dataframes.items():
        summary_data.append({
            'Station': station_id,
            'Records': len(df),
            'Start': df['valid_time'].min(),
            'End': df['valid_time'].max(),
            'Duration_Days': (df['valid_time'].max() - df['valid_time'].min()).days,
        })
    
    return pd.DataFrame(summary_data)
