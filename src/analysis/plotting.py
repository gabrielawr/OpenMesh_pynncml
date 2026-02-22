"""
Plotting functions for OpenMesh data analysis.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.dates import AutoDateLocator
from typing import Optional, List, Dict, Union
from pathlib import Path


def plot_cml_rsl_attenuation(
    df_cml: pd.DataFrame,
    df_rain: pd.DataFrame,
    selected_link_id: str,
    rain_source: str = "ASOS"
) -> None:
    """
    Plot CML RSL, attenuation, and rain data on the same time axis.
    
    Parameters
    ----------
    df_cml : pd.DataFrame
        CML data with 'rsl' and 'attenuation' columns, indexed by time
    df_rain : pd.DataFrame
        Rain data with 'precipitation_mm' column, indexed by time
    selected_link_id : str
        Link ID for title
    rain_source : str
        Source of rain data (e.g., 'ASOS', 'PWS')
    """
    if df_cml is None or df_rain is None:
        print("⚠ Cannot plot - missing data")
        return
    
    # Align on common time index
    time_start = max(df_cml.index.min(), df_rain.index.min())
    time_end = min(df_cml.index.max(), df_rain.index.max())
    
    freq = '5min'
    
    # Resample CML data (continuous signal)
    df_cml_resampled = df_cml[['rsl', 'attenuation']].resample(freq).mean()
    
    # Don't resample rain data - use original timestamps
    # ASOS: already 5-min timestamps with hourly accumulation
    # PWS: already 5-min timestamps with 5-min amounts
    df_rain_plot = df_rain[['precipitation_mm']].copy()
    
    # Merge on time index (will align automatically)
    df_combined = pd.merge(
        df_cml_resampled,
        df_rain_plot,
        left_index=True,
        right_index=True,
        how='inner'
    )
    df_combined = df_combined.loc[time_start:time_end]
    
    if len(df_combined) == 0:
        print("⚠ Cannot plot - no overlapping data")
        return
    
    # Plot
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    
    # RSL
    ax1.plot(df_combined.index, df_combined['rsl'], 'b-', linewidth=0.5, alpha=0.7, label='RSL')
    ax1.set_ylabel('RSL (dBm)', fontsize=12)
    ax1.set_title(f'OpenMesh Link {selected_link_id} - Received Signal Level', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Attenuation
    ax2.plot(df_combined.index, df_combined['attenuation'], 'r-', linewidth=0.5, alpha=0.7, label='Attenuation')
    ax2.set_ylabel('Attenuation (dB)', fontsize=12)
    ax2.set_title('CML Attenuation (Baseline - RSL)', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    # Precipitation
    if rain_source == "ASOS":
        # ASOS: hourly accumulation (even at 5-min timestamps)
        ax3.bar(df_combined.index, df_combined['precipitation_mm'], width=0.001, 
                color='orange', alpha=0.6, label='ASOS (Hourly Accumulation)')
        ax3.set_ylabel('Precipitation (mm) - Hourly Accumulation', fontsize=12)
    else:
        # PWS: 5-minute interval amounts
        ax3.bar(df_combined.index, df_combined['precipitation_mm'], width=0.001, 
                color='green', alpha=0.6, label='PWS (5-min Interval)')
        ax3.set_ylabel('Precipitation (mm)', fontsize=12)
    ax3.set_xlabel('Time', fontsize=12)
    ax3.set_title(f'Ground Truth Rain Data ({rain_source})', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    
    # Format x-axis
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    locator = AutoDateLocator(maxticks=20)
    ax3.xaxis.set_major_locator(locator)
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    plt.show()
    
    print("✓ Plots generated")


def plot_all_datasets(
    df_cml: Optional[pd.DataFrame],
    df_pws: Optional[pd.DataFrame],
    df_asos: Optional[pd.DataFrame],
    selected_link_id: str,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
    pws_stations: Optional[list] = None,
    pws_max_stations: Optional[int] = None,
    ylims: Optional[Dict[str, List[float]]] = None
) -> None:
    """
    Plot all three datasets (CML, PWS, ASOS) on the same time axis.
    Only plots data in the shared/overlapping time period between all available datasets.
    
    Parameters
    ----------
    df_cml : pd.DataFrame, optional
        CML data with 'rsl', 'attenuation', and optionally 'baseline' columns
    df_pws : pd.DataFrame, optional
        PWS data with one column per station (precipitation values)
    df_asos : pd.DataFrame, optional
        ASOS data with one column per station (precipitation values) or single 'precip_mm' column
    selected_link_id : str
        Link ID for title
    start_date : pd.Timestamp, optional
        Start date for filtering. If None, uses shared period start.
    end_date : pd.Timestamp, optional
        End date for filtering. If None, uses shared period end.
    pws_stations : list, optional
        List of specific PWS station IDs to plot. If None (default), plots median and mean across all stations.
    pws_max_stations : int, optional
        Maximum number of PWS stations to plot if pws_stations is None. If None, plots median and mean.
    ylims : dict, optional
        Dictionary of y-axis limits. Keys can be 'pws' and/or 'asos'. Values are [min, max] lists.
        Example: {'pws': [0, 3], 'asos': [0, 3]}. If None, no y-limits are enforced (auto-scale).
    """
    # Find shared/overlapping time period between all available datasets
    time_starts = []
    time_ends = []
    
    if df_cml is not None and len(df_cml) > 0:
        time_starts.append(df_cml.index.min())
        time_ends.append(df_cml.index.max())
    
    if df_pws is not None and len(df_pws) > 0:
        time_starts.append(df_pws.index.min())
        time_ends.append(df_pws.index.max())
    
    if df_asos is not None and len(df_asos) > 0:
        time_starts.append(df_asos.index.min())
        time_ends.append(df_asos.index.max())
    
    # Use shared period if dates not provided
    if start_date is None or end_date is None:
        if len(time_starts) > 0 and len(time_ends) > 0:
            shared_start = max(time_starts)  # Latest start = shared start
            shared_end = min(time_ends)      # Earliest end = shared end
            if start_date is None:
                start_date = shared_start
            if end_date is None:
                end_date = shared_end
            print(f"📅 Using shared time period: {start_date} to {end_date}")
        else:
            # Fallback to default if no data available
            if start_date is None:
                start_date = pd.Timestamp('2024-01-01')
            if end_date is None:
                end_date = pd.Timestamp('2024-01-14 23:59:59')
    
    fig, axes = plt.subplots(4, 1, figsize=(16, 12), sharex=True)
    freq = '5min'
    
    # 1. CML Data (RSL and Attenuation)
    if df_cml is not None and len(df_cml) > 0:
        df_cml_filtered = df_cml[(df_cml.index >= start_date) & (df_cml.index <= end_date)].copy()
        if len(df_cml_filtered) > 0:
            cols_to_plot = ['rsl', 'attenuation']
            if 'baseline' in df_cml_filtered.columns:
                cols_to_plot.append('baseline')
            df_cml_plot = df_cml_filtered[cols_to_plot].resample(freq).mean()
        else:
            df_cml_plot = None
        
        if df_cml_plot is not None and len(df_cml_plot) > 0:
            axes[0].plot(df_cml_plot.index, df_cml_plot['rsl'], 'b-', linewidth=0.8, alpha=0.7, label='RSL')
            if 'baseline' in df_cml_plot.columns:
                axes[0].plot(df_cml_plot.index, df_cml_plot['baseline'], 'g--', linewidth=1.0, alpha=0.6, label='Rolling Baseline (3H)')
            axes[0].set_ylabel('RSL (dBm)', fontsize=11)
            axes[0].set_title(f'OpenMesh CML Link {selected_link_id} - Received Signal Level', fontsize=13, fontweight='bold')
            axes[0].grid(True, alpha=0.3)
            axes[0].legend(loc='upper right')
            
            axes[1].plot(df_cml_plot.index, df_cml_plot['attenuation'], 'r-', linewidth=0.8, alpha=0.7, label='Attenuation')
            axes[1].set_ylabel('Attenuation (dB)', fontsize=11)
            atten_title = 'CML Attenuation (Rolling Baseline - RSL, 3H window)' if 'baseline' in df_cml_plot.columns else 'CML Attenuation'
            axes[1].set_title(atten_title, fontsize=13, fontweight='bold')
            axes[1].grid(True, alpha=0.3)
            axes[1].legend(loc='upper right')
        else:
            axes[0].text(0.5, 0.5, 'No CML data in date range', ha='center', va='center', transform=axes[0].transAxes, fontsize=12)
            axes[0].set_xlim(start_date, end_date)  # Set x-axis limits even with no data
            axes[1].text(0.5, 0.5, 'No CML data in date range', ha='center', va='center', transform=axes[1].transAxes, fontsize=12)
            axes[1].set_xlim(start_date, end_date)  # Set x-axis limits even with no data
    else:
        axes[0].text(0.5, 0.5, 'No CML data available', ha='center', va='center', transform=axes[0].transAxes, fontsize=12)
        if start_date and end_date:
            axes[0].set_xlim(start_date, end_date)
        axes[1].text(0.5, 0.5, 'No CML data available', ha='center', va='center', transform=axes[1].transAxes, fontsize=12)
        if start_date and end_date:
            axes[1].set_xlim(start_date, end_date)
    
    # 2. PWS Data
    if df_pws is not None and len(df_pws) > 0:
        # Use the already-filtered data (high values already removed), just filter by date if needed
        df_pws_filtered = df_pws[(df_pws.index >= start_date) & (df_pws.index <= end_date)].copy()
        
        if len(df_pws_filtered) > 0:
            # Don't resample - use original 5-minute data as-is
            df_pws_plot = df_pws_filtered.copy()
            
            if pws_stations is not None and len(pws_stations) > 0:
                # Plot specific stations if provided
                available_stations = [s for s in pws_stations if s in df_pws_plot.columns]
                if len(available_stations) > 0:
                    # Limit number of stations if pws_max_stations is set
                    if pws_max_stations is not None and len(available_stations) > pws_max_stations:
                        available_stations = available_stations[:pws_max_stations]
                        title_suffix = f' ({len(available_stations)} of {len(pws_stations)} selected stations)'
                    else:
                        title_suffix = f' ({len(available_stations)} selected stations)'
                    
                    for station_id in available_stations:
                        axes[2].plot(df_pws_plot.index, df_pws_plot[station_id], 
                                    linewidth=1.0, alpha=0.7, label=station_id)
                else:
                    # Fallback to median and mean if specified stations not found
                    # Skip NaN values (filtered high values)
                    pws_median = df_pws_plot.median(axis=1, skipna=True)
                    pws_mean = df_pws_plot.mean(axis=1, skipna=True)
                    axes[2].plot(df_pws_plot.index, pws_median, 'g-', linewidth=1.2, alpha=0.8, label=f'PWS Median ({len(df_pws.columns)} stations)')
                    axes[2].plot(df_pws_plot.index, pws_mean, 'g--', linewidth=1.0, alpha=0.7, label=f'PWS Mean ({len(df_pws.columns)} stations)')
                    title_suffix = f' ({len(df_pws.columns)} stations)'
            else:
                # Default: plot median and mean across all stations, or limit individual stations
                if pws_max_stations is not None and pws_max_stations > 0:
                    # Plot individual stations (up to max_stations) instead of median/mean
                    stations_to_plot = list(df_pws_plot.columns)[:pws_max_stations]
                    for station_id in stations_to_plot:
                        axes[2].plot(df_pws_plot.index, df_pws_plot[station_id], 
                                    linewidth=1.0, alpha=0.7, label=station_id)
                    title_suffix = f' ({len(stations_to_plot)} of {len(df_pws.columns)} stations)'
                else:
                    # Plot median and mean across all stations
                    # Skip NaN values (filtered high values)
                    pws_median = df_pws_plot.median(axis=1, skipna=True)
                    pws_mean = df_pws_plot.mean(axis=1, skipna=True)
                    axes[2].plot(df_pws_plot.index, pws_median, 'g-', linewidth=1.2, alpha=0.8, label=f'PWS Median ({len(df_pws.columns)} stations)')
                    axes[2].plot(df_pws_plot.index, pws_mean, 'g--', linewidth=1.0, alpha=0.7, label=f'PWS Mean ({len(df_pws.columns)} stations)')
                    title_suffix = f' ({len(df_pws.columns)} stations)'
            
            axes[2].set_ylabel('Precipitation (mm) - 5-min Interval', fontsize=11)
            axes[2].set_title(f'PWS Rainfall Data{title_suffix}', fontsize=13, fontweight='bold')
            # Set y-limits only if provided
            if ylims is not None and 'pws' in ylims:
                axes[2].set_ylim(ylims['pws'])
            axes[2].grid(True, alpha=0.3)
            axes[2].legend(loc='upper right', fontsize=9)
        else:
            axes[2].text(0.5, 0.5, 'No PWS data in date range', ha='center', va='center', transform=axes[2].transAxes, fontsize=12)
            if start_date and end_date:
                axes[2].set_xlim(start_date, end_date)
    else:
        axes[2].text(0.5, 0.5, 'No PWS data available', ha='center', va='center', transform=axes[2].transAxes, fontsize=12)
        if start_date and end_date:
            axes[2].set_xlim(start_date, end_date)
    
    # 3. ASOS Data - Handle multiple stations
    if df_asos is not None and len(df_asos) > 0:
        df_asos_filtered = df_asos[(df_asos.index >= start_date) & (df_asos.index <= end_date)].copy()
        
        if len(df_asos_filtered) > 0:
            # Check if ASOS has multiple stations (multiple columns) or single column
            # Note: ASOS data is now 1-minute per-minute precipitation (not hourly accumulation)
            if 'precip_mm' in df_asos_filtered.columns:
                # Single station format (legacy)
                # Data is 1-minute per-minute precipitation
                df_asos_plot = df_asos_filtered[['precip_mm']].copy()
                axes[3].plot(df_asos_plot.index, df_asos_plot['precip_mm'], 
                            color='orange', linewidth=1.0, alpha=0.8, 
                            label='ASOS (1-min)')
                axes[3].set_ylabel('Precipitation (mm/min)', fontsize=11)
                axes[3].set_title('NOAA ASOS Rainfall Data (1-minute)', fontsize=13, fontweight='bold')
            else:
                # Multiple stations format (one column per station)
                # Data is 1-minute per-minute precipitation
                df_asos_plot = df_asos_filtered.copy()
                # Skip NaN values (filtered high values)
                asos_mean = df_asos_plot.mean(axis=1, skipna=True)
                axes[3].plot(df_asos_plot.index, asos_mean, 'orange', linewidth=1.0, alpha=0.8, 
                            label=f'ASOS Mean ({len(df_asos_plot.columns)} stations, 1-min)')
                
                # Plot individual stations if not too many
                if len(df_asos_plot.columns) <= 5:
                    for station_id in df_asos_plot.columns:
                        axes[3].plot(df_asos_plot.index, df_asos_plot[station_id], 
                                    linewidth=0.5, alpha=0.4, label=f'{station_id} (1-min)')
                else:
                    sample_stations = list(df_asos_plot.columns)[:3]
                    for station_id in sample_stations:
                        axes[3].plot(df_asos_plot.index, df_asos_plot[station_id], 
                                    linewidth=0.5, alpha=0.4, label=f'{station_id} (1-min, sample)')
                axes[3].set_ylabel('Precipitation (mm/min)', fontsize=11)
                axes[3].set_title(f'NOAA ASOS Rainfall Data ({len(df_asos_plot.columns)} stations, 1-minute)', fontsize=13, fontweight='bold')
            # Set y-limits only if provided
            if ylims is not None and 'asos' in ylims:
                axes[3].set_ylim(ylims['asos'])
            axes[3].grid(True, alpha=0.3)
            axes[3].legend(loc='upper right', fontsize=9)
        else:
            axes[3].text(0.5, 0.5, 'No ASOS data in date range', ha='center', va='center', transform=axes[3].transAxes, fontsize=12)
            if start_date and end_date:
                axes[3].set_xlim(start_date, end_date)
    else:
        axes[3].text(0.5, 0.5, 'No ASOS data available', ha='center', va='center', transform=axes[3].transAxes, fontsize=12)
        if start_date and end_date:
            axes[3].set_xlim(start_date, end_date)
    
    # Format x-axis - apply to all subplots since they share x-axis
    # Format the bottom axis (last subplot) which will be visible
    axes[3].set_xlabel('Time', fontsize=12, fontweight='bold')
    
    # Calculate time range to determine appropriate formatting
    if start_date and end_date:
        time_range = (end_date - start_date).total_seconds() / 3600  # hours
    else:
        # Try to get from data
        all_times = []
        if df_cml is not None and len(df_cml) > 0:
            all_times.extend([df_cml.index.min(), df_cml.index.max()])
        if df_pws is not None and len(df_pws) > 0:
            all_times.extend([df_pws.index.min(), df_pws.index.max()])
        if df_asos is not None and len(df_asos) > 0:
            all_times.extend([df_asos.index.min(), df_asos.index.max()])
        
        if len(all_times) > 0:
            time_range = (max(all_times) - min(all_times)).total_seconds() / 3600
        else:
            time_range = 24  # default
    
    # Choose format based on time range
    if time_range <= 24:
        date_format = '%Y-%m-%d %H:%M'  # Show full date and time
        major_interval = 2  # hours
    elif time_range <= 168:  # 1 week
        date_format = '%m-%d %H:%M'
        major_interval = 6  # hours
    else:
        date_format = '%Y-%m-%d'
        major_interval = 1  # days
    
    # Apply formatting to the bottom axis (last subplot) - this is the one that shows labels
    # With sharex=True, only the bottom axis shows labels
    ax_bottom = axes[3]
    ax_bottom.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
    
    if time_range <= 24:
        ax_bottom.xaxis.set_major_locator(mdates.HourLocator(interval=major_interval))
        ax_bottom.xaxis.set_minor_locator(mdates.HourLocator(interval=1))  # Minor ticks every hour
    elif time_range <= 168:
        ax_bottom.xaxis.set_major_locator(mdates.HourLocator(interval=major_interval))
        ax_bottom.xaxis.set_minor_locator(mdates.HourLocator(interval=3))  # Minor ticks every 3 hours
    else:
        ax_bottom.xaxis.set_major_locator(mdates.DayLocator(interval=major_interval))
        ax_bottom.xaxis.set_minor_locator(mdates.HourLocator(interval=12))  # Minor ticks every 12 hours
    
    # Rotate labels to avoid overlap and make them visible
    if time_range > 24:
        plt.setp(ax_bottom.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=10)
    else:
        plt.setp(ax_bottom.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=10)
    
    # Ensure x-axis is visible
    ax_bottom.tick_params(axis='x', which='major', labelsize=10, bottom=True)
    ax_bottom.tick_params(axis='x', which='minor', labelsize=8, bottom=True)
    
    # Make sure x-axis labels are not hidden
    for label in ax_bottom.get_xticklabels():
        label.set_visible(True)
    
    # Adjust layout to prevent label cutoff - leave more space at bottom
    plt.tight_layout(rect=[0, 0.03, 1, 0.98])  # Leave 3% space at bottom for labels
    plt.show()
    
    print("✓ Plotted all three datasets (CML, PWS, ASOS)")


def plot_rain_detection(
    df_cml: Optional[pd.DataFrame],
    df_rain_detection: Optional[pd.DataFrame],
    df_rain_ground_truth: Optional[pd.DataFrame] = None,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
    overlay_detection_on_rain: bool = True,
    method_name: str = "Detection Method"
) -> None:
    """
    Plot rain detection results with CML attenuation, detection binary signal, and ground truth.
    
    Parameters
    ----------
    df_cml : pd.DataFrame, optional
        CML data with 'attenuation' column
    df_rain_detection : pd.DataFrame, optional
        Rain detection results with 'attenuation', 'rain_detected', and 'threshold_constant' columns
    df_rain_ground_truth : pd.DataFrame, optional
        Ground truth rain data with 'precip_mm' column for comparison
        This is from PWS (Personal Weather Stations) or ASOS (NOAA Automated Surface Observing System)
    start_date : pd.Timestamp, optional
        Start date for filtering
    end_date : pd.Timestamp, optional
        End date for filtering
    overlay_detection_on_rain : bool, optional
        If True, overlay detection signal on ground truth rain plot for direct comparison.
        If False, show detection in separate panel. Default: True
    """
    if overlay_detection_on_rain:
        fig, axes = plt.subplots(2, 1, figsize=(18, 8), sharex=True)
    else:
        fig, axes = plt.subplots(3, 1, figsize=(18, 10), sharex=True)
    
    # Filter by date if provided
    if start_date is not None and end_date is not None:
        if df_cml is not None:
            df_cml = df_cml[(df_cml.index >= start_date) & (df_cml.index <= end_date)]
        if df_rain_detection is not None:
            df_rain_detection = df_rain_detection[(df_rain_detection.index >= start_date) & 
                                                  (df_rain_detection.index <= end_date)]
        if df_rain_ground_truth is not None:
            df_rain_ground_truth = df_rain_ground_truth[(df_rain_ground_truth.index >= start_date) & 
                                                       (df_rain_ground_truth.index <= end_date)]
    
    # 1. CML Attenuation with Threshold (or Rolling Std)
    is_rolling_std_method = False
    if df_rain_detection is not None and len(df_rain_detection) > 0:
        if 'rolling_std' in df_rain_detection.columns:
            is_rolling_std_method = True
            # Plot rolling std instead of attenuation
            axes[0].plot(df_rain_detection.index, df_rain_detection['rolling_std'], 
                       'b-', linewidth=1.0, alpha=0.7, label='Rolling Std')
            if 'threshold' in df_rain_detection.columns:
                threshold_val = df_rain_detection['threshold'].iloc[0]
                axes[0].axhline(y=threshold_val, color='r', linestyle='--', 
                               linewidth=2.0, alpha=0.8, 
                               label=f'Threshold = {threshold_val} dB')
            axes[0].set_ylabel('Rolling Std (dB)', fontsize=12, fontweight='bold')
            axes[0].set_title(f'Rolling Std with Detection Threshold - {method_name}', fontsize=14, fontweight='bold')
        else:
            # Constant baseline method - plot attenuation
            if df_cml is not None and len(df_cml) > 0:
                df_cml_plot = df_cml[['attenuation']].resample('5min').mean()
                axes[0].plot(df_cml_plot.index, df_cml_plot['attenuation'], 'b-', linewidth=1.0, alpha=0.7, label='CML Attenuation')
                
                # Add threshold line if available
                if 'threshold_constant' in df_rain_detection.columns:
                    threshold_val = df_rain_detection['threshold_constant'].iloc[0]
                    axes[0].axhline(y=threshold_val, color='r', linestyle='--', linewidth=2.0, alpha=0.8, 
                                   label=f'Threshold = {threshold_val} dB (constant)')
                elif 'threshold' in df_rain_detection.columns:
                    # Legacy: rolling threshold as a line (for backward compatibility)
                    axes[0].plot(df_rain_detection.index, df_rain_detection['threshold'], 
                               'r--', linewidth=1.5, alpha=0.7, label='Threshold')
            
            axes[0].set_ylabel('Attenuation (dB)', fontsize=12, fontweight='bold')
            axes[0].set_title(f'CML Attenuation with Detection Threshold - {method_name}', fontsize=14, fontweight='bold')
    elif df_cml is not None and len(df_cml) > 0:
        # Fallback: plot attenuation if no detection data
        df_cml_plot = df_cml[['attenuation']].resample('5min').mean()
        axes[0].plot(df_cml_plot.index, df_cml_plot['attenuation'], 'b-', linewidth=1.0, alpha=0.7, label='CML Attenuation')
        axes[0].set_ylabel('Attenuation (dB)', fontsize=12, fontweight='bold')
        axes[0].set_title(f'CML Attenuation - {method_name}', fontsize=14, fontweight='bold')
    else:
        axes[0].text(0.5, 0.5, 'No CML data available', ha='center', va='center', transform=axes[0].transAxes)
    
    axes[0].grid(True, alpha=0.3, linestyle=':')
    axes[0].legend(loc='upper right', fontsize=10)
    
    # Determine which panel index for rain plot
    if overlay_detection_on_rain:
        rain_panel_idx = 1
    else:
        rain_panel_idx = 2
        # 2. Rain Detection (Binary: 1/0) - separate panel
        if df_rain_detection is not None and len(df_rain_detection) > 0:
            # Plot binary detection as filled area
            axes[1].fill_between(df_rain_detection.index, 0, df_rain_detection['rain_detected'], 
                                 color='red', alpha=0.5, label='Rain Detected (1)')
            axes[1].set_ylabel('Rain Detection\n(1 = Rain, 0 = No Rain)', fontsize=12, fontweight='bold')
            axes[1].set_title('Rain Detection (Binary)', fontsize=14, fontweight='bold')
            axes[1].set_ylim(-0.1, 1.1)
            axes[1].set_yticks([0, 1])
            axes[1].grid(True, alpha=0.3, linestyle=':')
            axes[1].legend(loc='upper right', fontsize=10)
        else:
            axes[1].text(0.5, 0.5, 'No detection data available', ha='center', va='center', transform=axes[1].transAxes)
    
    # Ground Truth Rain with optional detection overlay
    if df_rain_ground_truth is not None and len(df_rain_ground_truth) > 0:
        if 'precip_mm' in df_rain_ground_truth.columns:
            df_rain_plot = df_rain_ground_truth[['precip_mm']].resample('5min').mean()
            
            # Plot ground truth rain
            axes[rain_panel_idx].bar(df_rain_plot.index, df_rain_plot['precip_mm'], 
                        width=pd.Timedelta('5min'), color='green', alpha=0.6, 
                        label='Ground Truth: PWS/ASOS Rain')
            
            # Overlay detection signal if requested
            if overlay_detection_on_rain and df_rain_detection is not None and len(df_rain_detection) > 0:
                # Get max rain value for scaling detection signal
                max_rain = df_rain_plot['precip_mm'].max() if len(df_rain_plot) > 0 else 1.0
                if max_rain == 0:
                    max_rain = 1.0
                
                # Plot detection as overlay (scaled to max rain for visibility)
                detection_scaled = df_rain_detection['rain_detected'] * max_rain * 0.3  # Scale to 30% of max rain
                axes[rain_panel_idx].fill_between(df_rain_detection.index, 0, detection_scaled,
                                                 color='red', alpha=0.4, label='CML Detection (overlay)')
            
            axes[rain_panel_idx].set_ylabel('Precipitation (mm)', fontsize=12, fontweight='bold')
            axes[rain_panel_idx].set_xlabel('Time', fontsize=13, fontweight='bold')
            
            # Title with explanation
            title = 'Ground Truth Rain (PWS/ASOS) vs CML Detection'
            if overlay_detection_on_rain:
                title += ' - Red overlay = CML detection'
            axes[rain_panel_idx].set_title(title, fontsize=14, fontweight='bold')
            axes[rain_panel_idx].grid(True, alpha=0.3, linestyle=':')
            axes[rain_panel_idx].legend(loc='upper right', fontsize=10)
        else:
            axes[rain_panel_idx].text(0.5, 0.5, 'No precipitation data in ground truth', ha='center', va='center', transform=axes[rain_panel_idx].transAxes)
    else:
        axes[rain_panel_idx].text(0.5, 0.5, 'No ground truth data available', ha='center', va='center', transform=axes[rain_panel_idx].transAxes)
    
    # Format x-axis - Fix overlapping issue
    # Use AutoDateLocator to automatically adjust based on time range
    # Only format the bottom axis (rain panel)
    ax_to_format = axes[rain_panel_idx] if len(axes) > rain_panel_idx else axes[-1]
    
    # Calculate time range for formatting
    if df_rain_detection is not None and len(df_rain_detection) > 0:
        time_range = (df_rain_detection.index.max() - df_rain_detection.index.min()).total_seconds() / 3600  # hours
    elif df_cml is not None and len(df_cml) > 0:
        time_range = (df_cml.index.max() - df_cml.index.min()).total_seconds() / 3600
    else:
        time_range = 24  # default
    
    # Adjust tick interval based on time range
    if time_range <= 24:
        # Less than 1 day: show every 2-4 hours
        major_interval = 4
        date_format = '%H:%M'
    elif time_range <= 7 * 24:
        # Less than 1 week: show every 12 hours
        major_interval = 12
        date_format = '%m/%d\n%H:%M'
    else:
        # More than 1 week: show daily
        major_interval = 24
        date_format = '%m/%d'
    
    # Format only the bottom axis
    ax_to_format.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
    ax_to_format.xaxis.set_major_locator(mdates.HourLocator(interval=major_interval))
    ax_to_format.xaxis.set_minor_locator(mdates.HourLocator(interval=major_interval // 2))
    
    # Rotate labels to avoid overlap
    if time_range > 24:
        plt.setp(ax_to_format.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
    else:
        plt.setp(ax_to_format.xaxis.get_majorticklabels(), rotation=0, ha='center', fontsize=10)
    
    ax_to_format.tick_params(axis='x', which='major', length=8, width=1.5)
    ax_to_format.tick_params(axis='x', which='minor', length=4, width=1)
    
    # Hide x-axis labels on upper panels
    for i, ax in enumerate(axes):
        if i < len(axes) - 1:
            ax.set_xticklabels([])
    
    # Add vertical grid lines for better time visibility
    for ax in axes:
        ax.grid(True, alpha=0.2, linestyle='-', which='major', axis='x')
        ax.grid(True, alpha=0.1, linestyle=':', which='minor', axis='x')
    
    plt.tight_layout()
    plt.show()
    
    print("✓ Rain detection plots generated")


def plot_both_detection_methods(
    df_cml: Optional[pd.DataFrame],
    df_const_detection: Optional[pd.DataFrame],
    df_rolling_detection: Optional[pd.DataFrame],
    df_rain_ground_truth: Optional[pd.DataFrame] = None,
    start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
    overlay_detection_on_rain: bool = True
) -> None:
    """
    Plot both detection methods (Constant Baseline and Rolling Std) side by side for comparison.
    
    Parameters
    ----------
    df_cml : pd.DataFrame, optional
        CML data with 'attenuation' column
    df_const_detection : pd.DataFrame, optional
        Constant baseline detection results
    df_rolling_detection : pd.DataFrame, optional
        Rolling std detection results
    df_rain_ground_truth : pd.DataFrame, optional
        Ground truth rain data with 'precip_mm' column
    start_date : pd.Timestamp, optional
        Start date for filtering
    end_date : pd.Timestamp, optional
        End date for filtering
    overlay_detection_on_rain : bool, optional
        If True, overlay detection signal on ground truth rain plot
    """
    # Filter by date if provided
    if start_date is not None and end_date is not None:
        if df_cml is not None:
            df_cml = df_cml[(df_cml.index >= start_date) & (df_cml.index <= end_date)]
        if df_const_detection is not None:
            df_const_detection = df_const_detection[(df_const_detection.index >= start_date) & 
                                                    (df_const_detection.index <= end_date)]
        if df_rolling_detection is not None:
            df_rolling_detection = df_rolling_detection[(df_rolling_detection.index >= start_date) & 
                                                        (df_rolling_detection.index <= end_date)]
        if df_rain_ground_truth is not None:
            df_rain_ground_truth = df_rain_ground_truth[(df_rain_ground_truth.index >= start_date) & 
                                                        (df_rain_ground_truth.index <= end_date)]
    
    if overlay_detection_on_rain:
        fig, axes = plt.subplots(4, 1, figsize=(18, 14), sharex=True)
    else:
        fig, axes = plt.subplots(6, 1, figsize=(18, 16), sharex=True)
    
    # Determine panel indices
    if overlay_detection_on_rain:
        const_atten_idx = 0
        const_rain_idx = 1
        rolling_atten_idx = 2
        rolling_rain_idx = 3
    else:
        const_atten_idx = 0
        const_det_idx = 1
        const_rain_idx = 2
        rolling_atten_idx = 3
        rolling_det_idx = 4
        rolling_rain_idx = 5
    
    # ===== CONSTANT BASELINE METHOD =====
    # Attenuation with threshold
    if df_cml is not None and len(df_cml) > 0:
        df_cml_plot = df_cml[['attenuation']].resample('5min').mean()
        axes[const_atten_idx].plot(df_cml_plot.index, df_cml_plot['attenuation'], 
                                   'b-', linewidth=1.0, alpha=0.7, label='CML Attenuation')
        
        if df_const_detection is not None and len(df_const_detection) > 0:
            if 'threshold_constant' in df_const_detection.columns:
                threshold_val = df_const_detection['threshold_constant'].iloc[0]
                axes[const_atten_idx].axhline(y=threshold_val, color='r', linestyle='--', 
                                             linewidth=2.0, alpha=0.8, 
                                             label=f'Threshold = {threshold_val} dB (constant)')
        
        axes[const_atten_idx].set_ylabel('Attenuation (dB)', fontsize=12, fontweight='bold')
        axes[const_atten_idx].set_title('Constant Baseline Method - CML Attenuation with Threshold', 
                                       fontsize=14, fontweight='bold')
        axes[const_atten_idx].grid(True, alpha=0.3, linestyle=':')
        axes[const_atten_idx].legend(loc='upper right', fontsize=10)
    
    # Detection binary (if not overlay)
    if not overlay_detection_on_rain and df_const_detection is not None and len(df_const_detection) > 0:
        axes[const_det_idx].fill_between(df_const_detection.index, 0, df_const_detection['rain_detected'], 
                                         color='red', alpha=0.5, label='Rain Detected (1)')
        axes[const_det_idx].set_ylabel('Rain Detection\n(1 = Rain, 0 = No Rain)', fontsize=12, fontweight='bold')
        axes[const_det_idx].set_title('Constant Baseline Method - Rain Detection (Binary)', 
                                     fontsize=14, fontweight='bold')
        axes[const_det_idx].set_ylim(-0.1, 1.1)
        axes[const_det_idx].set_yticks([0, 1])
        axes[const_det_idx].grid(True, alpha=0.3, linestyle=':')
        axes[const_det_idx].legend(loc='upper right', fontsize=10)
    
    # Ground truth rain with detection overlay
    if df_rain_ground_truth is not None and len(df_rain_ground_truth) > 0:
        if 'precip_mm' in df_rain_ground_truth.columns:
            df_rain_plot = df_rain_ground_truth[['precip_mm']].resample('5min').mean()
            axes[const_rain_idx].bar(df_rain_plot.index, df_rain_plot['precip_mm'], 
                        width=pd.Timedelta('5min'), color='green', alpha=0.6, 
                        label='Ground Truth: PWS/ASOS Rain')
            
            if overlay_detection_on_rain and df_const_detection is not None and len(df_const_detection) > 0:
                max_rain = df_rain_plot['precip_mm'].max() if len(df_rain_plot) > 0 else 1.0
                if max_rain == 0:
                    max_rain = 1.0
                detection_scaled = df_const_detection['rain_detected'] * max_rain * 0.3
                axes[const_rain_idx].fill_between(df_const_detection.index, 0, detection_scaled,
                                                 color='red', alpha=0.4, label='CML Detection (Constant Baseline)')
            
            axes[const_rain_idx].set_ylabel('Precipitation (mm)', fontsize=12, fontweight='bold')
            title = 'Constant Baseline Method - Ground Truth vs Detection'
            if overlay_detection_on_rain:
                title += ' (Red overlay = detection)'
            axes[const_rain_idx].set_title(title, fontsize=14, fontweight='bold')
            axes[const_rain_idx].grid(True, alpha=0.3, linestyle=':')
            axes[const_rain_idx].legend(loc='upper right', fontsize=10)
    
    # ===== ROLLING STD METHOD =====
    # Rolling std with threshold
    if df_rolling_detection is not None and len(df_rolling_detection) > 0:
        if 'rolling_std' in df_rolling_detection.columns:
            axes[rolling_atten_idx].plot(df_rolling_detection.index, df_rolling_detection['rolling_std'], 
                                         'b-', linewidth=1.0, alpha=0.7, label='Rolling Std')
            
            if 'threshold' in df_rolling_detection.columns:
                threshold_val = df_rolling_detection['threshold'].iloc[0]
                axes[rolling_atten_idx].axhline(y=threshold_val, color='r', linestyle='--', 
                                               linewidth=2.0, alpha=0.8, 
                                               label=f'Threshold = {threshold_val} dB')
        
        axes[rolling_atten_idx].set_ylabel('Rolling Std (dB)', fontsize=12, fontweight='bold')
        axes[rolling_atten_idx].set_title('Rolling Std Method - Rolling Standard Deviation with Threshold', 
                                         fontsize=14, fontweight='bold')
        axes[rolling_atten_idx].grid(True, alpha=0.3, linestyle=':')
        axes[rolling_atten_idx].legend(loc='upper right', fontsize=10)
    
    # Detection binary (if not overlay)
    if not overlay_detection_on_rain and df_rolling_detection is not None and len(df_rolling_detection) > 0:
        axes[rolling_det_idx].fill_between(df_rolling_detection.index, 0, df_rolling_detection['rain_detected'], 
                                          color='red', alpha=0.5, label='Rain Detected (1)')
        axes[rolling_det_idx].set_ylabel('Rain Detection\n(1 = Rain, 0 = No Rain)', fontsize=12, fontweight='bold')
        axes[rolling_det_idx].set_title('Rolling Std Method - Rain Detection (Binary)', 
                                      fontsize=14, fontweight='bold')
        axes[rolling_det_idx].set_ylim(-0.1, 1.1)
        axes[rolling_det_idx].set_yticks([0, 1])
        axes[rolling_det_idx].grid(True, alpha=0.3, linestyle=':')
        axes[rolling_det_idx].legend(loc='upper right', fontsize=10)
    
    # Ground truth rain with detection overlay
    if df_rain_ground_truth is not None and len(df_rain_ground_truth) > 0:
        if 'precip_mm' in df_rain_ground_truth.columns:
            df_rain_plot = df_rain_ground_truth[['precip_mm']].resample('5min').mean()
            axes[rolling_rain_idx].bar(df_rain_plot.index, df_rain_plot['precip_mm'], 
                        width=pd.Timedelta('5min'), color='green', alpha=0.6, 
                        label='Ground Truth: PWS/ASOS Rain')
            
            if overlay_detection_on_rain and df_rolling_detection is not None and len(df_rolling_detection) > 0:
                max_rain = df_rain_plot['precip_mm'].max() if len(df_rain_plot) > 0 else 1.0
                if max_rain == 0:
                    max_rain = 1.0
                detection_scaled = df_rolling_detection['rain_detected'] * max_rain * 0.3
                axes[rolling_rain_idx].fill_between(df_rolling_detection.index, 0, detection_scaled,
                                                    color='red', alpha=0.4, label='CML Detection (Rolling Std)')
            
            axes[rolling_rain_idx].set_ylabel('Precipitation (mm)', fontsize=12, fontweight='bold')
            axes[rolling_rain_idx].set_xlabel('Time', fontsize=13, fontweight='bold')
            title = 'Rolling Std Method - Ground Truth vs Detection'
            if overlay_detection_on_rain:
                title += ' (Red overlay = detection)'
            axes[rolling_rain_idx].set_title(title, fontsize=14, fontweight='bold')
            axes[rolling_rain_idx].grid(True, alpha=0.3, linestyle=':')
            axes[rolling_rain_idx].legend(loc='upper right', fontsize=10)
    
    # Format x-axis - only on bottom plot
    ax_to_format = axes[rolling_rain_idx]
    
    # Calculate time range for formatting
    if df_rolling_detection is not None and len(df_rolling_detection) > 0:
        time_range = (df_rolling_detection.index.max() - df_rolling_detection.index.min()).total_seconds() / 3600
    elif df_const_detection is not None and len(df_const_detection) > 0:
        time_range = (df_const_detection.index.max() - df_const_detection.index.min()).total_seconds() / 3600
    elif df_cml is not None and len(df_cml) > 0:
        time_range = (df_cml.index.max() - df_cml.index.min()).total_seconds() / 3600
    else:
        time_range = 24
    
    # Adjust tick interval based on time range
    if time_range <= 24:
        major_interval = 4
        date_format = '%H:%M'
    elif time_range <= 7 * 24:
        major_interval = 12
        date_format = '%m/%d\n%H:%M'
    else:
        major_interval = 24
        date_format = '%m/%d'
    
    # Format only the bottom axis
    ax_to_format.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
    ax_to_format.xaxis.set_major_locator(mdates.HourLocator(interval=major_interval))
    ax_to_format.xaxis.set_minor_locator(mdates.HourLocator(interval=major_interval // 2))
    
    if time_range > 24:
        plt.setp(ax_to_format.xaxis.get_majorticklabels(), rotation=45, ha='right', fontsize=9)
    else:
        plt.setp(ax_to_format.xaxis.get_majorticklabels(), rotation=0, ha='center', fontsize=10)
    
    ax_to_format.tick_params(axis='x', which='major', length=8, width=1.5)
    ax_to_format.tick_params(axis='x', which='minor', length=4, width=1)
    
    # Hide x-axis labels on upper panels
    for i, ax in enumerate(axes):
        if i < len(axes) - 1:
            ax.set_xticklabels([])
    
    # Add vertical grid lines
    for ax in axes:
        ax.grid(True, alpha=0.2, linestyle='-', which='major', axis='x')
        ax.grid(True, alpha=0.1, linestyle=':', which='minor', axis='x')
    
    plt.tight_layout()
    plt.show()
    
    print("✓ Combined plots generated for both detection methods")


def plot_weather_subplots(
    processed_data: Dict[str, pd.DataFrame],
    params: List[str],
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    figsize: tuple = (14, 14),
    ylims: Optional[Union[List[float], Dict[str, List[float]]]] = None,
    title_prefix: str = ""
) -> tuple:
    """
    Plot multiple weather parameters as subplots.
    
    Parameters
    ----------
    processed_data : dict
        Dictionary of DataFrames keyed by station_id, each with datetime index
    params : list of str
        List of parameter names to plot (e.g., ['precip_mm', 'temp_c', 'wind_speed_ms'])
    start_date : pd.Timestamp
        Start date for filtering
    end_date : pd.Timestamp
        End date for filtering
    figsize : tuple, optional
        Figure size (width, height). Default is (14, 14)
    ylims : list or dict, optional
        Y-axis limits. Can be:
        - List [ymin, ymax]: Applied to all subplots
        - Dict {param: [ymin, ymax]}: Different limits per parameter
    title_prefix : str, optional
        Prefix for plot titles
    
    Returns
    -------
    fig, axes : matplotlib figure and axes objects
    """
    n_params = len(params)
    fig, axes = plt.subplots(n_params, 1, figsize=figsize, sharex=True)
    
    # Handle single subplot case (axes is not a list)
    if n_params == 1:
        axes = [axes]
    
    # Determine ylims format
    if ylims is not None:
        if isinstance(ylims, list) and len(ylims) == 2:
            # Single ylim applied to all subplots
            ylims_dict = {param: ylims for param in params}
        elif isinstance(ylims, dict):
            # Different ylims per parameter
            ylims_dict = ylims
        else:
            ylims_dict = None
    else:
        ylims_dict = None
    
    # Plot each parameter
    for idx, param in enumerate(params):
        ax = axes[idx]
        
        # Plot data for each station
        for station_id, df in processed_data.items():
            if param in df.columns:
                df_filtered = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)].copy()
                if len(df_filtered) > 0:
                    ax.plot(df_filtered['datetime'], df_filtered[param], 
                           label=station_id, linewidth=1.5, alpha=0.8)
        
        # Set labels and title
        param_label = param.replace('_', ' ').title()
        ax.set_ylabel(param_label, fontsize=12, fontweight='bold')
        if title_prefix:
            ax.set_title(f'{title_prefix} - {param_label}', fontsize=13, fontweight='bold')
        else:
            ax.set_title(param_label, fontsize=13, fontweight='bold')
        
        # Apply ylims if specified
        if ylims_dict and param in ylims_dict:
            ax.set_ylim(ylims_dict[param])
        
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=10)
    
    # Format x-axis on bottom subplot
    axes[-1].set_xlabel('Date (UTC)', fontsize=12, fontweight='bold')
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
    locator = AutoDateLocator(maxticks=20)
    axes[-1].xaxis.set_major_locator(locator)
    plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    
    return fig, axes


def plot_all_metadata_on_map(
    df_cml_metadata: Optional[pd.DataFrame] = None,
    pws_metadata_file: Optional[Union[str, Path]] = None,
    asos_metadata_file: Optional[Union[str, Path]] = None,
    mesonet_metadata_file: Optional[Union[str, Path]] = None,
    output_file: Optional[Union[str, Path]] = None,
    base_path: Optional[Path] = None,
    output_dir: Optional[Path] = None
) -> Optional[object]:
    """
    Load metadata from all datasets and create an interactive Folium map.
    
    This function loads station/link metadata from:
    - CML (Commercial Microwave Links) - links_metadata.csv
    - PWS (Personal Weather Stations) - pws_metadata.csv
    - ASOS (Automated Surface Observing System) - ASOS_stations.csv
    - NYC Mesonet - mesonet_metadata.csv (from processed output)
    
    Parameters
    ----------
    df_cml_metadata : pd.DataFrame, optional
        CML links metadata DataFrame. If None, will load from default location.
    pws_metadata_file : str or Path, optional
        Path to PWS metadata CSV. If None, will search in default location.
    asos_metadata_file : str or Path, optional
        Path to ASOS stations CSV. If None, will search in default location.
    mesonet_metadata_file : str or Path, optional
        Path to Mesonet metadata CSV. If None, will search in OUTPUT_DIR / 'mesonet'.
    output_file : str or Path, optional
        Path to save HTML map. If None, map is displayed inline (returns Folium map object).
    base_path : Path, optional
        Project base path. If None, will try to import from config or auto-detect.
    output_dir : Path, optional
        Output directory path. If None, will try to import from config or use default.
    
    Returns
    -------
    folium.Map or None
        Interactive Folium map with all stations and links plotted.
        Returns None if no metadata could be loaded.
    
    Examples
    --------
    >>> from pathlib import Path
    >>> from src.analysis.plotting import plot_all_metadata_on_map
    >>> 
    >>> # Create map (display inline in Jupyter)
    >>> map_obj = plot_all_metadata_on_map()
    >>> 
    >>> # Save map to HTML file
    >>> plot_all_metadata_on_map(output_file="dataset_maps/all_stations_map.html")
    """
    try:
        import folium
        from folium import plugins
    except ImportError:
        print("⚠ Error: folium is required for map creation. Install with: pip install folium")
        return None
    
    # Import config for paths
    if base_path is None or output_dir is None:
        try:
            from config_analysis import BASE_PATH, OUTPUT_DIR
            if base_path is None:
                base_path = BASE_PATH
            if output_dir is None:
                output_dir = OUTPUT_DIR
        except ImportError:
            # Fallback: auto-detect project root
            if base_path is None:
                current = Path(__file__).resolve()
                for parent in [current.parent.parent] + list(current.parent.parents):
                    if (parent / "dataset").exists() and (parent / "src").exists():
                        base_path = parent
                        break
                if base_path is None:
                    base_path = Path.cwd()
            if output_dir is None:
                output_dir = base_path / "src" / "data" / "output"
    
    print("=" * 70)
    print("CREATING METADATA MAP")
    print("=" * 70)
    
    # ========================================================================
    # Load CML Metadata
    # ========================================================================
    if df_cml_metadata is None:
        cml_metadata_path = base_path / "dataset" / "links" / "links_metadata.csv"
        if cml_metadata_path.exists():
            df_cml_metadata = pd.read_csv(cml_metadata_path)
            print(f"✓ Loaded CML metadata: {len(df_cml_metadata)} sublinks")
        else:
            print(f"✗ CML metadata not found at: {cml_metadata_path}")
            df_cml_metadata = pd.DataFrame()
    else:
        print(f"✓ Using provided CML metadata: {len(df_cml_metadata)} sublinks")
    
    # ========================================================================
    # Load PWS Metadata
    # ========================================================================
    if pws_metadata_file is None:
        pws_metadata_file = base_path / "dataset" / "weather stations" / "pws_metadata.csv"
    
    df_pws_metadata = None
    if Path(pws_metadata_file).exists():
        df_pws_metadata = pd.read_csv(pws_metadata_file)
        # Handle both 'Latitude' and 'latitude' column names
        if 'Latitude' in df_pws_metadata.columns:
            df_pws_metadata = df_pws_metadata.rename(columns={
                'Latitude': 'latitude', 
                'Longitude': 'longitude',
                'Station ID': 'station_id'
            })
        print(f"✓ Loaded PWS metadata: {len(df_pws_metadata)} stations")
    else:
        print(f"✗ PWS metadata not found at: {pws_metadata_file}")
    
    # ========================================================================
    # Load ASOS Metadata
    # ========================================================================
    if asos_metadata_file is None:
        asos_metadata_file = base_path / "dataset" / "weather stations" / "ASOS_stations.csv"
    
    df_asos_metadata = None
    if Path(asos_metadata_file).exists():
        df_asos_metadata = pd.read_csv(asos_metadata_file)
        # Handle both 'Latitude' and 'latitude' column names
        if 'Latitude' in df_asos_metadata.columns:
            df_asos_metadata = df_asos_metadata.rename(columns={
                'Latitude': 'latitude', 
                'Longitude': 'longitude',
                'Station ID': 'station_id'
            })
        print(f"✓ Loaded ASOS metadata: {len(df_asos_metadata)} stations")
    else:
        print(f"✗ ASOS metadata not found at: {asos_metadata_file}")
    
    # ========================================================================
    # Load Mesonet Metadata
    # ========================================================================
    if mesonet_metadata_file is None:
        mesonet_metadata_file = output_dir / "mesonet" / "mesonet_metadata.csv"
    
    df_mesonet_metadata = None
    if Path(mesonet_metadata_file).exists():
        df_mesonet_metadata = pd.read_csv(mesonet_metadata_file)
        print(f"✓ Loaded Mesonet metadata: {len(df_mesonet_metadata)} stations")
    else:
        print(f"✗ Mesonet metadata not found at: {mesonet_metadata_file}")
    
    # ========================================================================
    # Calculate map center and bounds
    # ========================================================================
    all_lats = []
    all_lons = []
    
    # Collect all coordinates
    if not df_cml_metadata.empty and 'site_0_lat' in df_cml_metadata.columns:
        all_lats.extend(df_cml_metadata['site_0_lat'].dropna())
        all_lats.extend(df_cml_metadata['site_1_lat'].dropna())
        all_lons.extend(df_cml_metadata['site_0_lon'].dropna())
        all_lons.extend(df_cml_metadata['site_1_lon'].dropna())
    
    if df_pws_metadata is not None and not df_pws_metadata.empty and 'latitude' in df_pws_metadata.columns:
        all_lats.extend(df_pws_metadata['latitude'].dropna())
        all_lons.extend(df_pws_metadata['longitude'].dropna())
    
    if df_asos_metadata is not None and not df_asos_metadata.empty and 'latitude' in df_asos_metadata.columns:
        all_lats.extend(df_asos_metadata['latitude'].dropna())
        all_lons.extend(df_asos_metadata['longitude'].dropna())
    
    if df_mesonet_metadata is not None and not df_mesonet_metadata.empty and 'latitude' in df_mesonet_metadata.columns:
        all_lats.extend(df_mesonet_metadata['latitude'].dropna())
        all_lons.extend(df_mesonet_metadata['longitude'].dropna())
    
    if not all_lats:
        print("⚠ No metadata coordinates found - cannot create map")
        return None
    
    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)
    
    # ========================================================================
    # Create Folium Map
    # ========================================================================
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles='OpenStreetMap'
    )
    
    # Add different tile layers
    folium.TileLayer('CartoDB positron', name='CartoDB Positron').add_to(m)
    folium.TileLayer('CartoDB dark_matter', name='CartoDB Dark').add_to(m)
    
    # ========================================================================
    # Add CML Links (lines connecting site pairs)
    # ========================================================================
    if not df_cml_metadata.empty and 'cml_id' in df_cml_metadata.columns:
        cml_group = folium.FeatureGroup(name='CML Links', show=True)
        
        # Group by cml_id to avoid duplicate lines
        for cml_id, group in df_cml_metadata.groupby('cml_id'):
            # Use first sublink's coordinates for the link
            first_sublink = group.iloc[0]
            site0_lat = first_sublink['site_0_lat']
            site0_lon = first_sublink['site_0_lon']
            site1_lat = first_sublink['site_1_lat']
            site1_lon = first_sublink['site_1_lon']
            
            # Get link metadata for popup
            frequency = first_sublink.get('frequency', 'N/A')
            length = first_sublink.get('length', 'N/A')
            polarization = first_sublink.get('polarization', 'N/A')
            
            # Draw line
            folium.PolyLine(
                locations=[[site0_lat, site0_lon], [site1_lat, site1_lon]],
                color='blue',
                weight=2,
                opacity=0.6,
                popup=f'<b>CML Link {cml_id}</b><br>Frequency: {frequency} MHz<br>Length: {length} m<br>Polarization: {polarization}',
                tooltip=f'CML Link {cml_id}'
            ).add_to(cml_group)
            
            # Add markers for endpoints
            folium.CircleMarker(
                location=[site0_lat, site0_lon],
                radius=5,
                popup=f'<b>CML {cml_id}</b><br>Site 0<br>Lat: {site0_lat:.4f}, Lon: {site0_lon:.4f}',
                color='blue',
                fill=True,
                fillColor='blue',
                fillOpacity=0.7
            ).add_to(cml_group)
            
            folium.CircleMarker(
                location=[site1_lat, site1_lon],
                radius=5,
                popup=f'<b>CML {cml_id}</b><br>Site 1<br>Lat: {site1_lat:.4f}, Lon: {site1_lon:.4f}',
                color='blue',
                fill=True,
                fillColor='blue',
                fillOpacity=0.7
            ).add_to(cml_group)
        
        cml_group.add_to(m)
        print(f"✓ Added {len(df_cml_metadata.groupby('cml_id'))} CML links")
    
    # ========================================================================
    # Add PWS Stations
    # ========================================================================
    if df_pws_metadata is not None and not df_pws_metadata.empty:
        pws_group = folium.FeatureGroup(name='PWS Stations', show=True)
        
        for idx, row in df_pws_metadata.iterrows():
            station_id = row.get('station_id', row.get('Station ID', f'PWS_{idx}'))
            lat = row['latitude']
            lon = row['longitude']
            elevation = row.get('Elevation', row.get('elevation', 'N/A'))
            description = row.get('Description', row.get('description', ''))
            
            popup_html = f'<b>PWS Station</b><br>ID: {station_id}'
            if elevation != 'N/A':
                popup_html += f'<br>Elevation: {elevation} m'
            if description:
                popup_html += f'<br>Source: {description}'
            
            folium.CircleMarker(
                location=[lat, lon],
                radius=4,
                popup=popup_html,
                tooltip=station_id,
                color='purple',
                fill=True,
                fillColor='purple',
                fillOpacity=0.7
            ).add_to(pws_group)
        
        pws_group.add_to(m)
        print(f"✓ Added {len(df_pws_metadata)} PWS stations")
    
    # ========================================================================
    # Add ASOS Stations
    # ========================================================================
    if df_asos_metadata is not None and not df_asos_metadata.empty:
        asos_group = folium.FeatureGroup(name='ASOS Stations', show=True)
        
        for idx, row in df_asos_metadata.iterrows():
            station_id = row.get('station_id', row.get('Station ID', f'ASOS_{idx}'))
            lat = row['latitude']
            lon = row['longitude']
            elevation = row.get('Elevation', row.get('elevation', 'N/A'))
            description = row.get('Description', row.get('description', ''))
            
            popup_html = f'<b>ASOS Station</b><br>ID: {station_id}'
            if elevation != 'N/A':
                popup_html += f'<br>Elevation: {elevation} m'
            if description:
                popup_html += f'<br>Source: {description}'
            
            folium.Marker(
                location=[lat, lon],
                popup=popup_html,
                tooltip=station_id,
                icon=folium.Icon(color='red', icon='info-sign', prefix='glyphicon')
            ).add_to(asos_group)
        
        asos_group.add_to(m)
        print(f"✓ Added {len(df_asos_metadata)} ASOS stations")
    
    # ========================================================================
    # Add Mesonet Stations
    # ========================================================================
    if df_mesonet_metadata is not None and not df_mesonet_metadata.empty:
        mesonet_group = folium.FeatureGroup(name='NYC Mesonet Stations', show=True)
        
        for idx, row in df_mesonet_metadata.iterrows():
            station_id = row.get('station', f'Mesonet_{idx}')
            lat = row['latitude']
            lon = row['longitude']
            elevation = row.get('elevation', 'N/A')
            
            popup_html = f'<b>NYC Mesonet Station</b><br>ID: {station_id}'
            if elevation != 'N/A':
                popup_html += f'<br>Elevation: {elevation} m'
            popup_html += f'<br>Lat: {lat:.4f}, Lon: {lon:.4f}'
            
            folium.Marker(
                location=[lat, lon],
                popup=popup_html,
                tooltip=station_id,
                icon=folium.Icon(color='green', icon='cloud', prefix='glyphicon')
            ).add_to(mesonet_group)
        
        mesonet_group.add_to(m)
        print(f"✓ Added {len(df_mesonet_metadata)} Mesonet stations")
    
    # ========================================================================
    # Add Layer Control and Legend
    # ========================================================================
    folium.LayerControl(collapsed=False).add_to(m)
    
    # Add legend
    legend_html = '''
    <div style="position: fixed; 
                bottom: 50px; right: 50px; width: 200px; height: auto; 
                background-color: white; z-index:9999; font-size:14px;
                border:2px solid grey; border-radius: 5px; padding: 12px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3);">
    <p style="margin: 0 0 8px 0; font-weight: bold; font-size: 15px;">Map Legend</p>
    <p style="margin: 6px 0;"><span style="color: blue; font-size: 18px;">━</span> CML Links</p>
    <p style="margin: 6px 0;"><span style="color: purple; font-size: 18px;">●</span> PWS Stations</p>
    <p style="margin: 6px 0;"><span style="color: red; font-size: 18px;">📍</span> ASOS Stations</p>
    <p style="margin: 6px 0;"><span style="color: green; font-size: 18px;">☁</span> Mesonet Stations</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # ========================================================================
    # Save or return map
    # ========================================================================
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        m.save(str(output_path))
        print(f"\n✓ Map saved to: {output_path}")
    
    print("\n" + "=" * 70)
    print("MAP CREATION COMPLETE")
    print("=" * 70)
    
    return m


def plot_all_metadata_grid(
    df_cml_metadata: Optional[pd.DataFrame] = None,
    df_pws_metadata: Optional[pd.DataFrame] = None,
    df_asos_metadata: Optional[pd.DataFrame] = None,
    df_mesonet_metadata: Optional[pd.DataFrame] = None,
    output_dir: Optional[Union[str, Path]] = None,
    base_path: Optional[Union[str, Path]] = None,
    show_plot: bool = True,
    save_png: bool = True,
    save_html: bool = True
) -> Optional[plt.Figure]:
    """
    Create a static grid visualization of all dataset metadata (stations and links).
    
    Parameters
    ----------
    df_cml_metadata : pd.DataFrame, optional
        CML links metadata with columns: 'cml_id', 'site_0_lat', 'site_0_lon', 'site_1_lat', 'site_1_lon'
    df_pws_metadata : pd.DataFrame, optional
        PWS stations metadata with columns: 'latitude', 'longitude'
    df_asos_metadata : pd.DataFrame, optional
        ASOS stations metadata with columns: 'latitude', 'longitude'
    df_mesonet_metadata : pd.DataFrame, optional
        Mesonet stations metadata with columns: 'latitude', 'longitude'
    output_dir : str or Path, optional
        Directory to save output files. If None, uses base_path / "dataset_maps"
    base_path : str or Path, optional
        Project base path. If None, tries to import from config_analysis
    show_plot : bool, default True
        Whether to display the plot
    save_png : bool, default True
        Whether to save PNG file
    save_html : bool, default True
        Whether to save HTML file
    
    Returns
    -------
    matplotlib.figure.Figure or None
        Figure object if plot was created, None otherwise
    
    Examples
    --------
    >>> from plotting import plot_all_metadata_grid
    >>> from config_analysis import load_all_metadata
    >>> 
    >>> all_metadata = load_all_metadata()
    >>> fig = plot_all_metadata_grid(
    ...     df_cml_metadata=all_metadata['cml'],
    ...     df_pws_metadata=all_metadata['pws'],
    ...     df_asos_metadata=all_metadata['asos'],
    ...     df_mesonet_metadata=all_metadata['mesonet']
    ... )
    """
    # Import config for paths if needed
    if base_path is None or output_dir is None:
        try:
            from config_analysis import BASE_PATH
            if base_path is None:
                base_path = BASE_PATH
        except ImportError:
            if base_path is None:
                base_path = Path.cwd()
    
    if output_dir is None:
        output_dir = Path(base_path) / "dataset_maps"
    else:
        output_dir = Path(output_dir)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 12))
    
    # Collect all coordinates for bounds
    all_lats = []
    all_lons = []
    
    # Plot CML Links (blue lines)
    n_cml_links = 0
    if df_cml_metadata is not None and not df_cml_metadata.empty:
        if 'cml_id' in df_cml_metadata.columns:
            cml_plotted = False
            for cml_id, group in df_cml_metadata.groupby('cml_id'):
                first_sublink = group.iloc[0]
                if all(col in first_sublink for col in ['site_0_lat', 'site_0_lon', 'site_1_lat', 'site_1_lon']):
                    lat0, lon0 = first_sublink['site_0_lat'], first_sublink['site_0_lon']
                    lat1, lon1 = first_sublink['site_1_lat'], first_sublink['site_1_lon']
                    label = 'CML Links' if not cml_plotted else ''
                    ax.plot([lon0, lon1], [lat0, lat1], 'b-', linewidth=1.5, alpha=0.6, label=label)
                    cml_plotted = True
                    n_cml_links += 1
                    all_lats.extend([lat0, lat1])
                    all_lons.extend([lon0, lon1])
    
    # Plot PWS Stations (purple circles)
    n_pws = 0
    if df_pws_metadata is not None and not df_pws_metadata.empty:
        if 'latitude' in df_pws_metadata.columns and 'longitude' in df_pws_metadata.columns:
            ax.scatter(df_pws_metadata['longitude'], df_pws_metadata['latitude'], 
                      c='purple', s=30, marker='o', alpha=0.7, label='PWS Stations', 
                      edgecolors='darkviolet', linewidths=0.5)
            all_lats.extend(df_pws_metadata['latitude'].dropna())
            all_lons.extend(df_pws_metadata['longitude'].dropna())
            n_pws = len(df_pws_metadata)
    
    # Plot ASOS Stations (red triangles)
    n_asos = 0
    if df_asos_metadata is not None and not df_asos_metadata.empty:
        if 'latitude' in df_asos_metadata.columns and 'longitude' in df_asos_metadata.columns:
            ax.scatter(df_asos_metadata['longitude'], df_asos_metadata['latitude'], 
                      c='red', s=100, marker='^', alpha=0.8, label='ASOS Stations', 
                      edgecolors='darkred', linewidths=1)
            all_lats.extend(df_asos_metadata['latitude'].dropna())
            all_lons.extend(df_asos_metadata['longitude'].dropna())
            n_asos = len(df_asos_metadata)
    
    # Plot Mesonet Stations (green squares)
    n_mesonet = 0
    if df_mesonet_metadata is not None and not df_mesonet_metadata.empty:
        if 'latitude' in df_mesonet_metadata.columns and 'longitude' in df_mesonet_metadata.columns:
            ax.scatter(df_mesonet_metadata['longitude'], df_mesonet_metadata['latitude'], 
                      c='green', s=100, marker='s', alpha=0.8, label='NYC Mesonet', 
                      edgecolors='darkgreen', linewidths=1)
            all_lats.extend(df_mesonet_metadata['latitude'].dropna())
            all_lons.extend(df_mesonet_metadata['longitude'].dropna())
            n_mesonet = len(df_mesonet_metadata)
    
    # Check if we have any coordinates
    if not all_lats or not all_lons:
        print("⚠ No coordinates found - cannot create visualization")
        plt.close(fig)
        return None
    
    # Set plot bounds with some padding
    lat_margin = (max(all_lats) - min(all_lats)) * 0.1
    lon_margin = (max(all_lons) - min(all_lons)) * 0.1
    ax.set_xlim(min(all_lons) - lon_margin, max(all_lons) + lon_margin)
    ax.set_ylim(min(all_lats) - lat_margin, max(all_lats) + lat_margin)
    ax.set_aspect('equal', adjustable='box')
    ax.set_xlabel('Longitude (°)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Latitude (°)', fontsize=12, fontweight='bold')
    ax.set_title('All Dataset Stations and Links\n(CML Links, PWS, ASOS, Mesonet)', 
                 fontsize=14, fontweight='bold', pad=15)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='upper right', fontsize=10, framealpha=0.9)
    plt.tight_layout()
    
    print(f"  Plotted: {n_cml_links} CML links, {n_pws} PWS, {n_asos} ASOS, {n_mesonet} Mesonet")
    
    # Save as PNG
    if save_png:
        output_dir.mkdir(parents=True, exist_ok=True)
        png_path = output_dir / "all_stations_grid.png"
        plt.savefig(png_path, dpi=300, bbox_inches='tight')
        print(f"✓ Grid visualization saved to: {png_path}")
    
    # Save as HTML
    if save_html:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        import base64
        from io import BytesIO
        
        canvas = FigureCanvasAgg(fig)
        buf = BytesIO()
        canvas.print_png(buf)
        img_data = base64.b64encode(buf.getvalue()).decode('utf-8')
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>All Stations and Links Grid Map</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; }}
        .legend {{ margin: 20px 0; padding: 15px; background-color: #f9f9f9; border-radius: 5px; }}
        .legend-item {{ margin: 5px 0; }}
        img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>All Dataset Stations and Links</h1>
        <div class="legend">
            <h3>Legend</h3>
            <div class="legend-item"><strong>Blue Lines:</strong> CML Links (Commercial Microwave Links)</div>
            <div class="legend-item"><strong>Purple Circles:</strong> PWS Stations (Personal Weather Stations)</div>
            <div class="legend-item"><strong>Red Triangles:</strong> ASOS Stations (NOAA Automated Surface Observing System)</div>
            <div class="legend-item"><strong>Green Squares:</strong> NYC Mesonet Stations</div>
        </div>
        <img src="data:image/png;base64,{img_data}" alt="Stations and Links Grid Map">
    </div>
</body>
</html>"""
        
        output_dir.mkdir(parents=True, exist_ok=True)
        html_path = output_dir / "all_stations_grid.html"
        with open(html_path, 'w') as f:
            f.write(html_content)
        print(f"✓ HTML visualization saved to: {html_path}")
    
    if show_plot:
        plt.show()
    else:
        plt.close(fig)
    
    return fig

