"""
Simple config setup for process directory.

Usage:
    from config_process import BASE_PATH, OUTPUT_DIR, ASOS_1MIN_DIR
"""


import sys
from pathlib import Path

# Find project root
current = Path(__file__).resolve().parent  # process/
project_root = current.parent.parent  # -> project root

# Add to path
sys.path.insert(0, str(project_root))

# Import and re-export everything from main config
from config import *

# =============================================================================
# PROCESSING DEFAULTS
# =============================================================================
DEFAULT_PROCESSING_ACTION_IF_EXISTS = 'add'  # 'add' (save with timestamp), 'replace' (overwrite), or 'skip' (don't process)