import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from typing import List, Optional, Dict, Union
import matplotlib.dates as mdates


def plot_3d_scatter_attenuation_precip_temp(
    df_cml_dict: Dict[str, pd.DataFrame],
    all_params: Dict,
    days: List[Union[str, pd.Timestamp]],
    precip_source: str = 'pws',
    temp_source: str = 'asos_1min',
    signal_type: str = 'attenuation',
    figsize: tuple = (12, 10),
    alpha: float = 0.6,
    s: float = 20,
    color_by: str = 'time',
    cmap: str = 'viridis'
):
    """
    Create a 3D scatter plot of attenuation, precipitation, and temperature
    for specified event days (e.g., snowfall days).
    
    Parameters
    ----------
    df_cml_dict : dict
        Dictionary with keys like "cml_id_sublink_idx" and values as DataFrames
        with columns: 'rsl', 'baseline', 'attenuation', indexed by 'time'
    all_params : dict
        Dictionary containing weather parameters:
        - 'precip': dict with precipitation data sources (e.g., 'pws', 'noaa_daily')
        - 'temp': dict with temperature data sources (e.g., 'asos_1min', 'mesonet')
    days : list
        List of event days (e.g., snowy_days). Can be strings or pd.Timestamp
    precip_source : str, default 'pws'
        Which precipitation source to use from all_params['precip']
    temp_source : str, default 'asos_1min'
        Which temperature source to use from all_params['temp']
    signal_type : str, default 'attenuation'
        Which signal to plot from df_cml_dict ('attenuation' or 'rsl')
    figsize : tuple, default (12, 10)
        Figure size
    alpha : float, default 0.6
        Transparency of scatter points
    s : float, default 20
        Size of scatter points
    color_by : str, default 'time'
        How to color points: 'time' (by timestamp), 'cml' (by CML ID), or 'precip' (by precipitation)
    cmap : str, default 'viridis'
        Colormap to use
    
    Returns
    -------
    fig : matplotlib.figure.Figure
        The figure object
    ax : matplotlib.axes._subplots.Axes3DSubplot
        The 3D axes object
    """
    # Convert days to datetime
    event_days = pd.to_datetime(days)
    
    # Extract data sources
    precip_data = all_params.get('precip', {}).get(precip_source)
    temp_data = all_params.get('temp', {}).get(temp_source)
    
    if precip_data is None:
        raise ValueError(f"Precipitation data not found for source '{precip_source}'. "
                        f"Available sources: {list(all_params.get('precip', {}).keys())}")
    if temp_data is None:
        raise ValueError(f"Temperature data not found for source '{temp_source}'. "
                        f"Available sources: {list(all_params.get('temp', {}).keys())}")
    
    # Collect all data points
    all_attenuation = []
    all_precipitation = []
    all_temperature = []
    all_times = []
    all_cml_ids = []
    
    # Determine time range from event days
    start_time = event_days.min() - pd.Timedelta(hours=12)
    end_time = event_days.max() + pd.Timedelta(days=1, hours=12)
    
    # Filter precipitation and temperature data to event days
    if isinstance(precip_data, pd.DataFrame) and 'time' in precip_data.columns:
        precip_data = precip_data.set_index('time')
    if isinstance(temp_data, pd.DataFrame) and 'time' in temp_data.columns:
        temp_data = temp_data.set_index('time')
    
    # Get precipitation column (handle different column names)
    precip_col = None
    for col in precip_data.columns:
        if 'precip' in col.lower() or 'rain' in col.lower() or 'rate' in col.lower():
            precip_col = col
            break
    if precip_col is None:
        precip_col = precip_data.columns[0]  # Use first column as fallback
    
    # Get temperature column
    temp_col = None
    for col in temp_data.columns:
        if 'temp' in col.lower() or 'tmp' in col.lower():
            temp_col = col
            break
    if temp_col is None:
        temp_col = temp_data.columns[0]  # Use first column as fallback
    
    # Filter to event days window
    precip_filtered = precip_data.loc[start_time:end_time, precip_col].dropna()
    temp_filtered = temp_data.loc[start_time:end_time, temp_col].dropna()
    
    # Process each CML link
    for cml_key, df_cml in df_cml_dict.items():
        if signal_type not in df_cml.columns:
            continue
        
        # Extract CML ID
        cml_id = str(cml_key.split('_')[0])
        
        # Filter CML data to event days window
        cml_data = df_cml.loc[start_time:end_time, signal_type].dropna()
        
        if len(cml_data) == 0:
            continue
        
        # Align all three datasets by time
        # Find common time indices
        common_times = cml_data.index.intersection(precip_filtered.index).intersection(temp_filtered.index)
        
        if len(common_times) == 0:
            continue
        
        # Extract aligned data
        atten_aligned = cml_data.loc[common_times]
        precip_aligned = precip_filtered.loc[common_times]
        temp_aligned = temp_filtered.loc[common_times]
        
        # Store data
        all_attenuation.extend(atten_aligned.values)
        all_precipitation.extend(precip_aligned.values)
        all_temperature.extend(temp_aligned.values)
        all_times.extend(common_times)
        all_cml_ids.extend([cml_id] * len(common_times))
    
    if len(all_attenuation) == 0:
        print("⚠ No overlapping data found for the specified days")
        return None, None
    
    # Convert to arrays
    atten_array = np.array(all_attenuation)
    precip_array = np.array(all_precipitation)
    temp_array = np.array(all_temperature)
    times_array = pd.to_datetime(all_times)
    
    # Create figure and 3D axes
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection='3d')
    
    # Determine colors based on color_by parameter
    if color_by == 'time':
        # Color by timestamp (convert to numeric for colormap)
        time_numeric = mdates.date2num(times_array)
        colors = time_numeric
        color_label = 'Time'
    elif color_by == 'cml':
        # Color by CML ID
        unique_cmls = sorted(set(all_cml_ids))
        cml_to_num = {cml: i for i, cml in enumerate(unique_cmls)}
        colors = [cml_to_num[cml] for cml in all_cml_ids]
        color_label = 'CML ID'
    elif color_by == 'precip':
        # Color by precipitation value
        colors = precip_array
        color_label = 'Precipitation (mm/hr)'
    else:
        colors = 'blue'
        color_label = 'Fixed'
    
    # Create scatter plot
    scatter = ax.scatter(
        atten_array,
        precip_array,
        temp_array,
        c=colors,
        cmap=cmap,
        alpha=alpha,
        s=s,
        edgecolors='black',
        linewidths=0.5
    )
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax, pad=0.1)
    cbar.set_label(color_label, fontsize=12, fontweight='bold')
    
    # Set labels
    ax.set_xlabel(f'Attenuation (dB)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Precipitation (mm/hr)', fontsize=12, fontweight='bold')
    ax.set_zlabel('Temperature (°C)', fontsize=12, fontweight='bold')
    
    # Set title
    n_days = len(event_days)
    day_str = f"{event_days[0].strftime('%Y-%m-%d')}" if n_days == 1 else f"{n_days} days"
    ax.set_title(
        f'3D Scatter: Attenuation vs Precipitation vs Temperature\n'
        f'Event Days: {day_str}',
        fontsize=14,
        fontweight='bold',
        pad=20
    )
    
    # Add grid
    ax.grid(True, alpha=0.3)
    
    # Rotate view for better perspective
    ax.view_init(elev=20, azim=45)
    
    plt.tight_layout()
    plt.show()
    
    # Print summary statistics
    print("=" * 70)
    print("3D SCATTER PLOT SUMMARY")
    print("=" * 70)
    print(f"Total data points: {len(atten_array):,}")
    print(f"Number of CML links: {len(set(all_cml_ids))}")
    print(f"Event days: {n_days}")
    print(f"\nAttenuation range: {atten_array.min():.2f} - {atten_array.max():.2f} dB")
    print(f"Precipitation range: {precip_array.min():.2f} - {precip_array.max():.2f} mm/hr")
    print(f"Temperature range: {temp_array.min():.2f} - {temp_array.max():.2f} °C")
    print("=" * 70)
    
    return fig, ax


