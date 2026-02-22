# Fixes for plot_3d_scatter_attenuation_precip_temp Function

## Issues Identified:
1. **Precipitation scale/units**: Function doesn't handle different time resolutions or convert units properly (e.g., daily totals to mm/hr)
2. **Time coloring**: Not clear - uses raw timestamp numbers which don't show time progression well
3. **No time window detection**: Doesn't detect or report the actual time resolution being used

## Fixes Needed:

### 1. Add Time Resolution Detection and Proper Resampling

Replace the section starting at line ~4335 with:

```python
    # Detect CML time resolution (use first non-empty CML as reference)
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
    
    # Resample precipitation data to match CML time resolution
    # Handle different precipitation sources and their units
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
        
        # Extract aligned data s
        atten_aligned = cml_data_resampled.loc[common_times]
        precip_aligned = precip_resampled.loc[common_times]
        temp_aligned = temp_resampled.loc[common_times]
```

### 2. Improve Time Coloring

Replace the time coloring section (around line ~4387) with:

```python
    # Determine colors based on color_by parameter
    if color_by == 'time':
        # Color by timestamp - normalize to hours from start for clearer interpretation
        time_delta = times_array - times_array.min()
        time_hours = time_delta.total_seconds() / 3600.0
        colors = time_hours
        color_label = 'Time (hours from start)'
        # Use a sequential colormap that's more intuitive for time
        if cmap == 'viridis':
            cmap = 'plasma'  # Better for time progression
```

### 3. Update Y-axis Label to Show Units

Update the y-axis label (around line ~4425) to use the detected units:

```python
    # Set labels
    ax.set_xlabel(f'Attenuation (dB)', fontsize=12, fontweight='bold')
    ax.set_ylabel(f'Precipitation ({precip_units})', fontsize=12, fontweight='bold')
    ax.set_zlabel('Temperature (°C)', fontsize=12, fontweight='bold')
```

## Summary of Changes:
- ✅ Detects CML time resolution automatically
- ✅ Resamples precipitation to match CML resolution
- ✅ Converts units properly (daily totals → mm/hr, interval sums → mm/hr)
- ✅ Improves time coloring to show "hours from start" with better colormap
- ✅ Adds informative print statements about time windows and conversions
- ✅ Updates axis labels to show actual units used
