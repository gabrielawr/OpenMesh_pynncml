# 3D Scatter Plot Usage Examples

## Example 1: Basic 3D Scatter for Snowfall Days (colored by time)
```python
from src.analysis.scatter_plots import plot_3d_scatter_attenuation_precip_temp

# Plot 3D scatter for snowfall days - colored by time progression
plot_3d_scatter_attenuation_precip_temp(
    df_cml_filtered,
    all_params_filtered,
    days=snowy_days,
    precip_source='pws',
    temp_source='asos_1min',
    signal_type='attenuation',
    color_by='time',
    figsize=(12, 10)
)
```

## Example 2: 3D Scatter for Single Snowfall Day (colored by CML ID)
```python
# Focus on a specific snowfall day and color by CML link
plot_3d_scatter_attenuation_precip_temp(
    df_cml_filtered,
    all_params_filtered,
    days=[snowy_days[-1]],  # Last snowfall day
    precip_source='pws',
    temp_source='asos_1min',
    signal_type='attenuation',
    color_by='cml',  # Different color for each CML link
    cmap='tab20',  # Use discrete colormap for CML IDs
    figsize=(14, 10),
    alpha=0.7,
    s=30
)
```

## Example 3: 3D Scatter for Multiple Days (colored by precipitation intensity)
```python
# Color points by precipitation intensity to see relationship
plot_3d_scatter_attenuation_precip_temp(
    df_cml_filtered,
    all_params_filtered,
    days=snowy_days[:3],  # First 3 snowfall days
    precip_source='pws',
    temp_source='asos_1min',
    signal_type='attenuation',
    color_by='precip',  # Color by precipitation value
    cmap='Blues',  # Blue colormap for precipitation
    figsize=(12, 10),
    alpha=0.6,
    s=25
)
```

## Example 4: Compare Rainy vs Snowy Days
```python
# Snowfall days
plot_3d_scatter_attenuation_precip_temp(
    df_cml_filtered,
    all_params_filtered,
    days=snowy_days[:2],
    precip_source='pws',
    temp_source='asos_1min',
    signal_type='attenuation',
    color_by='time',
    cmap='cool',  # Cool colors for snow
    figsize=(12, 10)
)

# Rainy days (for comparison)
plot_3d_scatter_attenuation_precip_temp(
    df_cml_filtered,
    all_params_filtered,
    days=rainy_days[:2],
    precip_source='pws',
    temp_source='asos_1min',
    signal_type='attenuation',
    color_by='time',
    cmap='hot',  # Warm colors for rain
    figsize=(12, 10)
)
```
