# Config Folder Structure

## Overview
The config folder is now split into focused, reusable modules:

```
config/
├── __init__.py          # Package entry point (exposes main imports)
├── config.py            # All paths and settings (read-only)
├── utils.py             # Helper functions that use config
└── README.md            # This file
```

## Why This Structure?

**Separation of Concerns:**
- `config.py` → Pure configuration (paths, defaults, mappings)
- `utils.py` → Logic that uses the configuration
- `__init__.py` → Clean public API

**Benefits:**
1. **Easier to understand** - Config is just data, utilities are functions
2. **No circular imports** - Utils import from config, not the other way
3. **Scalable** - Easy to add more utilities later without cluttering config
4. **Cleaner imports** - Everything available from the `config` package directly

## Usage

### Option 1: Import from package (recommended)
```python
from config import BASE_PATH, DATASET_DIR, load_pws_metadata

metadata = load_pws_metadata()
```

### Option 2: Import from specific modules
```python
from config.config import BASE_PATH, VARIABLE_MAPPING
from config.utils import load_all_metadata, verify_paths
```

### Option 3: Check config status
```python
from config import print_config_status
print_config_status()
```

## File Descriptions

### `config.py`
Contains all static configuration:
- **Paths**: BASE_PATH, DATASET_DIR, DATA_DIR, etc.
- **File locations**: PWS_SAMPLE_FILE, LINKS_FILE, etc.
- **Settings**: DEFAULT_START_DATE, PLOT_DPI, etc.
- **Mappings**: VARIABLE_MAPPING, UNIT_MAP
- **Helper function**: `get_base_path()` (auto-detects project root)

No logic here—just data definitions.

### `utils.py`
Helper functions that read from config and do something useful:
- **Loading metadata**: `load_pws_metadata()`, `load_asos_metadata()`, etc.
- **Path verification**: `verify_paths()`, `find_pws_file()`, `find_asos_dir()`
- **Status reporting**: `print_config_status()`

All functions import from `config.py`.

### `__init__.py`
Makes the folder a Python package and exposes the public API:
- Imports commonly-used items from config.py and utils.py
- Defines `__all__` for clear API documentation
- Users can do `from config import X` instead of `from config.config import X`

## When to Add New Code

**Add to `config.py`:**
- New path definitions
- New default values
- New mappings (VARIABLE_MAPPING, etc.)

**Add to `utils.py`:**
- Functions that load or verify data
- Helper functions that use config paths
- Functions that process or search for files

**Update `__init__.py`:**
- When you add exports to config.py or utils.py
- Keep __all__ synchronized with actual exports

## Example: Adding a New Data Source

1. Add path to `config.py`:
```python
CUSTOM_DATA_DIR = BASE_PATH / "data" / "custom"
CUSTOM_FILE = CUSTOM_DATA_DIR / "data.csv"
```

2. Add utility to `utils.py`:
```python
from .config import CUSTOM_FILE

def load_custom_data():
    if not CUSTOM_FILE.exists():
        raise FileNotFoundError(f"Custom data not found at: {CUSTOM_FILE}")
    return pd.read_csv(CUSTOM_FILE)
```

3. Export from `__init__.py`:
```python
from .config import CUSTOM_FILE, CUSTOM_DATA_DIR
from .utils import load_custom_data

__all__ = [
    ...,
    'CUSTOM_FILE',
    'CUSTOM_DATA_DIR',
    'load_custom_data',
]
```

4. Use it:
```python
from config import load_custom_data, CUSTOM_FILE
df = load_custom_data()
```

---

This structure keeps your config maintainable and scalable as your project grows!
