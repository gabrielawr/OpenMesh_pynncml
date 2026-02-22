"""
Universal setup snippet - Copy this to the top of any notebook or script.

Usage:
    # Copy the code below to your notebook/script
    import sys
    from pathlib import Path
    for parent in [Path.cwd()] + list(Path.cwd().parents):
        if (parent / "config").exists():
            sys.path.insert(0, str(parent))
            break
    from config import BASE_PATH, DATASET_DIR, load_pws_metadata
"""

