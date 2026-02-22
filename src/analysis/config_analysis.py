"""
Simple config setup for analysis directory.

Usage:
    from config_analysis import BASE_PATH, OUTPUT_DIR, load_all_metadata
"""

import sys
from pathlib import Path

# Find project root
current = Path(__file__).resolve().parent  # analysis/
project_root = current.parent.parent  # -> project root

# Add to path
sys.path.insert(0, str(project_root))

# Import and re-export everything from main config
from config import *