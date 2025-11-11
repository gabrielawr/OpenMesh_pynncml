# Quick Start Guide

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Download ASOS Data

Visit: https://mesonet.agron.iastate.edu/request/asos/1min.phtml

Steps:
1. Select station(s) - e.g., KJFK (JFK), KLGA (LaGuardia)
2. Select date range
3. Choose variables: tmpf, dwpf, sknt, drct, precip, pres1, vsby (or select all)
5. Choose Temporal Resolution.
6. Rename to: [STATION_ID].txt (e.g., KJFK.txt)

## 3. Organize Data

```
asos_analysis/
├── asos_data/         (create this folder)
│   ├── KJFK.txt       (download files here)
│   ├── KLGA.txt
│   └── KEWR.txt
├── asos_processor.py
└── examples.py
```

## 4. Run Analysis

```bash
python examples.py
```

Select an example from the menu to see the toolkit in action.

## 5. Use in Your Code

```python
from asos_processor import read_asos_files, analyze_data, plot_variable

# Load data
data = read_asos_files('./asos_data')

# Analyze
for station_id, df in data.items():
    analysis = analyze_data(df, station_id)
    
# Plot
plot_variable(data, 'tmpf', save_path='temperature.png')
```

## Common Tasks

### Analyze all stations
```python
from asos_processor import read_asos_files, analyze_data, print_analysis

data = read_asos_files('./asos_data')

for station_id, df in data.items():
    analysis = analyze_data(df, station_id)
    print_analysis(analysis)
```

### Filter to date range
```python
from asos_processor import filter_by_date_range

filtered = filter_by_date_range(df, '2024-01-15', '2024-01-31')
```

### Plot specific variable
```python
from asos_processor import plot_variable

plot_variable(data, 'tmpf')
```

### Compare stations
```python
from asos_processor import compare_stations

compare_stations(data, 'tmpf')
```

## Troubleshooting

**"No .txt files found"**
- Create `asos_data/` folder in project directory
- Ensure files are named correctly: [STATION_ID].txt

**"Variable not found"**
- Check which variables are in your data: `df.columns`
- Common variables: tmpf, dwpf, sknt, drct, precip_mm, pres1, vsby

**Plot not showing**
- Saves to file automatically if save_path specified
- Or use `plt.show()` in your own script

## Next Steps

1. Read USAGE_GUIDE.md for detailed function documentation
2. Explore examples.py for more examples
3. Check README.md for background information
