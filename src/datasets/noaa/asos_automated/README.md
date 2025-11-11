# NOAA ASOS Data Module

## 1. Overview

This module is responsible for fetching, processing, and managing weather data from the **NOAA Automated Surface Observing System (ASOS)** network.

The primary focus is on downloading high-frequency **5-minute interval data** for a specific set of weather stations located in the **New York City area**, particularly covering Manhattan and the areas surrounding Brooklyn. The module is designed to retrieve data for a user-defined time period.

## 2. Data Source

* **Dataset Name**: Automated Surface Observing System (ASOS) 5-Minute Data
* **Hosting Agency**: NOAA National Centers for Environmental Information (NCEI)
* **Source URL**: [https://www.ncei.noaa.gov/data/automated-surface-observing-system-five-minute/](https://www.ncei.noaa.gov/data/automated-surface-observing-system-five-minute/)
* **Documentation**: [ASOS Metadata](https://www.ncei.noaa.gov/access/metadata/landing-page/bin/iso?id=gov.noaa.ncdc:C00418)

## 3. Geographic Focus & Target Stations

This module is configured to target stations providing coverage for Manhattan and Brooklyn. The primary stations are:

| Station ID | Name / Location                       | Borough Coverage | WBAN  |
| :--------- | :------------------------------------ | :--------------- | :---- |
| `KNYC`     | Central Park                          | Manhattan        | 94728 |
| `KJFK`     | John F. Kennedy International Airport | Queens (serves Brooklyn) | 94789 |
| `KLGA`     | LaGuardia Airport                     | Queens (serves Brooklyn) | 14732 |

**Note**: While there are no major ASOS stations of this type located directly within Brooklyn, the stations at JFK and LGA in Queens provide the most relevant and comprehensive coverage for the borough.

## 4. Installation & Dependencies

### Required packages:

```bash
pip install requests pandas matplotlib numpy
```

Or install from the project requirements:

```bash
pip install -r requirements.txt
```

### Dependencies:
- `requests` >= 2.31.0 - For HTTP data fetching
- `pandas` >= 2.0.0 - For data processing
- `matplotlib` >= 3.8.0 - For visualization
- `numpy` >= 1.26 - For numerical operations

## 5. Module Components

### 5.1 `config.py`
Contains key configuration variables:
- List of target station IDs
- Start and end dates for data fetching
- File paths for data storage
- Quality control parameters
- Missing data codes

### 5.2 `fetcher.py`
Handles connection to the NCEI data server and downloads raw, fixed-width `.dat` files.

**Key Features:**
- Automatic URL generation for monthly files
- Retry logic with exponential backoff
- Skip already downloaded files
- Progress logging

**Usage:**
```python
from fetcher import ASOSFetcher
from datetime import datetime

fetcher = ASOSFetcher(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 3, 31)
)
results = fetcher.fetch_all_stations()
```

### 5.3 `processor.py`
Reads the raw `.dat` files, parses the fixed-width format, cleans the data, and outputs it into a structured format (CSV or Parquet).

**Key Features:**
- Fixed-width format parsing
- Unit conversions (°F to °C, knots to m/s, inHg to hPa)
- Missing data handling
- Quality control flagging
- Duplicate removal

**Usage:**
```python
from processor import ASOSProcessor

processor = ASOSProcessor()
results = processor.process_all_files()
```

**Output Variables:**
- `datetime` - Observation timestamp
- `station_id` - Station identifier
- `temp_c` - Temperature (°C)
- `dewpoint_c` - Dew point (°C)
- `wind_speed_ms` - Wind speed (m/s)
- `wind_gust_ms` - Wind gust (m/s)
- `wind_dir_deg` - Wind direction (degrees)
- `pressure_hpa` - Atmospheric pressure (hPa)
- `visibility_mi` - Visibility (statute miles)
- `present_wx` - Present weather code
- `qc_flag` - Quality control flags

### 5.4 `validator.py`
Performs data quality checks on the processed data to ensure completeness and accuracy.

**Checks performed:**
- Temporal coverage and gap identification
- Variable completeness
- Value range validation
- Quality control flag summary

**Usage:**
```python
from validator import ASOSValidator

validator = ASOSValidator()
report = validator.validate_all_stations()
validator.save_report(report)
```

### 5.5 `analyzer.py`
Provides basic analysis and visualization capabilities.

**Features:**
- Daily statistics computation
- Temperature time series plots
- Wind rose diagrams
- Summary statistics generation

**Usage:**
```python
from analyzer import ASOSAnalyzer

analyzer = ASOSAnalyzer()
df = analyzer.load_station_data('KJFK')
daily = analyzer.compute_daily_statistics(df, 'KJFK')
```

### 5.6 `main.py`
Orchestration script that runs the complete pipeline.

**Usage:**
```bash
# Run full pipeline for default date range
python main.py

# Run for specific date range
python main.py --start-date 2024-01-01 --end-date 2024-03-31

# Run only specific steps
python main.py --skip-fetch  # Skip fetching, process existing data
python main.py --skip-analyze  # Fetch, process, validate but don't analyze

# Process specific stations only
python main.py --stations KJFK KLGA
```

## 6. Usage Workflow

### Basic Workflow

The typical workflow is:

1. **Configure** the desired stations and date range in `config.py`
2. **Fetch** raw data using `fetcher.py`
3. **Process** the data using `processor.py`
4. **Validate** data quality using `validator.py`
5. **Analyze** the data using `analyzer.py`

### Quick Start

```python
# Run the entire pipeline
from main import run_full_pipeline
from datetime import datetime

success = run_full_pipeline(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)
```

### Advanced Usage

```python
# Custom fetching for specific station
from fetcher import ASOSFetcher
from datetime import datetime

fetcher = ASOSFetcher(
    stations={'KJFK': {'wban': '94789', 'name': 'JFK Airport'}},
    start_date=datetime(2024, 6, 1),
    end_date=datetime(2024, 8, 31)
)
results = fetcher.fetch_station_data('KJFK')

# Custom processing with specific output format
from processor import ASOSProcessor

processor = ASOSProcessor()
df = processor.process_file(Path('data/noaa/asos/raw/KJFK_202406.dat'))
```

## 7. Data Format

### Raw Format
- **Format**: Fixed-width text (`.dat`) files
- **Structure**: Defined by NOAA ASOS specifications
- **Temporal Resolution**: 5-minute intervals
- **File Naming**: `{WBAN}{STATION_ID}{YYYYMM}.dat`
  - Example: `64010KJFK202401.dat`

### Processed Format
- **Format**: Comma-Separated Values (`.csv`) or Parquet (`.parquet`)
- **Structure**: Clearly defined columns with standardized units
- **Missing Data**: Represented as NaN
- **Quality Flags**: Included in `qc_flag` column
  - `T` = Temperature out of range
  - `P` = Pressure out of range
  - `W` = Wind speed out of range

## 8. Directory Structure

```
data/noaa/asos/
├── raw/                    # Original .dat files from NOAA
│   ├── KJFK_202401.dat
│   ├── KJFK_202402.dat
│   └── ...
├── processed/              # Cleaned CSV/Parquet files
│   ├── KJFK_202401.csv
│   ├── KJFK_202402.csv
│   ├── KJFK_daily_stats.csv
│   └── ...
├── logs/                   # Processing and download logs
│   └── noaa_pipeline.log
└── validation_report.csv   # Data quality report
```

## 9. Citation

When using this data, please cite:

```
NOAA National Weather Service, U.S. Federal Aviation Administration, U.S. Department of Defense, 
NOAA National Centers for Environmental Information (2005): 5-Minute Surface Weather Observations 
from the Automated Surface Observing Systems (ASOS) Network. NOAA National Centers for Environmental 
Information. NCEI DSI 6401_02. [access date].
```

## 10. Troubleshooting

### Common Issues

**Problem**: Files not downloading (404 errors)
- **Solution**: Check that the date range is valid. ASOS 5-minute data may not be available for all months/stations.

**Problem**: Processing fails with parsing errors
- **Solution**: The fixed-width format may vary by station/time period. Check the NOAA documentation for format changes.

**Problem**: Missing data in processed files
- **Solution**: This is normal - ASOS stations can have data gaps due to maintenance or technical issues. Check the validation report for completeness statistics.

### Logging

All operations are logged to `noaa_pipeline.log`. Check this file for detailed error messages and debugging information.

## 11. Contributing

To add new stations, edit the `STATIONS` dictionary in `config.py`:

```python
STATIONS = {
    'KNEW': {
        'name': 'New Station Name',
        'wban': '12345',
        'location': 'Location',
        'lat': 40.0,
        'lon': -73.0,
        'elevation_ft': 100
    }
}
```

## 12. License

This module is part of the OpenMesh project. Please refer to the main project LICENSE file.

## 13. Contact

For questions or issues:
- Open an issue on the project GitHub repository
- Contact the OpenMesh project team

---

Last updated: 2025-11-11
