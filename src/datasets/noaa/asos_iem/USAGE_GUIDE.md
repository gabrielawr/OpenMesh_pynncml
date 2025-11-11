# ASOS Processor - Usage Guide

## Function Reference

### read_asos_files(data_path)

Load all ASOS .txt files from a directory and prepare for analysis.

```python
from asos_processor import read_asos_files

data = read_asos_files('./asos_data')
```

Returns: `Dict[str, pd.DataFrame]` with station IDs as keys

**Features:**
- Automatically detects .txt files
- Converts valid_time to datetime
- Converts precipitation from inches to millimeters
- Prints loading summary

---

### filter_by_date_range(df, start_date, end_date)

Filter data to a specific date range.

```python
from asos_processor import filter_by_date_range

# Get data for specific period
df_filtered = filter_by_date_range(df, 
                                   start_date='2024-01-15', 
                                   end_date='2024-01-31')

# Get data from start of dataset to specific date
df_before = filter_by_date_range(df, end_date='2024-01-31')

# Get data from specific date onward
df_after = filter_by_date_range(df, start_date='2024-01-15')
```

**Date format:** 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'

---

### analyze_data(df, station_id)

Generate comprehensive statistics for all numeric columns.

```python
from asos_processor import analyze_data, print_analysis

analysis = analyze_data(df, 'KJFK')
print_analysis(analysis)
```

Returns dictionary with:
- `station`: Station identifier
- `total_records`: Number of data points
- `date_range`: Time span of data
- For each numeric column:
  - `{variable}_count`: Number of non-null values
  - `{variable}_mean`: Average
  - `{variable}_min`: Minimum
  - `{variable}_max`: Maximum
  - `{variable}_std`: Standard deviation

---

### plot_variable(dataframes, variable, start_date, end_date, save_path)

Create time-series plot for a single variable.

```python
from asos_processor import plot_variable

# Plot temperature for all stations
plot_variable(data, 'tmpf')

# Plot with date filter
plot_variable(data, 'tmpf', 
              start_date='2024-01-15',
              end_date='2024-01-31')

# Save plot
plot_variable(data, 'precip_mm',
              save_path='precipitation.png')
```

**Features:**
- Supports multiple stations (creates subplots)
- Automatic statistics overlay
- Date filtering
- Grid and formatting included

---

### compare_stations(dataframes, variable, start_date, end_date, save_path)

Compare single variable across multiple stations on one plot.

```python
from asos_processor import compare_stations

# Compare temperature across airports
compare_stations(data, 'tmpf')

# Compare for specific date range
compare_stations(data, 'precip_mm',
                start_date='2024-01-15',
                end_date='2024-01-20',
                save_path='precip_comparison.png')
```

**Use cases:**
- Compare conditions across region
- Verify sensor consistency
- Regional analysis

---

### get_summary_table(dataframes)

Generate summary statistics table for all stations.

```python
from asos_processor import get_summary_table

summary = get_summary_table(data)
print(summary)
```

Returns DataFrame with columns:
- Station: Station ID
- Records: Number of observations
- Start: First timestamp
- End: Last timestamp
- Duration_Days: Days of data

---

## Common Workflows

### Workflow 1: Basic Analysis

```python
from asos_processor import read_asos_files, analyze_data, print_analysis

# Load data
data = read_asos_files('./asos_data')

# Analyze all stations
for station_id, df in data.items():
    analysis = analyze_data(df, station_id)
    print_analysis(analysis)
```

### Workflow 2: Temperature Analysis

```python
from asos_processor import read_asos_files, analyze_data, plot_variable

data = read_asos_files('./asos_data')

# Analyze temperature
for station_id, df in data.items():
    analysis = analyze_data(df, station_id)
    print(f"{station_id} - Avg Temp: {analysis['tmpf_mean']:.1f}°F")

# Plot temperature
plot_variable(data, 'tmpf', save_path='temperature.png')
```

### Workflow 3: Precipitation Analysis

