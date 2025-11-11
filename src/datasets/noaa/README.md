# NOAA ASOS Weather Data

Two complementary methods for accessing NOAA Automated Surface Observing System (ASOS) data for NYC area stations (JFK, LaGuardia, Central Park).

## Methods Overview

### Method 1: IEM Manual Download (`asos_iem/`)
**Best for:** Quick analysis, exploratory work, specific time periods

**Advantages:**
- ✅ User-friendly web interface
- ✅ Pre-processed, clean CSV format
- ✅ 1-minute OR 5-minute resolution
- ✅ Flexible variable selection
- ✅ Often more complete data coverage

**Process:**
1. Visit https://mesonet.agron.iastate.edu/request/asos/1min.phtml
2. Select stations and date range
3. Download CSV files
4. Process with provided scripts

[→ See asos_iem/QUICKSTART.md for details](asos_iem/QUICKSTART.md)

---

### Method 2: Automated NOAA Download (`asos_automated/`)
**Best for:** Batch processing, automation, reproducible pipelines

**Advantages:**
- ✅ Fully programmatic (no manual steps)
- ✅ Direct from official NOAA NCEI source
- ✅ Complete pipeline: fetch → process → validate → analyze
- ✅ Good for large date ranges
- ✅ Reproducible research workflows

**Process:**
1. Configure stations and dates in config.py
2. Run: `python main.py`
3. Automated download, processing, validation

[→ See asos_automated/README.md for details](asos_automated/README.md)

---

## Which Method Should I Use?

| Use Case | Recommended Method |
|----------|-------------------|
| Quick exploratory analysis | IEM Manual |
| One-time data pull for specific dates | IEM Manual |
| Automated data pipeline | NOAA Automated |
| Large date ranges (> 6 months) | NOAA Automated |
| Reproducible research | NOAA Automated |
| Publication dataset | Both (validate consistency) |

## Stations Covered

Both methods support:
- **KJFK** - John F. Kennedy International Airport
- **KLGA** - LaGuardia Airport  
- **KNYC** - Central Park

## Data Variables

Common variables available in both:
- Temperature & Dew Point
- Wind Speed & Direction
- Atmospheric Pressure
- Visibility
- Precipitation

## Quick Start

### IEM Method:
```bash
cd asos_iem
python examples.py
```

### Automated Method:
```bash
cd asos_automated
python main.py --start-date 2024-01-01 --end-date 2024-12-31
```

## Citation

When using ASOS data, cite:
```
NOAA National Weather Service, U.S. Federal Aviation Administration, 
U.S. Department of Defense (2005): Automated Surface Observing System (ASOS) Data. 
NOAA National Centers for Environmental Information. [access date]
```

---

**Need help?** Check the README in each subdirectory for detailed documentation.
