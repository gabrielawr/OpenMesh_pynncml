"""
Configuration package for OpenMesh project.

Universal setup: Just import from config!

Usage:
    from config import BASE_PATH, DATASET_DIR, load_pws_metadata
"""
import sys
from pathlib import Path

# Auto-setup: Find project root and add to path (if not already there)
_current_file = Path(__file__).resolve()
_project_root = _current_file.parent.parent  # config/__init__.py -> config/ -> project_root

# Verify it's the right project root
if not (_project_root / "config").exists():
    # Fallback: search from current working directory
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "config").exists():
            _project_root = parent
            break

# Add project root to path if not already there
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from .config import (
    BASE_PATH,
    DATASET_DIR,
    WEATHER_STATIONS_DIR,
    LINKS_DIR,
    PWS_SAMPLE_FILE,
    PWS_FULL_FILE,
    PWS_METADATA_FILE,
    LINKS_FILE,
    LINKS_METADATA_FILE,
    SRC_DIR,
    DATA_DIR,
    OUTPUT_DIR,
    ASOS_1MIN_OUTPUT_DIR,
    ASOS_1MIN_DIR,
    NOAA_DAILY_OUTPUT_DIR,
    NOAA_ASOS_RAW_DIR,
    MESONET_OUTPUT_DIR,
    MESONET_RAW_DIR,
    WU_PWS_DIR,
    SNOW_DIR,
    NOAA_DIR,
    MESONET_DIR,
    NOAA_DAILY_DIR,
    VARIABLE_MAPPING,
    UNIT_MAP,
    DEFAULT_START_DATE,
    DEFAULT_END_DATE,
    USE_SAMPLE_BY_DEFAULT,
    PLOT_DPI,
    PLOT_FIGSIZE_SINGLE,
    PLOT_FIGSIZE_MULTI,
)

from .utils import (
    setup_config,
    load_pws_metadata,
    load_asos_metadata,
    load_cml_metadata,
    load_mesonet_metadata,
    load_all_metadata,
    verify_paths,
    find_pws_file,
    find_asos_dir,
    print_config_status,
)

from .conventions import (
    STANDARD_COLUMNS,
    SOURCE_SPECIFIC_COLUMNS,
    CONVERSIONS,
    ASOS_COLUMN_MAP,
    ASOS_CONVERSIONS,
    MESONET_COLUMN_MAP,
    MESONET_CONVERSIONS,
    NOAA_DAILY_COLUMN_MAP,
    NOAA_DAILY_CONVERSIONS,
    PRECIP_TYPE_MAP,
    convert_column,
    convert_temperature,
    convert_wind_speed,
    convert_precip,
    map_precip_type,
)

__all__ = [
    # Paths
    'BASE_PATH',
    'DATASET_DIR',
    'WEATHER_STATIONS_DIR',
    'LINKS_DIR',
    'PWS_SAMPLE_FILE',
    'PWS_FULL_FILE',
    'PWS_METADATA_FILE',
    'LINKS_FILE',
    'LINKS_METADATA_FILE',
    'SRC_DIR',
    'DATA_DIR',
    'OUTPUT_DIR',
    'ASOS_1MIN_OUTPUT_DIR',
    'ASOS_1MIN_DIR',
    'NOAA_DAILY_OUTPUT_DIR',
    'NOAA_ASOS_RAW_DIR',
    'MESONET_OUTPUT_DIR',
    'MESONET_RAW_DIR',
    'WU_PWS_DIR',
    'SNOW_DIR',
    'NOAA_DIR',
    'MESONET_DIR',
    'NOAA_DAILY_DIR',
    # Settings
    'VARIABLE_MAPPING',
    'UNIT_MAP',
    'DEFAULT_START_DATE',
    'DEFAULT_END_DATE',
    'USE_SAMPLE_BY_DEFAULT',
    'PLOT_DPI',
    'PLOT_FIGSIZE_SINGLE',
    'PLOT_FIGSIZE_MULTI',
    # Functions
    'setup_config',
    'load_pws_metadata',
    'load_asos_metadata',
    'load_cml_metadata',
    'load_mesonet_metadata',
    'load_all_metadata',
    'verify_paths',
    'find_pws_file',
    'find_asos_dir',
    'print_config_status',
    # Conventions
    'STANDARD_COLUMNS',
    'SOURCE_SPECIFIC_COLUMNS',
    'CONVERSIONS',
    'ASOS_COLUMN_MAP',
    'ASOS_CONVERSIONS',
    'MESONET_COLUMN_MAP',
    'MESONET_CONVERSIONS',
    'NOAA_DAILY_COLUMN_MAP',
    'NOAA_DAILY_CONVERSIONS',
    'PRECIP_TYPE_MAP',
    'convert_column',
    'convert_temperature',
    'convert_wind_speed',
    'convert_precip',
    'map_precip_type',
]
