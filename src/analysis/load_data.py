"""
Helper functions to load OpenMesh datasets.

This module provides functions to load:
1. OpenMesh CML (Commercial Microwave Links) data
2. PWS (Personal Weather Stations) data
3. NOAA ASOS (Automated Surface Observing System) data
4. Rain detection from CML attenuation data
"""

import xarray as xr
import pandas as pd
import numpy as np
import netCDF4 as nc
from pathlib import Path
from typing import Dict, Optional, Union, Tuple


# Default paths relative to this file
BASE_DIR = Path(__file__).parent.parent.parent
DATASET_DIR = BASE_DIR / "dataset"
LINKS_DIR = DATASET_DIR / "links"
WEATHER_STATIONS_DIR = DATASET_DIR / "weather stations"
# Alternative path: extracted dataset from Zenodo
EXTRACTED_WEATHER_STATIONS_DIR = BASE_DIR / "src" / "data" / "openmesh" / "extracted" / "dataset" / "weather stations"

# --- 1. CONFIGURATION ---
PHASE_THRESHOLDS = {
    'dry_snow_limit': -0.5,
    'wet_snow_limit': 0.5,
    'mixed_limit': 1.5
}



def load_all_data(output_dir, pws_source='full'):
    """Load all data sources with error handling."""
    data = {}
    
    # CML
    try:
        data['ds_cml'], data['df_cml_metadata'] = load_openmesh_cml()
    except Exception as e:
        data['ds_cml'], data['df_cml_metadata'] = None, None
        print(f"  ⚠ CML: {e}")
    
    # PWS
    try:
        pws_data = load_pws_data(source=pws_source)
        data['df_pws'] = extract_all_pws_rainfall(pws_data)
    except Exception as e:
        data['df_pws'] = None
        print(f"  ⚠ PWS: {e}")
    
    # CSV sources
    data['weather'] = load_all_csv_sources(output_dir)
    
    return data


"""
DATA SUMMARY FUNCTIONS
======================
Add to load_data.py or analysis.py
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional


def print_data_summary(
    all_params: Dict,
    df_cml_dict: Dict = None,
    start_date: pd.Timestamp = None,
    end_date: pd.Timestamp = None,
    rainy_days: List = None,
    snowy_days: List = None,
    dry_days: List = None,
    title: str = "DATA SUMMARY"
):
    """
    Print comprehensive data summary with statistics table.
    
    Parameters
    ----------
    all_params : dict
        Weather parameters dict {param: {source: DataFrame}}
    df_cml_dict : dict, optional
        CML data dict {link_id: DataFrame}
    start_date, end_date : pd.Timestamp, optional
        Date range
    rainy_days, snowy_days, dry_days : list, optional
        Event day lists
    """
    
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "="))
    print("=" * 80)
    
    # ========================================================================
    # 1. DATE RANGE
    # ========================================================================
    if start_date and end_date:
        total_days = (end_date - start_date).days + 1
        print(f"\n📅 DATE RANGE: {start_date.date()} → {end_date.date()} ({total_days} days)")
    
    # ========================================================================
    # 2. EVENT SUMMARY
    # ========================================================================
    if rainy_days is not None or snowy_days is not None:
        print("\n" + "-" * 80)
        print("📊 EVENT SUMMARY")
        print("-" * 80)
        
        total = len(dry_days or []) + len(rainy_days or [])
        if total == 0 and start_date and end_date:
            total = (end_date - start_date).days + 1
        
        events = []
        if rainy_days is not None:
            events.append(('🌧️  Rainy', len(rainy_days), rainy_days))
        if snowy_days is not None:
            events.append(('❄️  Snowy', len(snowy_days), snowy_days))
        if dry_days is not None:
            events.append(('☀️  Dry', len(dry_days), None))
        
        print(f"\n{'Event Type':<15} {'Days':>8} {'Percent':>10} {'Date Range':<30}")
        print("-" * 65)
        
        for event_name, count, days_list in events:
            pct = 100 * count / total if total > 0 else 0
            if days_list is not None and len(days_list) > 0:
                date_range = f"{min(days_list).strftime('%Y-%m-%d')} → {max(days_list).strftime('%Y-%m-%d')}"
            else:
                date_range = "-"
            print(f"{event_name:<15} {count:>8} {pct:>9.1f}% {date_range:<30}")
        
        print("-" * 65)
        print(f"{'Total':<15} {total:>8} {'100.0':>9}%")
        
        # Show actual snow days
        if snowy_days is not None and len(snowy_days) > 0:
            print(f"\n❄️  Snow days: {[d.strftime('%Y-%m-%d') for d in sorted(snowy_days)]}")
    
    # ========================================================================
    # 3. WEATHER DATA SUMMARY
    # ========================================================================
    print("\n" + "-" * 80)
    print("🌡️  WEATHER DATA SUMMARY")
    print("-" * 80)
    
    # Build table data
    table_data = []
    
    for param, sources in all_params.items():
        for source, df in sources.items():
            if df is None or (isinstance(df, pd.DataFrame) and df.empty):
                continue
            
            n_records = len(df)
            n_stations = df.shape[1] if isinstance(df, pd.DataFrame) else 1
            
            # Time range
            if hasattr(df, 'index') and len(df) > 0:
                t_start = df.index.min()  # pyright: ignore[reportUnusedVariable]
                t_end = df.index.max()
                
                # Detect resolution
                if len(df) > 1:
                    diff = pd.Series(df.index).diff().median()
                    if diff < pd.Timedelta(minutes=2):
                        resolution = "1min"
                    elif diff < pd.Timedelta(minutes=10):
                        resolution = "5min"
                    elif diff < pd.Timedelta(hours=2):
                        resolution = "hourly"
                    else:
                        resolution = "daily"
                else:
                    resolution = "?"
            else:
                t_start, t_end, resolution = None, None, "?"
            
            # Data quality
            if isinstance(df, pd.DataFrame):
                null_pct = 100 * df.isna().sum().sum() / (df.shape[0] * df.shape[1])
            else:
                null_pct = 100 * df.isna().sum() / len(df)
            
            table_data.append({
                'Parameter': param,
                'Source': source,
                'Stations': n_stations,
                'Records': n_records,
                'Resolution': resolution,
                'Null%': null_pct,
            })
    
    # Print table
    print(f"\n{'Parameter':<12} {'Source':<12} {'Stations':>8} {'Records':>10} {'Resolution':>10} {'Null%':>8}")
    print("-" * 65)
    
    for row in table_data:
        print(f"{row['Parameter']:<12} {row['Source']:<12} {row['Stations']:>8} {row['Records']:>10,} {row['Resolution']:>10} {row['Null%']:>7.1f}%")
    
    # ========================================================================
    # 4. CML DATA SUMMARY
    # ========================================================================
    if df_cml_dict is not None and len(df_cml_dict) > 0:
        print("\n" + "-" * 80)
        print("📡 CML DATA SUMMARY")
        print("-" * 80)
        
        n_links = len(df_cml_dict)
        
        # Aggregate stats
        total_records = 0
        all_starts = []
        all_ends = []
        
        for link_id, df in df_cml_dict.items():
            if df is not None and len(df) > 0:
                total_records += len(df)
                all_starts.append(df.index.min())
                all_ends.append(df.index.max())
        
        print(f"\n  Links:       {n_links}")
        print(f"  Records:     {total_records:,}")
        if all_starts:
            print(f"  Time range:  {min(all_starts)} → {max(all_ends)}")
        
        # Show a few link examples
        print(f"\n  Sample links:")
        for i, (link_id, df) in enumerate(list(df_cml_dict.items())[:5]):
            if df is not None:
                cols = [c for c in df.columns if c not in ['time']]
                print(f"    • Link {link_id}: {len(df):,} records, columns: {cols[:4]}...")
    
    # ========================================================================
    # 5. QUICK STATS
    # ========================================================================
    print("\n" + "-" * 80)
    print("📈 QUICK STATS")
    print("-" * 80)
    
    # Precipitation stats
    if 'precip' in all_params:
        print("\n  Precipitation:")
        for source, df in all_params['precip'].items():
            if df is not None and len(df) > 0:
                total = df.sum().sum() if isinstance(df, pd.DataFrame) else df.sum()
                mean_daily = total / max(1, len(df))
                print(f"    {source:<12}: total={total:,.1f}mm, mean={mean_daily:.2f}mm/record")
    
    # Temperature stats
    if 'temp' in all_params:
        print("\n  Temperature:")
        for source, df in all_params['temp'].items():
            if df is not None and len(df) > 0:
                t_min = df.min().min() if isinstance(df, pd.DataFrame) else df.min()
                t_max = df.max().max() if isinstance(df, pd.DataFrame) else df.max()
                t_mean = df.mean().mean() if isinstance(df, pd.DataFrame) else df.mean()
                print(f"    {source:<12}: min={t_min:.1f}°C, max={t_max:.1f}°C, mean={t_mean:.1f}°C")
    
    # Snow stats
    if 'snow' in all_params or 'snow_depth' in all_params:
        print("\n  Snow:")
        for param in ['snow', 'snow_depth']:
            if param in all_params:
                for source, df in all_params[param].items():
                    if df is not None and len(df) > 0:
                        s_max = df.max().max() if isinstance(df, pd.DataFrame) else df.max()
                        s_total = df.sum().sum() if isinstance(df, pd.DataFrame) else df.sum()
                        print(f"    {param}/{source}: max={s_max:.1f}mm, total={s_total:.1f}mm")
    
    print("\n" + "=" * 80 + "\n")



def convert_mesonet_to_utc(all_params):
    """
    Convert all Mesonet data from America/New_York timezone to UTC.
    """
    print("=" * 70)
    print("CONVERTING MESONET TIMEZONE: EST/EDT → UTC")
    print("=" * 70)
    
    for param_name, sources in all_params.items():
        if 'mesonet' in sources:
            df = sources['mesonet'].copy()
            
            if df.index.tz is None:
                try:
                    # For ambiguous times, assume DST=False (standard time, second occurrence)
                    # This is more common for weather data
                    df.index = df.index.tz_localize(
                        'America/New_York', 
                        ambiguous=False,  # Use standard time for ambiguous times
                        nonexistent='shift_forward'
                    )
                    
                    # Convert to UTC
                    df.index = df.index.tz_convert('UTC')
                    
                    # Make timezone-naive
                    df.index = df.index.tz_localize(None)
                    
                    sources['mesonet'] = df
                    print(f"  ✓ {param_name}: Converted mesonet from EST/EDT to UTC ({len(df)} records)")
                    
                except Exception as e:
                    print(f"  ✗ {param_name}: Error converting timezone - {e}")
            else:
                print(f"  ⚠ {param_name}: Mesonet already has timezone")
    
    print("=" * 70)
    return all_params



"""
Unified Parameter Extraction
=============================

Single function to extract any parameters from all data sources.
Pass params you want, get dicts back organized by source.