"""
Match CML Links with PWS Stations
==================================

Functions to:
1. Calculate distance between CML link midpoint and PWS stations
2. Find nearest PWS stations for each CML link
3. Organize extracted data by CML->PWS mapping

Methods:
- 'closest_n': Find N closest PWS stations
- 'distance_radius': Find PWS within radius (meters)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


# =============================================================================
# FUNCTION 1: Calculate Distance Between Two Coordinates
# =============================================================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two points using Haversine formula.
    
    Parameters
    ----------
    lat1, lon1 : float
        First point (latitude, longitude)
    lat2, lon2 : float
        Second point (latitude, longitude)
    
    Returns
    -------
    distance : float
        Distance in meters
    """
    R = 6371000  # Earth radius in meters
    
    lat1_rad = np.radians(lat1)
    lat2_rad = np.radians(lat2)
    delta_lat = np.radians(lat2 - lat1)
    delta_lon = np.radians(lon2 - lon1)
    
    a = np.sin(delta_lat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c


# =============================================================================
# FUNCTION 2: Find Weather Stations Near CML Link (Generalized)
# =============================================================================

def find_nearest_ws(
    cml_metadata: pd.DataFrame,
    ws_metadata: pd.DataFrame,
    cml_id: str,
    method: str = 'closest_n',
    n_nearest: int = 3,
    radius_m: float = 5000,
    station_id_col: str = 'station_id',
) -> pd.DataFrame:
    """
    Find weather stations nearest to a CML link (works with any station type).
    
    Parameters
    ----------
    cml_metadata : pd.DataFrame
        CML metadata (has site_0_lat, site_0_lon, site_1_lat, site_1_lon)
    ws_metadata : pd.DataFrame
        Weather station metadata (has latitude, longitude, and station_id_col)
    cml_id : str
        CML link ID to match
    method : str
        'closest_n': Find N closest stations (uses n_nearest)
        'distance_radius': Find all within radius (uses radius_m)
    n_nearest : int
        Number of nearest stations to return (for method='closest_n')
    radius_m : float
        Radius in meters (for method='distance_radius')
    station_id_col : str
        Column name for station ID (default: 'station_id')
        Can be 'station_id', 'station', etc.
    
    Returns
    -------
    result : pd.DataFrame
        Weather stations with columns: station_id (or station_id_col), latitude, longitude, distance_m
    """
    # Get CML link info
    cml_row = cml_metadata[cml_metadata['cml_id'] == cml_id]
    
    if len(cml_row) == 0:
        print(f"⚠ CML ID {cml_id} not found")
        return pd.DataFrame()
    
    # Calculate midpoint of link
    site_0_lat = cml_row['site_0_lat'].values[0]
    site_0_lon = cml_row['site_0_lon'].values[0]
    site_1_lat = cml_row['site_1_lat'].values[0]
    site_1_lon = cml_row['site_1_lon'].values[0]
    
    link_mid_lat = (site_0_lat + site_1_lat) / 2
    link_mid_lon = (site_0_lon + site_1_lon) / 2
    
    # Calculate distance to all weather stations
    distances = []
    for idx, ws_row in ws_metadata.iterrows():
        dist = haversine_distance(
            link_mid_lat, link_mid_lon,
            ws_row['latitude'], ws_row['longitude']
        )
        distances.append(dist)
    
    ws_metadata_copy = ws_metadata.copy()
    ws_metadata_copy['distance_m'] = distances
    ws_metadata_copy = ws_metadata_copy.sort_values('distance_m')
    
    # Filter by method
    if method == 'closest_n':
        result = ws_metadata_copy.head(n_nearest).copy()
    elif method == 'distance_radius':
        result = ws_metadata_copy[ws_metadata_copy['distance_m'] <= radius_m].copy()
    else:
        raise ValueError(f"Unknown method: {method}")
    
    # Ensure station_id column exists (rename if needed)
    if station_id_col != 'station_id' and station_id_col in result.columns:
        result = result.rename(columns={station_id_col: 'station_id'})
    
    return result


# Backward compatibility: keep old function name
def find_nearest_pws(
    cml_metadata: pd.DataFrame,
    pws_metadata: pd.DataFrame,
    cml_id: str,
    method: str = 'closest_n',
    n_nearest: int = 3,
    radius_m: float = 5000,
) -> pd.DataFrame:
    """Backward compatibility wrapper for find_nearest_ws."""
    return find_nearest_ws(
        cml_metadata, pws_metadata, cml_id, method, n_nearest, radius_m, station_id_col='station_id'
    )


# =============================================================================
# FUNCTION 3: Match All CML Links with Weather Stations (Generalized)
# =============================================================================

def match_cml_to_ws(
    cml_metadata: pd.DataFrame,
    ws_metadata: pd.DataFrame,
    method: str = 'closest_n',
    n_nearest: int = 3,
    radius_m: float = 5000,
    station_id_col: str = 'station_id',
    ws_type: str = 'weather stations',
    max_distance_km: Optional[float] = None,
) -> Dict[str, pd.DataFrame]:
    """
    For each CML link, find matching weather stations (works with any station type).
    
    Parameters
    ----------
    cml_metadata : pd.DataFrame
        CML metadata (with site_0_lat, site_0_lon, site_1_lat, site_1_lon, cml_id)
    ws_metadata : pd.DataFrame
        Weather station metadata (with latitude, longitude, and station_id_col)
        Can be PWS, ASOS, Mesonet, or any other station type
    method : str
        'closest_n' or 'distance_radius'
    n_nearest : int
        For method='closest_n': number of nearest stations
    radius_m : float
        For method='distance_radius': radius in meters
    station_id_col : str
        Column name for station ID (default: 'station_id')
        Can be 'station_id', 'station', etc.
    ws_type : str
        Label for station type (for printing), e.g., 'PWS', 'ASOS', 'Mesonet'
    max_distance_km : float, optional
        Maximum distance threshold in kilometers. When provided with method='closest_n',
        filters the n_nearest stations to only include those within this distance.
        Example: max_distance_km=5.0 means only stations within 5 km will be included.
        Default is None (no distance filtering).
    
    Returns
    -------
    cml_to_ws : dict
        {cml_id: DataFrame with matched weather stations}
        Each DataFrame has columns: station_id, latitude, longitude, distance_m
    """
    cml_to_ws = {}
    
    print(f"Matching CML links to {ws_type}:")
    print("-" * 70)
    print(f"Method: {method}", end="")
    if method == 'closest_n':
        print(f" (N={n_nearest})", end="")
        if max_distance_km is not None:
            print(f" + max_distance={max_distance_km}km", end="")
        print()
    else:
        print(f" (radius={radius_m}m)")
    print()
    
    # Get unique CML IDs
    unique_cml_ids = cml_metadata['cml_id'].unique()
    
    for cml_id in unique_cml_ids:
        ws_matches = find_nearest_ws(
            cml_metadata,
            ws_metadata,
            cml_id,
            method=method,
            n_nearest=n_nearest,
            radius_m=radius_m,
            station_id_col=station_id_col,
        )
        
        # Apply distance threshold if specified (for closest_n method)
        if max_distance_km is not None and method == 'closest_n' and len(ws_matches) > 0:
            max_distance_m = max_distance_km * 1000  # Convert km to meters
            before_count = len(ws_matches)
            ws_matches = ws_matches[ws_matches['distance_m'] <= max_distance_m].copy()
            if len(ws_matches) < before_count:
                print(f"  CML {cml_id}: Filtered from {before_count} to {len(ws_matches)} stations (within {max_distance_km}km)")
        
        if len(ws_matches) > 0:
            cml_to_ws[cml_id] = ws_matches
            station_ids = ws_matches['station_id'].tolist()
            distances = ws_matches['distance_m'].tolist()
            print(f"  CML {cml_id}: {len(ws_matches)} {ws_type} found")
            for station_id, dist in zip(station_ids, distances):
                dist_km = dist / 1000
                print(f"    - {station_id}: {dist:.0f}m ({dist_km:.2f}km)")
        else:
            print(f"  CML {cml_id}: No {ws_type} found")
    
    print()
    return cml_to_ws


# Backward compatibility: keep old function name
def match_cml_to_pws(
    cml_metadata: pd.DataFrame,
    pws_metadata: pd.DataFrame,
    method: str = 'closest_n',
    n_nearest: int = 3,
    radius_m: float = 5000,
    max_distance_km: Optional[float] = None,
) -> Dict[str, pd.DataFrame]:
    """Backward compatibility wrapper for match_cml_to_ws."""
    return match_cml_to_ws(
        cml_metadata, pws_metadata, method, n_nearest, radius_m,
        station_id_col='station_id', ws_type='PWS', max_distance_km=max_distance_km
    )


# =============================================================================
# FUNCTION 4: Extract and Organize Data by CML->PWS Mapping
# =============================================================================

def organize_by_cml_pws(
    df_cml_dict: Dict[str, pd.DataFrame],
    df_pws_dict: Dict[str, pd.DataFrame],
    cml_to_pws_map: Dict[str, pd.DataFrame],
) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Organize CML and PWS data by CML->PWS mapping.
    
    Parameters
    ----------
    df_cml_dict : dict
        From extract_cml_timeseries_dict()
        Keys like: '1_1', '2_1', ...
    df_pws_dict : dict
        PWS data from extract_parameters()['precip'] or similar
        Keys like: 'pws' if merged, or station IDs if separate
    cml_to_pws_map : dict
        From match_cml_to_pws()
        Keys: cml_id, Values: DataFrame with PWS matches
    
    Returns
    -------
    organized : dict
        {cml_id: {pws_station_id: df}}
        Each df is matched pair (CML + nearby PWS)
    """
    organized = {}
    
    print("Organizing by CML->PWS mapping:")
    print("-" * 70)
    
    for cml_id, pws_matches in cml_to_pws_map.items():
        organized[cml_id] = {}
        
        # Find CML data for this link
        cml_keys = [k for k in df_cml_dict.keys() if k.startswith(f"{cml_id}_")]
        
        if not cml_keys:
            print(f"  ⚠ CML {cml_id}: No data found in df_cml_dict")
            continue
        
        cml_data = df_cml_dict[cml_keys[0]]  # Get first sublink
        
        # Match with PWS
        pws_ids = pws_matches['station_id'].tolist()
        
        for pws_id in pws_ids:
            # Try to find PWS data
            if isinstance(df_pws_dict, dict):
                # If PWS dict has 'pws' key with all PWS combined
                if 'pws' in df_pws_dict:
                    if pws_id in df_pws_dict['pws'].columns:
                        pws_data = df_pws_dict['pws'][[pws_id]].copy()
                        pws_data.columns = [pws_id]
                    else:
                        continue
                # If PWS dict has individual station keys
                elif pws_id in df_pws_dict:
                    pws_data = df_pws_dict[pws_id]
                else:
                    continue
            else:
                continue
            
            # Store pair
            organized[cml_id][pws_id] = {
                'cml': cml_data,
                'pws': pws_data,
                'cml_key': cml_keys[0],
            }
        
        print(f"  ✓ CML {cml_id}: {len(organized[cml_id])} PWS pairs")
    
    print()
    return organized


# =============================================================================
# FUNCTION 5: Summary - Show Mapping
# =============================================================================

def show_cml_pws_mapping(cml_to_pws_map: Dict[str, pd.DataFrame]):
    """
    Print summary of CML->PWS mapping.
    """
    print("=" * 70)
    print("CML -> PWS MAPPING SUMMARY")
    print("=" * 70)
    
    total_pairs = 0
    for cml_id, pws_df in cml_to_pws_map.items():
        n_pws = len(pws_df)
        total_pairs += n_pws
        pws_list = ', '.join(pws_df['station_id'].tolist())
        print(f"\nCML {cml_id} → {n_pws} PWS")
        print(f"  {pws_list}")
        print(f"  Distances: {', '.join([f'{d:.0f}m' for d in pws_df['distance_m']])}")
    
    print(f"\nTotal pairs: {total_pairs}")
    print("=" * 70 + "\n")


# =============================================================================
# FUNCTION 6: Filter Mapping to Selected CML IDs
# =============================================================================

def filter_cml_pws_map(
    cml_to_pws_map: Dict[str, pd.DataFrame],
    cml_ids: List[str]
) -> Dict[str, pd.DataFrame]:
    """
    Filter CML->PWS mapping to only include selected CML IDs.
    
    Parameters
    ----------
    cml_to_pws_map : dict
        Full mapping from match_cml_to_pws()
        Keys: cml_id, Values: DataFrame with PWS matches
    cml_ids : list
        List of CML IDs to keep in the filtered mapping
    
    Returns
    -------
    filtered_map : dict
        Subset of cml_to_pws_map containing only the selected CML IDs
        Same structure: {cml_id: DataFrame with PWS matches}
    
    Examples
    --------
    >>> # Filter to only CML IDs '1', '2', '5'
    >>> selected_cmls = ['1', '2', '5']
    >>> filtered_map = filter_cml_pws_map(cml_to_pws_map, selected_cmls)
    >>> show_cml_pws_mapping(filtered_map)
    """
    filtered = {}
    not_found = []
    
    for cml_id in cml_ids:
        if cml_id in cml_to_pws_map:
            filtered[cml_id] = cml_to_pws_map[cml_id]
        else:
            not_found.append(cml_id)
    
    if not_found:
        print(f"⚠ Warning: CML IDs not found in mapping: {not_found}")
    
    print(f"✓ Filtered mapping: {len(filtered)}/{len(cml_ids)} CML IDs")
    
    return filtered


"""
Snow-specific plotting functions for OpenMesh data analysis.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Optional, List, Dict, Union
from load_data import extract_cml_timeseries_dict


def categorize_precip_type(ptype_str):
    """
    Categorize precipitation type from ASOS ptype code.
    
    Parameters
    ----------
    ptype_str : str
        Precipitation type code from ASOS (e.g., 'R', 'S', 'RS', etc.)
    
    Returns
    -------
    str
        Category: 'none', 'rain', 'snow', 'mix', 'precip'
    """
    if pd.isna(ptype_str) or ptype_str == '':
        return 'none'
    ptype_str = str(ptype_str).upper().strip()
    
    # Check for mix (contains both R and S)
    has_rain = 'R' in ptype_str
    has_snow = 'S' in ptype_str
    
    if has_rain and has_snow:
        return 'mix'
    elif has_rain:
        return 'rain'
    elif has_snow:
        return 'snow'
    elif 'P' in ptype_str:  # Precipitation but type uncertain
        return 'precip'
    else:
        return 'none'


def plot_cml_attenuation_on_days(
    df_cml_dict,
    event_days,
    event_name="Event",
    window_days=1,
    show_legend=False
):
    """
    Plot CML attenuation data on specific event days.
    
    Parameters
    ----------
    df_cml_dict : dict
        Dictionary of CML DataFrames {cml_id: df} from extract_cml_timeseries_dict()
    event_days : list
        List of event dates to plot
    event_name : str
        Name for plot titles (default: "Event")
    window_days : int
        Days before/after event to show (default: 1)
    show_legend : bool
        Whether to show legend (default: False)
    """
    fig, axes = plt.subplots(len(event_days), 1, figsize=(16, 4*len(event_days)))
    if len(event_days) == 1:
        axes = [axes]
    
    colors = plt.cm.tab10(np.linspace(0, 1, len(df_cml_dict)))
    
    for day_idx, event_day in enumerate(event_days):
        ax = axes[day_idx]
        
        window_start = event_day - pd.Timedelta(days=window_days)
        window_end = event_day + pd.Timedelta(days=window_days+1)
        
        for color_idx, (cml_key, df_cml) in enumerate(df_cml_dict.items()):
            # Filter to window BEFORE plotting
            data_window = df_cml.loc[window_start:window_end, 'attenuation']
            
            if len(data_window) > 0:
                ax.plot(data_window.index, data_window.values, 
                       linewidth=2, marker='o', markersize=3, 
                       label=cml_key if show_legend else None,
                       color=colors[color_idx], alpha=0.8)
        
        # Highlight event day
        ax.axvspan(event_day, event_day + pd.Timedelta(days=1), 
                  alpha=0.15, color='red', zorder=1)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)
        
        ax.set_title(f'{event_day.strftime("%Y-%m-%d")} - {event_name} (±{window_days} day)', 
                    fontsize=12, fontweight='bold')
        ax.set_ylabel('Attenuation (dB)', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        if show_legend:
            ax.legend(loc='upper left', fontsize=9, ncol=3)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    plt.show()


def _plot_precip_type_below(snow_day, all_params, window_days=1):
    """
    Plot precipitation type below main figure with gray/cyan colors.
    Categories: mix/rain/snow based on NOAA 1min data.
    
    Parameters
    ----------
    snow_day : pd.Timestamp
        Snow day to plot
    all_params : dict
        Dictionary containing 'p_class' data
    window_days : int
        Days before/after to show (default: 1)
    """
    # Get precipitation type data
    if 'precip_type' not in all_params:
        print("⚠️ No precip_type data available")
        return
    
    precip_type_data = all_params['precip_type']
    if 'asos_1min' not in precip_type_data:
        print("⚠️ No ASOS 1min precip_type data available")
        return
    
    precip_type_df = precip_type_data['asos_1min']
    if precip_type_df is None or len(precip_type_df) == 0:
        print("⚠️ Precip type DataFrame is empty")
        return
    
    # Time window
    window_start = snow_day - pd.Timedelta(days=window_days)
    window_end = snow_day + pd.Timedelta(days=window_days + 1)
    
    # Filter to window
    precip_window = precip_type_df.loc[window_start:window_end]
    
    if len(precip_window) == 0:
        print(f"⚠️ No precip type data for {snow_day.strftime('%Y-%m-%d')}")
        return
    
    # Create figure with 3 subplots for mix/rain/snow
    fig, axes = plt.subplots(3, 1, figsize=(20, 8), sharex=True)
    ax_mix = axes[0]
    ax_rain = axes[1]
    ax_snow = axes[2]
    
    # Process each station
    for col in precip_window.columns:
        col_data = precip_window[col].dropna()
        if len(col_data) == 0:
            continue
        
        # Categorize each time point
        categories = col_data.apply(categorize_precip_type)
        time_index = col_data.index
        
        # Mix (gray)
        mix_mask = categories == 'mix'
        if mix_mask.any():
            ax_mix.scatter(time_index[mix_mask], [1] * mix_mask.sum(),
                          color='gray', s=50, alpha=0.7, label=col)
        
        # Rain (cyan)
        rain_mask = categories == 'rain'
        if rain_mask.any():
            ax_rain.scatter(time_index[rain_mask], [1] * rain_mask.sum(),
                           color='cyan', s=50, alpha=0.7, label=col)
        
        # Snow (cyan)
        snow_mask = categories == 'snow'
        if snow_mask.any():
            ax_snow.scatter(time_index[snow_mask], [1] * snow_mask.sum(),
                           color='cyan', s=50, alpha=0.7, label=col)
    
    # Format mix subplot
    ax_mix.axvspan(snow_day, snow_day + pd.Timedelta(days=1), 
                  alpha=0.15, color='red', zorder=0, label='Snow day')
    ax_mix.set_ylabel('Mix', fontsize=12, fontweight='bold')
    ax_mix.set_title(f'Precipitation Type (NOAA 1min) - {snow_day.strftime("%Y-%m-%d")}', 
                    fontsize=14, fontweight='bold', loc='left')
    ax_mix.set_ylim(0.5, 1.5)
    ax_mix.set_yticks([1])
    ax_mix.set_yticklabels([''])
    ax_mix.grid(True, alpha=0.3, axis='x')
    ax_mix.legend(loc='upper right', fontsize=8, ncol=3)
    
    # Format rain subplot
    ax_rain.axvspan(snow_day, snow_day + pd.Timedelta(days=1), 
                   alpha=0.15, color='red', zorder=0)
    ax_rain.set_ylabel('Rain', fontsize=12, fontweight='bold')
    ax_rain.set_ylim(0.5, 1.5)
    ax_rain.set_yticks([1])
    ax_rain.set_yticklabels([''])
    ax_rain.grid(True, alpha=0.3, axis='x')
    ax_rain.legend(loc='upper right', fontsize=8, ncol=3)
    
    # Format snow subplot
    ax_snow.axvspan(snow_day, snow_day + pd.Timedelta(days=1), 
                   alpha=0.15, color='red', zorder=0)
    ax_snow.set_ylabel('Snow', fontsize=12, fontweight='bold')
    ax_snow.set_xlabel('Time', fontsize=12, fontweight='bold')
    ax_snow.set_ylim(0.5, 1.5)
    ax_snow.set_yticks([1])
    ax_snow.set_yticklabels([''])
    ax_snow.grid(True, alpha=0.3, axis='x')
    ax_snow.legend(loc='upper right', fontsize=8, ncol=3)
    
    # Format x-axis
    ax_snow.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    plt.setp(ax_snow.xaxis.get_majorticklabels(), rotation=45, ha='right')
    ax_mix.set_xticklabels([])
    ax_rain.set_xticklabels([])
    
    plt.tight_layout()
    plt.show()
    print(f"✓ Plotted precipitation type for {snow_day.strftime('%Y-%m-%d')}")


def plot_cml_on_snow_days_with_precip_type(
    df_cml_meta,
    ds_cml,
    snow_days,
    all_params,
    freq_range=(62000, 70000),
    length_range=(1000, 20000),
    window_size='3H',
    quantile=0.9999,
    sublink_mode='part',
    window_days=1,
    show_legend=False
):
    """
    Filter CMLs by frequency & length, plot attenuation on snowy days,
    and add precipitation type visualization below.
    
    Parameters
    ----------
    df_cml_meta : pd.DataFrame
        CML metadata DataFrame
    ds_cml : xr.Dataset
        CML xarray Dataset
    snow_days : list
        List of snow day timestamps
    all_params : dict
        Dictionary containing all weather parameters including 'precip_type'
    freq_range : tuple
        Frequency range in MHz (min, max)
    length_range : tuple
        Length range in meters (min, max)
    window_size : str
        Window size for baseline calculation (default: '3H')
    quantile : float
        Quantile for baseline calculation (default: 0.9999)
    sublink_mode : str
        'part' or 'full' for sublink extraction
    window_days : int
        Days before/after to show (default: 1)
    show_legend : bool
        Whether to show legend (default: False)
    """
    # STEP 1: Filter CML metadata by frequency and length
    print("=" * 70)
    print("FILTERING CML METADATA")
    print("=" * 70)
    
    df_filtered = df_cml_meta.copy()
    
    # Filter by frequency
    if freq_range:
        df_filtered = df_filtered[
            (df_filtered['frequency'] >= freq_range[0]) & 
            (df_filtered['frequency'] <= freq_range[1])
        ]
        print(f"After frequency filter ({freq_range[0]}-{freq_range[1]} MHz): {len(df_filtered)} links")
    
    # Filter by length
    if length_range:
        df_filtered = df_filtered[
            (df_filtered['length'] >= length_range[0]) & 
            (df_filtered['length'] <= length_range[1])
        ]
        print(f"After length filter ({length_range[0]}-{length_range[1]} m): {len(df_filtered)} links")
    
    # Get unique CML IDs (as strings to match dataset)
    selected_cml_ids = set(df_filtered['cml_id'].astype(str).unique())
    print(f"\n✓ Selected {len(selected_cml_ids)} unique CML IDs")
    print(f"CML IDs: {sorted(selected_cml_ids, key=lambda x: int(x))[:20]}")
    
    # STEP 2: Extract ALL time series
    print("\n" + "=" * 70)
    df_cml_all = extract_cml_timeseries_dict(
        ds_cml,
        window_size=window_size,
        quantile=quantile,
        sublink_mode=sublink_mode
    )
    
    # STEP 3: Filter the extracted dict to only selected CMLs
    df_cml_filtered = {
        key: df for key, df in df_cml_all.items()
        if key.split('_')[0] in selected_cml_ids
    }
    
    print(f"\n✓ Filtered to {len(df_cml_filtered)} CML time series")
    print(f"Keys: {list(df_cml_filtered.keys())}")
    
    # STEP 4: Plot on snowy days with precipitation type
    if len(df_cml_filtered) > 0:
        for snow_day in snow_days:
            # Main plot: CML attenuation
            plot_cml_attenuation_on_days(
                df_cml_filtered,
                [snow_day],
                event_name="Snow",
                window_days=window_days,
                show_legend=show_legend
            )
            
            # Additional plot: Precipitation type
            _plot_precip_type_below(
                snow_day,
                all_params,
                window_days=window_days
            )
    else:
        print("⚠️ No CMLs matched the filter criteria!")



def plot_snow_day_analysis(
    df_cml_dict,
    snow_days,
    snow_data,
    snow_depth_data,
    temp_data,
    precip_data,
    signal_type='attenuation',  # 'attenuation' or 'rsl'
    brooklyn_station='BKLN',
    window_days=1
):
    """
    Plot snow day analysis with 4 VERTICAL subplots per day (shared time axis):
    1. CML signal (RSL or attenuation)
    2. Snow depth (Brooklyn) 
    3. Temperature
    4. Precipitation (all sources)
    
    Parameters
    ----------
    df_cml_dict : dict
        Dictionary of CML DataFrames {cml_id: df}
    snow_days : list
        List of snow day timestamps
    snow_data : dict
        Snowfall data from all_params['snow']
    snow_depth_data : dict
        Snow depth data from all_params['snow_depth']
    temp_data : dict
        Temperature data from all_params['temp']
    precip_data : dict
        Precipitation data from all_params['precip']
    signal_type : str
        'attenuation' or 'rsl' (default: 'attenuation')
    brooklyn_station : str
        Brooklyn station name (default: 'BKLN')
    window_days : int
        Days before/after to show (default: 1)
    """
    
    colors_cml = plt.cm.tab10(np.linspace(0, 1, len(df_cml_dict)))
    
    for day_idx, snow_day in enumerate(snow_days):
        # Create figure with 4 rows, 1 column - SHARED X-AXIS
        fig, axes = plt.subplots(4, 1, figsize=(20, 16), sharex=True)
        
        ax_signal = axes[0]
        ax_snow = axes[1]
        ax_temp = axes[2]
        ax_precip = axes[3]
        
        window_start = snow_day - pd.Timedelta(days=window_days)
        window_end = snow_day + pd.Timedelta(days=window_days+1)
        
        # ====================================================================
        # SUBPLOT 1: CML Signal (RSL or Attenuation)
        # ====================================================================
        for color_idx, (cml_key, df_cml) in enumerate(df_cml_dict.items()):
            if signal_type in df_cml.columns:
                data_window = df_cml.loc[window_start:window_end, signal_type]
                
                if len(data_window) > 0:
                    ax_signal.plot(data_window.index, data_window.values, 
                                  linewidth=2.5, marker='o', markersize=3, 
                                  color=colors_cml[color_idx], alpha=0.8)
        
        ax_signal.axvspan(snow_day, snow_day + pd.Timedelta(days=1), 
                         alpha=0.15, color='red', zorder=1, label='Snow Day')
        ax_signal.axhline(y=0, color='black', linestyle='-', linewidth=1.5, alpha=0.3)
        
        ylabel = 'Attenuation (dB)' if signal_type == 'attenuation' else 'RSL (dBm)'
        ax_signal.set_title(f'CML {signal_type.upper()}', 
                           fontsize=15, fontweight='bold', loc='left')
        ax_signal.set_ylabel(ylabel, fontsize=13, fontweight='bold')
        ax_signal.grid(True, alpha=0.3, linewidth=1)
        ax_signal.tick_params(labelsize=12)
        ax_signal.legend(loc='upper right', fontsize=10)
        
        # ====================================================================
        # SUBPLOT 2: Snow Depth (Brooklyn) + NOAA Daily Stats
        # ====================================================================
        # Plot Snow DEPTH (Mesonet)
        mesonet_depth = snow_depth_data.get('mesonet')
        if mesonet_depth is not None and brooklyn_station in mesonet_depth.columns:
            depth_window = mesonet_depth[brooklyn_station].loc[window_start:window_end]
            
            if len(depth_window) > 0:
                ax_snow.plot(depth_window.index, depth_window.values, 
                            linewidth=3.5, marker='o', markersize=5, 
                            color='#1f77b4', alpha=0.8, label='Snow Depth (Mesonet)')
        
        ax_snow.axvspan(snow_day, snow_day + pd.Timedelta(days=1), 
                       alpha=0.15, color='red', zorder=1)
        ax_snow.axhline(y=0, color='black', linestyle='-', linewidth=1.5, alpha=0.3)
        
        # ====================================================================
        # NOAA DAILY STATS FOR SNOW DAY
        # ====================================================================
        stats_text = []
        day_start = snow_day.normalize()
        day_end = day_start + pd.Timedelta(days=1)
        
        # Mesonet snow depth stats (for reference)
        if mesonet_depth is not None and brooklyn_station in mesonet_depth.columns:
            day_depth = mesonet_depth[brooklyn_station][(mesonet_depth[brooklyn_station].index >= day_start) & 
                                                         (mesonet_depth[brooklyn_station].index < day_end)]
            if len(day_depth) > 0:
                max_depth = day_depth.max()
                mean_depth = day_depth.mean()
                stats_text.append(f'Mesonet Depth: Max={max_depth:.1f}mm, Avg={mean_depth:.1f}mm')
        
        stats_text.append('')  # Blank line
        stats_text.append('NOAA DAILY:')
        
        # NOAA Daily - Snow (snowfall)
        if 'noaa_daily' in snow_data:
            noaa_snow = snow_data['noaa_daily']
            day_mask = noaa_snow.index.normalize() == snow_day.normalize()
            if day_mask.any():
                day_snowfall = noaa_snow.loc[day_mask].mean(axis=1).values[0]
                stats_text.append(f'  Snowfall: {day_snowfall:.1f}mm')
        
        # NOAA Daily - Snow Depth
        if 'noaa_daily' in snow_depth_data:
            noaa_depth = snow_depth_data['noaa_daily']
            day_mask = noaa_depth.index.normalize() == snow_day.normalize()
            if day_mask.any():
                day_depth_noaa = noaa_depth.loc[day_mask].mean(axis=1).values[0]
                stats_text.append(f'  Snow Depth: {day_depth_noaa:.1f}mm')
        
        # NOAA Daily - Precipitation
        if 'noaa_daily' in precip_data:
            noaa_precip = precip_data['noaa_daily']
            day_mask = noaa_precip.index.normalize() == snow_day.normalize()
            if day_mask.any():
                day_precip_noaa = noaa_precip.loc[day_mask].mean(axis=1).values[0]
                stats_text.append(f'  Precipitation: {day_precip_noaa:.1f}mm')
        
        if stats_text:
            ax_snow.text(0.02, 0.98, '\n'.join(stats_text), 
                        transform=ax_snow.transAxes, fontsize=10, 
                        verticalalignment='top', bbox=dict(boxstyle='round', 
                        facecolor='lightblue', alpha=0.8))
        
        ax_snow.set_title(f'Snow Depth (Brooklyn)', fontsize=15, fontweight='bold', loc='left')
        ax_snow.set_ylabel('Snow Depth (mm)', fontsize=13, fontweight='bold')
        ax_snow.tick_params(labelsize=12)
        ax_snow.grid(True, alpha=0.3, linewidth=1)
        ax_snow.legend(loc='upper right', fontsize=10)
        
        # ====================================================================
        # SUBPLOT 3: Temperature
        # ====================================================================
        temp_plotted = False
        temp_df = None
        
        # Try 1-min data first
        if 'asos_1min' in temp_data:
            temp_df = temp_data['asos_1min']
            temp_window = temp_df.loc[window_start:window_end]
            
            if len(temp_window) > 0:
                for col in temp_window.columns:
                    ax_temp.plot(temp_window.index, temp_window[col], 
                               linewidth=2.5, alpha=0.8, label=col)
                temp_plotted = True
        
        # Try mesonet
        if not temp_plotted and 'mesonet' in temp_data:
            temp_df = temp_data['mesonet']
            temp_window = temp_df.loc[window_start:window_end]
            
            if len(temp_window) > 0:
                for col in temp_window.columns:
                    ax_temp.plot(temp_window.index, temp_window[col], 
                               linewidth=2.5, alpha=0.8, label=col)
                temp_plotted = True
        
        ax_temp.axvspan(snow_day, snow_day + pd.Timedelta(days=1), 
                       alpha=0.15, color='red', zorder=1)
        ax_temp.axhline(y=0, color='blue', linestyle='--', linewidth=1.5, alpha=0.5)
        
        # Daily average
        if temp_plotted and temp_df is not None:
            day_data = temp_df[(temp_df.index >= day_start) & (temp_df.index < day_end)]
            if len(day_data) > 0:
                day_avg = day_data.mean().mean()
                ax_temp.text(0.02, 0.98, f'Daily Avg: {day_avg:.1f}°C', 
                            transform=ax_temp.transAxes, fontsize=11, 
                            verticalalignment='top', bbox=dict(boxstyle='round', 
                            facecolor='wheat', alpha=0.8))
        
        ax_temp.set_title(f'Temperature', fontsize=15, fontweight='bold', loc='left')
        ax_temp.set_ylabel('Temperature (°C)', fontsize=13, fontweight='bold')
        ax_temp.grid(True, alpha=0.3, linewidth=1)
        ax_temp.legend(loc='upper right', fontsize=10)
        ax_temp.tick_params(labelsize=12)
        
        # ====================================================================
        # SUBPLOT 4: Precipitation (ALL SOURCES)
        # ====================================================================
        daily_totals = []
        
        # 1. Mesonet (Brooklyn)
        if 'mesonet' in precip_data:
            precip_df = precip_data['mesonet']
            if brooklyn_station in precip_df.columns:
                precip_window = precip_df[brooklyn_station].loc[window_start:window_end]
                
                if len(precip_window) > 0:
                    ax_precip.bar(precip_window.index, precip_window.values, 
                                 width=0.002, color='#2ca02c', alpha=0.7, 
                                 label=f'{brooklyn_station} (Mesonet)')
                    
                    # Daily total
                    day_data = precip_window[(precip_window.index >= day_start) & (precip_window.index < day_end)]
                    if len(day_data) > 0:
                        daily_totals.append(f'Mesonet: {day_data.sum():.1f}mm')
        
        # 2. ASOS 1-min (all stations)
        if 'asos_1min' in precip_data:
            asos_df = precip_data['asos_1min']
            asos_window = asos_df.loc[window_start:window_end]
            
            if len(asos_window) > 0:
                # Plot mean across ASOS stations
                mean_asos = asos_window.mean(axis=1)
                ax_precip.bar(mean_asos.index, mean_asos.values, 
                             width=0.002, color='#ff7f0e', alpha=0.6, 
                             label='ASOS (mean)')
                
                # Daily total
                day_data = asos_window[(asos_window.index >= day_start) & (asos_window.index < day_end)]
                if len(day_data) > 0:
                    daily_totals.append(f'ASOS: {day_data.mean(axis=1).sum():.1f}mm')
        
        # 3. PWS (mean across stations)
        if 'pws' in precip_data:
            pws_df = precip_data['pws']
            pws_window = pws_df.loc[window_start:window_end]
            
            if len(pws_window) > 0:
                mean_pws = pws_window.mean(axis=1)
                ax_precip.bar(mean_pws.index, mean_pws.values, 
                             width=0.002, color='#9467bd', alpha=0.6, 
                             label='PWS (mean)')
                
                # Daily total
                day_data = pws_window[(pws_window.index >= day_start) & (pws_window.index < day_end)]
                if len(day_data) > 0:
                    daily_totals.append(f'PWS: {day_data.mean(axis=1).sum():.1f}mm')
        
        ax_precip.axvspan(snow_day, snow_day + pd.Timedelta(days=1), 
                         alpha=0.15, color='red', zorder=1)
        ax_precip.axhline(y=0, color='black', linestyle='-', linewidth=1.5, alpha=0.3)
        
        ax_precip.set_ylim(0, 0.6)
        # Show daily totals
        if daily_totals:
            ax_precip.text(0.02, 0.98, '\n'.join(daily_totals), 
                          transform=ax_precip.transAxes, fontsize=10, 
                          verticalalignment='top', bbox=dict(boxstyle='round', 
                          facecolor='lightgreen', alpha=0.8))
        
        ax_precip.set_title(f'Precipitation (All Sources)', fontsize=15, fontweight='bold', loc='left')
        ax_precip.set_ylabel('Precipitation (mm)', fontsize=13, fontweight='bold')
        ax_precip.set_xlabel('Time', fontsize=13, fontweight='bold')
        ax_precip.grid(True, alpha=0.3, linewidth=1)
        ax_precip.legend(loc='upper right', fontsize=10)
        ax_precip.tick_params(labelsize=12)
        
        # Format x-axis (only on bottom plot since sharex=True)
        ax_precip.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%m-%d %H:%M'))
        plt.setp(ax_precip.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Add main title with date
        fig.suptitle(f'Snow Day Analysis - {snow_day.strftime("%B %d, %Y (%A)")}', 
                     fontsize=18, fontweight='bold', y=0.995)
        
        plt.tight_layout(rect=[0, 0, 1, 0.99])
        plt.show()
        
        print(f"✓ Plotted {snow_day.strftime('%Y-%m-%d')}")


def plot_precipitation_accumulation_all_sources(
    precip_data: Dict[str, pd.DataFrame],
    rainy_days: List[pd.Timestamp] = None,
    snowy_days: List[pd.Timestamp] = None,
    start_date: pd.Timestamp = None,
    end_date: pd.Timestamp = None,
    figsize: tuple = (18, 12)
):
    """
    Plot precipitation accumulation for all sources in one figure with subplots.
    
    - PWS: Shows mean and median prominently, all others in light color
    - ASOS 1min: Shows all stations (typically 3)
    - ASOS Daily (NOAA): Shows all stations (typically 3)
    - Mesonet: Shows all stations
    
    Emphasizes rain and snow days with vertical grid lines.
    
    Parameters
    ----------
    precip_data : dict
        Dictionary with keys like 'pws', 'asos_1min', 'noaa_daily', 'mesonet'
        Each value is a DataFrame with stations as columns, time as index
    rainy_days : list of pd.Timestamp, optional
        List of rainy days to highlight with vertical grid lines
    snowy_days : list of pd.Timestamp, optional
        List of snowy days to highlight with vertical grid lines
    start_date : pd.Timestamp, optional
        Start date for plotting (defaults to data range)
    end_date : pd.Timestamp, optional
        End date for plotting (defaults to data range)
    figsize : tuple
        Figure size (default: (18, 12))
    
    Returns
    -------
    fig : matplotlib.figure.Figure
        The figure object
    """
    # Filter date range if provided
    if start_date is not None or end_date is not None:
        filtered_data = {}
        for source, df in precip_data.items():
            if df is None or len(df) == 0:
                continue
            mask = pd.Series(True, index=df.index)
            if start_date is not None:
                mask &= (df.index >= start_date)
            if end_date is not None:
                mask &= (df.index <= end_date)
            filtered_data[source] = df[mask]
        precip_data = filtered_data
    
    # Convert event days to datetime for grid lines
    if rainy_days is not None:
        rainy_days = [pd.Timestamp(d).normalize() for d in rainy_days]
    if snowy_days is not None:
        snowy_days = [pd.Timestamp(d).normalize() for d in snowy_days]
    
    # Determine number of subplots needed
    n_plots = 0
    plot_order = []
    if 'pws' in precip_data and precip_data['pws'] is not None and len(precip_data['pws']) > 0:
        n_plots += 1
        plot_order.append('pws')
    if 'asos_1min' in precip_data and precip_data['asos_1min'] is not None and len(precip_data['asos_1min']) > 0:
        n_plots += 1
        plot_order.append('asos_1min')
    if 'noaa_daily' in precip_data and precip_data['noaa_daily'] is not None and len(precip_data['noaa_daily']) > 0:
        n_plots += 1
        plot_order.append('noaa_daily')
    if 'mesonet' in precip_data and precip_data['mesonet'] is not None and len(precip_data['mesonet']) > 0:
        n_plots += 1
        plot_order.append('mesonet')
    
    if n_plots == 0:
        print("⚠ No precipitation data available for plotting")
        return None
    
    # Create figure with subplots
    fig, axes = plt.subplots(n_plots, 1, figsize=figsize, sharex=True)
    if n_plots == 1:
        axes = [axes]
    
    plot_idx = 0
    
    # ========================================================================
    # 1. PWS - Mean and Median prominent, others light
    # ========================================================================
    if 'pws' in plot_order:
        df_pws = precip_data['pws'].copy()
        if len(df_pws) > 0:
            ax = axes[plot_idx]
            # Calculate cumulative sum for accumulation
            df_pws_accum = df_pws.cumsum()
            
            # Plot all individual stations in light color
            for col in df_pws_accum.columns:
                ax.plot(df_pws_accum.index, df_pws_accum[col], 
                       color='lightblue', alpha=0.2, linewidth=0.5, label='_nolegend_')
            
            # Calculate and plot mean
            mean_accum = df_pws_accum.mean(axis=1)
            ax.plot(mean_accum.index, mean_accum.values, 
                   color='blue', linewidth=2.5, label='PWS Mean', zorder=10)
            
            # Calculate and plot median
            median_accum = df_pws_accum.median(axis=1)
            ax.plot(median_accum.index, median_accum.values, 
                   color='navy', linewidth=2.5, linestyle='--', label='PWS Median', zorder=10)
            
            # Add grid lines for rain days
            if rainy_days:
                for day in rainy_days:
                    if day >= df_pws_accum.index.min() and day <= df_pws_accum.index.max():
                        ax.axvline(day, color='blue', linestyle=':', linewidth=1.5, 
                                 alpha=0.5, label='Rain Days' if day == rainy_days[0] else '')
            
            # Add grid lines for snow days
            if snowy_days:
                for day in snowy_days:
                    if day >= df_pws_accum.index.min() and day <= df_pws_accum.index.max():
                        ax.axvline(day, color='cyan', linestyle=':', linewidth=1.5, 
                                 alpha=0.5, label='Snow Days' if day == snowy_days[0] else '')
            
            ax.set_ylabel('Cumulative Precipitation (mm)', fontsize=12)
            ax.set_title(f'PWS Precipitation Accumulation (n={len(df_pws.columns)} stations)', 
                        fontsize=13, fontweight='bold')
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax.legend(loc='upper left', fontsize=10)
            plot_idx += 1
    
    # ========================================================================
    # 2. ASOS 1min - All stations (typically 3)
    # ========================================================================
    if 'asos_1min' in plot_order:
        df_asos = precip_data['asos_1min'].copy()
        if len(df_asos) > 0:
            ax = axes[plot_idx]
            # Calculate cumulative sum for accumulation
            df_asos_accum = df_asos.cumsum()
            
            # Plot all ASOS stations
            colors_asos = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            for idx, col in enumerate(df_asos_accum.columns):
                color = colors_asos[idx % len(colors_asos)]
                ax.plot(df_asos_accum.index, df_asos_accum[col], 
                       color=color, linewidth=2, label=f'ASOS 1min {col}', zorder=5)
            
            # Add grid lines for rain days
            if rainy_days:
                for day in rainy_days:
                    if day >= df_asos_accum.index.min() and day <= df_asos_accum.index.max():
                        ax.axvline(day, color='blue', linestyle=':', linewidth=1.5, 
                                 alpha=0.5, label='Rain Days' if day == rainy_days[0] else '')
            
            # Add grid lines for snow days
            if snowy_days:
                for day in snowy_days:
                    if day >= df_asos_accum.index.min() and day <= df_asos_accum.index.max():
                        ax.axvline(day, color='cyan', linestyle=':', linewidth=1.5, 
                                 alpha=0.5, label='Snow Days' if day == snowy_days[0] else '')
            
            ax.set_ylabel('Cumulative Precipitation (mm)', fontsize=12)
            ax.set_title(f'ASOS 1-min Precipitation Accumulation (n={len(df_asos.columns)} stations)', 
                        fontsize=13, fontweight='bold')
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax.legend(loc='upper left', fontsize=10)
            plot_idx += 1
    
    # ========================================================================
    # 3. ASOS Daily (NOAA) - All stations (typically 3)
    # ========================================================================
    if 'noaa_daily' in plot_order:
        df_noaa = precip_data['noaa_daily'].copy()
        if len(df_noaa) > 0:
            ax = axes[plot_idx]
            # Calculate cumulative sum for accumulation
            df_noaa_accum = df_noaa.cumsum()
            
            # Plot all NOAA daily stations
            colors_noaa = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            for idx, col in enumerate(df_noaa_accum.columns):
                color = colors_noaa[idx % len(colors_noaa)]
                ax.plot(df_noaa_accum.index, df_noaa_accum[col], 
                       color=color, linewidth=2.5, marker='o', markersize=3,
                       label=f'ASOS Daily {col}', zorder=5)
            
            # Add grid lines for rain days
            if rainy_days:
                for day in rainy_days:
                    if day >= df_noaa_accum.index.min() and day <= df_noaa_accum.index.max():
                        ax.axvline(day, color='blue', linestyle=':', linewidth=1.5, 
                                 alpha=0.5, label='Rain Days' if day == rainy_days[0] else '')
            
            # Add grid lines for snow days
            if snowy_days:
                for day in snowy_days:
                    if day >= df_noaa_accum.index.min() and day <= df_noaa_accum.index.max():
                        ax.axvline(day, color='cyan', linestyle=':', linewidth=1.5, 
                                 alpha=0.5, label='Snow Days' if day == snowy_days[0] else '')
            
            ax.set_ylabel('Cumulative Precipitation (mm)', fontsize=12)
            ax.set_title(f'ASOS Daily (NOAA) Precipitation Accumulation (n={len(df_noaa.columns)} stations)', 
                        fontsize=13, fontweight='bold')
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax.legend(loc='upper left', fontsize=10)
            plot_idx += 1
    
    # ========================================================================
    # 4. Mesonet - All stations
    # ========================================================================
    if 'mesonet' in plot_order:
        df_mesonet = precip_data['mesonet'].copy()
        if len(df_mesonet) > 0:
            ax = axes[plot_idx]
            # Calculate cumulative sum for accumulation
            df_mesonet_accum = df_mesonet.cumsum()
            
            # Plot all Mesonet stations
            colors_mesonet = plt.cm.tab20.colors
            for idx, col in enumerate(df_mesonet_accum.columns):
                color = colors_mesonet[idx % len(colors_mesonet)]
                ax.plot(df_mesonet_accum.index, df_mesonet_accum[col], 
                       color=color, linewidth=1.5, label=f'Mesonet {col}', alpha=0.8)
            
            # Add grid lines for rain days
            if rainy_days:
                for day in rainy_days:
                    if day >= df_mesonet_accum.index.min() and day <= df_mesonet_accum.index.max():
                        ax.axvline(day, color='blue', linestyle=':', linewidth=1.5, 
                                 alpha=0.5, label='Rain Days' if day == rainy_days[0] else '')
            
            # Add grid lines for snow days
            if snowy_days:
                for day in snowy_days:
                    if day >= df_mesonet_accum.index.min() and day <= df_mesonet_accum.index.max():
                        ax.axvline(day, color='cyan', linestyle=':', linewidth=1.5, 
                                 alpha=0.5, label='Snow Days' if day == snowy_days[0] else '')
            
            ax.set_ylabel('Cumulative Precipitation (mm)', fontsize=12)
            ax.set_title(f'Mesonet Precipitation Accumulation (n={len(df_mesonet.columns)} stations)', 
                        fontsize=13, fontweight='bold')
            ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
            ax.legend(loc='upper left', fontsize=9, ncol=2)
            plot_idx += 1
    
    # Set common x-axis label and formatting for the bottom plot
    axes[-1].set_xlabel('Date', fontsize=12)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    axes[-1].xaxis.set_major_locator(mdates.AutoDateLocator())
    plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    plt.tight_layout()
    plt.show()
    
    print("✓ Precipitation accumulation plots completed")
    
    return fig



"""
CML-SENSOR MATCHING VISUALIZATION
=================================
Add to plotting.py
"""

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import pandas as pd
import numpy as np


"""
PREPROCESSING FUNCTIONS
=======================
Snow depth cleaning and visualization
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch


# ============================================================================
# SNOW DEPTH CLEANING
# ============================================================================

def clean_snow_depth(
    raw_data: pd.DataFrame,
    snow_days: list,
    stations: list = None,
    calibration_hours: float = 24.0,
    filter_window_minutes: int = 30,
    max_depth: float = 500.0
):
    """
    Clean snow depth data using pre-snow calibration.
    
    Model:  x(t) = s(t) + b(t) + ε(t)
            where s=true snow, b=baseline drift, ε=noise
    
    Algorithm:
        1. b̂ᵢ = median(x) in [tᵢ-24h, tᵢ) for each snow event
        2. b̂(t) = interpolate between calibration points
        3. ŝ(t) = x(t) - b̂(t)
        4. ŝ(t) = median_filter(ŝ, window=30min)
        5. ŝ(t) = clip(ŝ, 0, max_depth)
    
    Returns: (cleaned_df, baselines_df)
    """
    
    if stations is None:
        stations = raw_data.columns.tolist()
    
    snow_times = pd.to_datetime(snow_days)
    
    cleaned = pd.DataFrame(index=raw_data.index)
    baselines = pd.DataFrame(index=raw_data.index)
    
    for station in stations:
        raw = raw_data[station].copy()
        
        # Step 1: Baseline at each snow event
        cal_points = []
        for snow_time in snow_times:
            window_start = snow_time - pd.Timedelta(hours=calibration_hours)
            mask = (raw.index >= window_start) & (raw.index < snow_time)
            window_data = raw[mask].dropna()
            
            if len(window_data) >= 12:
                cal_points.append((snow_time, window_data.median()))
        
        # Step 2: Interpolate baseline
        if len(cal_points) == 0:
            baseline_series = pd.Series(raw.median(), index=raw.index)
        else:
            times, values = zip(*cal_points)
            baseline_at_cal = pd.Series(values, index=pd.DatetimeIndex(times))
            baseline_series = baseline_at_cal.reindex(baseline_at_cal.index.union(raw.index))
            baseline_series = baseline_series.interpolate(method='time').ffill().bfill()
            baseline_series = baseline_series.reindex(raw.index)
        
        # Step 3-5: Correct, filter, clip
        corrected = raw - baseline_series
        window_samples = max(1, filter_window_minutes // 5)
        smoothed = corrected.rolling(window=window_samples, center=True, min_periods=1).median()
        final = smoothed.clip(lower=0, upper=max_depth)
        
        cleaned[station] = final
        baselines[station] = baseline_series
    
    return cleaned, baselines


# ============================================================================
# STATISTICS
# ============================================================================

def print_cleaning_stats(raw_data, cleaned_data, stations):
    """Print before/after statistics for snow cleaning."""
    
    print("=" * 60)
    print("CLEANING STATISTICS")
    print("=" * 60)
    
    for station in stations:
        raw = raw_data[station].dropna()
        clean = cleaned_data[station].dropna()
        
        raw_neg_pct = 100 * (raw < 0).sum() / len(raw) if len(raw) > 0 else 0
        clean_neg_pct = 100 * (clean < 0).sum() / len(clean) if len(clean) > 0 else 0
        
        print(f"\n{station}:")
        print(f"  Before: min={raw.min():7.1f}, max={raw.max():7.1f}, mean={raw.mean():7.1f}, neg={raw_neg_pct:5.1f}%")
        print(f"  After:  min={clean.min():7.1f}, max={clean.max():7.1f}, mean={clean.mean():7.1f}, neg={clean_neg_pct:5.1f}%")
    
    print("\n" + "=" * 60)


# ============================================================================
# SNOW DEPTH PLOTS
# ============================================================================

def plot_snow_histograms(raw_data, cleaned_data, stations):
    """Plot histograms before/after cleaning."""
    
    fig, axes = plt.subplots(2, len(stations), figsize=(4*len(stations), 8))
    
    for idx, station in enumerate(stations):
        # Before
        ax = axes[0, idx]
        raw_data[station].dropna().hist(bins=50, ax=ax, color='red', alpha=0.7, edgecolor='black')
        ax.axvline(0, color='k', ls='--', lw=2)
        ax.set_title(f'{station} - BEFORE', fontweight='bold')
        ax.set_xlabel('Snow Depth (mm)')
        ax.set_ylabel('Count')
        ax.grid(True, alpha=0.3)
        
        # After
        ax = axes[1, idx]
        cleaned_data[station].dropna().hist(bins=50, ax=ax, color='blue', alpha=0.7, edgecolor='black')
        ax.axvline(0, color='k', ls='--', lw=2)
        ax.set_title(f'{station} - AFTER', fontweight='bold')
        ax.set_xlabel('Snow Depth (mm)')
        ax.set_ylabel('Count')
        ax.grid(True, alpha=0.3)
    
    plt.suptitle('Snow Depth Distribution: Before vs After Cleaning', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()


def plot_snow_timeseries(raw_data, cleaned_data, baselines, stations, snow_days, 
                         date_start=None, date_end=None):
    """Plot time series: raw, baseline, cleaned with snow days marked."""
    
    fig, axes = plt.subplots(len(stations), 1, figsize=(18, 3*len(stations)))
    if len(stations) == 1:
        axes = [axes]
    
    if date_start is None:
        date_start = raw_data.index.min()
    if date_end is None:
        date_end = raw_data.index.max()
    
    date_start = pd.Timestamp(date_start)
    date_end = pd.Timestamp(date_end)
    
    mask = (raw_data.index >= date_start) & (raw_data.index <= date_end)
    
    for idx, station in enumerate(stations):
        ax = axes[idx]
        
        ax.plot(raw_data.loc[mask, station], 'r-', alpha=0.5, lw=0.8, label='Raw')
        ax.plot(baselines.loc[mask, station], 'k--', lw=2, label='Baseline')
        ax.plot(cleaned_data.loc[mask, station], 'b-', alpha=0.9, lw=1.2, label='Cleaned')
        
        for sd in pd.to_datetime(snow_days):
            if date_start <= sd <= date_end:
                ax.axvspan(sd, sd + pd.Timedelta(days=1), alpha=0.15, color='green')
        
        ax.axhline(0, color='k', lw=0.5)
        ax.set_title(station, fontweight='bold')
        ax.set_ylabel('Snow Depth (mm)')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(date_start, date_end)
    
    axes[-1].set_xlabel('Date')
    plt.suptitle('Time Series: Raw vs Cleaned (green = snow days)', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()


def plot_snow_events_zoom(raw_data, cleaned_data, stations, snow_days, 
                          days_before=1, days_after=2, max_events=10):
    """Plot zoomed view of individual snow events."""
    
    snow_days = pd.to_datetime(snow_days)
    n_events = min(len(snow_days), max_events)
    
    fig, axes = plt.subplots(n_events, 1, figsize=(16, 3.5*n_events))
    if n_events == 1:
        axes = [axes]
    
    colors = {'BRON': '#1f77b4', 'QUEE': '#ff7f0e', 'MANH': '#2ca02c', 'BKLN': '#d62728'}
    default_colors = plt.cm.tab10.colors
    
    for i, sd in enumerate(snow_days[:n_events]):
        ax = axes[i]
        w_start = sd - pd.Timedelta(days=days_before)
        w_end = sd + pd.Timedelta(days=days_after)
        
        mask = (raw_data.index >= w_start) & (raw_data.index <= w_end)
        
        for j, station in enumerate(stations):
            color = colors.get(station, default_colors[j % len(default_colors)])
            ax.plot(cleaned_data.loc[mask, station], lw=2, color=color, label=station)
            ax.plot(raw_data.loc[mask, station], lw=1, ls=':', color=color, alpha=0.4)
        
        ax.axvspan(sd, sd + pd.Timedelta(days=1), alpha=0.15, color='green')
        ax.axhline(0, color='k', lw=0.5)
        ax.set_title(f'{sd.strftime("%Y-%m-%d")} (solid=cleaned, dotted=raw)', fontweight='bold')
        ax.set_ylabel('Snow Depth (mm)')
        ax.legend(loc='upper right', ncol=len(stations))
        ax.grid(True, alpha=0.3)
        ax.set_xlim(w_start, w_end)
    
    plt.suptitle('Snow Events: Before vs After Cleaning', fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.show()


# ============================================================================
# ASOS PRECIPITATION PLOT
# ============================================================================

def plot_asos_precip_by_event(df_asos_precip, df_asos_type, event_days, 
                              window_days=1, max_events=None, df_asos_temp=None):
    """
    Plot ASOS 1-min precipitation with type labels for each event day.
    
    Parameters
    ----------
    df_asos_precip : pd.DataFrame
        ASOS 1-min precipitation data
    df_asos_type : pd.DataFrame
        ASOS 1-min precipitation type data
    event_days : list
        List of event dates to plot
    window_days : int
        Days before/after event to show (default: 1)
    max_events : int, optional
        Maximum number of events to plot (default: all)
    df_asos_temp : pd.DataFrame, optional
        ASOS 1-min temperature data. If provided, will be plotted on secondary y-axis.
    """
    
    stations = df_asos_precip.columns.tolist()
    event_days = pd.to_datetime(event_days)
    
    if max_events is not None:
        event_days = event_days[:max_events]
    
    print(f"Plotting ASOS 1-min data for {len(stations)} stations, {len(event_days)} events")
    
    type_colors = {
        'dry': 'none', 'rain': 'blue', 'snow': 'cyan', 
        'mix': 'gray', 'unknown': 'lightgray', np.nan: 'none'
    }
    
    for event_day in event_days:
        
        plot_start = event_day - pd.Timedelta(days=window_days)
        plot_end = event_day + pd.Timedelta(days=window_days + 1)
        
        mask = (df_asos_precip.index >= plot_start) & (df_asos_precip.index <= plot_end)
        df_precip_plot = df_asos_precip.loc[mask]
        df_type_plot = df_asos_type.loc[mask]
        
        if len(df_precip_plot) == 0:
            print(f"⚠️ No data for {event_day.strftime('%Y-%m-%d')}")
            continue
        
        fig, axes = plt.subplots(len(stations), 1, figsize=(20, 4*len(stations)), sharex=True)
        if len(stations) == 1:
            axes = [axes]
        
        for idx, (ax, station) in enumerate(zip(axes, stations)):
            
            precip = df_precip_plot[station]
            ptype = df_type_plot[station]
            
            for time, precip_val in precip.items():
                if pd.isna(precip_val) or precip_val == 0:
                    continue
                
                type_val = ptype.loc[time] if time in ptype.index else 'unknown'
                
                if pd.isna(type_val):
                    color, edge_color = type_colors[np.nan], 'none'
                elif type_val in type_colors:
                    color = type_colors[type_val]
                    edge_color = 'navy' if color != 'none' else 'none'
                else:
                    color, edge_color = 'lightgray', 'gray'
                
                ax.bar(time, precip_val, width=0.0007, color=color,
                       alpha=0.8, edgecolor=edge_color, linewidth=0.5)
            
            # Background shading
            for time_idx in range(len(df_type_plot) - 1):
                time_current = df_type_plot.index[time_idx]
                time_next = df_type_plot.index[time_idx + 1]
                type_val = ptype.iloc[time_idx]
                
                if pd.isna(type_val) or type_val == 'dry':
                    continue
                if type_val == 'rain':
                    ax.axvspan(time_current, time_next, alpha=0.05, color='blue', zorder=0)
                elif type_val == 'snow':
                    ax.axvspan(time_current, time_next, alpha=0.1, color='cyan', zorder=0)
                elif type_val == 'mix':
                    ax.axvspan(time_current, time_next, alpha=0.05, color='gray', zorder=0)
            
            # Plot temperature on secondary y-axis if available
            if df_asos_temp is not None and station in df_asos_temp.columns:
                ax2 = ax.twinx()
                temp_data = df_asos_temp[station].loc[plot_start:plot_end]
                if len(temp_data) > 0:
                    ax2.plot(temp_data.index, temp_data.values, 
                            color='red', linewidth=2, alpha=0.7, label='Temperature')
                    ax2.set_ylabel('Temperature (°C)', fontsize=12, fontweight='bold', color='red')
                    ax2.tick_params(axis='y', labelcolor='red')
                    ax2.grid(True, alpha=0.2, linestyle=':', color='red')
            
            station_name = station.replace('1min_', '')
            ax.set_ylabel('Precip (mm)', fontsize=12, fontweight='bold')
            ax.set_title(f'{station_name}', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_ylim(bottom=0)
            ax.set_xlim(plot_start, plot_end)
            
            legend_elements = [
                Patch(facecolor='blue', alpha=0.8, label='Rain'),
                Patch(facecolor='cyan', alpha=0.8, label='Snow'),
                Patch(facecolor='gray', alpha=0.8, label='Mix'),
            ]
            if df_asos_temp is not None and station in df_asos_temp.columns:
                from matplotlib.lines import Line2D
                legend_elements.append(Line2D([0], [0], color='red', linewidth=2, label='Temperature'))
            ax.legend(handles=legend_elements, loc='upper right', fontsize=10, ncol=4)
        
        axes[-1].set_xlabel('Time', fontsize=12, fontweight='bold')
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.suptitle(f'ASOS 1-Min Precipitation - {event_day.strftime("%Y-%m-%d")}',
                     fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.show()


def plot_tw_pclass_by_event(df_tw, df_p_class, event_days, 
                             window_days=1, max_events=None):
    """
    Plot wet-bulb temperature (Tw) and precipitation classification (p_class) for each event day.
    
    Similar format to plot_asos_precip_by_event but for Tw and p_class data.
    
    Parameters
    ----------
    df_tw : pd.DataFrame
        Wet-bulb temperature data (columns = stations, index = time)
    df_p_class : pd.DataFrame
        Precipitation classification data (columns = stations, index = time)
        Values should be: 'Dry Snow', 'Wet Snow', 'Mixed Phase', 'Rain', 'Unknown', etc.
    event_days : list
        List of event dates to plot
    window_days : int
        Days before/after event to show (default: 1)
    max_events : int, optional
        Maximum number of events to plot (default: all)
    """
    
    # Phase color configuration
    PHASE_COLORS = {
        'Dry Snow': '#d1e5f0',     # Light Blue
        'Wet Snow': '#f4a582',     # Red/Orange
        'Mixed Phase': '#c2a5cf',  # Purple
        'Rain': '#92c5de',         # Blue
        'No Precip': '#ffffff',    # White
        'Unknown': '#f0f0f0'       # Light Gray
    }
    
    # Thresholds for classification (used for horizontal lines)
    THRESHOLDS = {
        'dry_snow_limit': -0.5,
        'wet_snow_limit': 0.5,
        'mixed_limit': 1.5
    }
    
    stations = df_tw.columns.tolist()
    event_days = pd.to_datetime(event_days)
    
    if max_events is not None:
        event_days = event_days[:max_events]
    
    print(f"Plotting Tw & p_class for {len(stations)} stations, {len(event_days)} events")
    
    for event_day in event_days:
        
        plot_start = event_day - pd.Timedelta(days=window_days)
        plot_end = event_day + pd.Timedelta(days=window_days + 1)
        
        mask = (df_tw.index >= plot_start) & (df_tw.index <= plot_end)
        df_tw_plot = df_tw.loc[mask]
        df_pclass_plot = df_p_class.loc[mask]
        
        if len(df_tw_plot) == 0:
            print(f"⚠️ No data for {event_day.strftime('%Y-%m-%d')}")
            continue
        
        fig, axes = plt.subplots(len(stations), 1, figsize=(20, 4*len(stations)), sharex=True)
        if len(stations) == 1:
            axes = [axes]
        
        for idx, (ax, station) in enumerate(zip(axes, stations)):
            
            tw_series = df_tw_plot[station]
            pclass_series = df_pclass_plot[station]
            
            # Align data
            common_index = tw_series.index.intersection(pclass_series.index)
            tw_aligned = tw_series.loc[common_index]
            pclass_aligned = pclass_series.loc[common_index]
            
            if len(tw_aligned) == 0:
                ax.text(0.5, 0.5, 'No data', transform=ax.transAxes,
                       ha='center', va='center', fontsize=12, color='gray')
                continue
            
            # A. Plot threshold lines first (so they're behind everything)
            ax.axhline(THRESHOLDS['dry_snow_limit'], color='blue', linestyle='--', 
                      alpha=0.5, linewidth=1.5, label='Dry Snow Limit (-0.5°C)', zorder=1)
            ax.axhline(THRESHOLDS['wet_snow_limit'], color='red', linestyle='--', 
                      alpha=0.5, linewidth=1.5, label='Wet Snow Limit (0.5°C)', zorder=1)
            ax.axhline(THRESHOLDS['mixed_limit'], color='orange', linestyle='--', 
                      alpha=0.4, linewidth=1.5, label='Mixed Phase Limit (1.5°C)', zorder=1)
            
            # B. Color background based on precipitation classification
            # Group contiguous phases to draw colored spans efficiently
            plot_df = pd.DataFrame({
                'Tw': tw_aligned.values,
                'p_class': pclass_aligned.values
            }, index=common_index)
            
            plot_df['group'] = (plot_df['p_class'] != plot_df['p_class'].shift()).cumsum()
            
            for g, block in plot_df.groupby('group'):
                phase = block['p_class'].iloc[0]
                color = PHASE_COLORS.get(phase, '#ffffff')
                
                if phase not in ['No Precip', 'Unknown']:
                    start_x = block.index[0]
                    end_x = block.index[-1]
                    ax.axvspan(start_x, end_x, color=color, alpha=0.3, zorder=0)
            
            # C. Plot Tw line (on top of background)
            ax.plot(tw_aligned.index, tw_aligned.values, 
                   color='black', linewidth=2, alpha=0.9, label='Tw (°C)', zorder=3)
            
            # D. Formatting
            station_name = station.replace('1min_', '').replace('mesonet_', '')
            ax.set_ylabel('Wet-Bulb Temp ($T_w$) [°C]', fontsize=12, fontweight='bold')
            ax.set_title(f'{station_name}', fontsize=14, fontweight='bold')
            ax.grid(True, alpha=0.3, linestyle='--', zorder=0)
            ax.set_xlim(plot_start, plot_end)
            
            # Legend
            from matplotlib.patches import Patch
            from matplotlib.lines import Line2D
            
            legend_elements = [
                Line2D([0], [0], color='black', linewidth=2, label='Tw (°C)'),
                Line2D([0], [0], color='blue', linestyle='--', linewidth=1.5, label='Dry Snow Limit (-0.5°C)'),
                Line2D([0], [0], color='red', linestyle='--', linewidth=1.5, label='Wet Snow Limit (0.5°C)'),
                Line2D([0], [0], color='orange', linestyle='--', linewidth=1.5, label='Mixed Phase Limit (1.5°C)'),
            ]
            
            # Add phase colors to legend (only unique phases present)
            unique_phases = pclass_aligned.unique()
            phase_labels_added = set()
            for phase in unique_phases:
                if pd.notna(phase) and phase not in ['No Precip', 'Unknown'] and phase not in phase_labels_added:
                    color = PHASE_COLORS.get(phase, '#ffffff')
                    legend_elements.append(
                        Patch(facecolor=color, alpha=0.3, edgecolor='gray', label=phase)
                    )
                    phase_labels_added.add(phase)
            
            ax.legend(handles=legend_elements, loc='upper right', fontsize=9, ncol=2, framealpha=0.9)
        
        axes[-1].set_xlabel('Time', fontsize=12, fontweight='bold')
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        axes[-1].xaxis.set_major_locator(mdates.HourLocator(interval=3))  # Show every 3 hours
        plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.suptitle(f'Wet-Bulb Temperature & Precipitation Classification - {event_day.strftime("%Y-%m-%d")}',
                     fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.show()


def plot_tw_pclass_from_params(all_params, event_days, source='asos_1min', 
                                window_days=1, max_events=None):
    """
    Convenience wrapper: Plot Tw and p_class from all_params.
    
    Extracts Tw and p_class from all_params and plots them for each event day.
    
    Parameters
    ----------
    all_params : dict
        Output from extract_parameters(). Should contain 'Tw' and 'p_class' keys.
        Structure: {'Tw': {source: DataFrame}, 'p_class': {source: DataFrame}}
    event_days : list
        List of event dates to plot
    source : str, default 'asos_1min'
        Data source to use ('asos_1min' or 'mesonet')
    window_days : int, default 1
        Days before/after event to show
    max_events : int, optional
        Maximum number of events to plot (default: all)
    
    Example
    -------
    plot_tw_pclass_from_params(all_params, snowy_days, source='asos_1min')
    """
    
    # Extract Tw and p_class DataFrames
    if 'Tw' not in all_params:
        raise ValueError("'Tw' not found in all_params. Run classification first.")
    if 'p_class' not in all_params:
        raise ValueError("'p_class' not found in all_params. Run classification first.")
    
    tw_dict = all_params['Tw']
    pclass_dict = all_params['p_class']
    
    if source not in tw_dict:
        available = list(tw_dict.keys())
        raise ValueError(f"Source '{source}' not found in Tw data. Available: {available}")
    if source not in pclass_dict:
        available = list(pclass_dict.keys())
        raise ValueError(f"Source '{source}' not found in p_class data. Available: {available}")
    
    df_tw = tw_dict[source]
    df_p_class = pclass_dict[source]
    
    # Call the main plotting function
    plot_tw_pclass_by_event(df_tw, df_p_class, event_days, 
                            window_days=window_days, max_events=max_events)


def plot_precip_type_tw_by_event(all_params, event_days, source='asos_1min',
                                  window_days=1, max_events=None):
    """
    Unified plotting function: Plot precipitation, precipitation type, and Tw (if available)
    for each event day, with each station as a subplot.
    
    Shows:
    - Row 1: Precipitation (bars colored by type)
    - Row 2: Precipitation Type (background shading)
    - Row 3: Tw (wet-bulb temperature, if available)
    
    Parameters
    ----------
    all_params : dict
        Output from extract_parameters(). Should contain:
        - 'precip': {source: DataFrame}
        - 'precip_type': {source: DataFrame} (for asos_1min)
        - 'p_class': {source: DataFrame} (calculated classification)
        - 'Tw': {source: DataFrame} (wet-bulb temperature, optional)
    event_days : list
        List of event dates to plot
    source : str, default 'asos_1min'
        Data source to use ('asos_1min' or 'mesonet')
    window_days : int, default 1
        Days before/after event to show
    max_events : int, optional
        Maximum number of events to plot (default: all)
    
    Example
    -------
    plot_precip_type_tw_by_event(all_params, snowy_days, source='asos_1min')
    """
    
    # Extract data
    if 'precip' not in all_params:
        raise ValueError("'precip' not found in all_params")
    if 'precip_type' not in all_params and 'p_class' not in all_params:
        raise ValueError("'precip_type' or 'p_class' not found in all_params")
    
    precip_dict = all_params['precip']
    ptype_dict = all_params.get('precip_type', {})
    pclass_dict = all_params.get('p_class', {})
    tw_dict = all_params.get('Tw', {})
    
    # Get the right source data
    if source not in precip_dict:
        available = list(precip_dict.keys())
        raise ValueError(f"Source '{source}' not found in precip data. Available: {available}")
    
    df_precip = precip_dict[source]
    
    # Get precip type (prefer p_class if available, otherwise precip_type)
    if source in pclass_dict:
        df_type = pclass_dict[source]
        use_pclass = True
    elif source in ptype_dict:
        df_type = ptype_dict[source]
        use_pclass = False
    else:
        raise ValueError(f"Neither 'p_class' nor 'precip_type' found for source '{source}'")
    
    # Get Tw if available
    df_tw = tw_dict.get(source, None)
    has_tw = df_tw is not None and not df_tw.empty
    
    # Color configurations
    if use_pclass:
        # Classification colors (Dry Snow, Wet Snow, etc.)
        type_colors = {
            'Dry Snow': '#d1e5f0',     # Light Blue
            'Wet Snow': '#f4a582',     # Red/Orange
            'Mixed Phase': '#c2a5cf',  # Purple
            'Rain': '#92c5de',         # Blue
            'No Precip': 'none',
            'Unknown': 'lightgray'
        }
    else:
        # ASOS precip type colors
        type_colors = {
            'dry': 'none', 'rain': 'blue', 'snow': 'cyan', 
            'mix': 'gray', 'unknown': 'lightgray', np.nan: 'none'
        }
    
    # Thresholds for Tw (if available)
    THRESHOLDS = {
        'dry_snow_limit': -0.5,
        'wet_snow_limit': 0.5,
        'mixed_limit': 1.5
    }
    
    stations = df_precip.columns.tolist()
    event_days = pd.to_datetime(event_days)
    
    if max_events is not None:
        event_days = event_days[:max_events]
    
    print(f"Plotting {source} data for {len(stations)} stations, {len(event_days)} events")
    if has_tw:
        print(f"  Including Tw (wet-bulb temperature)")
    
    for event_day in event_days:
        
        plot_start = event_day - pd.Timedelta(days=window_days)
        plot_end = event_day + pd.Timedelta(days=window_days + 1)
        
        mask = (df_precip.index >= plot_start) & (df_precip.index <= plot_end)
        df_precip_plot = df_precip.loc[mask]
        df_type_plot = df_type.loc[mask]
        if has_tw:
            df_tw_plot = df_tw.loc[mask]
        else:
            df_tw_plot = None
        
        if len(df_precip_plot) == 0:
            print(f"⚠️ No data for {event_day.strftime('%Y-%m-%d')}")
            continue
        
        # Determine number of rows (2 if no Tw, 3 if Tw available)
        n_rows = 3 if has_tw else 2
        fig, axes = plt.subplots(n_rows, len(stations), 
                                figsize=(4*len(stations), 3.5*n_rows), 
                                sharex=True, sharey='row')
        
        if len(stations) == 1:
            axes = axes.reshape(-1, 1)
        if n_rows == 1:
            axes = axes.reshape(1, -1)
        
        for col_idx, station in enumerate(stations):
            
            precip = df_precip_plot[station]
            ptype = df_type_plot[station]
            if has_tw:
                tw_series = df_tw_plot[station]
            
            # === ROW 1: PRECIPITATION (bars colored by type) ===
            ax_precip = axes[0, col_idx]
            
            for time, precip_val in precip.items():
                if pd.isna(precip_val) or precip_val == 0:
                    continue
                
                # Get type value
                type_val = ptype.loc[time] if time in ptype.index else ('Unknown' if use_pclass else 'unknown')
                
                if pd.isna(type_val):
                    color = type_colors.get(np.nan, 'lightgray') if not use_pclass else type_colors.get('Unknown', 'lightgray')
                else:
                    color = type_colors.get(type_val, 'lightgray')
                
                if color == 'none':
                    continue
                
                edge_color = 'navy' if color not in ['none', 'lightgray'] else 'gray'
                ax_precip.bar(time, precip_val, width=0.0007, color=color,
                             alpha=0.8, edgecolor=edge_color, linewidth=0.5)
            
            # Background shading for precip type
            for time_idx in range(len(df_type_plot) - 1):
                time_current = df_type_plot.index[time_idx]
                time_next = df_type_plot.index[time_idx + 1]
                type_val = ptype.iloc[time_idx]
                
                if pd.isna(type_val):
                    continue
                
                if use_pclass:
                    if type_val in ['No Precip', 'Unknown']:
                        continue
                    color = type_colors.get(type_val, '#ffffff')
                    ax_precip.axvspan(time_current, time_next, alpha=0.1, color=color, zorder=0)
                else:
                    if type_val == 'dry':
                        continue
                    if type_val == 'rain':
                        ax_precip.axvspan(time_current, time_next, alpha=0.05, color='blue', zorder=0)
                    elif type_val == 'snow':
                        ax_precip.axvspan(time_current, time_next, alpha=0.1, color='cyan', zorder=0)
                    elif type_val == 'mix':
                        ax_precip.axvspan(time_current, time_next, alpha=0.05, color='gray', zorder=0)
            
            station_name = station.replace('1min_', '').replace('mesonet_', '')
            ax_precip.set_ylabel('Precip (mm)', fontsize=11, fontweight='bold')
            ax_precip.set_title(f'{station_name}', fontsize=12, fontweight='bold')
            ax_precip.grid(True, alpha=0.3, linestyle='--')
            ax_precip.set_ylim(bottom=0)
            ax_precip.set_xlim(plot_start, plot_end)
            
            # === ROW 2: PRECIPITATION TYPE (background shading) ===
            ax_type = axes[1, col_idx]
            
            # Plot type as background shading
            for time_idx in range(len(df_type_plot) - 1):
                time_current = df_type_plot.index[time_idx]
                time_next = df_type_plot.index[time_idx + 1]
                type_val = ptype.iloc[time_idx]
                
                if pd.isna(type_val):
                    continue
                
                if use_pclass:
                    if type_val in ['No Precip', 'Unknown']:
                        continue
                    color = type_colors.get(type_val, '#ffffff')
                    ax_type.axvspan(time_current, time_next, alpha=0.4, color=color, zorder=0)
                else:
                    if type_val == 'dry':
                        continue
                    if type_val == 'rain':
                        ax_type.axvspan(time_current, time_next, alpha=0.2, color='blue', zorder=0)
                    elif type_val == 'snow':
                        ax_type.axvspan(time_current, time_next, alpha=0.3, color='cyan', zorder=0)
                    elif type_val == 'mix':
                        ax_type.axvspan(time_current, time_next, alpha=0.2, color='gray', zorder=0)
            
            ax_type.set_ylabel('Precip Type', fontsize=11, fontweight='bold')
            ax_type.set_ylim(0, 1)
            ax_type.set_xlim(plot_start, plot_end)
            ax_type.set_yticks([])
            ax_type.grid(True, alpha=0.3, linestyle='--', axis='x')
            
            # === ROW 3: TW (if available) ===
            if has_tw:
                ax_tw = axes[2, col_idx]
                
                # Align Tw with type data
                common_index = tw_series.index.intersection(ptype.index)
                tw_aligned = tw_series.loc[common_index]
                ptype_aligned = ptype.loc[common_index]
                
                if len(tw_aligned) > 0:
                    # Plot threshold lines
                    ax_tw.axhline(THRESHOLDS['dry_snow_limit'], color='blue', linestyle='--', 
                                alpha=0.5, linewidth=1.5, label='Dry Snow Limit (-0.5°C)', zorder=1)
                    ax_tw.axhline(THRESHOLDS['wet_snow_limit'], color='red', linestyle='--', 
                                alpha=0.5, linewidth=1.5, label='Wet Snow Limit (0.5°C)', zorder=1)
                    ax_tw.axhline(THRESHOLDS['mixed_limit'], color='orange', linestyle='--', 
                                alpha=0.4, linewidth=1.5, label='Mixed Phase Limit (1.5°C)', zorder=1)
                    
                    # Background shading based on p_class
                    if use_pclass:
                        plot_df = pd.DataFrame({
                            'Tw': tw_aligned.values,
                            'p_class': ptype_aligned.values
                        }, index=common_index)
                        plot_df['group'] = (plot_df['p_class'] != plot_df['p_class'].shift()).cumsum()
                        
                        for g, block in plot_df.groupby('group'):
                            phase = block['p_class'].iloc[0]
                            color = type_colors.get(phase, '#ffffff')
                            if phase not in ['No Precip', 'Unknown']:
                                start_x = block.index[0]
                                end_x = block.index[-1]
                                ax_tw.axvspan(start_x, end_x, color=color, alpha=0.3, zorder=0)
                    
                    # Plot Tw line
                    ax_tw.plot(tw_aligned.index, tw_aligned.values, 
                             color='black', linewidth=2, alpha=0.9, label='Tw (°C)', zorder=3)
                
                ax_tw.set_ylabel('Tw (°C)', fontsize=11, fontweight='bold')
                ax_tw.set_xlim(plot_start, plot_end)
                ax_tw.grid(True, alpha=0.3, linestyle='--', zorder=0)
        
        # Format bottom row x-axis
        for col_idx in range(len(stations)):
            axes[-1, col_idx].set_xlabel('Time', fontsize=11, fontweight='bold')
            axes[-1, col_idx].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            axes[-1, col_idx].xaxis.set_major_locator(mdates.HourLocator(interval=3))
            plt.setp(axes[-1, col_idx].xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Legend on first subplot
        from matplotlib.patches import Patch
        from matplotlib.lines import Line2D
        
        legend_elements = []
        if use_pclass:
            legend_elements = [
                Patch(facecolor='#d1e5f0', alpha=0.8, label='Dry Snow'),
                Patch(facecolor='#f4a582', alpha=0.8, label='Wet Snow'),
                Patch(facecolor='#c2a5cf', alpha=0.8, label='Mixed Phase'),
                Patch(facecolor='#92c5de', alpha=0.8, label='Rain'),
            ]
        else:
            legend_elements = [
                Patch(facecolor='blue', alpha=0.8, label='Rain'),
                Patch(facecolor='cyan', alpha=0.8, label='Snow'),
                Patch(facecolor='gray', alpha=0.8, label='Mix'),
            ]
        
        if has_tw:
            legend_elements.extend([
                Line2D([0], [0], color='black', linewidth=2, label='Tw (°C)'),
                Line2D([0], [0], color='blue', linestyle='--', linewidth=1.5, label='Dry Snow Limit'),
                Line2D([0], [0], color='red', linestyle='--', linewidth=1.5, label='Wet Snow Limit'),
            ])
        
        axes[0, 0].legend(handles=legend_elements, loc='upper right', fontsize=9, ncol=3, framealpha=0.9)
        
        plt.suptitle(f'{source.upper()} - {event_day.strftime("%Y-%m-%d")}\n'
                     f'Precipitation | Type | {"Tw" if has_tw else ""}',
                     fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.show()


def plot_cml_sensor_matching(
    df_cml_meta, 
    sensor_metas=None,
    cml_to_sensor_maps=None,
    cml_ids=None, 
    sensor_types=None,
    n_cmls=5, 
    base_path=None, 
    figsize=(14, 12),
    all_metadata=None,
    debug=True  # ADD DEBUG FLAG
):
    """
    Plot selected CMls with their matched sensors, showing distances.
    """
    
    # Handle all_metadata convenience input
    if all_metadata is not None and sensor_metas is None:
        sensor_metas = {
            'PWS': all_metadata.get('pws'),
            'ASOS': all_metadata.get('asos'),
            'Mesonet': all_metadata.get('mesonet'),
        }
        sensor_metas = {k: v for k, v in sensor_metas.items() if v is not None}
    
    if sensor_metas is None:
        sensor_metas = {}
    
    if cml_to_sensor_maps is None:
        cml_to_sensor_maps = {}
    
    # Determine which sensor types to plot
    if sensor_types is None:
        sensor_types = list(cml_to_sensor_maps.keys())
    
    if len(sensor_types) == 0:
        print("⚠ No sensor types to plot - cml_to_sensor_maps is empty!")
        print(f"  Received cml_to_sensor_maps keys: {list(cml_to_sensor_maps.keys())}")
        return None
    
    if debug:
        print(f"DEBUG: sensor_types to plot: {sensor_types}")
        for st in sensor_types:
            if st in cml_to_sensor_maps:
                map_keys = list(cml_to_sensor_maps[st].keys())[:5]
                print(f"  {st} map has {len(cml_to_sensor_maps[st])} CMLs, first keys: {map_keys}")
                # Check key types
                if len(map_keys) > 0:
                    print(f"    Key type: {type(map_keys[0])}")
    
    # Sensor type styling
    sensor_styles = {
        'PWS': {'marker': 'o', 'size': 60, 'label': 'PWS'},
        'ASOS': {'marker': '^', 'size': 80, 'label': 'ASOS'},
        'Mesonet': {'marker': 'D', 'size': 70, 'label': 'Mesonet'},
        'NOAA': {'marker': 'p', 'size': 80, 'label': 'NOAA'},
    }
    
    # Select CMls
    if cml_ids is None:
        all_cml_ids_in_maps = set()
        for sensor_type in sensor_types:
            if sensor_type in cml_to_sensor_maps:
                all_cml_ids_in_maps.update(cml_to_sensor_maps[sensor_type].keys())
        
        available = list(all_cml_ids_in_maps)
        if len(available) == 0:
            available = df_cml_meta['cml_id'].astype(str).tolist()
        
        if len(available) == 0:
            print("⚠ No CML IDs found")
            return None
        
        n_select = min(n_cmls, len(available)) if n_cmls else len(available)
        cml_ids = list(np.random.choice(available, size=n_select, replace=False))
    
    if debug:
        print(f"DEBUG: cml_ids to plot: {cml_ids}")
        print(f"  CML ID type: {type(cml_ids[0]) if len(cml_ids) > 0 else 'N/A'}")
    
    # Color map for CMls
    cmap = plt.cm.tab10
    cml_colors = {str(cml_id): cmap(i % 10) for i, cml_id in enumerate(cml_ids)}
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Plot NYC boundary if available
    if base_path:
        try:
            import geopandas as gpd
            nyc_shp = base_path / "gis" / "NYC_boundary" / "nyc_boundary.shp"
            if nyc_shp.exists():
                nyc = gpd.read_file(nyc_shp)
                nyc.boundary.plot(ax=ax, color='gray', linewidth=1, alpha=0.5)
        except Exception as e:
            if debug:
                print(f"DEBUG: Could not load NYC boundary: {e}")
    
    # Track plotted sensors
    plotted_sensors = {st: set() for st in sensor_types}
    
    # Detect CML coordinate columns
    if 'site_0_lon' in df_cml_meta.columns:
        lon_a_col, lat_a_col = 'site_0_lon', 'site_0_lat'
        lon_b_col, lat_b_col = 'site_1_lon', 'site_1_lat'
    elif 'site_a_longitude' in df_cml_meta.columns:
        lon_a_col, lat_a_col = 'site_a_longitude', 'site_a_latitude'
        lon_b_col, lat_b_col = 'site_b_longitude', 'site_b_latitude'
    else:
        print(f"⚠ Unknown CML coordinate columns: {df_cml_meta.columns.tolist()}")
        return None
    
    # Track bounds for auto-zoom
    all_lons, all_lats = [], []
    
    # Plot each CML and its matched sensors
    for cml_id in cml_ids:
        cml_id_str = str(cml_id)
        color = cml_colors[cml_id_str]
        
        # Get CML location
        cml_row = df_cml_meta[df_cml_meta['cml_id'].astype(str) == cml_id_str]
        if len(cml_row) == 0:
            if debug:
                print(f"DEBUG: CML {cml_id} not found in metadata")
            continue
        cml_row = cml_row.iloc[0]
        
        # CML endpoints
        lon_a, lat_a = cml_row[lon_a_col], cml_row[lat_a_col]
        lon_b, lat_b = cml_row[lon_b_col], cml_row[lat_b_col]
        cml_lon, cml_lat = (lon_a + lon_b) / 2, (lat_a + lat_b) / 2
        
        all_lons.extend([lon_a, lon_b])
        all_lats.extend([lat_a, lat_b])
        
        # Plot CML line
        ax.plot([lon_a, lon_b], [lat_a, lat_b], color=color, linewidth=3, 
                solid_capstyle='round', zorder=5)
        ax.scatter(cml_lon, cml_lat, color=color, s=100, marker='s', 
                   edgecolor='black', linewidth=1.5, zorder=6)
        
        # Plot matched sensors for each sensor type
        for sensor_type in sensor_types:
            if sensor_type not in cml_to_sensor_maps:
                continue
            
            sensor_map = cml_to_sensor_maps[sensor_type]
            style = sensor_styles.get(sensor_type, {'marker': 'o', 'size': 60, 'label': sensor_type})
            
            # TRY BOTH STRING AND ORIGINAL KEY
            matches_df = sensor_map.get(cml_id_str)
            if matches_df is None:
                matches_df = sensor_map.get(cml_id)
            if matches_df is None:
                # Try int version
                try:
                    matches_df = sensor_map.get(int(cml_id))
                except:
                    pass
            
            if debug and matches_df is None:
                print(f"DEBUG: No matches for CML {cml_id} in {sensor_type}")
                print(f"  Available keys (first 5): {list(sensor_map.keys())[:5]}")
            
            if matches_df is None or (isinstance(matches_df, pd.DataFrame) and matches_df.empty):
                continue
            
            if debug:
                print(f"DEBUG: CML {cml_id} has {len(matches_df)} {sensor_type} matches")
            
            # Iterate over DataFrame rows
            for _, match_row in matches_df.iterrows():
                sensor_id = match_row.get('station_id', match_row.get('station', 'unknown'))
                distance_m = match_row.get('distance_m', 0)
                distance_km = distance_m / 1000
                
                # Get sensor location - try multiple column names
                s_lat = match_row.get('latitude', match_row.get('lat', None))
                s_lon = match_row.get('longitude', match_row.get('lon', None))
                
                if s_lat is None or s_lon is None:
                    if debug:
                        print(f"DEBUG: Missing lat/lon for sensor {sensor_id}")
                        print(f"  Available columns: {match_row.index.tolist()}")
                    continue
                
                all_lons.append(s_lon)
                all_lats.append(s_lat)
                
                # Draw connection line
                ax.plot([cml_lon, s_lon], [cml_lat, s_lat], 
                        color=color, linestyle='--', linewidth=1, alpha=0.5, zorder=3)
                
                # Plot sensor (only once per sensor per type)
                if sensor_id not in plotted_sensors[sensor_type]:
                    ax.scatter(s_lon, s_lat, color=color, s=style['size'], marker=style['marker'],
                               edgecolor='black', linewidth=0.8, zorder=4, alpha=0.9)
                    plotted_sensors[sensor_type].add(sensor_id)
                
                # Add distance label
                mid_lon, mid_lat = (cml_lon + s_lon) / 2, (cml_lat + s_lat) / 2
                ax.annotate(f'{distance_km:.1f}km', (mid_lon, mid_lat), fontsize=7,
                            color=color, alpha=0.8, ha='center',
                            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))
    
    # Auto-zoom to data extent with padding
    if len(all_lons) > 0:
        pad = 0.02  # degrees
        ax.set_xlim(min(all_lons) - pad, max(all_lons) + pad)
        ax.set_ylim(min(all_lats) - pad, max(all_lats) + pad)
    
    # Build legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='gray', linewidth=3, label='CML Link'),
        Line2D([0], [0], marker='s', color='gray', markersize=10, 
               linestyle='None', label='CML Midpoint'),
    ]
    
    for sensor_type in sensor_types:
        n_sensors = len(plotted_sensors.get(sensor_type, set()))
        if n_sensors > 0:
            style = sensor_styles.get(sensor_type, {'marker': 'o', 'label': sensor_type})
            legend_elements.append(
                Line2D([0], [0], marker=style['marker'], color='gray', markersize=8,
                       linestyle='None', markeredgecolor='black', label=f'{style["label"]} ({n_sensors})')
            )
    
    legend_elements.append(
        Line2D([0], [0], color='gray', linestyle='--', linewidth=1, label='Match')
    )
    
    ax.legend(handles=legend_elements, loc='upper right')
    
    # Summary
    total_sensors = sum(len(s) for s in plotted_sensors.values())
    sensor_summary = ', '.join([f'{len(plotted_sensors.get(st, set()))} {st}' for st in sensor_types])
    
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title(f'CML to Sensor Matching\n{len(cml_ids)} CMls → {sensor_summary}', fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    
    plt.tight_layout()
    plt.show()
    
    print(f"✓ Plotted {len(cml_ids)} CMls with {total_sensors} sensors ({sensor_summary})")
    
    return fig



import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

def plot_precipitation_phase(weather_data_dict):
    """
    Plot precipitation phase classification for each data source.
    
    Parameters
    ----------
    weather_data_dict : dict
        Structure: {source: {parameter: DataFrame}}
        Expects 'p_class' and 'Tw' parameters to exist
    """
    # --- Color Configuration ---
    PHASE_COLORS = {
        'Dry Snow': '#d1e5f0',     # Light Blue (Safe)
        'Wet Snow': '#f4a582',     # Red/Orange (Danger/Sticky)
        'Mixed Phase': '#c2a5cf',  # Purple (Transition)
        'Rain': '#92c5de',         # Blue (Liquid)
        'No Precip': '#ffffff',    # White
        'Unknown': '#f0f0f0'       # Light Gray
    }
    
    # Iterate through each dataset (ASOS, Mesonet, etc.)
    # Skip NOAA daily as it doesn't have dewpoint data
    for key, param_dict in weather_data_dict.items():
        # Skip if not a dictionary (wrong structure)
        if not isinstance(param_dict, dict):
            print(f"⚠ Skipping '{key}': not a parameter dictionary")
            continue
        
        # Skip NOAA daily - it doesn't have dewpoint data
        if key == 'noaa_daily':
            print(f"⚠ Skipping '{key}': no dewpoint data available")
            continue
        
        # Check if Precip_Type and Tw_calc exist
        if 'p_class' not in param_dict or 'Tw' not in param_dict:
            print(f"⚠ Skipping '{key}': Precip_Type or Tw_calc not found. Available parameters: {list(param_dict.keys())}")
            continue
        
        precip_type_df = param_dict['p_class']
        tw_calc_df = param_dict['Tw']
        
        if precip_type_df is None or tw_calc_df is None:
            print(f"⚠ Skipping '{key}': Precip_Type or Tw_calc is None")
            continue
        
        if precip_type_df.empty or tw_calc_df.empty:
            print(f"⚠ Skipping '{key}': Precip_Type or Tw_calc is empty")
            continue

        print(f"--- Plotting {key} ---")
        
        # Align DataFrames by time index
        common_index = precip_type_df.index.intersection(tw_calc_df.index)
        if len(common_index) == 0:
            print(f"  [!] No common time index between Precip_Type and Tw_calc")
            continue
        
        precip_aligned = precip_type_df.loc[common_index]
        tw_aligned = tw_calc_df.loc[common_index]
        
        # Get common stations (columns)
        common_stations = set(precip_aligned.columns).intersection(set(tw_aligned.columns))
        if len(common_stations) == 0:
            print(f"  [!] No common stations between Precip_Type and Tw_calc")
            continue
        
        common_stations = sorted(list(common_stations))
        print(f"  Plotting {len(common_stations)} stations: {common_stations[:3]}..." if len(common_stations) > 3 else f"  Plotting {len(common_stations)} stations: {common_stations}")
        
        # 3. Setup Figure (One Subplot per Station)
        num_stations = len(common_stations)
        fig, axes = plt.subplots(nrows=num_stations, ncols=1, figsize=(14, 4 * num_stations), sharex=True)
        if num_stations == 1: 
            axes = [axes]  # Make iterable
        
        fig.suptitle(f"Wet-Bulb Temperature & Precip Classification: {key}", fontsize=16)
        
        # 4. Plot Each Station
        for ax, station in zip(axes, common_stations):
            # Get data for this station (extract Series, not DataFrame)
            tw_series = tw_aligned[station]  # This is a Series, not DataFrame
            precip_series = precip_aligned[station]  # This is a Series, not DataFrame
            
            # X values (time index)
            x_vals = tw_series.index
            
            # Y values (Tw values) - ensure it's a 1D array
            y_vals = tw_series.values
            
            # A. Plot Tw Line
            ax.plot(x_vals, y_vals, color='black', linewidth=1.5, label='Tw (°C)', zorder=2)
            
            # B. Plot Threshold Lines
            ax.axhline(0.5, color='red', linestyle='--', alpha=0.5, linewidth=1, label='Wet Snow Limit', zorder=1)
            ax.axhline(-0.5, color='blue', linestyle='--', alpha=0.5, linewidth=1, label='Dry Snow Limit', zorder=1)
            ax.axhline(1.5, color='orange', linestyle='--', alpha=0.3, linewidth=1, label='Mixed Phase Limit', zorder=1)
            
            # C. Color Background based on Precip Type
            # Create a DataFrame with aligned data for easier grouping
            plot_df = pd.DataFrame({
                'Tw': tw_series.values,
                'p_class': precip_series.values
            }, index=x_vals)
            
            # Identify where phase changes
            plot_df['group'] = (plot_df['p_class'] != plot_df['p_class'].shift()).cumsum()
            
            # Plot background shading for each phase block
            for g, block in plot_df.groupby('group'):
                phase = block['p_class'].iloc[0]
                color = PHASE_COLORS.get(phase, '#ffffff')
                
                # Add vertical span for this phase block
                if phase not in ['No Precip', 'Unknown']:
                    start_x = block.index[0]
                    end_x = block.index[-1]
                    ax.axvspan(start_x, end_x, color=color, alpha=0.3, zorder=0, 
                              label=phase if g == 1 else '')  # Only label first occurrence
            
            # D. Formatting
            ax.set_title(f"Station: {station}", fontsize=12)
            ax.set_ylabel("Wet-Bulb Temp ($T_w$) [°C]", fontsize=10)
            ax.grid(True, linestyle=':', alpha=0.6, zorder=0)
            
            # Format X-Axis dates nicely
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))  # Show every 6 hours
            plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=8)
            
            # Avoid duplicate labels in legend
            handles, labels = ax.get_legend_handles_labels()
            seen_labels = set()
            unique_handles = []
            unique_labels = []
            for h, l in zip(handles, labels):
                if l not in seen_labels:
                    seen_labels.add(l)
                    unique_handles.append(h)
                    unique_labels.append(l)
            
            ax.legend(unique_handles, unique_labels, loc='upper right', fontsize=8, ncol=2)

        plt.tight_layout(rect=[0, 0.03, 1, 0.97])  # Adjust for suptitle
        plt.show()
