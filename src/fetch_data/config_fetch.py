"""
Simple config setup for fetch_data directory.

Usage:
    from config_fetch import BASE_PATH, DATA_DIR, OUTPUT_DIR
"""
import sys
from pathlib import Path

# Find project root
current = Path(__file__).resolve().parent  # fetch_data/
project_root = current.parent.parent  # -> project root

# Add to path
sys.path.insert(0, str(project_root))

# Import and re-export everything from main config
from config import *