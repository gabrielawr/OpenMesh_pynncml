
"""
Parse ASOS stations metadata and produce standardized CSVs.
Location: src/datasets/noaa/meta/parse_stations.py

Outputs:
- data/exports/stations/noaa/asos_stations_all.csv
- data/exports/stations/noaa/asos_stations_selected.csv        (if selection provided)
- data/exports/stations/noaa/asos_stations_all_standard.csv
- data/exports/stations/noaa/asos_stations_selected_standard.csv
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Iterable, Optional, Tuple, Dict, Any

import pandas as pd

# Optional YAML dependency: only needed if you pass a .yml/.yaml selection file
try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # we'll error nicely if user tries YAML without PyYAML

# Shared schema/labels
from src.common.config import (
    # columns / schema
    STATION_COLUMNS, STATION_ID, LATITUDE, LONGITUDE, ELEVATION, DESCRIPTION,
    # units / labels
    ELEVATION_UNITS, PROVIDER_LABELS,
    # export layout
    EXPORT_STATIONS_DIR,
    # filenames (optional but recommended)
    FILE_ALL_NATIVE, FILE_ALL_STANDARD, FILE_SEL_NATIVE, FILE_SEL_STANDARD,
)


# ---------- Helpers: repo root & output dirs ----------

def find_repo_root(start: Path) -> Path:
    """
    Heuristic: climb parents until we find a directory that looks like the repo root.
    Signals: folder containing 'src', or a .git dir, or requirements.txt/pyproject.toml.
    """
    for p in [start, *start.parents]:
        if (p / "src").is_dir() or (p / ".git").is_dir() or (p / "requirements.txt").exists() or (p / "pyproject.toml").exists():
            return p
    # fallback to start's parent
    return start.parent


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def export_dir_for_provider(repo_root: Path, provider: str = "noaa") -> Path:
    """
    e.g., <repo>/data/exports/stations/noaa
    """
    return ensure_dir(repo_root.joinpath(*EXPORT_STATIONS_DIR, provider))

def save_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)
    print(f"Saved CSV: {path.resolve()}")


# ---------- Selection loading (ids / yaml) ----------

def load_selection(selection: Optional[str | Iterable[str]]) -> Dict[str, Any]:
    """
    Normalize selection into a dict with keys:
      - ids: list[str] or None
      - id_type: "IATA" | "ICAO" | None
      - state: str | None
      - name_patterns: list[str] | None
    Accepts:
      - None
      - iterable of station ids (["JFK","LGA","NYC"])
      - path to YAML file with fields (ids, id_type, state, name_patterns)
    """
    if selection is None:
        return {"ids": None, "id_type": None, "state": None, "name_patterns": None}

    if isinstance(selection, (list, tuple, set)):
        return {"ids": list(selection), "id_type": "IATA", "state": None, "name_patterns": None}

    # Otherwise treat as path
    sel_path = Path(selection)
    if sel_path.suffix.lower() in {".yml", ".yaml"}:
        if yaml is None:
            raise RuntimeError("PyYAML not installed. Run: pip install pyyaml (or conda install pyyaml)")
        with open(sel_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return {
            "ids": data.get("ids"),
            "id_type": data.get("id_type", "IATA"),
            "state": data.get("state"),
            "name_patterns": data.get("name_patterns"),
        }

    # Fallback: assume a simple text file of IDs (one per line)
    if sel_path.exists():
        ids = [line.strip() for line in sel_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return {"ids": ids, "id_type": "IATA", "state": None, "name_patterns": None}

    raise FileNotFoundError(f"Selection file not found: {sel_path}")


# ---------- Core parsing / standardization ----------

def _read_asos_fixed_width(input_file: Path) -> pd.DataFrame:
    # NOAA fixed-width columns (1-based in doc; here 0-based slices are inclusive:exclusive)
    colspecs = [
        (0, 8),      # NCDCID
        (22, 26),    # CALL (station code, often IATA-like without 'K')
        (27, 57),    # NAME
        (110, 112),  # STATE
        (144, 153),  # LAT
        (154, 164),  # LON
        (165, 171),  # ELEV (feet)
        (229, 237),  # BEGDT
    ]
    df = pd.read_fwf(
        input_file,
        colspecs=colspecs,
        skiprows=2,
        names=["NCDCID", "CALL", "NAME", "STATE", "LAT", "LON", "ELEV", "BEGDT"],
        dtype=str,
    )

    # Clean
    df["CALL"] = df["CALL"].str.strip()
    df["NAME"] = df["NAME"].str.strip()
    df["STATE"] = df["STATE"].str.strip()

    # Numeric conversions
    for col in ["LAT", "LON", "ELEV"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["ELEV_M"] = (df["ELEV"] * 0.3048).round(1)  # feet → meters

    # Keep US stations (STATE present)
    df_us = df[df["STATE"].notna()].copy()
    return df_us


def _select_rows(
    df_us: pd.DataFrame,
    ids: Optional[Iterable[str]],
    id_type: Optional[str],
    state: Optional[str],
    name_patterns: Optional[Iterable[str]],
) -> pd.DataFrame:
    sel = df_us

    if state:
        sel = sel[sel["STATE"] == state].copy()

    if ids:
        ids = list(ids)
        if id_type and id_type.upper() == "ICAO":
            # ICAO: match as-is against CALL (if CALL holds ICAO)
            sel_ids = sel[sel["CALL"].isin(ids)]
        else:
            # IATA-like: match CALL directly (e.g., "JFK") OR try to match 'K'+CALL against ICAO ids
            # Build both forms
            call = sel["CALL"].fillna("")
            # Direct match against given ids
            mask_direct = call.isin(ids)
            # If the passed ids are ICAO-like (KJFK) and CALL is IATA-like, match by stripping leading 'K'
            if any(i.startswith("K") and len(i) == 4 for i in ids):
                ids_stripped = {i[1:] if i.startswith("K") else i for i in ids}
                mask_direct = mask_direct | call.isin(ids_stripped)
            sel_ids = sel[mask_direct].copy()

        sel = sel_ids

    # Name fallback
    if name_patterns and len(sel) == 0:
        mask = pd.Series(False, index=df_us.index)
        for pat in name_patterns:
            mask |= df_us["NAME"].str.contains(pat, case=False, na=False)
        sel = df_us[mask].copy()

    return sel


def _standardize(df: pd.DataFrame, provider: str = "noaa") -> pd.DataFrame:
    """
    Map provider-native columns to the common schema.
    For NOAA ASOS:
      Station ID  <- CALL
      Latitude    <- LAT
      Longitude   <- LON
      Elevation   <- ELEV_M  (meters)
      Description <- "NOAA ASOS"
    """
    label = PROVIDER_LABELS.get(provider, provider)
    out = pd.DataFrame({
        "Station ID": df["CALL"],
        "Latitude": df["LAT"],
        "Longitude": df["LON"],
        "Elevation": df["ELEV_M"],
        "Description": label,
    })
    # enforce column order
    return out[STATION_COLUMNS]




def parse_asos_stations(
    input_file: str | Path = "asos-stations.txt",
    selection: Optional[str | Iterable[str]] = None,   # YAML path, text file, or list of IDs
    provider: str = "noaa",
    *,
    save_all_native: bool = False,
    save_all_standard: bool = False,
    save_selected_native: bool = True,
    save_selected_standard: bool = True,
    verbose: bool = True,
) -> Tuple[pd.DataFrame, Optional[pd.DataFrame], pd.DataFrame, Optional[pd.DataFrame]]:
    """
    Parse the ASOS stations text file and (optionally) write standardized CSVs.

    Returns:
        (df_all_native, df_selected_native, df_all_standard, df_selected_standard)
    """
    here = Path(__file__).resolve().parent
    repo_root = find_repo_root(here)
    out_dir = ensure_dir(repo_root.joinpath(*EXPORT_STATIONS_DIR, provider))

    input_path = Path(input_file)
    if not input_path.is_absolute():
        input_path = (here / input_path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # --- Load & clean (provider-native columns) ---
    df_us = _read_asos_fixed_width(input_path)

    # --- Standardize full table ---
    label = PROVIDER_LABELS.get(provider, provider)
    df_all_std = pd.DataFrame({
        STATION_ID: df_us["CALL"],
        LATITUDE:   df_us["LAT"],
        LONGITUDE:  df_us["LON"],
        ELEVATION:  df_us["ELEV_M"],
        DESCRIPTION: label,
    })[STATION_COLUMNS]

    # --- Selection (optional) ---
    df_sel = None
    df_sel_std = None
    if selection is not None:
        sel_cfg = load_selection(selection)
        df_sel = _select_rows(
            df_us,
            ids=sel_cfg.get("ids"),
            id_type=sel_cfg.get("id_type"),
            state=sel_cfg.get("state"),
            name_patterns=sel_cfg.get("name_patterns"),
        )
        if not df_sel.empty:
            df_sel_std = pd.DataFrame({
                STATION_ID: df_sel["CALL"],
                LATITUDE:   df_sel["LAT"],
                LONGITUDE:  df_sel["LON"],
                ELEVATION:  df_sel["ELEV_M"],
                DESCRIPTION: label,
            })[STATION_COLUMNS]
        elif verbose:
            print("Selection yielded 0 rows.")

    # --- Conditional saves ---
    if save_all_native:
        save_csv(df_us, out_dir / FILE_ALL_NATIVE)
    if save_all_standard:
        save_csv(df_all_std, out_dir / FILE_ALL_STANDARD)

    if selection is not None and df_sel is not None:
        if save_selected_native:
            save_csv(df_sel, out_dir / FILE_SEL_NATIVE)
        if df_sel_std is not None and save_selected_standard:
            save_csv(df_sel_std, out_dir / FILE_SEL_STANDARD)

    # --- Verbose summary (optional) ---
    if verbose:
        if selection is not None and df_sel is not None and df_sel_std is not None:
            print("\nSelected stations (first few):")
            for _, row in df_sel_std.head(10).iterrows():
                print(f"  {row[STATION_ID]} | {row[DESCRIPTION]} | "
                      f"Lat={row[LATITUDE]} Lon={row[LONGITUDE]} "
                      f"Elev={row[ELEVATION]} {ELEVATION_UNITS}")
        else:
            print("\nNo selection provided or no matches; wrote only 'all' outputs (as requested).")

    return df_us, df_sel, df_all_std, df_sel_std

# ---------- CLI entry (run directly) ----------

if __name__ == "__main__":
    try:
        # Default: use the local asos-stations.txt in the same folder.
        # And demonstrate NYC selection file:
        here = Path(__file__).resolve().parent
        default_input = here / "asos-stations.txt"
        nyc_yaml = here / "targets" / "nyc.yml"

        if nyc_yaml.exists():
            print(f"Using selection file: {nyc_yaml}")
            parse_asos_stations(input_file=default_input, selection=nyc_yaml)
        else:
            print("No selection file found; parsing all stations only.")
            parse_asos_stations(input_file=default_input, selection=None)

        print("\n✓ Processing complete!")
        print(f"Elevation units standardized to: {ELEVATION_UNITS}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except RuntimeError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