def plot_scatter_comparison(
    df_cml_dict,
    all_params,
    df_cml_meta,
    days=None,
    start_dt=None,
    end_dt=None,
    cml_to_pws_map=None,
    color_by='ptype',
    temp_threshold=0,
    figsize=(14, 6),
    **kwargs
):
    """
    Plot normalized (dB/km) vs non-normalized (dB) side by side.
    """
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    
    # Common params
    common_params = dict(
        days=days,
        start_dt=start_dt,
        end_dt=end_dt,
        cml_to_pws_map=cml_to_pws_map,
        color_by=color_by,
        temp_threshold=temp_threshold,
        combine_cmls=True,
        precip_source='pws',
        **kwargs
    )
    
    # LEFT: Not normalized (dB)
    # RIGHT: Normalized (dB/km)
    
    # We need to collect data manually and plot on our axes
    # For now, just call the function twice with different settings
    


def plot_precip_type_tw_by_event(all_params, event_days, source='asos_1min',
                                  window_days=1, max_events=None):
    """
    Unified plotting function: Plot precipitation, precipitation type, and Tw (if available)
    for each event day, with each station as a subplot.
    
    Shows:
    - Row 1: Precipitation (bars colored by type) + Type (background shading) - merged
    - Row 2: Tw (wet-bulb temperature, if available)
    
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
    
    # Color configurations - DIFFERENT for ASOS vs calculated
    if use_pclass:
        # Calculated classification colors (Dry Snow, Wet Snow, etc.)
        type_colors = {
            'Dry Snow': '#d1e5f0',     # Light Blue
            'Wet Snow': '#f4a582',     # Red/Orange
            'Mixed Phase': '#c2a5cf',  # Purple
            'Rain': '#92c5de',         # Blue
            'No Precip': 'none',
            'Unknown': 'lightgray'
        }
        type_labels = {
            'Dry Snow': 'Dry Snow (calc)',
            'Wet Snow': 'Wet Snow (calc)',
            'Mixed Phase': 'Mixed Phase (calc)',
            'Rain': 'Rain (calc)'
        }
    else:
        # ASOS precip type colors - DIFFERENT from calculated
        # Generic "snow" (not dry/wet distinction)
        type_colors = {
            'dry': 'none', 
            'rain': '#1f77b4',      # Darker blue (different from calc)
            'snow': '#00ced1',      # Dark cyan (different from calc dry/wet)
            'mix': '#808080',       # Gray
            'unknown': 'lightgray', 
            np.nan: 'none'
        }
        type_labels = {
            'rain': 'Rain (ASOS)',
            'snow': 'Snow (ASOS)',  # Generic snow, not dry/wet
            'mix': 'Mix (ASOS)'
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
        
        # Determine number of rows (1 if no Tw, 2 if Tw available)
        # HORIZONTAL LAYOUT: stations as columns, data types as rows
        n_rows = 2 if has_tw else 1
        n_cols = len(stations)
        fig, axes = plt.subplots(n_rows, n_cols, 
                                figsize=(4*n_cols, 3.5*n_rows), 
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
            
            # === ROW 1: PRECIPITATION + TYPE (merged - bars colored by type + background shading) ===
            ax_precip = axes[0, col_idx]
            
            for time, precip_val in precip.items():
                if pd.isna(precip_val) or precip_val == 0:
                    continue
                
                # Get type value
                type_val = ptype.loc[time] if time in ptype.index else ('Unknown' if use_pclass else 'unknown')
                
                if pd.isna(type_val):
                    color = type_colors.get(np.nan, 'lightgray') if not use_pclass else type_colors.get('Unknown', 'lightgray')
                else:
                    # Get color - different for ASOS vs calculated
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
                    # ASOS precip type - use different colors
                    if type_val == 'dry':
                        continue
                    if type_val == 'rain':
                        ax_precip.axvspan(time_current, time_next, alpha=0.05, color='#1f77b4', zorder=0)
                    elif type_val == 'snow':
                        ax_precip.axvspan(time_current, time_next, alpha=0.1, color='#00ced1', zorder=0)  # Dark cyan
                    elif type_val == 'mix':
                        ax_precip.axvspan(time_current, time_next, alpha=0.05, color='#808080', zorder=0)
            
            station_name = station.replace('1min_', '').replace('mesonet_', '')
            ax_precip.set_ylabel('Precip (mm)', fontsize=11, fontweight='bold')
            ax_precip.set_title(f'{station_name}', fontsize=12, fontweight='bold')
            ax_precip.grid(True, alpha=0.3, linestyle='--')
            ax_precip.set_ylim(bottom=0)
            ax_precip.set_xlim(plot_start, plot_end)
            
            # === ROW 2: TW (if available) ===
            if has_tw:
                ax_tw = axes[1, col_idx]
                
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
            # Calculated classification labels
            legend_elements = [
                Patch(facecolor='#d1e5f0', alpha=0.8, label='Dry Snow (calc)'),
                Patch(facecolor='#f4a582', alpha=0.8, label='Wet Snow (calc)'),
                Patch(facecolor='#c2a5cf', alpha=0.8, label='Mixed Phase (calc)'),
                Patch(facecolor='#92c5de', alpha=0.8, label='Rain (calc)'),
            ]
        else:
            # ASOS precip type labels - clearly marked as ASOS
            legend_elements = [
                Patch(facecolor='#1f77b4', alpha=0.8, label='Rain (ASOS)'),
                Patch(facecolor='#00ced1', alpha=0.8, label='Snow (ASOS)'),  # Generic snow
                Patch(facecolor='#808080', alpha=0.8, label='Mix (ASOS)'),
            ]
        
        if has_tw:
            legend_elements.extend([
                Line2D([0], [0], color='black', linewidth=2, label='Tw (°C)'),
                Line2D([0], [0], color='blue', linestyle='--', linewidth=1.5, label='Dry Snow Limit'),
                Line2D([0], [0], color='red', linestyle='--', linewidth=1.5, label='Wet Snow Limit'),
            ])
        
        axes[0, 0].legend(handles=legend_elements, loc='upper right', fontsize=9, ncol=3, framealpha=0.9)
        
        plt.suptitle(f'{source.upper()} - {event_day.strftime("%Y-%m-%d")}\n'
                     f'Precipitation + Type{" | Tw" if has_tw else ""}',
                     fontsize=14, fontweight='bold')
        plt.tight_layout()
        plt.show()



def plot_3d_scatter_attenuation_precip_temp(
    df_cml_dict: Dict[str, pd.DataFrame],
    all_params: Dict,
    days: List[Union[str, pd.Timestamp]],
    precip_source: str = 'pws',
    temp_source: str = 'asos_1min',
    signal_type: str = 'attenuation',
    precip_original_units: str = 'mm/hr',
    precip_xlim: tuple = (0, 20),  # ← NEW: Default limit for precip axis
    atten_ylim: tuple = None,      # ← NEW: Optional limit for attenuation
    temp_zlim: tuple = None,       # ← NEW: Optional limit for temperature
    figsize: tuple = (14, 10),
    alpha: float = 0.6,
    s: float = 30,
    color_by: str = 'temp',
    cmap: str = 'coolwarm',
    elev: float = 25,
    azim: float = -60
):
    """
    Create a 3D scatter plot with proper precipitation unit handling.
    
    Parameters
    ----------
    precip_original_units : str
        Units of the original precipitation data. Options:
        - 'mm/hr' : Already in mm/hr (PWS typical) - NO conversion needed
        - 'mm' : Accumulation in mm over measurement interval - CONVERT to rate
        - 'mm/5min' : Accumulation over 5 minutes - CONVERT to hourly rate
        - 'mm/day' : Daily accumulation (NOAA) - CONVERT to hourly rate
    precip_xlim : tuple
        X-axis limits for precipitation (mm/hr). Default: (0, 20)
    atten_ylim : tuple, optional
        Y-axis limits for attenuation (dB). Default: auto
    temp_zlim : tuple, optional
        Z-axis limits for temperature (°C). Default: auto
    """
    from mpl_toolkits.mplot3d import Axes3D
    from typing import List, Optional, Dict, Union
    import matplotlib.dates as mdates
    
    # Convert days to datetime
    event_days = pd.to_datetime(days)
    
    # Extract data sources
    precip_data = all_params.get('precip', {}).get(precip_source)
    temp_data = all_params.get('temp', {}).get(temp_source)
    
    if precip_data is None:
        raise ValueError(f"Precipitation data not found for source '{precip_source}'")
    if temp_data is None:
        raise ValueError(f"Temperature data not found for source '{temp_source}'")
    
    # Collect all data points
    all_attenuation = []
    all_precipitation = []
    all_temperature = []
    all_times = []
    all_cml_ids = []
    
    # Determine time range
    start_time = event_days.min() - pd.Timedelta(hours=12)
    end_time = event_days.max() + pd.Timedelta(days=1, hours=12)
    
    # Set index
    if isinstance(precip_data, pd.DataFrame) and 'time' in precip_data.columns:
        precip_data = precip_data.set_index('time')
    if isinstance(temp_data, pd.DataFrame) and 'time' in temp_data.columns:
        temp_data = temp_data.set_index('time')
    
    # Get columns
    precip_col = None
    for col in precip_data.columns:
        if 'precip' in col.lower() or 'rain' in col.lower() or 'rate' in col.lower():
            precip_col = col
            break
    if precip_col is None:
        precip_col = precip_data.columns[0]
    
    print(f"📊 Using precipitation column: '{precip_col}'")
    print(f"📏 Original units specified: '{precip_original_units}'")
    
    temp_col = None
    for col in temp_data.columns:
        if 'temp' in col.lower() or 'tmp' in col.lower():
            temp_col = col
            break
    if temp_col is None:
        temp_col = temp_data.columns[0]
    
    # Detect CML time resolution
    cml_time_resolution = None
    for cml_key, df_cml in df_cml_dict.items():
        if signal_type not in df_cml.columns:
            continue
        cml_data_sample = df_cml.loc[start_time:end_time, signal_type].dropna()
        if len(cml_data_sample) > 1:
            time_diffs = cml_data_sample.index.to_series().diff().dropna()
            cml_time_resolution = time_diffs.median()
            break
    
    if cml_time_resolution is None:
        cml_time_resolution = pd.Timedelta('15min')
        print(f"⚠ Using default CML resolution: {cml_time_resolution}")
    else:
        print(f"✓ Detected CML resolution: {cml_time_resolution}")
    
    interval_minutes = int(cml_time_resolution.total_seconds() / 60)
    interval_str = f"{interval_minutes}min"
    
    # ===== CORRECTED PRECIPITATION HANDLING =====
    precip_filtered_raw = precip_data.loc[start_time:end_time, precip_col].dropna()
    
    if precip_filtered_raw.empty:
        raise ValueError(f"No precipitation data available for '{precip_source}'")
    
    # Detect original resolution
    if len(precip_filtered_raw) > 1:
        orig_res = precip_filtered_raw.index.to_series().diff().dropna().median()
        print(f"✓ Original precip resolution: {orig_res}")
    
    # Convert based on original units
    if precip_original_units == 'mm/hr':
        # Already in mm/hr - just resample by AVERAGING
        print(f"✓ Data already in mm/hr - averaging over {interval_str}")
        precip_resampled = precip_filtered_raw.resample(interval_str).mean()
        precip_units = "mm/hr"
        
    elif precip_original_units == 'mm':
        # Accumulation in mm - sum over target interval, then convert to rate
        print(f"✓ Converting from mm accumulation to mm/hr")
        precip_resampled = precip_filtered_raw.resample(interval_str).sum()
        interval_hours = cml_time_resolution.total_seconds() / 3600
        precip_resampled = precip_resampled / interval_hours
        precip_units = "mm/hr"
        
    elif precip_original_units == 'mm/5min':
        # 5-minute accumulation - sum, then scale to hourly
        print(f"✓ Converting from mm/5min to mm/hr")
        precip_resampled = precip_filtered_raw.resample(interval_str).sum()
        # mm/5min * 12 = mm/hr
        precip_resampled = precip_resampled * 12
        precip_units = "mm/hr"
        
    elif precip_original_units == 'mm/day':
        # Daily accumulation (NOAA)
        print(f"✓ Converting from mm/day to mm/hr")
        precip_resampled = precip_filtered_raw.reindex(
            pd.date_range(start_time, end_time, freq=interval_str),
            method='ffill'
        )
        precip_resampled = precip_resampled / 24.0
        precip_units = "mm/hr (from daily)"
        
    else:
        raise ValueError(f"Unknown precip_original_units: '{precip_original_units}'. "
                        f"Options: 'mm/hr', 'mm', 'mm/5min', 'mm/day'")
    
    # Print diagnostic info
    print(f"\n📈 Resampled precipitation statistics:")
    print(f"   Min: {precip_resampled.min():.3f} mm/hr")
    print(f"   Max: {precip_resampled.max():.3f} mm/hr")
    print(f"   Mean: {precip_resampled.mean():.3f} mm/hr")
    print(f"   Non-zero count: {(precip_resampled > 0.01).sum()}")
    
    # Resample temperature
    temp_filtered_raw = temp_data.loc[start_time:end_time, temp_col].dropna()
    if not temp_filtered_raw.empty:
        temp_resampled = temp_filtered_raw.resample(interval_str).mean()
        print(f"✓ Resampled temperature -> {interval_str}")
    else:
        raise ValueError(f"No temperature data available")
    
    # Process each CML link
    for cml_key, df_cml in df_cml_dict.items():
        if signal_type not in df_cml.columns:
            continue
        
        cml_id = str(cml_key.split('_')[0])
        cml_data = df_cml.loc[start_time:end_time, signal_type].dropna()
        
        if len(cml_data) == 0:
            continue
        
        cml_data_resampled = cml_data.resample(interval_str).mean()
        
        # Align datasets
        common_times = cml_data_resampled.index.intersection(precip_resampled.index).intersection(temp_resampled.index)
        
        if len(common_times) == 0:
            continue
        
        atten_aligned = cml_data_resampled.loc[common_times]
        precip_aligned = precip_resampled.loc[common_times]
        temp_aligned = temp_resampled.loc[common_times]
        
        all_attenuation.extend(atten_aligned.values)
        all_precipitation.extend(precip_aligned.values)
        all_temperature.extend(temp_aligned.values)
        all_times.extend(common_times)
        all_cml_ids.extend([cml_id] * len(common_times))
    
    if len(all_attenuation) == 0:
        print("⚠ No overlapping data found")
        return None, None
    
    # Convert to arrays
    atten_array = np.array(all_attenuation)
    precip_array = np.array(all_precipitation)
    temp_array = np.array(all_temperature)
    times_array = pd.to_datetime(all_times)
    
    # Create figure
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection='3d')
    
    # Colors
    if color_by == 'temp':
        colors = temp_array
        color_label = 'Temperature (°C)'
        cmap = 'coolwarm'
    elif color_by == 'time':
        time_delta = times_array - times_array.min()
        time_hours = time_delta.total_seconds() / 3600.0
        colors = time_hours
        color_label = 'Hours from start'
        cmap = 'plasma'
    elif color_by == 'cml':
        unique_cmls = sorted(set(all_cml_ids))
        cml_to_num = {cml: i for i, cml in enumerate(unique_cmls)}
        colors = [cml_to_num[cml] for cml in all_cml_ids]
        color_label = 'CML ID'
        cmap = 'tab20'
    else:
        colors = atten_array
        color_label = 'Attenuation (dB)'
        cmap = 'viridis'
    
    # Scatter plot
    scatter = ax.scatter(
        precip_array,
        atten_array,
        temp_array,
        c=colors,
        cmap=cmap,
        alpha=alpha,
        s=s,
        edgecolors='black',
        linewidths=0.3
    )
    
    cbar = plt.colorbar(scatter, ax=ax, pad=0.1, shrink=0.8)
    cbar.set_label(color_label, fontsize=11, fontweight='bold')
    
    ax.set_xlabel(f'Precipitation ({precip_units})', fontsize=12, fontweight='bold', labelpad=10)
    ax.set_ylabel('Attenuation (dB)', fontsize=12, fontweight='bold', labelpad=10)
    ax.set_zlabel('Temperature (°C)', fontsize=12, fontweight='bold', labelpad=10)
    
    # ===== SET AXIS LIMITS =====
    if precip_xlim is not None:
        ax.set_xlim(precip_xlim)
        print(f"✓ Set precipitation axis limit: {precip_xlim}")
    
    if atten_ylim is not None:
        ax.set_ylim(atten_ylim)
        print(f"✓ Set attenuation axis limit: {atten_ylim}")
    
    if temp_zlim is not None:
        ax.set_zlim(temp_zlim)
        print(f"✓ Set temperature axis limit: {temp_zlim}")
    
    n_days = len(event_days)
    day_str = f"{event_days[0].strftime('%Y-%m-%d')}" if n_days == 1 else f"{n_days} days"
    ax.set_title(
        f'Attenuation vs Precipitation vs Temperature (3D)\n'
        f'{day_str} | {len(set(all_cml_ids))} CML Links',
        fontsize=13,
        fontweight='bold',
        pad=20
    )
    
    # Add freezing plane if temp crosses 0°C
    if temp_array.min() < 2 and temp_array.max() > -2:
        xx, yy = np.meshgrid(
            precip_xlim if precip_xlim else [precip_array.min(), precip_array.max()],
            atten_ylim if atten_ylim else [atten_array.min(), atten_array.max()]
        )
        zz = np.zeros_like(xx)  # 0°C plane
        ax.plot_surface(xx, yy, zz, alpha=0.15, color='cyan')
    
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.view_init(elev=elev, azim=azim)
    
    plt.tight_layout()
    
    print("\n" + "=" * 70)
    print("3D SCATTER SUMMARY")
    print("=" * 70)
    print(f"Points: {len(atten_array):,} | Links: {len(set(all_cml_ids))}")
    print(f"Precipitation: {precip_array.min():.2f} - {precip_array.max():.2f} mm/hr")
    print(f"Attenuation: {atten_array.min():.2f} - {atten_array.max():.2f} dB")
    print(f"Temperature: {temp_array.min():.2f} - {temp_array.max():.2f} °C")
    
    # Points outside limits
    if precip_xlim:
        outside = np.sum((precip_array < precip_xlim[0]) | (precip_array > precip_xlim[1]))
        print(f"Points outside precip limits: {outside} ({100*outside/len(precip_array):.1f}%)")
    
    print("=" * 70)
    
    return fig, ax


def auto_detect_precip_units(precip_data, precip_col, source_name):
    """
    Automatically detect precipitation units based on:
    1. Column name
    2. Time resolution
    3. Value ranges
    """
    # Get time resolution
    if len(precip_data) > 1:
        time_diff = precip_data.index.to_series().diff().dropna()
        time_res = time_diff.median()
        time_minutes = time_res.total_seconds() / 60
    else:
        time_res = None
        time_minutes = None
    
    # Check column name for explicit units
    col_lower = precip_col.lower()
    
    if 'mm/hr' in col_lower or 'mm_per_hr' in col_lower or 'mmhr' in col_lower:
        detected_units = 'mm/hr'
        confidence = 'HIGH (from column name)'
    elif 'mm/day' in col_lower or 'daily' in col_lower:
        detected_units = 'mm/day'
        confidence = 'HIGH (from column name)'
    elif 'mm/min' in col_lower or 'mm_per_min' in col_lower:
        detected_units = 'mm/min'
        confidence = 'HIGH (from column name)'
    elif 'rate' in col_lower:
        # "rate" usually means mm/hr
        detected_units = 'mm/hr'
        confidence = 'MEDIUM (rate typically means mm/hr)'
    elif time_minutes and time_minutes <= 1:
        # 1-minute data, likely mm per minute
        detected_units = 'mm'
        confidence = f'MEDIUM (1-min resolution suggests mm accumulation)'
    elif time_minutes and 4 <= time_minutes <= 6:
        # 5-minute data
        detected_units = 'mm/5min'
        confidence = f'MEDIUM (5-min resolution)'
    elif time_minutes and time_minutes >= 1440:
        # Daily data
        detected_units = 'mm/day'
        confidence = 'MEDIUM (daily resolution)'
    else:
        # Default to mm/hr
        detected_units = 'mm/hr'
        confidence = f'LOW (guessing, time res = {time_res})'
    
    print(f"🔍 Auto-detected units for '{source_name}': {detected_units}")
    print(f"   Confidence: {confidence}")
    print(f"   Column: '{precip_col}'")
    print(f"   Time resolution: {time_res if time_res else 'unknown'}")
    
    return detected_units


def plot_3d_scatter_attenuation_precip_temp(
    df_cml_dict: Dict[str, pd.DataFrame],
    all_params: Dict,
    days: List[Union[str, pd.Timestamp]],
    precip_source: str = 'pws',
    temp_source: str = 'asos_1min',
    signal_type: str = 'attenuation',
    precip_original_units: str = 'auto',  # ← NEW: 'auto' for automatic detection
    precip_xlim: tuple = (0, 20),
    atten_ylim: tuple = None,
    temp_zlim: tuple = None,
    figsize: tuple = (14, 10),
    alpha: float = 0.6,
    s: float = 30,
    color_by: str = 'temp',
    cmap: str = 'coolwarm',
    elev: float = 25,
    azim: float = -60
):
    """
    Create a 3D scatter plot with AUTOMATIC precipitation unit detection.
    
    Parameters
    ----------
    precip_original_units : str
        - 'auto' : Automatically detect units (RECOMMENDED)
        - 'mm/hr' : Already in mm/hr
        - 'mm' : Accumulation in mm over measurement interval
        - 'mm/5min' : Accumulation over 5 minutes
        - 'mm/day' : Daily accumulation
    """
    from mpl_toolkits.mplot3d import Axes3D
    from typing import List, Optional, Dict, Union
    import matplotlib.dates as mdates
    
    # Convert days to datetime
    event_days = pd.to_datetime(days)
    
    # Extract data sources
    precip_data = all_params.get('precip', {}).get(precip_source)
    temp_data = all_params.get('temp', {}).get(temp_source)
    
    if precip_data is None:
        available = list(all_params.get('precip', {}).keys())
        raise ValueError(f"Precipitation data not found for source '{precip_source}'. "
                        f"Available sources: {available}")
    if temp_data is None:
        available = list(all_params.get('temp', {}).keys())
        raise ValueError(f"Temperature data not found for source '{temp_source}'. "
                        f"Available sources: {available}")
    
    # Collect all data points
    all_attenuation = []
    all_precipitation = []
    all_temperature = []
    all_times = []
    all_cml_ids = []
    
    # Determine time range
    start_time = event_days.min() - pd.Timedelta(hours=12)
    end_time = event_days.max() + pd.Timedelta(days=1, hours=12)
    
    # Set index
    if isinstance(precip_data, pd.DataFrame) and 'time' in precip_data.columns:
        precip_data = precip_data.set_index('time')
    if isinstance(temp_data, pd.DataFrame) and 'time' in temp_data.columns:
        temp_data = temp_data.set_index('time')
    
    # Get precipitation column
    precip_col = None
    for col in precip_data.columns:
        if 'precip' in col.lower() or 'rain' in col.lower() or 'rate' in col.lower():
            precip_col = col
            break
    if precip_col is None:
        precip_col = precip_data.columns[0]
    
    # ===== AUTO-DETECT UNITS =====
    if precip_original_units == 'auto':
        precip_original_units = auto_detect_precip_units(precip_data, precip_col, precip_source)
    else:
        print(f"📊 Using precipitation column: '{precip_col}'")
        print(f"📏 Manual units: '{precip_original_units}'")
    
    # Get temperature column
    temp_col = None
    for col in temp_data.columns:
        if 'temp' in col.lower() or 'tmp' in col.lower():
            temp_col = col
            break
    if temp_col is None:
        temp_col = temp_data.columns[0]
    
    # Detect CML time resolution
    cml_time_resolution = None
    for cml_key, df_cml in df_cml_dict.items():
        if signal_type not in df_cml.columns:
            continue
        cml_data_sample = df_cml.loc[start_time:end_time, signal_type].dropna()
        if len(cml_data_sample) > 1:
            time_diffs = cml_data_sample.index.to_series().diff().dropna()
            cml_time_resolution = time_diffs.median()
            break
    
    if cml_time_resolution is None:
        cml_time_resolution = pd.Timedelta('15min')
        print(f"⚠ Using default CML resolution: {cml_time_resolution}")
    else:
        print(f"✓ Detected CML resolution: {cml_time_resolution}")
    
    interval_minutes = int(cml_time_resolution.total_seconds() / 60)
    interval_str = f"{interval_minutes}min"
    
    # ===== PRECIPITATION CONVERSION LOGIC =====
    precip_filtered_raw = precip_data.loc[start_time:end_time, precip_col].dropna()
    
    if precip_filtered_raw.empty:
        raise ValueError(f"No precipitation data available for '{precip_source}'")
    
    # Detect original resolution
    if len(precip_filtered_raw) > 1:
        orig_res = precip_filtered_raw.index.to_series().diff().dropna().median()
        print(f"✓ Original precip resolution: {orig_res}")
    
    # Convert based on detected/specified units
    if precip_original_units == 'mm/hr':
        print(f"✓ Data already in mm/hr - averaging over {interval_str}")
        precip_resampled = precip_filtered_raw.resample(interval_str).mean()
        precip_units = "mm/hr"
        
    elif precip_original_units == 'mm':
        print(f"✓ Converting from mm accumulation to mm/hr")
        precip_resampled = precip_filtered_raw.resample(interval_str).sum()
        interval_hours = cml_time_resolution.total_seconds() / 3600
        precip_resampled = precip_resampled / interval_hours
        precip_units = "mm/hr"
        
    elif precip_original_units == 'mm/min':
        print(f"✓ Converting from mm/min to mm/hr")
        precip_resampled = precip_filtered_raw.resample(interval_str).mean()
        precip_resampled = precip_resampled * 60  # mm/min -> mm/hr
        precip_units = "mm/hr"
        
    elif precip_original_units == 'mm/5min':
        print(f"✓ Converting from mm/5min to mm/hr")
        precip_resampled = precip_filtered_raw.resample(interval_str).sum()
        precip_resampled = precip_resampled * 12  # mm/5min -> mm/hr
        precip_units = "mm/hr"
        
    elif precip_original_units == 'mm/day':
        print(f"✓ Converting from mm/day to mm/hr")
        precip_resampled = precip_filtered_raw.reindex(
            pd.date_range(start_time, end_time, freq=interval_str),
            method='ffill'
        )
        precip_resampled = precip_resampled / 24.0
        precip_units = "mm/hr (from daily)"
        
    else:
        raise ValueError(f"Unknown precip_original_units: '{precip_original_units}'. "
                        f"Options: 'auto', 'mm/hr', 'mm', 'mm/min', 'mm/5min', 'mm/day'")
    
    # Print diagnostic info
    print(f"\n📈 Resampled precipitation statistics:")
    print(f"   Min: {precip_resampled.min():.3f} mm/hr")
    print(f"   Max: {precip_resampled.max():.3f} mm/hr")
    print(f"   Mean: {precip_resampled.mean():.3f} mm/hr")
    print(f"   Non-zero (>0.01): {(precip_resampled > 0.01).sum()}")
    
    # Resample temperature
    temp_filtered_raw = temp_data.loc[start_time:end_time, temp_col].dropna()
    if not temp_filtered_raw.empty:
        temp_resampled = temp_filtered_raw.resample(interval_str).mean()
        print(f"✓ Resampled temperature -> {interval_str}")
    else:
        raise ValueError(f"No temperature data available")
    
    # Process each CML link
    for cml_key, df_cml in df_cml_dict.items():
        if signal_type not in df_cml.columns:
            continue
        
        cml_id = str(cml_key.split('_')[0])
        cml_data = df_cml.loc[start_time:end_time, signal_type].dropna()
        
        if len(cml_data) == 0:
            continue
        
        cml_data_resampled = cml_data.resample(interval_str).mean()
        
        # Align datasets
        common_times = cml_data_resampled.index.intersection(precip_resampled.index).intersection(temp_resampled.index)
        
        if len(common_times) == 0:
            continue
        
        atten_aligned = cml_data_resampled.loc[common_times]
        precip_aligned = precip_resampled.loc[common_times]
        temp_aligned = temp_resampled.loc[common_times]
        
        all_attenuation.extend(atten_aligned.values)
        all_precipitation.extend(precip_aligned.values)
        all_temperature.extend(temp_aligned.values)
        all_times.extend(common_times)
        all_cml_ids.extend([cml_id] * len(common_times))
    
    if len(all_attenuation) == 0:
        print("⚠ No overlapping data found")
        return None, None
    
    # Convert to arrays
    atten_array = np.array(all_attenuation)
    precip_array = np.array(all_precipitation)
    temp_array = np.array(all_temperature)
    times_array = pd.to_datetime(all_times)
    
    # Create figure
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection='3d')
    
    # Colors
    if color_by == 'temp':
        colors = temp_array
        color_label = 'Temperature (°C)'
        cmap = 'coolwarm'
    elif color_by == 'time':
        time_delta = times_array - times_array.min()
        time_hours = time_delta.total_seconds() / 3600.0
        colors = time_hours
        color_label = 'Hours from start'
        cmap = 'plasma'
    elif color_by == 'cml':
        unique_cmls = sorted(set(all_cml_ids))
        cml_to_num = {cml: i for i, cml in enumerate(unique_cmls)}
        colors = [cml_to_num[cml] for cml in all_cml_ids]
        color_label = 'CML ID'
        cmap = 'tab20'
    else:
        colors = atten_array
        color_label = 'Attenuation (dB)'
        cmap = 'viridis'
    
    # Scatter plot
    scatter = ax.scatter(
        precip_array,
        atten_array,
        temp_array,
        c=colors,
        cmap=cmap,
        alpha=alpha,
        s=s,
        edgecolors='black',
        linewidths=0.3
    )
    
    cbar = plt.colorbar(scatter, ax=ax, pad=0.1, shrink=0.8)
    cbar.set_label(color_label, fontsize=11, fontweight='bold')
    
    ax.set_xlabel(f'Precipitation ({precip_units})', fontsize=12, fontweight='bold', labelpad=10)
    ax.set_ylabel('Attenuation (dB)', fontsize=12, fontweight='bold', labelpad=10)
    ax.set_zlabel('Temperature (°C)', fontsize=12, fontweight='bold', labelpad=10)
    
    # Set axis limits
    if precip_xlim is not None:
        ax.set_xlim(precip_xlim)
    if atten_ylim is not None:
        ax.set_ylim(atten_ylim)
    if temp_zlim is not None:
        ax.set_zlim(temp_zlim)
    
    n_days = len(event_days)
    day_str = f"{event_days[0].strftime('%Y-%m-%d')}" if n_days == 1 else f"{n_days} days"
    ax.set_title(
        f'Attenuation vs Precipitation vs Temperature (3D)\n'
        f'{day_str} | {len(set(all_cml_ids))} CML Links',
        fontsize=13,
        fontweight='bold',
        pad=20
    )
    
    # Add freezing plane
    if temp_array.min() < 2 and temp_array.max() > -2:
        xx, yy = np.meshgrid(
            precip_xlim if precip_xlim else [0, 20],
            atten_ylim if atten_ylim else [atten_array.min(), atten_array.max()]
        )
        zz = np.zeros_like(xx)
        ax.plot_surface(xx, yy, zz, alpha=0.15, color='cyan')
    
    ax.grid(True, alpha=0.3, linestyle='--')




def plot_3d_scatter_attenuation_precip_temp(
    df_cml_dict: Dict[str, pd.DataFrame],
    all_params: Dict,
    days: List[Union[str, pd.Timestamp]],
    precip_source: str = 'pws',
    temp_source: str = 'asos_1min',
    signal_type: str = 'attenuation',
    figsize: tuple = (12, 10),
    alpha: float = 0.6,
    s: float = 20,
    color_by: str = 'time',
    cmap: str = 'viridis'
):
    """
    Create a 3D scatter plot of attenuation, precipitation, and temperature
    for specified event days (e.g., snowfall days).
    
    FIXED VERSION with:
    - Automatic time resolution detection
    - Proper precipitation unit conversion (mm/hr)
    - Improved time coloring
    """
    from mpl_toolkits.mplot3d import Axes3D
    from typing import List, Optional, Dict, Union
    import matplotlib.dates as mdates
    
    # Convert days to datetime
    event_days = pd.to_datetime(days)
    
    # Extract data sources
    precip_data = all_params.get('precip', {}).get(precip_source)
    temp_data = all_params.get('temp', {}).get(temp_source)
    
    if precip_data is None:
        raise ValueError(f"Precipitation data not found for source '{precip_source}'. "
                        f"Available sources: {list(all_params.get('precip', {}).keys())}")
    if temp_data is None:
        raise ValueError(f"Temperature data not found for source '{temp_source}'. "
                        f"Available sources: {list(all_params.get('temp', {}).keys())}")
    
    # Collect all data points
    all_attenuation = []
    all_precipitation = []
    all_temperature = []
    all_times = []
    all_cml_ids = []
    
    # Determine time range from event days
    start_time = event_days.min() - pd.Timedelta(hours=12)
    end_time = event_days.max() + pd.Timedelta(days=1, hours=12)
    
    # Filter precipitation and temperature data to event days
    if isinstance(precip_data, pd.DataFrame) and 'time' in precip_data.columns:
        precip_data = precip_data.set_index('time')
    if isinstance(temp_data, pd.DataFrame) and 'time' in temp_data.columns:
        temp_data = temp_data.set_index('time')
    
    # Get precipitation column (handle different column names)
    precip_col = None
    for col in precip_data.columns:
        if 'precip' in col.lower() or 'rain' in col.lower() or 'rate' in col.lower():
            precip_col = col
            break
    if precip_col is None:
        precip_col = precip_data.columns[0]  # Use first column as fallback
    
    # Get temperature column
    temp_col = None
    for col in temp_data.columns:
        if 'temp' in col.lower() or 'tmp' in col.lower():
            temp_col = col
            break
    if temp_col is None:
        temp_col = temp_data.columns[0]  # Use first column as fallback
    
    # ===== FIX 1: Detect CML time resolution =====
    cml_time_resolution = None
    for cml_key, df_cml in df_cml_dict.items():
        if signal_type not in df_cml.columns:
            continue
        cml_data_sample = df_cml.loc[start_time:end_time, signal_type].dropna()
        if len(cml_data_sample) > 1:
            # Calculate median time difference
            time_diffs = cml_data_sample.index.to_series().diff().dropna()
            cml_time_resolution = time_diffs.median()
            break
    
    if cml_time_resolution is None:
        # Default to 15 minutes if can't detect
        cml_time_resolution = pd.Timedelta('15min')
        print(f"⚠ Could not detect CML time resolution, using default: {cml_time_resolution}")
    else:
        print(f"✓ Detected CML time resolution: {cml_time_resolution}")
    
    # Convert to pandas frequency string (e.g., '15min', '1H')
    interval_minutes = int(cml_time_resolution.total_seconds() / 60)
    interval_str = f"{interval_minutes}min"
    
    # ===== FIX 2: Resample precipitation with proper unit conversion =====
    precip_filtered_raw = precip_data.loc[start_time:end_time, precip_col].dropna()
    precip_units = "mm/hr"
    
    if precip_source == 'noaa_daily':
        # NOAA daily is in mm/day - need special handling
        if not precip_filtered_raw.empty:
            # Resample daily data to match CML resolution (forward fill)
            precip_resampled = precip_filtered_raw.reindex(
                pd.date_range(start_time, end_time, freq=interval_str),
                method='ffill'
            )
            # Convert from mm/day to mm/hr (approximate)
            precip_resampled = precip_resampled / 24.0
            precip_units = "mm/hr (from daily totals)"
            print(f"✓ Resampled NOAA daily precipitation: {precip_source} -> {interval_str} (converted from mm/day to mm/hr)")
        else:
            raise ValueError(f"No precipitation data available for source '{precip_source}'")
    else:
        # For other sources (pws, asos_1min, mesonet), resample properly
        if not precip_filtered_raw.empty:
            # Detect original time resolution
            if len(precip_filtered_raw) > 1:
                orig_res = precip_filtered_raw.index.to_series().diff().dropna().median()
                print(f"✓ Original precip resolution: {orig_res} -> Resampling to: {interval_str}")
            
            # Sum precipitation over interval, then convert to rate
            precip_resampled = precip_filtered_raw.resample(interval_str).sum()
            # Convert to mm/hr: mm per interval -> mm/hr
            interval_hours = cml_time_resolution.total_seconds() / 3600
            precip_resampled = precip_resampled / interval_hours
            precip_units = "mm/hr"
            print(f"✓ Resampled precipitation: {precip_source} -> {interval_str} (converted to mm/hr)")
        else:
            raise ValueError(f"No precipitation data available for source '{precip_source}'")
    
    # Resample temperature data to match CML time resolution
    temp_filtered_raw = temp_data.loc[start_time:end_time, temp_col].dropna()
    if not temp_filtered_raw.empty:
        temp_resampled = temp_filtered_raw.resample(interval_str).mean()
        print(f"✓ Resampled temperature: {temp_source} -> {interval_str}")
    else:
        raise ValueError(f"No temperature data available for source '{temp_source}'")
    
    # Process each CML link
    for cml_key, df_cml in df_cml_dict.items():
        if signal_type not in df_cml.columns:
            continue
        
        # Extract CML ID
        cml_id = str(cml_key.split('_')[0])
        
        # Filter CML data to event days window
        cml_data = df_cml.loc[start_time:end_time, signal_type].dropna()
        
        if len(cml_data) == 0:
            continue
        
        # Resample CML data to match interval
        cml_data_resampled = cml_data.resample(interval_str).mean()
        
        # Align all three datasets by time
        # Find common time indices
        common_times = cml_data_resampled.index.intersection(precip_resampled.index).intersection(temp_resampled.index)
        
        if len(common_times) == 0:
            continue
        
        # Extract aligned data
        atten_aligned = cml_data_resampled.loc[common_times]
        precip_aligned = precip_resampled.loc[common_times]
        temp_aligned = temp_resampled.loc[common_times]
        
        # Store data
        all_attenuation.extend(atten_aligned.values)
        all_precipitation.extend(precip_aligned.values)
        all_temperature.extend(temp_aligned.values)
        all_times.extend(common_times)
        all_cml_ids.extend([cml_id] * len(common_times))
    
    if len(all_attenuation) == 0:
        print("⚠ No overlapping data found for the specified days")
        return None, None
    
    # Convert to arrays
    atten_array = np.array(all_attenuation)
    precip_array = np.array(all_precipitation)
    temp_array = np.array(all_temperature)
    times_array = pd.to_datetime(all_times)
    
    # Create figure and 3D axes
    fig = plt.figure(figsize=figsize)
    ax = fig.add_subplot(111, projection='3d')
    
    # ===== FIX 3: Improve time coloring =====
    if color_by == 'time':
        # Color by timestamp - normalize to hours from start for clearer interpretation
        time_delta = times_array - times_array.min()
        time_hours = time_delta.total_seconds() / 3600.0
        colors = time_hours
        color_label = 'Time (hours from start)'
        # Use a sequential colormap that's more intuitive for time
        if cmap == 'viridis':
            cmap = 'plasma'  # Better for time progression
    elif color_by == 'cml':
        # Color by CML ID
        unique_cmls = sorted(set(all_cml_ids))
        cml_to_num = {cml: i for i, cml in enumerate(unique_cmls)}
        colors = [cml_to_num[cml] for cml in all_cml_ids]
        color_label = 'CML ID'
    elif color_by == 'precip':
        # Color by precipitation value
        colors = precip_array
        color_label = 'Precipitation (mm/hr)'
    else:
        colors = 'blue'
        color_label = 'Fixed'
    
    # Create scatter plot
    scatter = ax.scatter(
        atten_array,
        precip_array,
        temp_array,
        c=colors,
        cmap=cmap,
        alpha=alpha,
        s=s,
        edgecolors='black',
        linewidths=0.5
    )
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax, pad=0.1)
    cbar.set_label(color_label, fontsize=12, fontweight='bold')
    
    # Set labels (with proper units)
    ax.set_xlabel(f'Attenuation (dB)', fontsize=12, fontweight='bold')
    ax.set_ylabel(f'Precipitation ({precip_units})', fontsize=12, fontweight='bold')
    ax.set_zlabel('Temperature (°C)', fontsize=12, fontweight='bold')
    
    # Set title
    n_days = len(event_days)
    day_str = f"{event_days[0].strftime('%Y-%m-%d')}" if n_days == 1 else f"{n_days} days"
    ax.set_title(
        f'3D Scatter: Attenuation vs Precipitation vs Temperature\n'
        f'Event Days: {day_str}',
        fontsize=14,
        fontweight='bold',
        pad=20
    )
    
    # Add grid
    ax.grid(True, alpha=0.3)
    
    # Rotate view for better perspective
    ax.view_init(elev=20, azim=45)
    
    plt.tight_layout()
    plt.show()
    
    # Print summary statistics
    print("=" * 70)
    print("3D SCATTER PLOT SUMMARY")
    print("=" * 70)
    print(f"Total data points: {len(atten_array):,}")
    print(f"Number of CML links: {len(set(all_cml_ids))}")
    print(f"Event days: {n_days}")
    print(f"\nAttenuation range: {atten_array.min():.2f} - {atten_array.max():.2f} dB")
    print(f"Precipitation range: {precip_array.min():.2f} - {precip_array.max():.2f} {precip_units}")
    print(f"Temperature range: {temp_array.min():.2f} - {temp_array.max():.2f} °C")
    print("=" * 70)
    
    return fig, ax