```python
from asos_processor import read_asos_files, filter_by_date_range, plot_variable

data = read_asos_files('./asos_data')

# Filter to event period
filtered_data = {}
for station_id, df in data.items():
    filtered_data[station_id] = filter_by_date_range(
        df,
        start_date='2024-01-15',
        end_date='2024-01-16'
    )

# Plot precipitation
plot_variable(filtered_data, 'precip_mm', save_path='event_precip.png')
```

### Workflow 4: Multi-Station Comparison

```python
from asos_processor import read_asos_files, compare_stations, get_summary_table

data = read_asos_files('./asos_data')

# Show summary
print(get_summary_table(data))

# Compare temperatures
compare_stations(data, 'tmpf', save_path='temp_comparison.png')

# Compare wind speed
compare_stations(data, 'sknt', save_path='wind_comparison.png')
```

### Workflow 5: Data Export

```python
from asos_processor import read_asos_files, filter_by_date_range
import pandas as pd

data = read_asos_files('./asos_data')

# Export filtered data to CSV
results = []

for station_id, df in data.items():
    filtered = filter_by_date_range(df, '2024-01-15', '2024-01-31')
    
    for idx, row in filtered.iterrows():
        results.append({
            'Station': station_id,
            'Time': row['valid_time'],
            'Temp_F': row.get('tmpf'),
            'Precip_mm': row.get('precip_mm'),
            'Wind_knots': row.get('sknt'),
        })

export_df = pd.DataFrame(results)
export_df.to_csv('asos_export.csv', index=False)
print("Exported to asos_export.csv")
```

## Data Access

Access raw dataframes directly:

```python
data = read_asos_files('./asos_data')

# Get specific station
df = data['KJFK']

# View columns
print(df.columns)

# Access specific variable
temperatures = df['tmpf']

# Filter to specific condition
high_wind = df[df['sknt'] > 20]

# Group analysis
hourly_temp = df.groupby(df['valid_time'].dt.hour)['tmpf'].mean()
```

## Handling Missing Data

```python
# Check for missing values
print(df.isnull().sum())

# Remove rows with any missing values
df_clean = df.dropna()

# Remove rows missing specific column
df_temp_only = df.dropna(subset=['tmpf'])

# Fill missing values
df['precip_mm'].fillna(0, inplace=True)
```

## Date/Time Operations

```python
# Extract components
df['date'] = df['valid_time'].dt.date
df['hour'] = df['valid_time'].dt.hour
df['day_of_week'] = df['valid_time'].dt.day_name()

# Resample to hourly data
hourly_max_temp = df.set_index('valid_time')['tmpf'].resample('H').max()

# Get specific date
jan_15_data = df[df['valid_time'].dt.date == pd.to_datetime('2024-01-15').date()]
```

## Unit Conversions

```python
# Temperature: Fahrenheit to Celsius
df['tmpf_c'] = (df['tmpf'] - 32) * 5/9

# Wind: Knots to mph
df['sknt_mph'] = df['sknt'] * 1.15078

# Wind: Knots to m/s
df['sknt_ms'] = df['sknt'] * 0.51444

# Visibility: Statute miles to kilometers
df['vsby_km'] = df['vsby'] * 1.60934
```

## Statistics

```python
# Percentiles
q25 = df['tmpf'].quantile(0.25)
q75 = df['tmpf'].quantile(0.75)

# Find extremes
max_wind_idx = df['sknt'].idxmax()
max_wind_event = df.loc[max_wind_idx]

# Count occurrences
num_rain_events = (df['precip_mm'] > 0).sum()

# Correlation
correlation = df[['tmpf', 'dwpf']].corr()
```

## Troubleshooting

**"No .txt files found"**
- Verify files are in correct directory
- Check files have .txt extension

**"Variable not found in plot"**
- Check variable name matches column name exactly
- Use data['STATION'].columns to list available columns

**Missing data in output**
- Some stations may not measure all variables
- Use df.isnull().sum() to identify gaps
- Filter data to remove null values

**Plot not displaying**
- Add plt.show() after plot_variable()
- Or specify save_path to save to file instead
