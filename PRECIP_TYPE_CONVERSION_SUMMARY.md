# Precip Type Conversion Summary for snow_analysis_example.ipynb

## Data Flow

### Step 1: Raw Data (from fetch)
- **Column**: `ptype`
- **Original values**: Raw ASOS codes
  - `'NP'` - No precipitation
  - `'R'`, `'R+'`, `'R-'` - Rain (moderate, heavy, light)
  - `'S'`, `'S+'`, `'S-'` - Snow (moderate, heavy, light)
  - `'P'`, `'P?'` - Precipitation detected, type uncertain
  - `'M'`, `'?0'`, `'?1'`, `'?2'`, `'?3'` - Missing/sensor error

### Step 2: Processing (in `process_asos_1min.py`)
- **Function used**: `map_precip_type()` from `config/conventions.py`
- **Column renamed**: `ptype` → `precip_type`
- **Converted values stored in CSV**:
  - `'NP'` → `'dry'`
  - `'R'`, `'R+'`, `'R-'` → `'rain'`
  - `'S'`, `'S+'`, `'S-'` → `'snow'`
  - `'P'`, `'P?'` → `'unknown'`
  - `'M'` → `'unknown'`
  - Missing/NaN → `'unknown'`
  - Any unmapped code → `'unknown'`

**Location**: `src/process/process_asos_1min.py:110`
```python
out['precip_type'] = df['ptype'].apply(map_precip_type)
```

### Step 3: Loading in Notebook
- **Source**: `all_params['precip_type']['asos_1min']`
- **Values in DataFrame**: `'dry'`, `'rain'`, `'snow'`, `'unknown'`
- **Location**: `src/analysis/load_data.py:134`

### Step 4: Analysis/Plotting (in `snow_analysis_example.ipynb`)
- **Function used**: `categorize_precip_type()` (defined in notebook)
- **Applied to**: Already-converted values (`'dry'`, `'rain'`, `'snow'`, `'unknown'`)
- **Expected output**: `'none'`, `'rain'`, `'snow'`, `'mix'`, `'precip'`

**Function definition** (line 8368):
```python
def categorize_precip_type(ptype_str):
    """
    Categorize precipitation type from ASOS ptype code.
    Returns: 'none', 'rain', 'snow', 'mix', or 'precip'
    """
    if pd.isna(ptype_str) or ptype_str == '':
        return 'none'
    ptype_str = str(ptype_str).upper().strip()
    has_rain = 'R' in ptype_str
    has_snow = 'S' in ptype_str
    if has_rain and has_snow:
        return 'mix'
    elif has_rain:
        return 'rain'
    elif has_snow:
        return 'snow'
    elif 'P' in ptype_str:
        return 'precip'
    else:
        return 'none'
```

**Where it's used** (line 8930):
```python
categories = col_data.apply(categorize_precip_type)
```

## ⚠️ POTENTIAL ISSUE

The `categorize_precip_type()` function in the notebook expects **raw ASOS codes** (like `'R'`, `'S'`, `'RS'`), but the data has already been converted to **standardized categories** (`'dry'`, `'rain'`, `'snow'`, `'unknown'`).

**Current behavior**:
- `'rain'` → `'RAIN'` → contains `'R'` → returns `'rain'` ✓ (works by accident)
- `'snow'` → `'SNOW'` → contains `'S'` → returns `'snow'` ✓ (works by accident)
- `'dry'` → `'DRY'` → no `'R'` or `'S'` → returns `'none'` ✓ (works)
- `'unknown'` → `'UNKNOWN'` → no `'R'` or `'S'` → returns `'none'` ✓ (works)
- Mixed types (like `'RS'`) would never occur because they were already converted to `'unknown'` in Step 2

**Summary**: The function works for single types (`'rain'`, `'snow'`) but cannot detect mixed types because the data was already converted. The `'mix'` category will never be produced.

## Recommended Fix

If you want to detect mixed types, you need to either:
1. **Keep raw codes** in the processed data (don't convert in `process_asos_1min.py`)
2. **Modify `categorize_precip_type()`** to work with standardized values:
   ```python
   def categorize_precip_type(ptype_str):
       if pd.isna(ptype_str) or ptype_str == '':
           return 'none'
       ptype_str = str(ptype_str).lower().strip()
       if ptype_str == 'rain':
           return 'rain'
       elif ptype_str == 'snow':
           return 'snow'
       elif ptype_str == 'dry':
           return 'none'
       elif ptype_str == 'unknown':
           return 'precip'  # or 'none' depending on your preference
       else:
           return 'none'
   ```

