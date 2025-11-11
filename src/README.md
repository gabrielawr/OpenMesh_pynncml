# Source Code - Data Processing Modules

This directory contains data fetching and processing modules for the OpenMesh dataset.

## Directory Structure
```
src/
└── datasets/
    ├── noaa/          # NOAA ASOS weather station data
    └── wu/            # Weather Underground Personal Weather Stations
```

## Modules Overview

### 📡 NOAA ASOS (`datasets/noaa/`)

Two complementary methods for accessing official NOAA Automated Surface Observing System data from NYC airports (JFK, LaGuardia, Central Park):

**Method 1: Automated Fetcher** (`asos_automated/`)
- Programmatic downloads from NOAA NCEI
- Complete pipeline: fetch → process → validate → analyze
- Best for: Large date ranges, reproducible workflows

**Method 2: IEM Manual Download** (`asos_iem/`)
- User-friendly web interface download
- Pre-processed clean data
- Best for: Quick analysis, exploratory work

**Variables:** Temperature, dew point, wind speed/direction, pressure, visibility  
**Temporal Resolution:** 5-minute intervals  
**Documentation:** [See noaa/README.md](datasets/noaa/README.md)

---

### 🌦️ Weather Underground (`datasets/wu/`)

Personal Weather Station (PWS) data fetching from Weather Underground API.

**Features:**
- API-based data retrieval
- High-resolution observations (1-5 minute intervals)
- Multiple NYC-area personal weather stations
- Flexible date range selection

**Variables:** Temperature, humidity, rainfall, wind, pressure  
**Documentation:** [See wu/fetch_data/README.md](datasets/wu/fetch_data/README.md)

---

## Quick Start

### NOAA Data (Automated)
```bash
cd datasets/noaa/asos_automated
python main.py --start-date 2024-01-01 --end-date 2024-12-31
```

### NOAA Data (IEM Manual)
```bash
cd datasets/noaa/asos_iem
# 1. Download data from https://mesonet.agron.iastate.edu/request/asos/1min.phtml
# 2. Run processor:
python examples.py
```

### Weather Underground Data
```bash
cd datasets/wu/fetch_data
# Configure API key in main.py
python main.py
```

## Installation

Each module has its own `requirements.txt`. Install dependencies:
```bash
# For NOAA modules
pip install -r datasets/noaa/asos_automated/requirements.txt
pip install -r datasets/noaa/asos_iem/requirements.txt

# For Weather Underground
pip install -r datasets/wu/fetch_data/requirements.txt
```

Or install all at once:
```bash
pip install requests pandas numpy matplotlib xarray netCDF4
```

## Data Output Locations

Data is organized in the project's `data/` directory (created automatically):
```
data/
├── noaa/
│   └── asos/
│       ├── raw/          # Original .dat files
│       └── processed/    # Clean CSV files
└── wu/
    └── output/           # JSON/CSV files from API
```

## Usage Examples

### Fetch Multiple Data Sources
```python
# NOAA automated
from src.datasets.noaa.asos_automated.fetcher import ASOSFetcher
from datetime import datetime

fetcher = ASOSFetcher(
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 3, 31)
)
fetcher.fetch_all_stations()

# Weather Underground
from src.datasets.wu.fetch_data.wu_functions import fetch_all_data
# See wu documentation for details
```

### Process and Analyze
```python
# NOAA processing
from src.datasets.noaa.asos_automated.processor import ASOSProcessor

processor = ASOSProcessor()
processor.process_all_files()

# Analysis
from src.datasets.noaa.asos_automated.analyzer import ASOSAnalyzer

analyzer = ASOSAnalyzer()
df = analyzer.load_station_data('KJFK')
daily_stats = analyzer.compute_daily_statistics(df, 'KJFK')
```

## API Keys & Configuration

**Weather Underground:**
- Requires API key from https://www.wunderground.com/member/api-keys
- Configure in `datasets/wu/fetch_data/main.py`

**NOAA:**
- No API key required (public data)
- Configure stations and dates in `datasets/noaa/asos_automated/config.py`

## Contributing

When adding new data sources:

1. Create a new subdirectory under `datasets/`
2. Follow the modular structure: `fetcher.py`, `processor.py`, `config.py`
3. Include comprehensive README.md
4. Add requirements.txt with dependencies
5. Provide usage examples

## Citations

### NOAA ASOS Data
```
NOAA National Weather Service, U.S. Federal Aviation Administration, 
U.S. Department of Defense (2005): Automated Surface Observing System (ASOS) Data. 
NOAA National Centers for Environmental Information. [access date]
```

### Weather Underground Data
```
Weather Underground PWS Network. The Weather Company, an IBM Business. 
https://www.wunderground.com/ [access date]
```

---

For detailed documentation on each module, see the README files in their respective directories.
