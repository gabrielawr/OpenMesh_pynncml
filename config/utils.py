"""
Config utilities: Helper functions for loading data and verifying paths.
These functions use the configuration defined in config.py
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from .config import (
    PWS_SAMPLE_FILE, PWS_FULL_FILE, PWS_METADATA_FILE,
    LINKS_FILE, LINKS_METADATA_FILE,
    WEATHER_STATIONS_DIR, MESONET_OUTPUT_DIR,
    ASOS_1MIN_OUTPUT_DIR, DATA_DIR,
    PWS_SEARCH_FILES, ASOS_SEARCH_DIRS
)

if TYPE_CHECKING:
    import pandas as pd


# =============================================================================
# CONFIG SETUP (Simple - call this first!)
# =============================================================================

def setup_config():
    """
    Simple setup function - finds project root and prepares config imports.
    
    Works from anywhere (notebooks, scripts) by finding project root first.
    
    Call this at the start of any notebook or script:
        from config import setup_config
        setup_config()
        
    Or if config isn't importable yet, use the bootstrap:
        import sys
        from pathlib import Path
        # Find project root
        current = Path.cwd() if '__file__' not in dir() else Path(__file__).resolve()
        for parent in [current] + list(current.parents):
            if (parent / "config").exists():
                sys.path.insert(0, str(parent))
                break
        from config import setup_config
        setup_config()
        
    Then you can import from config normally:
        from config import ASOS_1MIN_DIR, OUTPUT_DIR, etc.
    """
    # Find project root - try multiple methods
    project_root = None
    
    # Method 1: If config is already importable, use __file__ from config module
    try:
        import config.config
        current = Path(config.config.__file__).resolve()
        project_root = current.parent.parent  # config/config.py -> config/ -> project_root
    except (ImportError, AttributeError):
        # Method 2: Find from current working directory (works in notebooks)
        current = Path.cwd()
        for parent in [current] + list(current.parents):
            if (parent / "config").exists() and (parent / "config" / "__init__.py").exists():
                project_root = parent
                break
            if (parent / "dataset").exists() and (parent / "src").exists():
                project_root = parent
                break
    
    if project_root is None:
        raise ValueError("Could not find project root. Make sure you're in the OpenMesh_pynncml project.")
    
    # Add project root to path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Clear config cache if already imported (forces fresh import)
    config_modules = [k for k in sys.modules.keys() if k.startswith('config')]
    for mod_name in config_modules:
        del sys.modules[mod_name]
    
    return project_root


# =============================================================================
# METADATA LOADING
# =============================================================================

def load_pws_metadata():
    """Load PWS metadata CSV file."""
    import pandas as pd
    if not PWS_METADATA_FILE.exists():
        raise FileNotFoundError(f"PWS metadata not found at: {PWS_METADATA_FILE}")
    df = pd.read_csv(PWS_METADATA_FILE)
    # Normalize column names
    if 'Latitude' in df.columns:
        df = df.rename(columns={'Latitude': 'latitude', 'Longitude': 'longitude', 'Station ID': 'station_id'})
    return df


def load_asos_metadata():
    """Load ASOS stations metadata CSV file."""
    import pandas as pd
    asos_meta_path = WEATHER_STATIONS_DIR / "ASOS_stations.csv"
    if not asos_meta_path.exists():
        raise FileNotFoundError(f"ASOS metadata not found at: {asos_meta_path}")
    df = pd.read_csv(asos_meta_path)
    # Normalize column names
    if 'Latitude' in df.columns:
        df = df.rename(columns={'Latitude': 'latitude', 'Longitude': 'longitude', 'Station ID': 'station_id'})
    return df


def load_cml_metadata():
    """Load CML links metadata CSV file."""
    import pandas as pd
    if not LINKS_METADATA_FILE.exists():
        raise FileNotFoundError(f"CML metadata not found at: {LINKS_METADATA_FILE}")
    return pd.read_csv(LINKS_METADATA_FILE)


def load_mesonet_metadata():
    """Load Mesonet stations metadata CSV file."""
    import pandas as pd
    mesonet_meta_path = MESONET_OUTPUT_DIR / "mesonet_metadata.csv"
    if not mesonet_meta_path.exists():
        raise FileNotFoundError(f"Mesonet metadata not found at: {mesonet_meta_path}")
    return pd.read_csv(mesonet_meta_path)


def load_all_metadata() -> dict:
    """
    Load all metadata files into a dictionary.
    
    Returns
    -------
    dict
        Dictionary with keys: 'pws', 'asos', 'cml', 'mesonet'
        Each value is a pandas DataFrame (or None if file not found)
    """
    metadata = {
        'pws': None,
        'asos': None,
        'cml': None,
        'mesonet': None
    }
    
    # Load PWS metadata
    try:
        metadata['pws'] = load_pws_metadata()
    except FileNotFoundError as e:
        print(f"⚠ {e}")
    
    # Load ASOS metadata
    try:
        metadata['asos'] = load_asos_metadata()
    except FileNotFoundError as e:
        print(f"⚠ {e}")
    
    # Load CML metadata
    try:
        metadata['cml'] = load_cml_metadata()
    except FileNotFoundError as e:
        print(f"⚠ {e}")
    
    # Load Mesonet metadata
    try:
        metadata['mesonet'] = load_mesonet_metadata()
    except FileNotFoundError as e:
        print(f"⚠ {e}")
    
    return metadata


# =============================================================================
# PATH VERIFICATION & FINDING
# =============================================================================

def verify_paths() -> dict:
    """Check which files/dirs exist."""
    return {
        'pws_sample': PWS_SAMPLE_FILE.exists(),
        'pws_full': PWS_FULL_FILE.exists(),
        'links': LINKS_FILE.exists(),
        'asos_output': ASOS_1MIN_OUTPUT_DIR.exists(),
        'mesonet': MESONET_OUTPUT_DIR.exists(),
    }


def find_pws_file(use_sample: bool = True) -> Path:
    """Find available PWS file."""
    for filepath in PWS_SEARCH_FILES:
        if filepath.exists():
            return filepath
    raise FileNotFoundError(f"PWS file not found. Tried: {PWS_SEARCH_FILES}")


def find_asos_dir() -> Path:
    """Find available ASOS directory."""
    for asos_dir in ASOS_SEARCH_DIRS:
        if asos_dir.exists() and list(asos_dir.glob('*.csv')):
            return asos_dir
    raise FileNotFoundError(f"ASOS directory not found. Tried: {ASOS_SEARCH_DIRS}")


# =============================================================================
# DEBUG: Print status
# =============================================================================

def print_config_status():
    """Print the current configuration status."""
    from .config import BASE_PATH
    
    print("PROJECT CONFIGURATION")
    print("=" * 70)
    print(f"\nBase path: {BASE_PATH}\n")
    
    print("REQUIRED DATA (⚠ needed for analysis):")
    print(f"  PWS Sample    {['✗', '✓'][PWS_SAMPLE_FILE.exists()]}")
    print(f"  PWS Full      {['✗', '✓'][PWS_FULL_FILE.exists()]}")
    print(f"  Links         {['✗', '✓'][LINKS_FILE.exists()]}")
    print(f"  ASOS 1min     {['✗', '✓'][ASOS_1MIN_OUTPUT_DIR.exists()]}")
    
    print("\nOPTIONAL DATA (⭐ enhances analysis):")
    print(f"  Mesonet       {['✗', '✓'][MESONET_OUTPUT_DIR.exists()]}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    print_config_status()
