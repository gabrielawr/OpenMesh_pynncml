"""
Example: How to use the new config structure
"""

# ============================================================================
# SIMPLE IMPORTS (from __init__.py)
# ============================================================================

# Import paths directly
from config import (
    BASE_PATH,
    DATASET_DIR,
    PWS_SAMPLE_FILE,
    ASOS_1MIN_OUTPUT_DIR,
    VARIABLE_MAPPING,
)

# Import utils directly
from config import (
    load_pws_metadata,
    verify_paths,
    find_pws_file,
    print_config_status,
)


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    
    # Check configuration status
    print_config_status()
    print()
    
    # Verify which paths exist
    status = verify_paths()
    print("Path Status:", status)
    print()
    
    # Find available PWS file
    try:
        pws_file = find_pws_file()
        print(f"Using PWS file: {pws_file}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    print()
    
    # Load metadata
    try:
        pws_meta = load_pws_metadata()
        print(f"PWS metadata loaded: {len(pws_meta)} stations")
        print(pws_meta.head())
    except FileNotFoundError as e:
        print(f"Error: {e}")
    print()
    
    # Access mapping
    print("Variable mapping:")
    print(VARIABLE_MAPPING['temperature'])