Available parameters:
- precip: precipitation amount (all sources)
- snow: snow accumulation (NOAA, Mesonet)
- snow_depth: snow depth (NOAA, Mesonet)
- temp: temperature (ASOS, NOAA, Mesonet)
- dewpoint: dew point (ASOS, Mesonet)
- wind_speed: wind speed (ASOS, NOAA, Mesonet)
- wind_dir: wind direction (ASOS, Mesonet)
- humidity: relative humidity (Mesonet)
- precip_type: precipitation type (ASOS 1-min)
- Tw: wet-bulb temperature (calculated, ASOS, Mesonet) - requires classification first
- p_class: precipitation classification (calculated, ASOS, Mesonet) - requires classification first
"""

import pandas as pd
from typing import Dict, List, Optional


# =============================================================================
# COLUMN MAPPINGS (param -> column names in each source)
# =============================================================================

COLUMN_MAPPING = {
    'precip': {
        'asos_1min': 'precip',
        'noaa_daily': 'precip',
        'mesonet': 'precip',
        'pws': 'rainfall_amount',
    },
    'snow': {
        'noaa_daily': 'snow',
        'mesonet': 'snow_depth',
    },
    'snow_depth': {
        'noaa_daily': 'snow_depth',
        'mesonet': 'snow_depth',
    },
    'temp': {
        'asos_1min': 'temp',
        'noaa_daily': ['temp', 'temp_avg'],
        'mesonet': ['temp', 'temp_2m'],
    },
    'dewpoint': {
        'asos_1min': 'dewpoint',
        'mesonet': 'dewpoint',
    },
    'wind_speed': {
        'asos_1min': 'wind_speed',
        'noaa_daily': 'wind_speed',
        'mesonet': 'wind_speed',
    },
    'wind_dir': {
        'asos_1min': 'wind_dir',
        'mesonet': 'wind_dir',
    },
    'humidity': {
        'mesonet': 'relative_humidity',
    },
    'precip_type': {
        'asos_1min': 'precip_type',
    },
    'Tw': {
        'asos_1min': 'Tw',
        'mesonet': 'Tw',
    },
    'p_class': {
        'asos_1min': 'Precip_Type',
        'mesonet': 'Precip_Type',
    },
}


# =============================================================================
# EXTRACTION FUNCTION
# =============================================================================

def extract_parameters(
    weather_data: dict,
    params: List[str],
    pws_data: Optional[pd.DataFrame] = None,
    preprocess: Optional[List[str]] = None,
) -> Dict[str, Dict[str, pd.DataFrame]]:
    """
    Extract specified parameters from all available data sources, with optional preprocessing.

    Parameters
    ----------
    weather_data : dict
        From load_all_csv_sources()
        Structure: {source: {parameter: DataFrame}}
    params : list
        Parameters to extract. Examples:
        - ['precip']
        - ['precip', 'temp', 'snow', 'snow_depth', 'precip_type']
        - ['precip', 'temp', 'snow']
        - ['Tw', 'p_class']  # Wet-bulb temp and precipitation classification (after running classification)
    pws_data : pd.DataFrame, optional
        PWS data (already extracted as single DataFrame)
    preprocess : list of str, optional
        List of preprocessing steps:
        - 'negative': for 'precip', 'snow', 'snow_depth', set negative values to 0
        - 'fill_na': for numeric params, fill NaN with 0

    Returns
    -------
    result : dict
        Structure: {param: {source: DataFrame}}
        
        Example:
        {
            'precip': {'asos_1min': df, 'noaa_daily': df, 'mesonet': df, 'pws': df},
            'temp': {'asos_1min': df, 'noaa_daily': df, 'mesonet': df},
            'snow': {'noaa_daily': df, 'mesonet': df},
            'snow_depth': {'noaa_daily': df, 'mesonet': df},
            'precip_type': {'asos_1min': df},
            'Tw': {'asos_1min': df, 'mesonet': df},  # Wet-bulb temperature (calculated)
            'p_class': {'asos_1min': df, 'mesonet': df}  # Precipitation classification (calculated)
        }
    """

    def _apply_preprocess(df: pd.DataFrame, col_name: str, param: str, preprocess: List[str]):
        """Apply preprocessing steps to a column"""
        # Handle negative values (for precip/snow parameters)
        if 'negative' in preprocess and param in ['precip', 'snow', 'snow_depth']:
            if col_name in df.columns and pd.api.types.is_numeric_dtype(df[col_name]):
                negative_ct = (df[col_name] < 0).sum()
                if negative_ct > 0:
                    print(f"      ⚠ Set {negative_ct} negative values to 0 in '{col_name}'")
                df[col_name] = df[col_name].clip(lower=0)
        
        # Fill NaN values
        if 'fill_na' in preprocess:
            if col_name in df.columns and pd.api.types.is_numeric_dtype(df[col_name]):
                na_ct = df[col_name].isna().sum()
                if na_ct > 0:
                    print(f"      ⚠ Filled {na_ct} NaN values with 0 in '{col_name}'")
                df[col_name] = df[col_name].fillna(0)
        
        return df

    result = {}

    if preprocess is None:
        preprocess = []

    print("=" * 70)
    print(f"EXTRACTING PARAMETERS: {params}")
    if preprocess:
        print(f"  Preprocessing: {preprocess}")
    print("=" * 70)

    for param in params:
        if param not in COLUMN_MAPPING:
            print(f"\n⚠ Parameter '{param}' not supported. Skipping.")
            print(f"   Available: {list(COLUMN_MAPPING.keys())}")
            continue

        param_dict = {}
        col_map = COLUMN_MAPPING[param]

        print(f"\n[{param.upper()}]")
        print("-" * 70)

        # Try each source
        for source, col_names in col_map.items():
            df = None
            found_col = None

            # Handle PWS separately (already a DataFrame)
            if source == 'pws':
                if pws_data is not None and isinstance(pws_data, pd.DataFrame):
                    df = pws_data.copy()
                    found_col = col_names
                    # Preprocess if requested
                    if preprocess and col_names in df.columns:
                        df = _apply_preprocess(df, col_names, param, preprocess)
                else:
                    print(f"  ⚠ {source}: data not provided or invalid")
                    continue

            # Handle CSV sources
            elif source in weather_data:
                # col_names can be string or list of alternatives
                if isinstance(col_names, str):
                    col_names_list = [col_names]
                else:
                    col_names_list = col_names if isinstance(col_names, list) else [col_names]

                # Try each column name (some params have aliases)
                for col in col_names_list:
                    if col in weather_data[source]:
                        df = weather_data[source][col].copy()
                        found_col = col
                        # Preprocess if requested
                        if preprocess:
                            df = _apply_preprocess(df, col, param, preprocess)
                        break

                if df is None:
                    print(f"  ✗ {source}: '{col_names_list}' not found")
                    continue
            else:
                print(f"  ⚠ {source}: not available")
                continue

            # Store if found
            if df is not None:
                param_dict[source] = df
                print(f"  ✓ {source}: {df.shape[0]} records, {df.shape[1]} stations")

        result[param] = param_dict

    print("\n" + "=" * 70)
    print(f"✓ Extraction complete")
    print(f"  Parameters extracted: {list(result.keys())}")
    for param, sources in result.items():
        if sources:  # Only show if sources found
            print(f"    {param}: {list(sources.keys())}")
    print("=" * 70 + "\n")

    return result


def load_openmesh_cml(
    cml_file: Optional[Union[str, Path]] = None,
    metadata_file: Optional[Union[str, Path]] = None
) -> Tuple[xr.Dataset, pd.DataFrame]:
    """
    Load OpenMesh CML (Commercial Microwave Links) dataset.
    
    Parameters
    ----------
    cml_file : str or Path, optional
        Path to ds_openmesh.nc file. If None, uses default location.
    metadata_file : str or Path, optional
        Path to links_metadata.csv file. If None, uses default location.
    
    Returns
    -------
    ds_cml : xarray.Dataset
        CML dataset with RSL (Received Signal Level) data
    df_metadata : pandas.DataFrame
        Link metadata (coordinates, frequency, polarization, etc.)
    
    Examples
    --------
    >>> ds_cml, df_metadata = load_openmesh_cml()
    >>> print(ds_cml)
    >>> print(df_metadata.head())
    """
    # Set default paths
    if cml_file is None:
        cml_file = LINKS_DIR / "ds_openmesh.nc"
    else:
        cml_file = Path(cml_file)
    
    if metadata_file is None:
        metadata_file = LINKS_DIR / "links_metadata.csv"
    else:
        metadata_file = Path(metadata_file)
    
    # Load CML dataset
    if not cml_file.exists():
        raise FileNotFoundError(f"CML file not found: {cml_file}")
    
    print(f"Loading OpenMesh CML data from: {cml_file}")
    ds_cml = xr.open_dataset(cml_file)
    
    print(f"  ✓ Loaded CML dataset:")
    print(f"    Links: {len(ds_cml.cml_id)}")
    print(f"    Time range: {pd.to_datetime(ds_cml.time.values[0])} to {pd.to_datetime(ds_cml.time.values[-1])}")
    print(f"    Time points: {len(ds_cml.time):,}")
    
    # Load metadata
    df_metadata = None
    if metadata_file.exists():
        df_metadata = pd.read_csv(metadata_file)
        print(f"  ✓ Loaded metadata: {len(df_metadata)} sublinks")
    else:
        print(f"  ⚠ Metadata file not found: {metadata_file}")
        df_metadata = pd.DataFrame()
    
    return ds_cml, df_metadata


def load_pws_data(
    pws_file: Optional[Union[str, Path]] = None,
    source: str = 'full'
) -> Dict[str, xr.Dataset]:
    """
    Load PWS (Personal Weather Stations) data from NetCDF files.
    
    This function automatically searches for files in two locations:
    1. `dataset/weather stations/` (recommended - extract files here)
    2. `src/data/openmesh/extracted/dataset/weather stations/` (from Zenodo extraction)
    
    Parameters
    ----------
    pws_file : str or Path, optional
        Path to PWS NetCDF file. If None, searches default locations based on source.
    source : str, optional
        Data source: 'full' (default) or 'sample'
        - 'full': Load from full NetCDF file (all periods: Oct 2023 - Jul 2024)
        - 'sample': Load sample NetCDF data (2 weeks: Jan 15-30, 2024)
    
    Returns
    -------
    pws_data : dict
        Dictionary mapping station_id to xarray.Dataset for each station
    
    Notes
    -----
    **File Locations:**
    - **Recommended**: Extract files from Zenodo to `dataset/weather stations/`
    - **Alternative**: Use files directly from `src/data/openmesh/extracted/dataset/weather stations/`
      (if you extracted the Zenodo archive there)
    
    **Sample vs Full:**
    - Sample: `pws_opensense_sample_jan.nc` - 2 weeks (Jan 15-30, 2024)
    - Full: `pws_opensense_os.nc` - Complete dataset (Oct 2023 - Jul 2024)
    
    Examples
    --------
    >>> # Load full NetCDF dataset (default)
    >>> pws_data = load_pws_data(source='full')
    
    >>> # Load sample NetCDF data
    >>> pws_data = load_pws_data(source='sample')
    """
    if source == 'sample':
        return load_pws_sample_data(pws_file)
    else:  # 'full' or default
        return load_pws_from_netcdf(pws_file)


def load_pws_from_netcdf(
    pws_file: Optional[Union[str, Path]] = None
) -> Dict[str, xr.Dataset]:
    """
    Load PWS (Personal Weather Stations) data from grouped NetCDF file.
    
    This function looks for the full dataset NetCDF file in two locations:
    1. `dataset/weather stations/` (recommended - extract files here)
    2. `src/data/openmesh/extracted/dataset/weather stations/` (from Zenodo extraction)
    
    Parameters
    ----------
    pws_file : str or Path, optional
        Path to PWS NetCDF file. If None, searches default locations:
        - `dataset/weather stations/pws_opensense_os.nc` (full dataset)
        - `src/data/openmesh/extracted/dataset/weather stations/pws_opensense_os.nc` (extracted)
    
    Returns
    -------
    pws_data : dict
        Dictionary mapping station_id to xarray.Dataset for each station
    
    Notes
    -----
    **File Locations:**
    - **Recommended**: Extract files from Zenodo to `dataset/weather stations/`
    - **Alternative**: Use files directly from `src/data/openmesh/extracted/dataset/weather stations/`
      (if you extracted the Zenodo archive there)
    """
    # Set default path
    if pws_file is None:
        # Try primary location first, then extracted location
        search_paths = [
            (WEATHER_STATIONS_DIR, "pws_opensense_os.nc"),
            (WEATHER_STATIONS_DIR, "pws.nc"),
            (EXTRACTED_WEATHER_STATIONS_DIR, "pws_opensense_os.nc"),
            (EXTRACTED_WEATHER_STATIONS_DIR, "pws.nc"),
        ]
        
        for base_dir, filename in search_paths:
            candidate = base_dir / filename
            if candidate.exists():
                pws_file = candidate
                break
        
        if pws_file is None:
            tried_paths = "\n".join([f"  - {base_dir / filename}" for base_dir, filename in search_paths])
            raise FileNotFoundError(
                f"Full PWS NetCDF file not found. Tried:\n{tried_paths}\n\n"
                f"**Solution:** Extract files from Zenodo to `dataset/weather stations/` or "
                f"use the extracted path `src/data/openmesh/extracted/dataset/weather stations/`"
            )
    else:
        pws_file = Path(pws_file)
    
    if not pws_file.exists():
        raise FileNotFoundError(f"PWS file not found: {pws_file}")
    
    print(f"Loading FULL PWS data from NetCDF: {pws_file}")
    
    # Open NetCDF file to get groups
    nc_file = nc.Dataset(pws_file, 'r')
    station_ids = list(nc_file.groups.keys())
    nc_file.close()
    
    print(f"  Found {len(station_ids)} stations")
    
    # Load each station as xarray dataset
    pws_data = {}
    errors = []
    for i, station_id in enumerate(station_ids):
        try:
            station_ds = xr.open_dataset(pws_file, group=station_id, engine='netcdf4')
            pws_data[station_id] = station_ds
            # Show first 3 examples only
            if i < 3:
                print(f"    ✓ {station_id}: {len(station_ds.time)} records")
        except Exception as e:
            errors.append((station_id, str(e)))
            if i < 3:
                print(f"    ✗ {station_id}: Error - {e}")
    
    # Summary
    if len(pws_data) > 3:
        print(f"    ... and {len(pws_data) - 3} more stations")
    if errors:
        print(f"    ✗ {len(errors)} stations failed to load")
    print(f"  ✓ Loaded {len(pws_data)} PWS stations")
    
    return pws_data


def load_pws_from_csv(
    csv_dir: Optional[Union[str, Path]] = None
) -> Dict[str, xr.Dataset]:
    """
    Load PWS data from CSV files exported by wu_pipeline notebook.
    
    Converts CSV format to xarray.Dataset format matching the NetCDF structure.
    
    Parameters
    ----------
    csv_dir : str or Path, optional
        Directory containing CSV files. If None, searches in src/data/wu_pws/
    
    Returns
    -------
    pws_data : dict
        Dictionary mapping station_id to xarray.Dataset for each station
    """
    # Set default directory
    if csv_dir is None:
        csv_dir = BASE_DIR / "src" / "data" / "wu_pws"
    else:
        csv_dir = Path(csv_dir)
    
    if not csv_dir.exists():
        raise FileNotFoundError(f"CSV directory not found: {csv_dir}")
    
    print(f"Loading PWS data from CSV files: {csv_dir}")
    
    # Find all precipitation CSV files
    precip_files = list(csv_dir.glob("precipitation_*.csv"))
    if len(precip_files) == 0:
        raise FileNotFoundError(f"No precipitation CSV files found in {csv_dir}")
    
    print(f"  Found {len(precip_files)} CSV files")
    
    pws_data = {}
    
    for csv_file in precip_files:
        try:
            # Extract station ID from filename (format: precipitation_STATIONID_DATE.csv)
            filename = csv_file.stem  # Remove .csv extension
            parts = filename.split('_')
            if len(parts) >= 2:
                station_id = parts[1]  # Second part is station ID
            else:
                print(f"    ⚠ Could not parse station ID from {csv_file.name}, skipping...")
                continue
            
            # Read CSV
            df = pd.read_csv(csv_file)
            
            # Convert time_local to datetime
            if 'time_local' in df.columns:
                df['time'] = pd.to_datetime(df['time_local'])
            elif 'time' in df.columns:
                df['time'] = pd.to_datetime(df['time'])
            else:
                print(f"    ⚠ No time column found in {csv_file.name}, skipping...")
                continue
            
            # Set time as index
            df.set_index('time', inplace=True)
            df = df.sort_index()
            
            # Convert precipitation columns to mm
            # Prefer precip_total (already in mm), otherwise convert precip_rate (mm/h) to mm
            if 'precip_total' in df.columns:
                # Use total precipitation (already in mm per interval)
                precip_mm = df['precip_total'].values
            elif 'precip_rate' in df.columns:
                # Convert rate (mm/h) to amount (mm) based on actual time intervals
                # Calculate time differences in hours
                time_diffs = df.index.to_series().diff().dt.total_seconds() / 3600.0
                # Fill first NaN with median interval (usually 1 hour for hourly data)
                median_interval = time_diffs.median()
                time_diffs = time_diffs.fillna(median_interval)
                # Convert rate to amount: rate (mm/h) * interval (h) = amount (mm)
                precip_mm = (df['precip_rate'].values * time_diffs.values)
            else:
                print(f"    ⚠ No precipitation column found in {csv_file.name}, skipping...")
                continue
            
            # Create xarray Dataset matching NetCDF structure
            time_coords = df.index.values
            station_ds = xr.Dataset({
                'rainfall_amount': (['time'], precip_mm),
                'time': (['time'], time_coords)
            }, coords={'time': time_coords})
            
            pws_data[station_id] = station_ds
            print(f"    ✓ {station_id}: {len(station_ds.time)} records")
            
        except Exception as e:
            print(f"    ✗ Error loading {csv_file.name}: {e}")
            continue
    
    print(f"  ✓ Loaded {len(pws_data)} PWS stations from CSV")
    
    return pws_data


def load_pws_sample_data(
    pws_file: Optional[Union[str, Path]] = None
) -> Dict[str, xr.Dataset]:
    """
    Load sample PWS data from NetCDF file (2-week sample: Jan 15-30, 2024).
    
    This function looks for the sample NetCDF file in two locations:
    1. `dataset/weather stations/` (recommended - extract files here)
    2. `src/data/openmesh/extracted/dataset/weather stations/` (from Zenodo extraction)
    
    Parameters
    ----------
    pws_file : str or Path, optional
        Path to sample PWS NetCDF file. If None, searches default locations:
        - `dataset/weather stations/pws_opensense_sample_jan.nc` (sample: 2 weeks)
        - `src/data/openmesh/extracted/dataset/weather stations/pws_opensense_sample_jan.nc` (extracted)
        Falls back to full dataset if sample not found.
    
    Returns
    -------
    pws_data : dict
        Dictionary mapping station_id to xarray.Dataset for each station
    
    Notes
    -----
    **File Locations:**
    - **Recommended**: Extract files from Zenodo to `dataset/weather stations/`
    - **Alternative**: Use files directly from `src/data/openmesh/extracted/dataset/weather stations/`
      (if you extracted the Zenodo archive there)
    
    **Sample vs Full:**
    - Sample: `pws_opensense_sample_jan.nc` - 2 weeks (Jan 15-30, 2024)
    - Full: `pws_opensense_os.nc` - Complete dataset (Oct 2023 - Jul 2024)
    """
    # Set default path for sample data
    if pws_file is None:
        # Try sample file in both locations, then fall back to full file
        search_paths = [
            (WEATHER_STATIONS_DIR, "pws_opensense_sample_jan.nc"),
            (EXTRACTED_WEATHER_STATIONS_DIR, "pws_opensense_sample_jan.nc"),
            (WEATHER_STATIONS_DIR, "pws_opensense_os.nc"),
            (EXTRACTED_WEATHER_STATIONS_DIR, "pws_opensense_os.nc"),
            (WEATHER_STATIONS_DIR, "pws.nc"),
            (EXTRACTED_WEATHER_STATIONS_DIR, "pws.nc"),
        ]
        
        for base_dir, filename in search_paths:
            candidate = base_dir / filename
            if candidate.exists():
                pws_file = candidate
                is_sample = "sample_jan" in filename
                if not is_sample:
                    print(f"  ⚠ Sample file not found, using full dataset: {pws_file.name}")
                break
        
        if pws_file is None:
            tried_paths = "\n".join([f"  - {base_dir / filename}" for base_dir, filename in search_paths])
            raise FileNotFoundError(
                f"Sample PWS NetCDF file not found. Tried:\n{tried_paths}\n\n"
                f"**Solution:** Extract files from Zenodo to `dataset/weather stations/` or "
                f"use the extracted path `src/data/openmesh/extracted/dataset/weather stations/`"
            )
    else:
        pws_file = Path(pws_file)
    
    if not pws_file.exists():
        raise FileNotFoundError(f"Sample PWS file not found: {pws_file}")
    
    print(f"Loading SAMPLE PWS data from NetCDF: {pws_file}")
    
    # Use the same loading logic as full dataset
    return load_pws_from_netcdf(pws_file)


def load_noaa_asos(
    asos_dir: Optional[Union[str, Path]] = None,
    station_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    mode: str = 'load',
    stations: Optional[list] = None,
    resolution: str = '5min'
) -> Optional[pd.DataFrame]:
    """
    Load NOAA ASOS data from existing CSV files.
    Optionally fetch data from API if not found.
    
    Parameters
    ----------
    asos_dir : str or Path, optional
        Directory containing ASOS CSV files. If None, searches in common locations.
    station_id : str, optional
        Station ID (e.g., 'KNYC'). If None, loads all stations from file.
    start_date : str, optional
        Start date in 'YYYYMMDD' format for filename matching.
    end_date : str, optional
        End date in 'YYYYMMDD' format for filename matching.
    mode : str, optional
        Operation mode:
        - 'load': Only load from existing files (default)
        - 'fetch': Only fetch from API (don't load existing files)
        - 'auto': Load if exists, otherwise fetch from API
        Default: 'load'
    stations : list, optional
        Station IDs to fetch if mode='fetch' or 'auto'. 
        Default: ['KJFK', 'KLGA', 'KNYC']
    resolution : str, optional
        Data resolution for fetching ('5min' or 'hourly').
        Default: '5min'
    
    Returns
    -------
    df_asos : pandas.DataFrame or None
        ASOS data with datetime index. If multiple stations, one column per station (station_id as column name).
        If single station or no station_id column, returns single 'precip_mm' column.
    """
    # Search in common locations
    search_dirs = []
    
    if asos_dir is not None:
        search_dirs.append(Path(asos_dir))
    else:
        # Try common locations
        search_dirs.extend([
            BASE_DIR / "src" / "data" / "noaa_asos",
            BASE_DIR / "dataset" / "weather stations",
            BASE_DIR / "data" / "noaa_asos",
        ])
    
    # Find CSV files
    csv_files = []
    for search_dir in search_dirs:
        if Path(search_dir).exists():
            # Look for ASOS CSV files
            pattern = f"*{station_id}*" if station_id else "*.csv"
            csv_files.extend(list(Path(search_dir).glob(pattern)))
    
    # Helper function to fetch ASOS data from API
    def _fetch_asos_data(start_dt, end_dt, stations_list, res):
        """Internal function to fetch ASOS data from API"""
        try:
            from datetime import datetime
            import importlib.util
            import sys
            
            # Add project root to path if not already there
            project_root = BASE_DIR
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            # Try importing using the path
            try:
                from src.fetch_data.noaa_asos import asos_functions as asos
            except ImportError:
                # Fallback: use importlib to load from file path
                asos_functions_path = BASE_DIR / "src" / "fetch_data" / "noaa_asos" / "asos_functions.py"
                if not asos_functions_path.exists():
                    raise ImportError(f"ASOS functions file not found: {asos_functions_path}")
                
                spec = importlib.util.spec_from_file_location("asos_functions", asos_functions_path)
                asos = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(asos)
            
            print(f"\n🔄 Fetching ASOS data from IEM API...")
            print(f"   Period: {start_dt.date()} to {end_dt.date()}")
            print(f"   Stations: {stations_list}")
            print(f"   Resolution: {res}\n")
            
            # Fetch data
            raw_data = asos.fetch_all_stations(
                station_ids=stations_list,
                start_date=start_dt,
                end_date=end_dt,
                resolution=res,
                verbose=True
            )
            
            if len(raw_data) == 0:
                print(f"⚠ No data fetched from API")
                return False
            
            # Process data
            processed_data = asos.process_all_stations(raw_data, verbose=True)
            
            # Save to default location
            output_dir = BASE_DIR / "src" / "data" / "noaa_asos"
            asos.save_processed_data(
                processed_data, 
                output_dir, 
                start_dt, 
                end_dt, 
                res
            )
            
            print(f"✓ Data fetched and saved to: {output_dir}")
            return True
            
        except ImportError as e:
            print(f"⚠ Error importing ASOS functions: {e}")
            print(f"  → Please ensure src/fetch_data/noaa_asos/asos_functions.py exists")
            return False
        except Exception as e:
            print(f"⚠ Error during fetch: {e}")
            print(f"  → Please run: src/fetch_data/noaa_asos/asos_pipeline.ipynb manually")
            return False
    
    # Handle different modes
    if mode == 'fetch':
        # Only fetch, don't load existing files
        if not start_date or not end_date:
            print(f"⚠ Mode 'fetch' requires start_date and end_date")
            return None
        
        if stations is None:
            stations = ['KJFK', 'KLGA', 'KNYC']
        
        start_dt = pd.to_datetime(start_date, format='%Y%m%d')
        end_dt = pd.to_datetime(end_date, format='%Y%m%d')
        
        print(f"🔄 Mode 'fetch': Fetching new data (ignoring existing files)...")
        if _fetch_asos_data(start_dt, end_dt, stations, resolution):
            # After fetching, try loading
            print(f"✓ Fetch complete. Loading fetched data...")
            return load_noaa_asos(
                asos_dir=asos_dir,
                station_id=station_id,
                start_date=start_date,
                end_date=end_date,
                mode='load',  # Prevent infinite loop
                stations=stations,
                resolution=resolution
            )
        return None
    
    # For 'load' and 'auto' modes, try to find existing files first
    if mode not in ['load', 'auto']:
        print(f"⚠ Invalid mode '{mode}'. Using 'load' mode.")
        mode = 'load'
    if len(csv_files) == 0:
        if mode == 'load':
            # Load mode: just return None if no files found
            print(f"⚠ No ASOS CSV files found in search directories")
            return None
        elif mode == 'auto':
            # Auto mode: fetch if not found
            if not start_date or not end_date:
                print(f"⚠ No ASOS CSV files found and auto-fetch requires start_date and end_date")
                return None
            
            print(f"⚠ No ASOS CSV files found in search directories")
            print(f"🔄 Auto-fetching ASOS data...")
            
            if stations is None:
                stations = ['KJFK', 'KLGA', 'KNYC']
            
            start_dt = pd.to_datetime(start_date, format='%Y%m%d')
            end_dt = pd.to_datetime(end_date, format='%Y%m%d')
            
            if _fetch_asos_data(start_dt, end_dt, stations, resolution):
                # After fetching, try loading again
                return load_noaa_asos(
                    asos_dir=asos_dir,
                    station_id=station_id,
                    start_date=start_date,
                    end_date=end_date,
                    mode='load',  # Prevent infinite loop
                    stations=stations,
                    resolution=resolution
                )
            return None
    
    # Filter by date in filename if provided (helps find the right file)
    if start_date and end_date:
        try:
            req_start = pd.to_datetime(start_date, format='%Y%m%d')
            req_end = pd.to_datetime(end_date, format='%Y%m%d')
            
            # Try exact match first
            filtered = [f for f in csv_files if start_date in f.name and end_date in f.name]
            
            if not filtered:
                # If exact match not found, try to find file that contains the date range
                # Look for files where the file's date range contains the requested range
                for f in csv_files:
                    # Try to extract dates from filename (format: ALL_STATIONS_YYYYMMDD_YYYYMMDD_*.csv)
                    parts = f.stem.split('_')
                    for i, part in enumerate(parts):
                        if len(part) == 8 and part.isdigit():  # YYYYMMDD format
                            file_start = pd.to_datetime(part, format='%Y%m%d')
                            # Check if next part is also a date
                            if i + 1 < len(parts) and len(parts[i+1]) == 8 and parts[i+1].isdigit():
                                file_end = pd.to_datetime(parts[i+1], format='%Y%m%d')
                                # Check if file's date range contains requested range
                                if file_start <= req_start and file_end >= req_end:
                                    filtered.append(f)
                                    break
        except Exception as e:
            print(f"  ⚠ Warning: Error parsing dates for file selection: {e}")
            # Fall back to simple string matching
            filtered = [f for f in csv_files if start_date in f.name or end_date in f.name]
        
        if filtered:
            csv_files = filtered
            if len(csv_files) > 1:
                # Prefer files with exact date match, or files that contain the requested range
                # Sort by: exact match first, then by how well the range is contained
                def file_score(f):
                    name = f.name
                    # Exact match gets highest priority
                    if start_date in name and end_date in name:
                        return (0, name)
                    # Files containing the range get next priority
                    try:
                        parts = f.stem.split('_')
                        for i, part in enumerate(parts):
                            if len(part) == 8 and part.isdigit():
                                file_start = pd.to_datetime(part, format='%Y%m%d')
                                if i + 1 < len(parts) and len(parts[i+1]) == 8 and parts[i+1].isdigit():
                                    file_end = pd.to_datetime(parts[i+1], format='%Y%m%d')
                                    req_start = pd.to_datetime(start_date, format='%Y%m%d')
                                    req_end = pd.to_datetime(end_date, format='%Y%m%d')
                                    # Check if file contains the requested range
                                    if file_start <= req_start and file_end >= req_end:
                                        return (1, name)  # Contains range
                                    elif file_start <= req_start and file_end >= req_start:
                                        return (2, name)  # Overlaps at start
                                    elif file_start <= req_end and file_end >= req_end:
                                        return (3, name)  # Overlaps at end
                    except:
                        pass
                    return (4, name)  # No match
                csv_files.sort(key=file_score)
        else:
            print(f"  ℹ No files found with exact date match {start_date} to {end_date}")
            print(f"    Will try to filter data from available files...")
    
    # Use first matching file (or first available if no date match)
    csv_file = csv_files[0]
    if mode == 'load':
        print(f"✓ Found existing ASOS file: {csv_file.name}")
    elif mode == 'auto':
        print(f"✓ Found existing ASOS file: {csv_file.name}")
    print(f"Loading NOAA ASOS data from: {csv_file}")
    
    try:
        df_asos = pd.read_csv(csv_file)
        
        # Convert datetime column if present
        if 'datetime' in df_asos.columns:
            df_asos['time'] = pd.to_datetime(df_asos['datetime'])
            df_asos.set_index('time', inplace=True)
        elif 'time' in df_asos.columns:
            df_asos['time'] = pd.to_datetime(df_asos['time'])
            df_asos.set_index('time', inplace=True)
        else:
            print(f"  ⚠ Warning: No 'datetime' or 'time' column found in CSV")
            print(f"    Available columns: {list(df_asos.columns)}")
            return None
        
        # Store original date range for error messages
        original_date_range = (df_asos.index.min(), df_asos.index.max())
        
        # Filter data by date range if provided (after loading, before processing)
        if start_date and end_date:
            try:
                # Convert YYYYMMDD strings to datetime
                filter_start = pd.to_datetime(start_date, format='%Y%m%d')
                filter_end = pd.to_datetime(end_date, format='%Y%m%d')
                # Include the full end date (set to end of day)
                filter_end = filter_end.replace(hour=23, minute=59, second=59)
                
                # Filter data to requested date range
                original_len = len(df_asos)
                df_asos = df_asos[(df_asos.index >= filter_start) & (df_asos.index <= filter_end)].copy()
                
                if len(df_asos) == 0:
                    print(f"  ⚠ Warning: No data in date range {start_date} to {end_date}")
                    print(f"    Available data range: {original_date_range[0]} to {original_date_range[1]}")
                    return None
                elif len(df_asos) < original_len:
                    print(f"  ℹ Filtered to date range: {filter_start.date()} to {filter_end.date()}")
                    print(f"    (Reduced from {original_len:,} to {len(df_asos):,} records)")
            except Exception as e:
                print(f"  ⚠ Warning: Could not filter by date range: {e}")
                # Continue with unfiltered data
        
        # Check if DataFrame is empty after setting index
        if len(df_asos) == 0:
            print(f"  ⚠ Warning: DataFrame is empty after setting index")
            return None
        
        # Check if file contains multiple stations
        if 'station_id' in df_asos.columns and 'precip_mm' in df_asos.columns:
            # Extract all unique stations
            unique_stations = df_asos['station_id'].unique()
            print(f"  ✓ Found {len(unique_stations)} stations: {list(unique_stations)}")
            
            # Create DataFrame with one column per station using pivot
            # This is more reliable than manual joins
            try:
                df_asos_stations = df_asos.pivot_table(
                    index=df_asos.index,
                    columns='station_id',
                    values='precip_mm',
                    aggfunc='first'  # Use first value if duplicates exist
                )
                df_asos_stations.index.name = 'time'
            except Exception as e:
                print(f"  ⚠ Warning: Pivot failed, trying manual join: {e}")
                # Fallback to manual join
                all_times = df_asos.index.sort_values().unique()
                df_asos_stations = pd.DataFrame(index=all_times)
                df_asos_stations.index.name = 'time'
                
                for st_id in unique_stations:
                    st_data = df_asos[df_asos['station_id'] == st_id][['precip_mm']].copy()
                    if len(st_data) > 0:
                        st_data.columns = [st_id]
                        df_asos_stations = df_asos_stations.join(st_data, how='outer')
            
            df_asos_stations = df_asos_stations.sort_index()
            
            # Apply date filtering to pivoted DataFrame if needed
            if start_date and end_date:
                try:
                    filter_start = pd.to_datetime(start_date, format='%Y%m%d')
                    filter_end = pd.to_datetime(end_date, format='%Y%m%d')
                    filter_end = filter_end.replace(hour=23, minute=59, second=59)
                    
                    original_len = len(df_asos_stations)
                    df_asos_stations = df_asos_stations[(df_asos_stations.index >= filter_start) & (df_asos_stations.index <= filter_end)].copy()
                    
                    if len(df_asos_stations) == 0:
                        print(f"  ⚠ Warning: No data in date range after pivoting")
                        return None
                except Exception as e:
                    print(f"  ⚠ Warning: Could not filter pivoted data by date: {e}")
            
            # Check if we have any columns (stations)
            if len(df_asos_stations.columns) == 0:
                print(f"  ⚠ Warning: No station columns created")
                print(f"    Debug: unique_stations={unique_stations}, df_asos shape={df_asos.shape}")
                return None
            
            # Fill NaN with 0 for better visibility (zero precipitation)
            df_asos_stations = df_asos_stations.fillna(0)
            
            # Clip negative values to 0
            df_asos_stations = df_asos_stations.clip(lower=0)
            
            print(f"  ✓ Loaded {len(df_asos_stations):,} time points")
            if len(df_asos_stations.columns) > 0:
                print(f"    Precipitation range: {df_asos_stations.min().min():.2f} to {df_asos_stations.max().max():.2f} mm")
            return df_asos_stations
        else:
            # Single station or no station_id column - return as is
            print(f"  ✓ Loaded {len(df_asos):,} records")
            if 'precip_mm' in df_asos.columns:
                # Fill NaN with 0 for better visibility
                df_asos['precip_mm'] = df_asos['precip_mm'].fillna(0)
                # Clip negative values to 0
                df_asos['precip_mm'] = df_asos['precip_mm'].clip(lower=0)
                print(f"    Precipitation range: {df_asos['precip_mm'].min():.2f} to {df_asos['precip_mm'].max():.2f} mm")
            return df_asos
        
    except Exception as e:
        import traceback
        print(f"  ✗ Error loading ASOS data: {e}")
        print(f"  Full traceback:")
        traceback.print_exc()
        return None



"""
Smart CML Data Extraction
==========================

Functions to:
1. Filter CML links by frequency, length, and other criteria
2. Extract time series for selected links as dict of DataFrames
3. Calculate baseline and attenuation with configurable parameters

Returns: df_cml_dict with columns named as cml_id_sublink_id
"""

import pandas as pd
import xarray as xr
from typing import Dict, List, Optional, Tuple


# =============================================================================
# FUNCTION 0: Debug - Show Available CML IDs
# =============================================================================

def show_cml_ids(ds_cml: xr.Dataset, df_metadata: pd.DataFrame):
    """
    Show available CML IDs to help with matching.
    """
    print("=" * 70)
    print("CML ID MATCHING DEBUG")
    print("=" * 70)
    
    dataset_ids = ds_cml.cml_id.values
    metadata_ids = df_metadata.index.tolist()
    
    print(f"\nDataset CML IDs: {len(dataset_ids)}")
    print(f"  Type: {type(dataset_ids[0])}")
    print(f"  Examples: {dataset_ids[:10].tolist()}")
    
    print(f"\nMetadata Index: {len(metadata_ids)}")
    print(f"  Type: {type(metadata_ids[0])}")
    print(f"  Examples: {metadata_ids[:10]}")
    print("=" * 70 + "\n")


# =============================================================================
# FUNCTION 1: Filter CML Links by Criteria
# =============================================================================
def filter_cml_links(
    df_metadata: pd.DataFrame,
    freq_range=None,
    length_range=None,
    cml_ids=None,
    min_links=1,
    sublink_mode: str = 'full',  # 'full' = all sublinks, 'part' = first sublink only
) -> Tuple[List[str], pd.DataFrame]:
    """
    Filter CML links from metadata based on criteria.
    Filtering is at SUBLINK level — each sublink has its own freq/length.

    Parameters
    ----------
    df_metadata : pd.DataFrame
        CML metadata with columns: cml_id, sublink_id, frequency, length
    freq_range : (min, max), optional
        Filter by frequency (same units as metadata)
    length_range : (min, max), optional
        Filter by length (same units as metadata)
    cml_ids : list of str, optional
        Keep only these cml_ids
    min_links : int
        Warn if fewer sublink keys survive
    sublink_mode : str
        'full' = return all matching sublinks as individual keys (default)
        'part' = return only first sublink per CML

    Returns
    -------
    sublink_keys : list of str
        Keys like ['1_1', '1_2', '3_1'] — one per matching sublink
    filtered_meta : pd.DataFrame
        Filtered metadata rows (one row per matching sublink)
    """
    df = df_metadata.copy()

    freq_col = next((c for c in ['frequency', 'freq'] if c in df.columns), None)
    len_col  = next((c for c in ['length', 'Length', 'distance'] if c in df.columns), None)

    if freq_range and freq_col:
        df = df[(df[freq_col] >= freq_range[0]) & (df[freq_col] <= freq_range[1])]
    if length_range and len_col:
        df = df[(df[len_col] >= length_range[0]) & (df[len_col] <= length_range[1])]
    if cml_ids:
        df = df[df['cml_id'].astype(str).isin([str(c) for c in cml_ids])]

    # Apply sublink_mode AFTER freq/length filtering
    if sublink_mode == 'part':
        # Keep only first sublink per cml_id
        df = df.groupby('cml_id', sort=False).first().reset_index()

    # Build sublink keys from filtered rows
    sublink_keys = []
    for _, row in df.iterrows():
        cml_id = str(row['cml_id'])
        if 'sublink_id' in df.columns:
            try:
                sub_idx = int(str(row['sublink_id']).replace('sublink_', '').strip())
                sublink_keys.append(f'{cml_id}_{sub_idx}')
            except ValueError:
                pass
        else:
            sublink_keys.append(f'{cml_id}_1')

    n_orig_cmls = len(df_metadata['cml_id'].unique())
    n_orig_subs = len(df_metadata)
    n_filt_cmls = len(df['cml_id'].unique()) if len(df) else 0
    n_filt_subs = len(sublink_keys)

    print(f"CML filter: {n_orig_cmls} CMLs ({n_orig_subs} sublinks) "
          f"→ {n_filt_cmls} CMLs ({n_filt_subs} sublinks) [mode='{sublink_mode}']")
    if freq_range:   print(f"  freq:   {freq_range[0]} – {freq_range[1]}")
    if length_range: print(f"  length: {length_range[0]} – {length_range[1]} m")
    if n_filt_subs < min_links:
        print(f"  ⚠ Only {n_filt_subs} sublinks survive (min={min_links})")

    return sublink_keys, df


def extract_cml_timeseries_dict(
    ds_cml: xr.Dataset,
    selected_links=None,        # list of sublink keys ['1_1','1_2'] OR DataFrame
    window_size: str = '24H',
    quantile: float = 0.999,
    sublink_mode: str = 'full', # only used when selected_links is None
) -> Dict[str, pd.DataFrame]:
    """
    Extract RSL time series for multiple CML links as dictionary.

    Parameters
    ----------
    ds_cml : xr.Dataset
        CML dataset
    selected_links : list of str or pd.DataFrame, optional
        List of sublink keys like ['1_1', '1_2'] from filter_cml_links().
        Or a DataFrame with cml_id column (legacy).
        If None, extracts all CMLs according to sublink_mode.
    window_size : str
        Rolling window for baseline. Examples: '3H', '6H', '12H', '1D'
    quantile : float
        Quantile for baseline (0-1). Default 0.95
    sublink_mode : str
        Only used when selected_links=None:
        'full' = all sublinks, 'part' = first sublink only

    Returns
    -------
    dict : {f"{cml_id}_{sublink_idx}": DataFrame}
        Each DataFrame has columns: 'rsl', 'baseline', 'attenuation'
    """
    df_cml_dict = {}
    available_cml_ids = list(ds_cml.cml_id.values)
    all_sublinks = list(ds_cml.sublink_id.values)

    # Resolve selected_links → set of sublink keys to extract
    selected_sublink_keys = None

    if selected_links is not None and len(selected_links) > 0:
        if isinstance(selected_links, pd.DataFrame):
            # Legacy DataFrame path: filter by cml_id, use sublink_mode
            if 'cml_id' in selected_links.columns:
                selected_cml_ids = set(selected_links['cml_id'].astype(str).unique())
            else:
                selected_cml_ids = set(selected_links.index.astype(str).unique())
            available_cml_ids = [c for c in available_cml_ids
                                  if str(c) in selected_cml_ids]
            # sublink_mode applies since we don't have specific sublink keys
            selected_sublink_keys = None

        else:
            # New path: list of sublink keys like ['1_1', '3_2']
            selected_sublink_keys = set(str(k) for k in selected_links)
            # Restrict cml loop to only relevant cml_ids
            relevant_cml_ids = {k.split('_')[0] for k in selected_sublink_keys}
            available_cml_ids = [c for c in available_cml_ids
                                  if str(c) in relevant_cml_ids]

        if len(available_cml_ids) == 0:
            print("⚠ No matching CML IDs found in dataset")
            return {}

    # Sublinks to consider when no specific keys given
    if selected_sublink_keys is None:
        if sublink_mode == 'part':
            sublinks_to_extract = [all_sublinks[0]]
        else:
            sublinks_to_extract = all_sublinks
    else:
        sublinks_to_extract = all_sublinks  # will be filtered by key check below

    window_size = window_size.replace('H', 'h') if isinstance(window_size, str) else window_size

    extracted_count = 0
    for cml_id in available_cml_ids:
        for sublink_idx, sublink_id in enumerate(all_sublinks):

            # Skip if not in sublinks_to_extract (part/full mode)
            if sublink_id not in sublinks_to_extract:
                continue

            key = f"{cml_id}_{sublink_idx + 1}"

            # Skip if not in our specific sublink key list
            if selected_sublink_keys is not None and key not in selected_sublink_keys:
                continue

            try:
                rsl_data = ds_cml.rsl.sel(cml_id=cml_id, sublink_id=sublink_id)
                df = pd.DataFrame({'rsl': rsl_data.values},
                                   index=pd.to_datetime(rsl_data.time.values))
                df.index.name = 'time'
                df['baseline']    = df['rsl'].rolling(window=window_size,
                                                       min_periods=1).quantile(quantile)
                df['attenuation'] = (df['baseline'] - df['rsl']).clip(lower=0)

                df_cml_dict[key] = df
                extracted_count += 1

            except Exception as e:
                print(f"  ✗ {key}: {e}")

    print(f"✓ Extracted {extracted_count} sublinks from {len(available_cml_ids)} CMLs "
          f"(window={window_size}, q={quantile})")

    return df_cml_dict

# =============================================================================
# FUNCTION 3: Merge CML Dict into Single DataFrame
# =============================================================================

def merge_cml_dict(
    df_cml_dict: Dict[str, pd.DataFrame],
    param: str = 'attenuation',
) -> pd.DataFrame:
    """
    Merge CML dictionary into a single DataFrame.
    """
    dfs = []
    
    for key, df in df_cml_dict.items():
        if param in df.columns:
            dfs.append(df[[param]].rename(columns={param: key}))
    
    df_merged = pd.concat(dfs, axis=1)
    df_merged = df_merged.sort_index()
    
    print(f"✓ Merged {len(df_cml_dict)} CML links ({param})")
    print(f"  Shape: {df_merged.shape}")
    print(f"  Time range: {df_merged.index.min()} to {df_merged.index.max()}")
    print()
    
    return df_merged

def extract_cml_timeseries(
    ds_cml: xr.Dataset,
    link_id: str = '1',
    sublink_id: str = 'sublink_1'
) -> pd.DataFrame:
    """
    Extract RSL time series for a specific link and sublink.
    
    Parameters
    ----------
    ds_cml : xarray.Dataset
        CML dataset
    link_id : str
        Link ID (e.g., '1', '2', etc.)
    sublink_id : str
        Sublink ID (e.g., 'sublink_1', 'sublink_2', etc.)
    
    Returns
    -------
    df_cml : pandas.DataFrame
        DataFrame with 'time' index and 'rsl' column, plus calculated 'attenuation'
    """
    # Extract RSL for selected link and sublink
    rsl_data = ds_cml.rsl.sel(cml_id=link_id, sublink_id=sublink_id)
    
    # Convert to pandas
    df_cml = pd.DataFrame({
        'time': pd.to_datetime(rsl_data.time.values),
        'rsl': rsl_data.values,
        'link_id': link_id,
        'sublink_id': sublink_id
    })
    
    # Set time as index first (needed for rolling window)
    df_cml.set_index('time', inplace=True)
    
    # Calculate rolling baseline (3 hours window) using 95th percentile for each time step
    # This gives a dynamic baseline that adapts to local conditions
    window_size = '3H'  # 3-hour rolling window
    rolling_baseline = df_cml['rsl'].rolling(window=window_size, min_periods=1).quantile(0.95)
    
    # Store rolling baseline in the dataframe
    df_cml['baseline'] = rolling_baseline
    
    # Calculate attenuation (rolling baseline - RSL) for each time step
    df_cml['attenuation'] = df_cml['baseline'] - df_cml['rsl']
    df_cml['attenuation'] = df_cml['attenuation'].clip(lower=0)  # Only positive attenuation
    
    return df_cml


def extract_pws_rainfall(
    pws_data: Dict[str, xr.Dataset],
    station_id: Optional[str] = None
) -> pd.DataFrame:
    """
    Extract rainfall data from PWS dataset.
    
    Parameters
    ----------
    pws_data : dict
        Dictionary of xarray.Dataset objects (one per station)
    station_id : str, optional
        Station ID to extract. If None, uses first station.
    
    Returns
    -------
    df_pws : pandas.DataFrame
        DataFrame with 'time' index and 'precipitation_mm' column
    """
    if station_id is None:
        station_id = list(pws_data.keys())[0]
        print(f"Using station '{station_id}' (first available)")
    
    if station_id not in pws_data:
        raise ValueError(f"Station '{station_id}' not found in PWS data")
    
    station_ds = pws_data[station_id]
    
    # Get time values directly from xarray Dataset (handles irregular time steps)
    # Convert time to pandas datetime - xarray handles the conversion
    try:
        # Try to get time as pandas DatetimeIndex directly
        if hasattr(station_ds.time, 'to_pandas'):
            time_index = station_ds.time.to_pandas()
        else:
            # Convert time values to datetime
            time_values = station_ds.time.values
            # Handle different time formats (seconds since epoch, datetime64, etc.)
            if isinstance(time_values[0], (int, float, np.integer, np.floating)):
                # Assume Unix timestamp (seconds since 1970-01-01)
                time_index = pd.to_datetime(time_values, unit='s', errors='coerce')
            else:
                # Already datetime-like
                time_index = pd.to_datetime(time_values, errors='coerce')
    except Exception as e:
        print(f"Warning: Error converting time: {e}. Trying alternative method...")
        time_index = pd.to_datetime(station_ds.time.values, errors='coerce')
    
    # Extract rainfall data
    if 'rainfall_amount' in station_ds.data_vars:
        rainfall_var = station_ds['rainfall_amount']
        # Get values - handle multi-dimensional arrays
        rainfall_values = rainfall_var.values
        
        # Flatten if multi-dimensional (e.g., if there are extra dimensions)
        if rainfall_values.ndim > 1:
            # Take the first slice along non-time dimensions
            # Assuming time is the first dimension
            if 'time' in rainfall_var.dims:
                time_dim_idx = rainfall_var.dims.index('time')
                # Reshape to 1D along time dimension
                rainfall_values = rainfall_values.flatten()
                # If flattened array is longer than time, truncate
                if len(rainfall_values) > len(time_index):
                    rainfall_values = rainfall_values[:len(time_index)]
                elif len(rainfall_values) < len(time_index):
                    # Pad with NaN if shorter
                    pad_length = len(time_index) - len(rainfall_values)
                    rainfall_values = np.concatenate([rainfall_values, np.full(pad_length, np.nan)])
        else:
            # Ensure same length as time
            if len(rainfall_values) != len(time_index):
                min_len = min(len(rainfall_values), len(time_index))
                rainfall_values = rainfall_values[:min_len]
                time_index = time_index[:min_len]
        
        df_pws = pd.DataFrame({
            'precipitation_mm': rainfall_values
        }, index=time_index)
        
    elif 'rainfall_rate' in station_ds.data_vars:
        rainfall_var = station_ds['rainfall_rate']
        # Get values - handle multi-dimensional arrays
        rainfall_values = rainfall_var.values
        
        # Flatten if multi-dimensional
        if rainfall_values.ndim > 1:
            rainfall_values = rainfall_values.flatten()
            if len(rainfall_values) > len(time_index):
                rainfall_values = rainfall_values[:len(time_index)]
            elif len(rainfall_values) < len(time_index):
                pad_length = len(time_index) - len(rainfall_values)
                rainfall_values = np.concatenate([rainfall_values, np.full(pad_length, np.nan)])
        else:
            if len(rainfall_values) != len(time_index):
                min_len = min(len(rainfall_values), len(time_index))
                rainfall_values = rainfall_values[:min_len]
                time_index = time_index[:min_len]
        
        # Convert rate (mm/h) to amount (mm) - assuming irregular intervals
        # For irregular intervals, we'll use a simple conversion factor
        # This is approximate - ideally we'd use actual time differences
        df_pws = pd.DataFrame({
            'precipitation_mm': rainfall_values * (5/60)  # Approximate: 5 min intervals
        }, index=time_index)
    else:
        raise ValueError(f"No rainfall variable found in station '{station_id}'. Available variables: {list(station_ds.data_vars.keys())}")
    
    # Remove rows with invalid time (NaT)
    df_pws = df_pws[df_pws.index.notna()]
    
    # Fill NaN with 0 for better visibility (zero precipitation)
    df_pws['precipitation_mm'] = df_pws['precipitation_mm'].fillna(0)
    
    # Clip negative values to 0 (shouldn't happen, but safety check)
    df_pws['precipitation_mm'] = df_pws['precipitation_mm'].clip(lower=0)
    
    # Clip unreasonably high values (>20 mm per 5-min = 240 mm/h, which is extreme)
    # This handles potential data issues while preserving real heavy rain events
    df_pws['precipitation_mm'] = df_pws['precipitation_mm'].clip(upper=20)
    
    return df_pws


def extract_all_pws_rainfall(
    pws_data: Dict[str, xr.Dataset],
    station_ids: Optional[list] = None
) -> pd.DataFrame:
    """
    Extract rainfall data from ALL PWS stations and combine into one DataFrame.
    Each station becomes a column.
    
    Parameters
    ----------
    pws_data : dict
        Dictionary of xarray.Dataset objects (one per station)
    station_ids : list, optional
        List of station IDs to extract. If None, extracts all stations.
    
    Returns
    -------
    df_pws_all : pandas.DataFrame
        DataFrame with 'time' index and one column per station (named by station_id)
    """
    if station_ids is None:
        station_ids = list(pws_data.keys())
    
    print(f"Extracting rainfall from {len(station_ids)} PWS stations...")
    
    # Dictionary to store DataFrames for each station
    station_dfs = {}
    errors = []
    no_data = []
    
    for i, station_id in enumerate(station_ids):
        if station_id not in pws_data:
            errors.append((station_id, "not found"))
            if i < 3:
                print(f"  ⚠ Station '{station_id}' not found, skipping...")
            continue
        
        try:
            # Extract single station data
            df_station = extract_pws_rainfall(pws_data, station_id=station_id)
            if df_station is not None and len(df_station) > 0:
                # Rename column to station ID
                df_station.columns = [station_id]
                station_dfs[station_id] = df_station
                # Show first 3 examples only
                if i < 3:
                    print(f"  ✓ {station_id}: {len(df_station):,} records")
            else:
                no_data.append(station_id)
                if i < 3:
                    print(f"  ⚠ {station_id}: No data extracted")
        except Exception as e:
            errors.append((station_id, str(e)))
            if i < 3:
                print(f"  ✗ {station_id}: Error - {e}")
            continue
    
    # Summary
    if len(station_dfs) > 3:
        example_stations = list(station_dfs.keys())[:3]
        print(f"  ... and {len(station_dfs) - 3} more stations (e.g., {', '.join(example_stations)})")
    if errors:
        print(f"  ⚠ {len(errors)} stations had errors")
    if no_data:
        print(f"  ⚠ {len(no_data)} stations had no data")
    
    if len(station_dfs) == 0:
        print("✗ No PWS data extracted from any station")
        return pd.DataFrame()
    
    # Combine all stations into one DataFrame
    # Use outer join to keep all time points (stations may have different time coverage)
    df_pws_all = pd.DataFrame()
    for station_id, df_station in station_dfs.items():
        # Ensure each station's data is properly processed (zero-fill and clip already done in extract_pws_rainfall)
        if len(df_pws_all) == 0:
            df_pws_all = df_station.copy()
        else:
            df_pws_all = df_pws_all.join(df_station, how='outer')
    
    # Sort by time
    df_pws_all = df_pws_all.sort_index()
    
    # Fill NaN with 0 for better visibility (zero precipitation)
    df_pws_all = df_pws_all.fillna(0)
    
    # Clip negative values to 0 and unreasonably high values (>20 mm per 5-min)
    df_pws_all = df_pws_all.clip(lower=0, upper=20)
    
    print(f"\n✓ Combined PWS data:")
    print(f"  Stations: {len(df_pws_all.columns)}")
    print(f"  Time range: {df_pws_all.index.min()} to {df_pws_all.index.max()}")
    print(f"  Total time points: {len(df_pws_all):,}")
    if len(df_pws_all.columns) > 0:
        print(f"  Precipitation range: {df_pws_all.min().min():.2f} to {df_pws_all.max().max():.2f} mm")
    
    return df_pws_all


def detect_rain_constant_threshold(
    df_cml: pd.DataFrame,
    threshold_dB: float = 2.0,
    resample_freq: str = '5min'
) -> pd.DataFrame:
    """
    Detect rain using a constant threshold on CML attenuation.
    
    Parameters
    ----------
    df_cml : pd.DataFrame
        CML data with 'attenuation' column, indexed by time
    threshold_dB : float, optional
        Constant threshold in dB. If attenuation > threshold, rain is detected. Default: 2.0 dB
    resample_freq : str, optional
        Resampling frequency for CML data. Default: '5min'
    
    Returns
    -------
    df_result : pd.DataFrame
        DataFrame with columns:
        - 'attenuation': resampled attenuation values
        - 'rain_detected': binary detection (1 = rain, 0 = no rain)
        - 'threshold_constant': constant threshold value
    """
    if df_cml is None or len(df_cml) == 0:
        print("⚠ Error: No CML data provided")
        return pd.DataFrame()
    
    if 'attenuation' not in df_cml.columns:
        print("⚠ Error: 'attenuation' column not found in CML data")
        return pd.DataFrame()
    
    # Resample CML to specified frequency
    df_resampled = df_cml[['attenuation']].resample(resample_freq).mean()
    
    # Binary detection: 1 = rain, 0 = no rain
    df_resampled['rain_detected'] = (
        df_resampled['attenuation'] > threshold_dB
    ).astype(int)
    
    # Store threshold for plotting
    df_resampled['threshold_constant'] = threshold_dB
    
    return df_resampled






def load_csv_source(source_name, source_dir, file_pattern):
    """
    Load CSV files from directory. Returns {parameter: DataFrame with all stations}.
    
    Parameters
    ----------
    source_name : str
        Display name (e.g., 'ASOS 1-Minute')
    source_dir : Path
        Directory with CSV files
    file_pattern : str
        File pattern (e.g., 'asos_1min_*.csv')
    
    Returns
    -------
    dict : {parameter: DataFrame}
    """
    result = {}
    
    if not source_dir.exists():
        print(f"    ✗ {source_name}: dir not found")
        return result
    
    csv_files = list(source_dir.glob(file_pattern))
    if not csv_files:
        print(f"    ✗ {source_name}: no files")
        return result
    
    # Collect parameters from all stations
    param_data = {}
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, index_col='time', parse_dates=True)
            station_id = csv_file.stem.split('_', 1)[1]
            
            for col in df.columns:
                if col not in param_data:
                    param_data[col] = []
                param_data[col].append(pd.DataFrame({station_id: df[col]}))
        except Exception as e:
            pass
    
    # Combine stations for each parameter
    for param, dfs in param_data.items():
        result[param] = pd.concat(dfs, axis=1)
    
    if result:
        print(f"    ✓ {source_name}: {len(result)} parameters, {len(csv_files)} file(s)")
    
    return result


def load_all_csv_sources(output_dir):
    """
    Load all CSV sources from output directory.
    
    Returns
    -------
    dict : {source: {parameter: DataFrame}}
    """
    sources = {
        'asos_1min': ('asos_1min', 'asos_1min_*.csv'),
        'noaa_daily': ('NOAA Daily', 'noaa_daily_*.csv'),
        'mesonet': ('Mesonet', 'mesonet_*.csv'),
    }
    
    weather_data = {}
    for key, (name, pattern) in sources.items():
        weather_data[key] = load_csv_source(
            name,
            output_dir / key,
            pattern
        )
    
    return weather_data




# ============================================================================
# FILTER ALL DATASETS
# ============================================================================

def filter_by_date(data_dict, start_date=None, end_date=None):
    """
    Filter dict of DataFrames by date range.
    If start/end are None, finds automatic intersection.
    
    Parameters
    ----------
    data_dict : dict or dict[str, dict[str, pd.DataFrame]]
        Either flat dict {key: df} or nested {param: {source: df}}
    start_date, end_date : Timestamp, optional
        If None, auto-finds intersection
    
    Returns
    -------
    filtered : dict (same structure as input)
    date_range : tuple (start_date, end_date)
    """
    # Collect all time ranges from all DataFrames
    time_ranges = []
    
    def collect_ranges(obj):
        if isinstance(obj, pd.DataFrame) and len(obj) > 0:
            time_ranges.append((obj.index.min(), obj.index.max()))
        elif isinstance(obj, dict):
            for v in obj.values():
                collect_ranges(v)
    
    collect_ranges(data_dict)
    
    if not time_ranges:
        print("⚠ No data found")
        return data_dict, (None, None)
    
    # Auto intersection if dates not provided
    if start_date is None or end_date is None:
        intersection_start = max([t[0] for t in time_ranges])
        intersection_end = min([t[1] for t in time_ranges])
        
        if start_date is None:
            start_date = intersection_start
        if end_date is None:
            end_date = intersection_end
        
        print("=" * 70)
        print("AUTOMATIC INTERSECTION MODE")
        print("=" * 70)
        print(f"\nFound {len(time_ranges)} data sources")
        for t_start, t_end in time_ranges:
            print(f"  {t_start} to {t_end}")
        print(f"\n✓ Using shared period: {start_date} to {end_date}")
    else:
        print("=" * 70)
        print("MANUAL DATE SELECTION MODE")
        print("=" * 70)
        print(f"\n✓ Using custom range: {start_date} to {end_date}")
    
    # Filter function
    def apply_filter(obj):
        if isinstance(obj, pd.DataFrame):
            if len(obj) > 0:
                return obj[(obj.index >= start_date) & (obj.index <= end_date)].copy()
            return obj
        elif isinstance(obj, dict):
            return {k: apply_filter(v) for k, v in obj.items()}
        return obj
    
    # Apply filter
    filtered = apply_filter(data_dict)
    
    # Print summary
    print("\n" + "-" * 70)
    print("Filtering complete")
    print("-" * 70)
    
    def count_records(obj, indent=0):
        if isinstance(obj, pd.DataFrame):
            if len(obj) > 0:
                return len(obj)
        elif isinstance(obj, dict):
            return sum(count_records(v, indent) for v in obj.values())
        return 0
    
    print(f"✓ Total records: {count_records(filtered):,}")
    print("=" * 70 + "\n")
    
    return filtered, (start_date, end_date)
"""
Event-Based Date Filtering
===========================

Functions to:
1. Identify rainy days from NOAA daily data
2. Identify snowy days from NOAA daily data
3. Filter any data objects by identified event dates
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


# =============================================================================
# FUNCTION 1: Identify Rainy Days
# =============================================================================

def identify_rainy_days(
    noaa_daily_precip: pd.DataFrame,
    threshold_mm: float = 0.5,
) -> List[pd.Timestamp]:
    """
    Identify days with rain from NOAA daily data.
    
    Parameters
    ----------
    noaa_daily_precip : pd.DataFrame
        NOAA daily precipitation data (from all_params_filtered['precip']['noaa_daily'])
        Columns: station names, Index: datetime
    threshold_mm : float
        Minimum precipitation to count as rainy day (default: 0.5 mm)
    
    Returns
    -------
    rainy_dates : list
        List of unique dates with rain
    
    Example
    -------
    >>> rainy_days = identify_rainy_days(all_params_filtered['precip']['noaa_daily'])
    >>> print(f"Found {len(rainy_days)} rainy days")
    """
    # Any precipitation above threshold counts as rainy
    rainy_mask = (noaa_daily_precip >= threshold_mm).any(axis=1)
    rainy_dates = noaa_daily_precip[rainy_mask].index.tolist()
    
    print("=" * 70)
    print("RAINY DAYS IDENTIFICATION")
    print("=" * 70)
    print(f"Threshold: {threshold_mm} mm")
    print(f"Total days analyzed: {len(noaa_daily_precip)}")
    print(f"Rainy days found: {len(rainy_dates)}")
    
    if len(rainy_dates) > 0:
        print(f"  First rainy day: {rainy_dates[0]}")
        print(f"  Last rainy day: {rainy_dates[-1]}")
        
        # Show stats
        max_precip = noaa_daily_precip.loc[rainy_dates].max().max()
        avg_precip = noaa_daily_precip.loc[rainy_dates].mean().mean()
        print(f"  Max precipitation: {max_precip:.1f} mm")
        print(f"  Avg precipitation (rainy days): {avg_precip:.1f} mm")
    
    print("=" * 70 + "\n")
    
    return rainy_dates


# =============================================================================
# FUNCTION 2: Identify Snowy Days
# =============================================================================

def identify_snowy_days(
    noaa_daily_snow: pd.DataFrame,
    threshold_mm: float = 1.0,
) -> List[pd.Timestamp]:
    """
    Identify days with snow from NOAA daily data.
    
    Parameters
    ----------
    noaa_daily_snow : pd.DataFrame
        NOAA daily snow data (from all_params_filtered['snow']['noaa_daily'])
        Columns: station names, Index: datetime
    threshold_mm : float
        Minimum snow depth/accumulation to count as snowy day (default: 1.0 mm)
    
    Returns
    -------
    snowy_dates : list
        List of unique dates with snow
    
    Example
    -------
    >>> snowy_days = identify_snowy_days(all_params_filtered['snow']['noaa_daily'])
    >>> print(f"Found {len(snowy_days)} snowy days")
    """
    # Any snow above threshold counts as snowy
    snowy_mask = (noaa_daily_snow >= threshold_mm).any(axis=1)
    snowy_dates = noaa_daily_snow[snowy_mask].index.tolist()
    
    print("=" * 70)
    print("SNOWY DAYS IDENTIFICATION")
    print("=" * 70)
    print(f"Threshold: {threshold_mm} mm")
    print(f"Total days analyzed: {len(noaa_daily_snow)}")
    print(f"Snowy days found: {len(snowy_dates)}")
    
    if len(snowy_dates) > 0:
        print(f"  First snowy day: {snowy_dates[0]}")
        print(f"  Last snowy day: {snowy_dates[-1]}")
        
        # Show stats
        max_snow = noaa_daily_snow.loc[snowy_dates].max().max()
        avg_snow = noaa_daily_snow.loc[snowy_dates].mean().mean()
        print(f"  Max snow: {max_snow:.1f} mm")
        print(f"  Avg snow (snowy days): {avg_snow:.1f} mm")
    
    print("=" * 70 + "\n")
    
    return snowy_dates


# =============================================================================
# FUNCTION 3: Filter Data by Event Dates
# =============================================================================

def filter_by_event_dates(
    data_dict,
    event_dates: List[pd.Timestamp],
    event_name: str = "EVENT",
) -> Tuple[dict, int]:
    """
    Filter data objects by specific event dates.
    
    Works with:
    - Simple DataFrames: {key: df}
    - Nested dicts: {param: {source: df}}
    - CML dict: {cml_id_sublink: df}
    
    Parameters
    ----------
    data_dict : dict or DataFrame
        Data to filter (any structure)
    event_dates : list
        List of dates to keep (from identify_rainy_days, identify_snowy_days, etc.)
    event_name : str
        Name of event (for logging)
    
    Returns
    -------
    filtered : dict (same structure as input)
    n_records : int
        Total records kept
    
    Example
    -------
    >>> rainy_days = identify_rainy_days(all_params_filtered['precip']['noaa_daily'])
    >>> rainy_data, n_records = filter_by_event_dates(all_params_filtered, rainy_days, "RAINY")
    """
    print(f"Filtering by {event_name} days ({len(event_dates)} dates)...")
    print("-" * 70)
    
    event_dates_normalized = pd.to_datetime(event_dates).normalize()
    
    def apply_filter(obj):
        if isinstance(obj, pd.DataFrame):
            if len(obj) == 0:
                return obj
            
            # Normalize index to date (remove time)
            obj_dates = obj.index.normalize()
            mask = obj_dates.isin(event_dates_normalized)
            return obj[mask].copy()
        
        elif isinstance(obj, dict):
            filtered_dict = {}
            for k, v in obj.items():
                filtered_v = apply_filter(v)
                if isinstance(filtered_v, pd.DataFrame) and len(filtered_v) > 0:
                    filtered_dict[k] = filtered_v
                elif isinstance(filtered_v, dict) and len(filtered_v) > 0:
                    filtered_dict[k] = filtered_v
            return filtered_dict
        
        return obj
    
    filtered = apply_filter(data_dict)
    
    # Count total records
    def count_records(obj):
        if isinstance(obj, pd.DataFrame):
            return len(obj)
        elif isinstance(obj, dict):
            return sum(count_records(v) for v in obj.values())
        return 0
    
    n_records = count_records(filtered)
    
    print(f"✓ Filtered to {n_records:,} records on {event_name} days")
    print("=" * 70 + "\n")
    
    return filtered, n_records


# =============================================================================
# FUNCTION 4: Show Event Summary
# =============================================================================

def show_event_summary(
    event_dates: List[pd.Timestamp],
    event_name: str,
    data_before: int = None,
    data_after: int = None,
):
    """
    Print summary of event-based filtering.
    """
    print("=" * 70)
    print(f"{event_name.upper()} SUMMARY")
    print("=" * 70)
    print(f"\nEvent dates found: {len(event_dates)}")
    
    if len(event_dates) > 0:
        date_range = (event_dates[0], event_dates[-1])
        duration = (date_range[1] - date_range[0]).days + 1
        print(f"  Date range: {date_range[0].date()} to {date_range[1].date()}")
        print(f"  Duration: {duration} days")
        
        # Check if consecutive or scattered
        dates_sorted = sorted(event_dates)
        gaps = []
        for i in range(len(dates_sorted) - 1):
            gap = (dates_sorted[i+1] - dates_sorted[i]).days
            if gap > 1:
                gaps.append(gap)
        
        if gaps:
            print(f"  Pattern: {len(gaps)} gap(s) between events")
        else:
            print(f"  Pattern: Consecutive days")
    
    if data_before is not None and data_after is not None:
        reduction = (1 - data_after / data_before) * 100
        print(f"\nData reduction: {data_before:,} → {data_after:,} records ({reduction:.1f}% filtered)")
    
    print("=" * 70 + "\n")



def clean_snow_depth(
    snow_data: pd.DataFrame,
    stations: Optional[List[str]] = None,
    exclude_bad_stations: bool = True,
    handle_negatives: str = 'clip',
    smooth: Optional[str] = None,
    smooth_window: int = 5,
) -> pd.DataFrame:
    """
    Clean mesonet snow_depth data with flexible options.
    
    Parameters
    ----------
    snow_data : pd.DataFrame
        Raw snow_depth DataFrame (from all_params['snow_depth']['mesonet'])
    stations : list of str, optional
        Which stations to keep. If None, auto-detect good stations
    exclude_bad_stations : bool
        If True, automatically exclude noisy stations (MANH)
    handle_negatives : str
        How to handle negative values (sensor noise below ground):
        - 'clip': Set negatives to 0 (keeps signal, adds zeros)
        - 'nan': Convert negatives to NaN (removes noise, loses continuity)
        - 'ffill': Forward-fill from last positive value (assumes continuous snow)
        - 'none': Keep as-is (no action)
    smooth : str, optional
        Smoothing method for noise reduction:
        - 'mean': Simple moving average
        - 'median': Moving median (robust to outliers)
        - 'ewm': Exponential weighted moving average
        - None: No smoothing
    smooth_window : int
        Window size for smoothing (default: 5)
    
    Returns
    -------
    snow_clean : pd.DataFrame
        Cleaned snow_depth data
    
    Examples
    --------
    # Method 1: Conservative (clip negatives, no smoothing)
    df_clean = clean_snow_depth(
        snow_data,
        handle_negatives='clip',
        exclude_bad_stations=True
    )
    
    # Method 2: Aggressive (forward-fill, smooth with median)
    df_clean = clean_snow_depth(
        snow_data,
        handle_negatives='ffill',
        smooth='median',
        smooth_window=5
    )
    
    # Method 3: Remove all noise (convert negatives to NaN)
    df_clean = clean_snow_depth(
        snow_data,
        handle_negatives='nan',
        exclude_bad_stations=True
    )
    """
    
    snow_clean = snow_data.copy()
    
    print("=" * 70)
    print("SNOW DEPTH CLEANING")
    print("=" * 70)
    
    # ========================================================================
    # STEP 1: Exclude bad stations
    # ========================================================================
    
    if exclude_bad_stations:
        print("\nStep 1: Exclude bad stations")
        print("-" * 70)
        
        # MANH is known to be very noisy
        bad_stations = ['MANH']
        available = [s for s in snow_clean.columns if s not in bad_stations]
        
        snow_clean = snow_clean[available]
        print(f"  Removed: {bad_stations}")
        print(f"  Kept: {list(snow_clean.columns)}")
    
    # ========================================================================
    # STEP 2: Select stations
    # ========================================================================
    
    if stations is not None:
        print(f"\nStep 2: Select specified stations")
        print("-" * 70)
        stations_to_use = [s for s in stations if s in snow_clean.columns]
        print(f"  Using: {stations_to_use}")
        snow_clean = snow_clean[stations_to_use]
    
    # ========================================================================
    # STEP 3: Handle negative values
    # ========================================================================
    
    print(f"\nStep 3: Handle negatives ({handle_negatives})")
    print("-" * 70)
    
    if handle_negatives == 'clip':
        # Set negatives to 0
        for col in snow_clean.columns:
            neg_count = (snow_clean[col] < 0).sum()
            if neg_count > 0:
                print(f"  {col}: Clipped {neg_count} negatives to 0")
                snow_clean[col] = snow_clean[col].clip(lower=0)
    
    elif handle_negatives == 'nan':
        # Convert negatives to NaN
        for col in snow_clean.columns:
            neg_count = (snow_clean[col] < 0).sum()
            if neg_count > 0:
                print(f"  {col}: Converted {neg_count} negatives to NaN")
                snow_clean.loc[snow_clean[col] < 0, col] = np.nan
    
    elif handle_negatives == 'ffill':
        # Forward-fill from last positive
        for col in snow_clean.columns:
            neg_count = (snow_clean[col] < 0).sum()
            if neg_count > 0:
                # First convert negatives to NaN
                snow_clean.loc[snow_clean[col] < 0, col] = np.nan
                # Then forward-fill
                snow_clean[col] = snow_clean[col].fillna(method='ffill')
                print(f"  {col}: Forward-filled {neg_count} negatives from last positive value")
    
    elif handle_negatives == 'none':
        print("  No action (keeping negatives as-is)")
    
    else:
        raise ValueError(f"Unknown handle_negatives method: {handle_negatives}")
    
    # ========================================================================
    # STEP 4: Smooth (optional)
    # ========================================================================
    
    if smooth is not None:
        print(f"\nStep 4: Smooth data ({smooth}, window={smooth_window})")
        print("-" * 70)
        
        if smooth == 'mean':
            snow_clean = snow_clean.rolling(window=smooth_window, center=True).mean()
            print(f"  Applied moving average (window={smooth_window})")
        
        elif smooth == 'median':
            snow_clean = snow_clean.rolling(window=smooth_window, center=True).median()
            print(f"  Applied moving median (window={smooth_window})")
        
        elif smooth == 'ewm':
            snow_clean = snow_clean.ewm(span=smooth_window, adjust=False).mean()
            print(f"  Applied exponential weighted moving average (span={smooth_window})")
        
        else:
            raise ValueError(f"Unknown smooth method: {smooth}")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    
    print("\n" + "=" * 70)
    print("CLEANING SUMMARY")
    print("=" * 70)
    print(f"\nFinal data shape: {snow_clean.shape}")
    print(f"Stations: {list(snow_clean.columns)}")
    for col in snow_clean.columns:
        print(f"  {col}: {snow_clean[col].notna().sum()} valid records, " +
              f"{snow_clean[col].isna().sum()} NaN")
    print("\n" + "=" * 70 + "\n")
    
    return snow_clean




def summarize_filtering(
    start_date, end_date,
    rainy_days, snowy_days, dry_days,
    n_rainy=None, n_snowy=None, n_dry=None
):
    """Quick summary after filtering by events."""
    
    total_days = (end_date - start_date).days + 1
    
    print("\n" + "=" * 70)
    print(" FILTERING SUMMARY ".center(70, "="))
    print("=" * 70)
    
    print(f"\n📅 Date range: {start_date.date()} → {end_date.date()} ({total_days} days)")
    
    print(f"\n{'Event':<12} {'Days':>6} {'Pct':>8} {'Records':>12}")
    print("-" * 42)
    print(f"{'🌧️ Rainy':<12} {len(rainy_days):>6} {100*len(rainy_days)/total_days:>7.1f}% {n_rainy or '-':>12}")
    print(f"{'❄️ Snowy':<12} {len(snowy_days):>6} {100*len(snowy_days)/total_days:>7.1f}% {n_snowy or '-':>12}")
    print(f"{'☀️ Dry':<12} {len(dry_days):>6} {100*len(dry_days)/total_days:>7.1f}% {n_dry or '-':>12}")
    print("-" * 42)
    
    if snowy_days:
        print(f"\n❄️ Snow days: {[d.strftime('%m-%d') for d in sorted(snowy_days)]}")
    
    print("=" * 70 + "\n")



# --- 2. ROBUST PROCESSING FUNCTION ---
def add_pcpn_class_robust(weather_data_dict, thresholds=PHASE_THRESHOLDS):
    """
    Add precipitation type classification to weather data.
    
    Parameters
    ----------
    weather_data_dict : dict
        Structure: {source: {parameter: DataFrame}}
        e.g., {'asos_1min': {'temp': df, 'dewpoint': df}, ...}
    thresholds : dict
        Phase classification thresholds
        
    Returns
    -------
    weather_data_dict : dict (modified in-place, also returned)
    """
    
    print("--- Starting Vectorized Classification ---")
    keys = ['asos_1min', 'mesonet', 'noaa_daily']
    
    for key in keys:
        if key not in weather_data_dict: 
            continue
        
        # A. Get the parameter dictionary for this source
        param_dict = weather_data_dict[key]
        if not isinstance(param_dict, dict):
            print(f"  [!] '{key}' is not a parameter dictionary. Skipping.")
            continue
        
        # B. Find temp and dewpoint parameters
        # Try different parameter name variations
        temp_df = None
        dewpoint_df = None
        
        # Look for temp parameter
        for temp_key in ['temp', 'temperature', 'tmpc']:
            if temp_key in param_dict:
                temp_df = param_dict[temp_key]
                break
        
        # Look for dewpoint parameter
        for dewpoint_key in ['dewpoint', 'dew_point', 'dwpc', 'td']:
            if dewpoint_key in param_dict:
                dewpoint_df = param_dict[dewpoint_key]
                break
        
        if temp_df is None or dewpoint_df is None:
            print(f"  [!] Missing temp or dewpoint in '{key}'. Available parameters: {list(param_dict.keys())}")
            print("-" * 30)
            continue
        
        # Ensure both are DataFrames
        if not isinstance(temp_df, pd.DataFrame):
            temp_df = pd.DataFrame(temp_df) if hasattr(temp_df, '__len__') else None
        if not isinstance(dewpoint_df, pd.DataFrame):
            dewpoint_df = pd.DataFrame(dewpoint_df) if hasattr(dewpoint_df, '__len__') else None
            
        if temp_df is None or dewpoint_df is None:
            print(f"  [!] Could not convert temp/dewpoint to DataFrame for '{key}'")
            print("-" * 30)
            continue
        
        print(f"Processing '{key}'")
        print(f"  Temp shape: {temp_df.shape}, Dewpoint shape: {dewpoint_df.shape}")
        
        # C. Align DataFrames by time index
        # Find common time index
        common_index = temp_df.index.intersection(dewpoint_df.index)
        if len(common_index) == 0:
            print(f"  [!] No common time index between temp and dewpoint for '{key}'")
            print("-" * 30)
            continue
        
        temp_aligned = temp_df.loc[common_index]
        dewpoint_aligned = dewpoint_df.loc[common_index]
        
        # D. Process each station column
        # Get common columns (stations that have both temp and dewpoint)
        temp_cols = set(temp_aligned.columns)
        dewpoint_cols = set(dewpoint_aligned.columns)
        common_stations = temp_cols.intersection(dewpoint_cols)
        
        if len(common_stations) == 0:
            print(f"  [!] No common stations between temp and dewpoint for '{key}'")
            print(f"      Temp stations: {list(temp_cols)[:5]}...")
            print(f"      Dewpoint stations: {list(dewpoint_cols)[:5]}...")
            print("-" * 30)
            continue
        
        print(f"  Processing {len(common_stations)} stations")
        
        # E. Create result DataFrame for precipitation type
        # Store results per station
        precip_type_dict = {}
        tw_calc_dict = {}
        
        for station in common_stations:
            # Extract series for this station
            t_series = temp_aligned[station]
            d_series = dewpoint_aligned[station]
            
            # Vectorized cleaning
            t_clean = pd.to_numeric(
                t_series.astype(str).str.replace(r'[^\d\.\-]', '', regex=True), 
                errors='coerce'
            )
            d_clean = pd.to_numeric(
                d_series.astype(str).str.replace(r'[^\d\.\-]', '', regex=True), 
                errors='coerce'
            )
            
            # Calculate Tw (wet bulb temperature approximation)
            # Tw = T - (T - Td) / 3
            tw = t_clean - ((t_clean - d_clean) / 3.0)
            
            # Classify precipitation type
            conds = [
                (tw < thresholds['dry_snow_limit']),
                (tw >= thresholds['dry_snow_limit']) & (tw <= thresholds['wet_snow_limit']),
                (tw > thresholds['wet_snow_limit']) & (tw <= thresholds['mixed_limit']),
                (tw > thresholds['mixed_limit'])
            ]
            choices = ['Dry Snow', 'Wet Snow', 'Mixed Phase', 'Rain']
            
            precip_type = np.select(conds, choices, default='Unknown')
            
            # Store results
            tw_calc_dict[station] = tw
            precip_type_dict[station] = precip_type
        
        # F. Store results back in the parameter dictionary
        # Create DataFrames with same index as aligned data
        tw_df = pd.DataFrame(tw_calc_dict, index=common_index)
        precip_type_df = pd.DataFrame(precip_type_dict, index=common_index)
        
        # Store in the parameter dictionary
        param_dict['Tw'] = tw_df
        param_dict['Precip_Type'] = precip_type_df
        
        # G. Print summary
        # Aggregate all stations for summary
        all_precip_types = pd.concat([precip_type_df[col] for col in precip_type_df.columns])
        summary = all_precip_types.value_counts().head(5)
        print(f"  > Success. Breakdown:")
        for ptype, count in summary.items():
            print(f"      {ptype}: {count:,}")
        print("-" * 30)
    
    return weather_data_dict

