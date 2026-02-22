"""
CML Event Day Analysis Module
==============================
Clean, single-definition version.

Key design decisions:
- resample_ptype() is a standalone function with ALL ptype logic
- resample_all() calls resample_ptype() internally
- plot functions accept aligned_data (pre-resampled) OR raw all_params
- _active_wins_resample / _reconcile_across_stations at MODULE LEVEL
- One definition per function — no duplicates

Usage:
    from day_analysis import resample_all, plot_time_window, plot_event_day_analysis
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from scipy.interpolate import interp1d
from scipy.stats import gaussian_kde
from typing import Optional, List, Dict, Union, Tuple
import xarray as xr
import matplotlib as mpl



# ============================================================================
# UTILITIES
# ============================================================================

def haversine_distance(lat1, lon1, lat2, lon2):
    """Distance between two lat/lon points in meters."""
    R = 6371000
    lat1_r, lat2_r = np.radians(lat1), np.radians(lat2)
    dlat, dlon = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(lat1_r)*np.cos(lat2_r)*np.sin(dlon/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))


def categorize_precip_type(ptype_str):
    """
    Map raw ASOS string to category.
    Returns: 'rain', 'snow', 'mix', 'precip', 'none'
    """
    if pd.isna(ptype_str) or str(ptype_str).strip() == '':
        return 'none'
    s = str(ptype_str).upper().strip()
    has_rain = 'R' in s
    has_snow = 'S' in s
    if has_rain and has_snow:
        return 'mix'
    elif has_rain:
        return 'rain'
    elif has_snow:
        return 'snow'
    elif 'P' in s:
        return 'precip'
    return 'none'


# ============================================================================
# PTYPE HELPERS — MODULE LEVEL (shared by resample + plot functions)
# ============================================================================

def _reconcile_across_stations(row):
    """
    At ONE timestamp: combine all station columns into a single category.

    Rules (applied in order, first match wins):
        rain + snow anywhere  →  mix
        any rain              →  rain
        any snow              →  snow
        any precip            →  precip
        all dry               →  dry
        else                  →  none
    """
    vals = [str(v).strip().lower() for v in row.dropna()
            if str(v).strip().lower() not in ('nan', 'none', '')]
    if not vals:
        return 'none'
    has_rain = any(v in ('rain', 'mix') for v in vals)
    has_snow = any(v in ('snow', 'mix') for v in vals)
    if has_rain and has_snow:
        return 'mix'
    if has_rain:
        return 'rain'
    if has_snow:
        return 'snow'
    if any(v == 'precip' for v in vals):
        return 'precip'
    if all(v in ('dry', 'none') for v in vals):
        return 'dry'
    return 'none'


def _active_wins_resample(series):
    """
    Resample aggregator for a categorical ptype Series.

    Within a time bin: if ANY value is rain/snow/mix/precip → use it.
    Never let dry/none beat an active type.
    rain + snow in same bin → mix.
    """
    vals = [str(v).strip().lower() for v in series.dropna()
            if str(v).strip().lower() not in ('nan', 'none', '')]
    if not vals:
        return 'none'
    has_rain = any(v in ('rain', 'mix') for v in vals)
    has_snow = any(v in ('snow', 'mix') for v in vals)
    if has_rain and has_snow:
        return 'mix'
    if has_rain:
        return 'rain'
    if has_snow:
        return 'snow'
    if any(v == 'precip' for v in vals):
        return 'precip'
    if any(v == 'dry' for v in vals):
        return 'dry'
    return 'none'


# ============================================================================
# PTYPE RESAMPLING — STANDALONE
# ============================================================================

def resample_ptype(
    ptype_data: dict,
    interval: str,
    precip_resampled: dict = None,
) -> tuple:
    """
    Resample and fully reconcile precipitation-type data.

    All logic lives here:
      Step 1  Reconcile across stations per raw timestamp
                → any rain+snow = mix, any rain = rain, etc.
      Step 2  Resample bin with active-wins
                → active type beats dry/none in the same 5-min window
      Step 3  Upgrade per-station columns to match reconciled
                → station-level lanes agree with the consensus
      Step 4  Cross-check ALL numeric precip sources
                → if precip > 0 anywhere but type is dry/none → 'precip'

    Parameters
    ----------
    ptype_data : dict
        {source_name: DataFrame}  — e.g. {'asos_1min': df}
        DataFrame columns = station names, values = category strings
        ('rain', 'snow', 'mix', 'dry', 'none', NaN, or raw ASOS strings)
    interval : str
        Resampling interval string (e.g. '5min', '15min', '1H')
    precip_resampled : dict, optional
        {source_name: DataFrame (already resampled, numeric mm)}
        Used for Step 4 upgrades.  If None, Step 4 is skipped.

    Returns
    -------
    result_ptype : dict
        {source_name: DataFrame}  — per-station resampled + upgraded
    result_reconciled : pd.Series or None
        Single reconciled Series across all stations + sources.
        None if ptype_data is empty.

    Notes
    -----
    The returned per-station DataFrames already have Step 4 applied,
    so plotting functions can use them directly without further logic.
    Raw ASOS strings (e.g. 'RA', 'SN', 'RASN') are handled via
    categorize_precip_type() before reconciliation.
    """
    result_ptype = {}
    result_reconciled = None

    if not ptype_data:
        return result_ptype, result_reconciled

    # Pre-build "any precip > 0?" mask for Step 4
    any_precip_index = None
    any_precip_mask = None
    if precip_resampled:
        # Union of all precip source indices
        for p_df in precip_resampled.values():
            if p_df is None or (hasattr(p_df, 'empty') and p_df.empty):
                continue
            idx = p_df.index
            if any_precip_index is None:
                any_precip_index = idx
                any_precip_mask = pd.Series(False, index=idx)
            else:
                any_precip_index = any_precip_index.union(idx)
                any_precip_mask = any_precip_mask.reindex(any_precip_index, fill_value=False)

        for p_source, p_df in precip_resampled.items():
            if p_df is None or (hasattr(p_df, 'empty') and p_df.empty):
                continue
            source_any = (p_df.fillna(0) > 0).any(axis=1)
            source_any = source_any.reindex(any_precip_index, fill_value=False)
            any_precip_mask = any_precip_mask | source_any

    print(f"\n  [PTYPE RESAMPLING → '{interval}']")

    for source_name, df_raw in ptype_data.items():
        if df_raw is None or (hasattr(df_raw, 'empty') and df_raw.empty):
            print(f"    ⚠ {source_name}: empty, skipping")
            continue
        if isinstance(df_raw, pd.Series):
            df_raw = df_raw.to_frame()

        # Normalise raw ASOS strings → category words
        # (handles 'RA', 'SN', 'RASN', 'dry', 'rain', NaN, 'unknown', etc.)
        def _normalise_cell(v):
            s = str(v).strip().lower()
            if s in ('nan', 'none', ''):
                return np.nan
            # Already a category word
            if s in ('rain', 'snow', 'mix', 'dry', 'precip', 'none'):
                return s
            # Raw ASOS string → categorize
            return categorize_precip_type(v)

        df_norm = df_raw.applymap(_normalise_cell)

        # ------------------------------------------------------------------
        # Step 1: reconcile across stations per raw timestamp → Series
        # ------------------------------------------------------------------
        reconciled_raw = df_norm.apply(_reconcile_across_stations, axis=1)

        # ------------------------------------------------------------------
        # Step 2: resample bin with active-wins
        # ------------------------------------------------------------------
        resampled_reconciled = reconciled_raw.resample(interval).apply(
            _active_wins_resample
        )

        # ------------------------------------------------------------------
        # Step 3: per-station resample, then upgrade to match reconciled
        # ------------------------------------------------------------------
        per_station = df_norm.resample(interval).apply(
            lambda col: _active_wins_resample(col)
        )

        for col in per_station.columns:
            upgrade_mask = (
                resampled_reconciled.isin(['rain', 'snow', 'mix', 'precip']) &
                per_station[col].isin(['dry', 'none'])
            )
            per_station.loc[upgrade_mask, col] = resampled_reconciled[upgrade_mask]

        # ------------------------------------------------------------------
        # Step 4: cross-check numeric precip sources
        # dry/none + any precip > 0 → 'precip'
        # ------------------------------------------------------------------
        if any_precip_mask is not None:
            # Align mask to this source's resampled index
            mask_aligned = any_precip_mask.reindex(
                resampled_reconciled.index, fill_value=False
            )
            is_inactive = resampled_reconciled.isin(['dry', 'none'])
            upgrade_to_precip = mask_aligned & is_inactive

            if upgrade_to_precip.any():
                n_up = upgrade_to_precip.sum()
                print(f"    ⚠ {source_name}: upgraded {n_up} bins "
                      f"dry/none → 'precip' (numeric precip > 0)")
                resampled_reconciled[upgrade_to_precip] = 'precip'
                for col in per_station.columns:
                    col_inactive = per_station[col].isin(['dry', 'none'])
                    per_station.loc[upgrade_to_precip & col_inactive, col] = 'precip'

        result_ptype[source_name] = per_station
        result_reconciled = resampled_reconciled  # last source; typically only one

        # Distribution report
        vc = per_station.apply(pd.Series.value_counts).fillna(0).astype(int)
        print(f"    ✓ {source_name}: {per_station.shape[1]} station(s), "
              f"{len(per_station)} bins")
        print(f"      Distribution:\n{vc.to_string()}")

    return result_ptype, result_reconciled


# ============================================================================
# POWER-LAW (ITU-R P.838-3)
# ============================================================================

_ITU_TABLE = np.array([
    # freq_GHz
    [1.0, 2.0, 4.0, 6.0, 7.0, 8.0, 10.0, 12.0, 15.0, 20.0, 25.0, 30.0, 35.0,
     40.0, 45.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0],
    # k_H
    [0.0000387, 0.000154, 0.00065, 0.00175, 0.00301, 0.00454, 0.0101, 0.0188,
     0.0367, 0.0751, 0.124, 0.187, 0.263, 0.350, 0.442, 0.536, 0.707, 0.851,
     0.975, 1.06, 1.12],
    # k_V
    [0.0000352, 0.000138, 0.00063, 0.00155, 0.00265, 0.00395, 0.00887, 0.0168,
     0.0335, 0.0691, 0.113, 0.167, 0.233, 0.310, 0.393, 0.479, 0.642, 0.784,
     0.906, 0.999, 1.06],
    # alpha_H
    [0.912, 0.963, 1.121, 1.308, 1.332, 1.327, 1.276, 1.217, 1.154, 1.099,
     1.061, 1.021, 0.979, 0.939, 0.903, 0.873, 0.826, 0.793, 0.769, 0.753, 0.743],
    # alpha_V
    [0.880, 0.923, 1.075, 1.265, 1.312, 1.310, 1.264, 1.200, 1.128, 1.065,
     1.030, 1.000, 0.963, 0.929, 0.897, 0.868, 0.824, 0.793, 0.769, 0.754, 0.744],
])


def _calc_a_b_from_frequency(f_GHz: float, pol: str = 'H') -> tuple:
    """Return ITU-R P.838-3 power-law coefficients (a, b) for given freq/pol."""
    f = float(f_GHz)
    row_a = 1 if pol.upper() in ('H', 'HORIZONTAL') else 2
    row_b = 3 if pol.upper() in ('H', 'HORIZONTAL') else 4
    a = float(interp1d(_ITU_TABLE[0], _ITU_TABLE[row_a], kind='cubic')(f))
    b = float(interp1d(_ITU_TABLE[0], _ITU_TABLE[row_b], kind='cubic')(f))
    return a, b


def _calc_R_from_A(A, L_km: float, a: float, b: float, R_min: float = 0.1) -> np.ndarray:
    """Rain rate (mm/h) from path-integrated attenuation: R = (A / (a·L))^(1/b)."""
    A = np.atleast_1d(np.asarray(A, dtype=float))
    R = np.zeros_like(A)
    valid = np.isfinite(A) & (A > 0)
    R[valid] = (A[valid] / (a * L_km)) ** (1.0 / b)
    R[R < R_min] = 0.0
    R[~np.isfinite(A)] = np.nan
    return R


def _get_power_law_params_for_cmls(df_cml_dict: dict, df_cml_meta: pd.DataFrame) -> dict:
    """Extract {cml_key: {a, b, L_km, f_GHz}} from metadata."""
    params = {}
    for cml_key in df_cml_dict:
        cml_id = str(cml_key.split('_')[0])
        sublink_idx = int(cml_key.split('_')[1]) if '_' in cml_key else 1
        sublink_id = f'sublink_{sublink_idx}'

        mask = df_cml_meta['cml_id'].astype(str) == cml_id
        if 'sublink_id' in df_cml_meta.columns:
            mask = mask & (df_cml_meta['sublink_id'] == sublink_id)
        rows = df_cml_meta[mask]
        if len(rows) == 0:
            # fallback: first row for this cml_id
            rows = df_cml_meta[df_cml_meta['cml_id'].astype(str) == cml_id]
        if len(rows) == 0:
            continue

        row = rows.iloc[0]
        freq = row.get('frequency', None)
        length = row.get('length', None)
        pol = str(row.get('polarization', 'H') or 'H')
        if freq is None or length is None:
            continue
        try:
            freq, length = float(freq), float(length)
        except (ValueError, TypeError):
            continue
        if np.isnan(freq) or np.isnan(length):
            continue

        f_GHz = freq / 1000.0 if freq > 200 else freq
        L_km = length / 1000.0 if length > 100 else length

        try:
            a, b = _calc_a_b_from_frequency(f_GHz, pol)
        except Exception:
            continue

        params[cml_key] = {'a': a, 'b': b, 'L_km': L_km, 'f_GHz': f_GHz}
    return params


# ============================================================================
# CML METADATA HELPERS
# ============================================================================

def get_cml_by_criteria(
    cml_metadata: pd.DataFrame,
    freq_range: tuple = (None, None),
    length_range: tuple = (None, None),
    cml_ids: list = None,
    verbose: bool = True,
) -> list:
    """Return list of cml_id strings matching frequency/length/id criteria."""
    df = cml_metadata.copy()
    fc = next((c for c in ['frequency', 'freq'] if c in df.columns), None)
    lc = next((c for c in ['length', 'distance'] if c in df.columns), None)

    if fc:
        lo, hi = freq_range
        if lo is not None: df = df[df[fc] >= lo]
        if hi is not None: df = df[df[fc] <= hi]
    if lc:
        lo, hi = length_range
        if lo is not None: df = df[df[lc] >= lo]
        if hi is not None: df = df[df[lc] <= hi]
    if cml_ids is not None:
        df = df[df['cml_id'].astype(str).isin([str(x) for x in cml_ids])]

    ids = df['cml_id'].astype(str).unique().tolist()
    if verbose:
        print(f"CML selection: {len(ids)} links found "
              f"(freq={freq_range}, len={length_range})")
    return ids


def get_cml_info(cml_metadata: pd.DataFrame, cml_id: str) -> dict:
    """Return dict with site coords, frequency, length for a CML."""
    row = cml_metadata[cml_metadata['cml_id'].astype(str) == str(cml_id)]
    if len(row) == 0:
        raise ValueError(f"CML {cml_id} not found in metadata")
    r = row.iloc[0]
    fc = next((c for c in ['frequency', 'freq'] if c in cml_metadata.columns), None)
    lc = next((c for c in ['length', 'distance'] if c in cml_metadata.columns), None)
    return {
        'cml_id': str(cml_id),
        'frequency': r[fc] if fc else None,
        'length': r[lc] if lc else None,
        'site_0': (r['site_0_lat'], r['site_0_lon']),
        'site_1': (r['site_1_lat'], r['site_1_lon']),
        'midpoint': ((r['site_0_lat'] + r['site_1_lat']) / 2,
                     (r['site_0_lon'] + r['site_1_lon']) / 2),
    }


def get_sublink_info(cml_metadata: pd.DataFrame, cml_id: str, sublink_idx: int) -> dict:
    """Return {frequency, length} for a specific sublink (1-based index)."""
    cml_id = str(cml_id)
    sublink_id = f'sublink_{sublink_idx}'
    mask = cml_metadata['cml_id'].astype(str) == cml_id
    if 'sublink_id' in cml_metadata.columns:
        mask = mask & (cml_metadata['sublink_id'] == sublink_id)
    rows = cml_metadata[mask]
    if len(rows) == 0:
        return {'frequency': None, 'length': None}
    r = rows.iloc[0]
    fc = next((c for c in ['frequency', 'freq'] if c in cml_metadata.columns), None)
    lc = next((c for c in ['length', 'distance'] if c in cml_metadata.columns), None)
    return {'frequency': r[fc] if fc else None, 'length': r[lc] if lc else None}


def find_nearby_pws(cml_info: dict, pws_metadata: pd.DataFrame,
                    max_distance_km: float = 5.0, n_nearest: int = 5) -> pd.DataFrame:
    """Find nearest PWS stations to a CML midpoint."""
    if pws_metadata is None or len(pws_metadata) == 0:
        return pd.DataFrame()
    mlat, mlon = cml_info['midpoint']
    dist = [haversine_distance(mlat, mlon, r['latitude'], r['longitude'])
            for _, r in pws_metadata.iterrows()]
    df = pws_metadata.copy()
    df['distance_m'] = dist
    df = df.sort_values('distance_m')
    return df[df['distance_m'] <= max_distance_km * 1000].head(n_nearest)[
        ['station_id', 'latitude', 'longitude', 'distance_m']
    ].copy()


def plot_time_window_2panel(
    df_cml_dict,
    start_dt,
    end_dt,
    all_params,
    df_cml_meta=None,
    cml_to_pws_map=None,
    aggregate='5min',
    signal_type='attenuation',
    show_title=False,
    statistics=False,
    figsize=(26, 12),
    label_size=18,
    title_size=20,
    tick_size=16,
    legend_size=14,
):
    """
    2-panel plot: CML + merged weather (precip+temp+ptype).
    
    Parameters
    ----------
    df_cml_dict : dict
        {cml_key: DataFrame}
    start_dt, end_dt : str or datetime
        Time window
    all_params : dict
        Weather data
    df_cml_meta : DataFrame, optional
        CML metadata
    cml_to_pws_map : dict, optional
        CML to PWS mapping
    aggregate : str
        Resample interval e.g. '5min'
    signal_type : str
        'attenuation' or 'rsl'
    show_title : bool
        Show figure title
    statistics : bool
        Return stats dict
    figsize : tuple
        Figure size
    label_size : int
        Axis label font size
    title_size : int
        Panel title font size
    tick_size : int
        Tick label font size
    legend_size : int
        Legend font size
    """
    w_start = pd.to_datetime(start_dt)
    w_end = pd.to_datetime(end_dt)
    resample_interval = aggregate
    
    precip_data = all_params.get('precip', {})
    temp_data = all_params.get('temp', {})
    ptype_data = all_params.get('precip_type', {})
    pws_stations = _get_pws_stations_for_cmls(df_cml_dict, cml_to_pws_map)
    
    fig, axes = plt.subplots(2, 1, figsize=figsize, sharex=True)
    
    # ================================================================
    # PANEL 1: CML
    # ================================================================
    ax = axes[0]
    n_links = len(df_cml_dict)
    cmap = plt.cm.tab20 if n_links > 10 else plt.cm.tab10
    colors = cmap(np.linspace(0, 1, min(n_links, 20)))
    
    n_plot = 0
    for i, (key, df) in enumerate(df_cml_dict.items()):
        if df is None or df.empty or signal_type not in df.columns:
            continue
        data = df.loc[w_start:w_end, signal_type]
        if data.empty or data.isna().all():
            continue
        if resample_interval:
            data = data.resample(resample_interval).mean()
        if data.empty:
            continue
        
        color = colors[i % len(colors)]
        label = _cml_label(key, df_cml_meta)
        ax.plot(data.index, data.values, lw=2.5, alpha=0.85, color=color, label=label)
        n_plot += 1
    
    if signal_type == 'attenuation':
        ax.axhline(0, color='k', lw=0.5, alpha=0.8)
        ax.set_ylim(bottom=0)  # attenuation starts at 0
    # For RSL, let matplotlib autoscale (no zero line, no ylim)
    
    ax.set_ylabel('Attenuation (dB)' if signal_type == 'attenuation' else 'RSL (dBm)',
                  fontweight='bold', fontsize=label_size)
                  
    ax.set_title('CML ATTENUATION', fontweight='bold', loc='left', fontsize=title_size)
    ax.grid(True, alpha=0.25, linewidth=0.5)
    
    if n_plot > 0:
        if n_plot <= 8:
            ax.legend(loc='upper right', fontsize=legend_size, ncol=2)
        elif n_plot <= 20:
            ax.legend(loc='upper right', fontsize=max(8, legend_size-2), ncol=3)
        else:
            ax.legend(bbox_to_anchor=(1.01, 1), loc='upper left',
                      borderaxespad=0, fontsize=max(8, legend_size-2), ncol=1)
    
    # ================================================================
    # PANEL 2: WEATHER MERGED
    # ================================================================
    ax = axes[1]
    
    # --- PTYPE BACKGROUND ---
    TYPE_BG = {'rain': '#4a90d9', 'snow': '#5ec4c4', 'mix': '#9e9e9e', 'precip': '#a8e6a0'}
    
    df_type = ptype_data.get('asos_1min')
    if df_type is not None:
        df_plot = df_type.loc[w_start:w_end]
        if len(df_plot) > 0:
            series = df_plot.iloc[:, 0]
            if resample_interval:
                series = series.resample(resample_interval).apply(_active_wins_resample)
            for idx in range(len(series) - 1):
                t0, t1 = series.index[idx], series.index[idx + 1]
                val = series.iloc[idx]
                if pd.isna(val) or val in ('dry', 'none'):
                    continue
                color = TYPE_BG.get(val)
                if color:
                    ax.axvspan(t0, t1, color=color, alpha=0.25, zorder=0)
    
    # --- PRECIP (left y-axis) ---
    _bw = {'1min': 0.002, '5min': 0.008, '10min': 0.012, '15min': 0.015,
           '30min': 0.025, '1H': 0.04, '1h': 0.04}.get(resample_interval or '', 0.015)
    
    # Official bars
    if 'mesonet' in precip_data:
        df = precip_data['mesonet']
        if 'BKLN' in df.columns:
            data = df['BKLN'].loc[w_start:w_end]
            if resample_interval:
                data = data.resample(resample_interval).sum()
            if len(data):
                ax.bar(data.index, data.values, width=_bw, color='green',
                       alpha=0.25, label='Mesonet', zorder=1,
                       edgecolor='darkgreen', linewidth=0.3)
    
    if 'asos_1min' in precip_data:
        data = precip_data['asos_1min'].loc[w_start:w_end].mean(axis=1)
        if resample_interval:
            data = data.resample(resample_interval).sum()
        if len(data):
            ax.bar(data.index, data.values, width=_bw, color='orange',
                   alpha=0.25, label='ASOS', zorder=1,
                   edgecolor='darkorange', linewidth=0.3)
    
    # PWS
    if 'pws' in precip_data:
        df = precip_data['pws'].loc[w_start:w_end]
        if pws_stations:
            avail = [s for s in pws_stations if s in df.columns]
            if avail:
                df = df[avail]
        if resample_interval and len(df):
            df = df.resample(resample_interval).sum()
        if len(df):
            mean_p = df.mean(axis=1)
            median_p = df.median(axis=1)
            ax.plot(mean_p.index, mean_p, color='purple', lw=3, alpha=0.95,
                    label=f'PWS Mean (n={len(df.columns)})', zorder=5)
            ax.plot(median_p.index, median_p, color='magenta', lw=2, alpha=0.8,
                    ls='--', label='PWS Median', zorder=4)
    
    ax.set_ylabel('Precip (mm)', fontweight='bold', fontsize=label_size, color='purple')
    ax.tick_params(axis='y', labelcolor='purple', labelsize=tick_size)
    _set_robust_ylim(ax, quantile=0.98)
    
    # --- TEMP (right y-axis) ---
    ax2 = ax.twinx()
    
    for src in ('asos_1min', 'mesonet'):
        if temp_data and src in temp_data:
            df_t = temp_data[src].loc[w_start:w_end]
            if resample_interval and len(df_t):
                df_t = df_t.resample(resample_interval).mean()
            if len(df_t):
                mean_t = df_t.mean(axis=1)
                min_t = df_t.min(axis=1)
                max_t = df_t.max(axis=1)
                
                ax2.plot(mean_t.index, mean_t, color='red', lw=2.5, alpha=0.9,
                         label='Temp Mean', zorder=6)
                ax2.fill_between(mean_t.index, min_t, max_t, color='red',
                                 alpha=0.15, zorder=2, label='Temp Range')
                break
    
    ax2.axhline(0, color='blue', ls='--', lw=1.5, alpha=0.7, zorder=2)
    ax2.set_ylabel('Temperature (°C)', fontweight='bold', fontsize=label_size, color='red')
    ax2.tick_params(axis='y', labelcolor='red', labelsize=tick_size)
    
    # Legend
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ptype_h = [Patch(facecolor='#5ec4c4', alpha=0.5, label='Snow'),
               Patch(facecolor='#4a90d9', alpha=0.5, label='Rain'),
               Patch(facecolor='#9e9e9e', alpha=0.5, label='Mix')]
    
    ax.legend(h1 + h2 + ptype_h, l1 + l2 + ['Snow', 'Rain', 'Mix'],
              loc='upper right', fontsize=legend_size, ncol=3)
    
    ax.set_title('Weather (Precip + Temp + Type)', fontweight='bold',
                 loc='left', fontsize=title_size)
    ax.grid(True, alpha=0.25, linewidth=0.5)
    
    # ================================================================
    # X-AXIS FORMATTING
    # ================================================================
    span_h = (w_end - w_start).total_seconds() / 3600
    if span_h <= 24:
        loc, fmt = mdates.HourLocator(interval=3), mdates.DateFormatter('%m-%d %H:%M')
    elif span_h <= 72:
        loc, fmt = mdates.HourLocator(interval=6), mdates.DateFormatter('%m-%d %H:%M')
    else:
        loc, fmt = mdates.DayLocator(interval=1), mdates.DateFormatter('%m-%d')
    
    for ax_i in axes:
        ax_i.xaxis.set_major_locator(loc)
        ax_i.xaxis.set_major_formatter(fmt)
        ax_i.tick_params(axis='both', labelsize=tick_size)
        plt.setp(ax_i.xaxis.get_majorticklabels(), visible=True, rotation=45, ha='right')
    
    axes[-1].set_xlabel('Time', fontweight='bold', fontsize=label_size)
    
    # ================================================================
    # TITLE & LAYOUT
    # ================================================================
    if show_title:
        fig.suptitle(f'CML Analysis [{aggregate}]  {start_dt} → {end_dt}',
                     fontsize=title_size + 2, fontweight='bold')
    
    rect = [0, 0, 0.82 if n_links > 20 else 1.0, 0.97 if show_title else 1.0]
    plt.tight_layout(rect=rect)
    plt.show()
    
    if statistics:
        stats = {
            'window_start': w_start,
            'window_end': w_end,
            'n_links': n_links,
        }
        return stats


def _get_pws_stations_for_cmls(df_cml_dict: dict, cml_to_pws_map: dict) -> list:
    """Return list of PWS station_ids matched to the CMLs in df_cml_dict."""
    if cml_to_pws_map is None:
        return None
    cml_ids = {str(k.split('_')[0]) for k in df_cml_dict}
    stations = set()
    for cid in cml_ids:
        matches = cml_to_pws_map.get(cid) or cml_to_pws_map.get(int(cid) if cid.isdigit() else None)
        if matches is None:
            continue
        if isinstance(matches, pd.DataFrame) and 'station_id' in matches.columns:
            stations.update(matches['station_id'].tolist())
    if stations:
        print(f"  ✓ PWS filter: {len(stations)} stations for {len(cml_ids)} CMLs")
        return list(stations)
    return None


def list_event_days(rainy_days=None, snowy_days=None, show_all=False, max_display=20):
    """Print a summary of event days."""
    print("=" * 60)
    print("AVAILABLE EVENT DAYS")
    print("=" * 60)
    for days, name in [(rainy_days, "RAINY"), (snowy_days, "SNOWY")]:
        if days:
            print(f"\n{name}: {len(days)} days")
            if show_all:
                for i, d in enumerate(days[:max_display]):
                    print(f"  [{i}] {pd.Timestamp(d).strftime('%Y-%m-%d (%A)')}")
                if len(days) > max_display:
                    print(f"  ... and {len(days) - max_display} more")
            else:
                print(f"  First: {pd.Timestamp(days[0]).strftime('%Y-%m-%d')}, "
                      f"Last: {pd.Timestamp(days[-1]).strftime('%Y-%m-%d')}")
    print("=" * 60)


# ============================================================================
# UNIFIED RESAMPLING
# ============================================================================

def resample_all(
    all_params: dict,
    df_cml_dict: dict,
    df_cml_meta: pd.DataFrame = None,
    interval: str = '5min',
    signal_type: str = 'attenuation',
    cml_to_pws_map: dict = None,
    R_min: float = 0.01,
) -> dict:
    """
    Resample ALL data sources to a common time grid.

    Returns aligned_data dict containing weather + CML on the same index,
    NaN for missing observations, pre-computed rain rates, and fully
    reconciled precipitation type.

    Parameters
    ----------
    all_params : dict
        {'precip': {...}, 'temp': {...}, 'precip_type': {...}, ...}
    df_cml_dict : dict
        {cml_key: DataFrame with signal columns}
    df_cml_meta : DataFrame, optional
        CML metadata for power-law R computation
    interval : str
        Common resampling interval (e.g. '5min', '15min', '1H')
    signal_type : str
        CML signal column ('attenuation' or 'rsl')
    cml_to_pws_map : dict, optional
        Maps CML IDs → nearby PWS station DataFrames
    R_min : float
        Minimum rain rate threshold for power-law (mm/h)

    Returns
    -------
    aligned_data : dict
        interval, interval_hours,
        precip             {source: DataFrame mm/bin},
        precip_rate        {source: DataFrame mm/h},
        precip_rate_mean   {source: Series mm/h},
        temp               {source: DataFrame °C},
        precip_type        {source: DataFrame categories},
        precip_type_reconciled  Series (single reconciled category),
        cml_attenuation    DataFrame dB,
        cml_R              DataFrame mm/h (power-law),
        cml_R_mean         Series mm/h,
        pl_params          {cml_key: {a,b,L_km,f_GHz}},
        n_obs              {source: DataFrame counts}
    """
    interval_td = pd.Timedelta(interval)
    interval_hours = interval_td.total_seconds() / 3600.0

    precip_data = all_params.get('precip', {})
    temp_data   = all_params.get('temp', {})
    ptype_data  = all_params.get('precip_type', {})

    pws_filter = _get_pws_stations_for_cmls(df_cml_dict, cml_to_pws_map)

    result_precip = {}
    result_rate   = {}
    result_rate_mean = {}
    result_temp   = {}
    result_nobs   = {}

    print("=" * 70)
    print(f"RESAMPLING ALL DATA → '{interval}'")
    print("=" * 70)

    # ------------------------------------------------------------------
    # PRECIPITATION
    # ------------------------------------------------------------------
    for src, df_raw in precip_data.items():
        if df_raw is None or (hasattr(df_raw, 'empty') and df_raw.empty):
            continue
        if isinstance(df_raw, pd.Series):
            df_raw = df_raw.to_frame()

        if src == 'pws' and pws_filter is not None:
            avail = [s for s in pws_filter if s in df_raw.columns]
            if avail:
                df_raw = df_raw[avail]

        n_obs     = df_raw.resample(interval).count()
        resampled = df_raw.resample(interval).sum()
        resampled[n_obs == 0] = np.nan

        rate      = resampled / interval_hours
        rate_mean = rate.mean(axis=1)

        result_precip[src]       = resampled
        result_rate[src]         = rate
        result_rate_mean[src]    = rate_mean
        result_nobs[src]         = n_obs

        print(f"  ✓ precip/{src}: {resampled.shape[1]} station(s), "
              f"{len(resampled)} bins, "
              f"{(resampled > 0).sum().sum()} non-zero, "
              f"{resampled.isna().sum().sum()} NaN")

    # ------------------------------------------------------------------
    # TEMPERATURE
    # ------------------------------------------------------------------
    for src, df_raw in temp_data.items():
        if df_raw is None or (hasattr(df_raw, 'empty') and df_raw.empty):
            continue
        if isinstance(df_raw, pd.Series):
            df_raw = df_raw.to_frame()
        resampled = df_raw.resample(interval).mean()
        result_temp[src] = resampled
        print(f"  ✓ temp/{src}: {resampled.shape[1]} station(s), {len(resampled)} bins")

    # ------------------------------------------------------------------
    # PRECIP TYPE — delegated entirely to resample_ptype()
    # ------------------------------------------------------------------
    result_ptype, result_reconciled = resample_ptype(
        ptype_data=ptype_data,
        interval=interval,
        precip_resampled=result_precip,   # used for Step 4 upgrades
    )

    # ------------------------------------------------------------------
    # CML ATTENUATION
    # ------------------------------------------------------------------
    cml_series = {}
    cml_nobs_dict = {}
    for cml_key, df in df_cml_dict.items():
        if df is None or df.empty or signal_type not in df.columns:
            continue
        data = df[signal_type]
        if data.isna().all():
            continue
        cml_series[cml_key]    = data.resample(interval).mean()
        cml_nobs_dict[cml_key] = data.resample(interval).count()

    df_cml_atten = pd.DataFrame(cml_series) if cml_series else pd.DataFrame()
    cml_nobs     = pd.DataFrame(cml_nobs_dict)
    if len(df_cml_atten.columns) > 0 and len(cml_nobs.columns) > 0:
        df_cml_atten[cml_nobs == 0] = np.nan
    result_nobs['cml'] = cml_nobs

    n_cml = df_cml_atten.shape[1]
    print(f"  ✓ cml/{signal_type}: {n_cml} links, {len(df_cml_atten)} bins")

    # ------------------------------------------------------------------
    # CML POWER-LAW R
    # ------------------------------------------------------------------
    pl_params  = {}
    df_cml_R   = pd.DataFrame(index=df_cml_atten.index)

    if df_cml_meta is not None and n_cml > 0:
        pl_params = _get_power_law_params_for_cmls(df_cml_dict, df_cml_meta)
        for cml_key, p in pl_params.items():
            if cml_key not in df_cml_atten.columns:
                continue
            R = _calc_R_from_A(df_cml_atten[cml_key].values,
                                p['L_km'], p['a'], p['b'], R_min)
            df_cml_R[cml_key] = R
        if pl_params:
            ex = list(pl_params.values())[0]
            print(f"  ✓ cml_R: {len(pl_params)} links "
                  f"(e.g. {ex['f_GHz']:.1f} GHz, a={ex['a']:.4f}, b={ex['b']:.3f})")

    cml_R_mean = df_cml_R.mean(axis=1) if len(df_cml_R.columns) > 0 else pd.Series(dtype=float)

    # ------------------------------------------------------------------
    # BUILD RESULT
    # ------------------------------------------------------------------
    aligned_data = {
        'interval':       interval,
        'interval_hours': interval_hours,
        # Precip
        'precip':              result_precip,
        'precip_rate':         result_rate,
        'precip_rate_mean':    result_rate_mean,
        # Temp
        'temp':                result_temp,
        # Ptype
        'precip_type':              result_ptype,
        'precip_type_reconciled':   result_reconciled,
        # CML
        'cml_attenuation': df_cml_atten,
        'cml_R':           df_cml_R,
        'cml_R_mean':      cml_R_mean,
        'pl_params':       pl_params,
        'n_obs':           result_nobs,
    }

    print(f"\n{'='*70}")
    print(f"✓ aligned_data ready — interval='{interval}', "
          f"{len(result_precip)} precip sources, "
          f"{len(result_temp)} temp sources, "
          f"{n_cml} CML links")
    if result_reconciled is not None:
        print(f"  ptype reconciled: {result_reconciled.value_counts().to_dict()}")
    print(f"{'='*70}\n")

    return aligned_data


# ============================================================================
# PLOT HELPERS
# ============================================================================

def _cml_label(cml_key: str, df_cml_meta: pd.DataFrame) -> str:
    """Build legend label for a CML key using sublink-specific metadata."""
    parts   = cml_key.split('_')
    cml_id  = parts[0]
    sub_idx = int(parts[1]) if len(parts) > 1 else 1
    sub_id  = f'sublink_{sub_idx}'

    if df_cml_meta is None:
        return cml_key

    mask = df_cml_meta['cml_id'].astype(str) == cml_id
    if 'sublink_id' in df_cml_meta.columns:
        mask = mask & (df_cml_meta['sublink_id'] == sub_id)
    rows = df_cml_meta[mask]
    if len(rows) == 0:
        rows = df_cml_meta[df_cml_meta['cml_id'].astype(str) == cml_id]
    if len(rows) == 0:
        return cml_key

    r    = rows.iloc[0]
    freq = r.get('frequency', None)
    leng = r.get('length', None)
    sl   = f'SL{sub_idx}'

    if freq is None or leng is None:
        return f'CML{cml_id}-{sl}'

    try:
        freq, leng = float(freq), float(leng)
    except (TypeError, ValueError):
        return f'CML{cml_id}-{sl}'

    f_str = f'{freq/1000:.1f}GHz' if freq >= 1000 else f'{freq:.0f}MHz'
    l_str = f'{leng/1000:.1f}km'  if leng >= 1000 else f'{leng:.0f}m'
    return f'CML{cml_id}-{sl} | {f_str} {l_str}'


def _set_robust_ylim(ax, quantile: float = 0.98, padding: float = 1.3,
                     min_ymax: float = 0.2):
    """Clip y-axis at a quantile of plotted data to suppress outlier spikes."""
    vals = []
    for line in ax.get_lines():
        yd = np.asarray(line.get_ydata(), dtype=float)
        vals.extend(yd[np.isfinite(yd) & (yd > 0)])
    for container in ax.containers:
        for bar in container:
            h = bar.get_height()
            if np.isfinite(h) and h > 0:
                vals.append(h)
    if vals:
        ax.set_ylim(0, max(np.quantile(vals, quantile) * padding, min_ymax))
    else:
        ax.set_ylim(0, min_ymax)


def _plot_cml_signal(ax, df_cml_dict, w_start, w_end, event_day=None,
                     signal_type='attenuation', event_color='red',
                     df_cml_meta=None, emphasize_cml_ids=None,
                     resample_interval=None, linewidth=2.5, linewidth_emphasized=4.0):
    """Plot CML attenuation or RSL time series."""
    n_links = len(df_cml_dict)
    # cycle through tab20 for more than 10 links
    cmap   = plt.cm.tab20 if n_links > 10 else plt.cm.tab10
    colors = cmap(np.linspace(0, 1, min(n_links, 20)))
    emph   = {str(c) for c in (emphasize_cml_ids or [])}
    n_plot = 0

    for i, (key, df) in enumerate(df_cml_dict.items()):
        if df is None or df.empty or signal_type not in df.columns:
            continue
        data = df.loc[w_start:w_end, signal_type]
        if data.empty or data.isna().all():
            continue
        if resample_interval:
            data = data.resample(resample_interval).mean()
        if data.empty:
            continue

        is_emph = str(key.split('_')[0]) in emph
        color   = 'cyan' if is_emph else colors[i % len(colors)]
        lw      = linewidth_emphasized if is_emph else linewidth
        label   = _cml_label(key, df_cml_meta)   # always build label

        ax.plot(data.index, data.values, lw=lw, alpha=0.9 if is_emph else 0.85,
                color=color, label=label)
        n_plot += 1

    if event_day is not None:
        ax.axvspan(event_day, event_day + pd.Timedelta(days=1),
                   alpha=0.06, color=event_color)
    ax.axhline(0, color='k', lw=0.5, alpha=0.8)
    ax.set_ylabel('Attenuation (dB)' if signal_type == 'attenuation' else 'RSL (dBm)',
                  fontweight='bold', fontsize=15)
    ax.set_title('CML ATTENUATION', fontweight='bold', loc='left', fontsize=16)
    ax.grid(True, alpha=0.25, linewidth=0.5)

    if n_plot > 0:
        # scale legend: outside axes for many links
        if n_plot <= 8:
            ax.legend(loc='upper right', fontsize=10, ncol=2)
        elif n_plot <= 20:
            ax.legend(loc='upper right', fontsize=8, ncol=3)
        else:
            ax.legend(bbox_to_anchor=(1.01, 1), loc='upper left',
                      borderaxespad=0, fontsize=8, ncol=1)


def _plot_temperature(ax, temp_data, w_start, w_end, event_day=None,
                      event_color='red', resample_interval=None):
    """Plot temperature time series."""
    plotted = False
    for src in ('asos_1min', 'mesonet'):
        if src in temp_data and not plotted:
            df = temp_data[src].loc[w_start:w_end]
            if resample_interval:
                df = df.resample(resample_interval).mean()
            if len(df) > 0:
                for col in df.columns[:4]:
                    ax.plot(df.index, df[col], lw=1.8, alpha=0.85, label=col)
                plotted = True
    if event_day is not None:
        ax.axvspan(event_day, event_day + pd.Timedelta(days=1),
                   alpha=0.06, color=event_color)
    ax.axhline(0, color='blue', ls='--', lw=1.2, alpha=0.6, label='0°C')
    ax.set_ylabel('Temperature (°C)', fontweight='bold', fontsize=15)
    ax.set_title('Temperature', fontweight='bold', loc='left', fontsize=16)
    ax.grid(True, alpha=0.25, linewidth=0.5)
    ax.legend(loc='upper right', fontsize=12, ncol=2)


def _plot_precip_merged(ax, precip_data, w_start, w_end, event_day=None,
                        station='BKLN', event_color='red', pws_stations=None,
                        resample_interval=None, official_alpha=0.25):
    """
    All precip sources in one panel.
    PWS mean/median highlighted; ASOS/Mesonet bars subdued in background.
    """
    _bw = {'1min': 0.002, '5min': 0.008, '10min': 0.012, '15min': 0.015,
           '30min': 0.025, '1H': 0.04, '1h': 0.04}.get(
               resample_interval or '', 0.015)

    # --- Official bars (background) ---
    if 'mesonet' in precip_data:
        df = precip_data['mesonet']
        if station in df.columns:
            data = df[station].loc[w_start:w_end]
            if resample_interval:
                data = data.resample(resample_interval).sum()
            if len(data):
                ax.bar(data.index, data.values, width=_bw, color='green',
                       alpha=official_alpha, label=f'Mesonet ({station})',
                       zorder=1, edgecolor='darkgreen', linewidth=0.3)

    if 'asos_1min' in precip_data:
        data = precip_data['asos_1min'].loc[w_start:w_end].mean(axis=1)
        if resample_interval:
            data = data.resample(resample_interval).sum()
        if len(data):
            ax.bar(data.index, data.values, width=_bw, color='orange',
                   alpha=official_alpha, label='ASOS (mean)',
                   zorder=1, edgecolor='darkorange', linewidth=0.3)

    if 'noaa_daily' in precip_data:
        ax.plot([], [], color='blue', marker='s', ls='None',
                alpha=0.5, label='NOAA Daily: see legend')

    # --- PWS (foreground) ---
    if 'pws' in precip_data:
        df = precip_data['pws'].loc[w_start:w_end]
        if pws_stations:
            avail = [s for s in pws_stations if s in df.columns]
            if avail:
                df = df[avail]
        if resample_interval and len(df):
            df = df.resample(resample_interval).sum()
        if len(df):
            n = len(df.columns)
            cols_c = plt.cm.Purples(np.linspace(0.3, 0.7, n))
            for i, col in enumerate(df.columns):
                ax.plot(df.index, df[col], color=cols_c[i], lw=1.2, alpha=0.35, zorder=2)
            mean_p   = df.mean(axis=1)
            median_p = df.median(axis=1)
            ax.plot(mean_p.index, mean_p,   color='purple',  lw=3.5, alpha=0.95,
                    label=f'★ PWS Mean (n={n})', zorder=5)
            ax.plot(median_p.index, median_p, color='magenta', lw=2.5, alpha=0.8,
                    ls='--', label='★ PWS Median', zorder=4)
            ax.fill_between(mean_p.index, mean_p, median_p,
                            color='purple', alpha=0.12, zorder=3)

    if event_day is not None:
        ax.axvspan(event_day, event_day + pd.Timedelta(days=1),
                   alpha=0.06, color=event_color)

    ax.set_ylabel('Precip (mm)', fontweight='bold', fontsize=15)
    ax.set_title('Precipitation (All Sources - PWS Highlighted)',
                 fontweight='bold', loc='left', fontsize=16)
    ax.grid(True, alpha=0.25, linewidth=0.5)
    ax.legend(loc='upper right', fontsize=11, ncol=2)
    _set_robust_ylim(ax, quantile=0.98)


def _plot_precip_type(ax, ptype_data, w_start, w_end, event_day=None,
                      event_color='red', resample_interval=None,
                      skip_resample=False):
    """Horizontal colour-lane plot: one lane per station, coloured by ptype."""
    TYPE_COLORS = {'rain': 'blue', 'snow': 'cyan', 'mix': 'gray',
                   'precip': 'lightgreen', 'unknown': 'lightgray'}

    df_type = ptype_data.get('asos_1min')
    if df_type is None:
        ax.text(0.5, 0.5, 'No ptype data', transform=ax.transAxes,
                ha='center', va='center', color='gray')
        return

    df_plot = df_type.loc[w_start:w_end]
    if len(df_plot) == 0:
        return

    stations    = df_plot.columns.tolist()
    n           = len(stations)
    lane_height = 1.0 / n

    for i, station in enumerate(stations):
        yb = i * lane_height
        yt = (i + 0.9) * lane_height
        series = df_plot[station]

        # Resample only if not already pre-resampled
        if not skip_resample and resample_interval:
            series = series.resample(resample_interval).apply(_active_wins_resample)

        for idx in range(len(series) - 1):
            t0  = series.index[idx]
            t1  = series.index[idx + 1]
            val = series.iloc[idx]
            if pd.isna(val) or val in ('dry', 'none'):
                continue
            color = TYPE_COLORS.get(val, 'lightgray')
            ax.fill_between([t0, t1], yb, yt, color=color, alpha=0.65, linewidth=0)

    if event_day is not None:
        ax.axvspan(event_day, event_day + pd.Timedelta(days=1),
                   alpha=0.06, color=event_color, zorder=0)

    ax.set_ylim(0, 1)
    ax.set_yticks([(i + 0.45) * lane_height for i in range(n)])
    ax.set_yticklabels([s.replace('1min_', '') for s in stations], fontsize=11)
    ax.legend(handles=[
        Patch(facecolor='cyan',  alpha=0.65, label='Snow'),
        Patch(facecolor='blue',  alpha=0.65, label='Rain'),
        Patch(facecolor='gray',  alpha=0.65, label='Mix'),
        Patch(facecolor='lightgreen', alpha=0.65, label='Precip'),
    ], loc='upper right', fontsize=11, ncol=4)
    ax.set_ylabel('Precip Type', fontweight='bold', fontsize=15)
    ax.set_title('Precip Type (ASOS)', fontweight='bold', loc='left', fontsize=16)
    ax.grid(True, alpha=0.2, axis='x')


def _plot_temp_ptype_combined(ax, temp_data, ptype_data, w_start, w_end,
                               event_day=None, event_color='red',
                               resample_interval=None, skip_resample=False):
    """
    Temperature lines over ptype background colour bands.

    skip_resample=True when ptype_data already comes from aligned_data
    (i.e. already resampled by resample_ptype).
    """
    TYPE_BG = {'rain': '#4a90d9', 'snow': '#5ec4c4',
               'mix': '#9e9e9e', 'precip': '#a8e6a0'}

    # --- ptype background ---
    df_type = ptype_data.get('asos_1min') if ptype_data else None
    if df_type is not None:
        df_plot = df_type.loc[w_start:w_end]
        if len(df_plot) > 0:
            series = df_plot.iloc[:, 0]  # first station drives background
            if not skip_resample and resample_interval:
                series = series.resample(resample_interval).apply(_active_wins_resample)
            for idx in range(len(series) - 1):
                t0, t1 = series.index[idx], series.index[idx + 1]
                val    = series.iloc[idx]
                if pd.isna(val) or val in ('dry', 'none'):
                    continue
                color = TYPE_BG.get(val)
                if color:
                    ax.axvspan(t0, t1, color=color, alpha=0.30, zorder=0)

    # --- temperature lines ---
    plotted = False
    for src in ('asos_1min', 'mesonet'):
        if temp_data and src in temp_data and not plotted:
            df = temp_data[src].loc[w_start:w_end]
            if resample_interval and len(df):
                df = df.resample(resample_interval).mean()
            if len(df):
                for col in df.columns[:4]:
                    ax.plot(df.index, df[col], lw=2, alpha=0.9, label=col, zorder=3)
                plotted = True

    if event_day is not None:
        ax.axvspan(event_day, event_day + pd.Timedelta(days=1),
                   alpha=0.06, color=event_color)

    ax.axhline(0, color='blue', ls='--', lw=1.5, alpha=0.7, label='0°C', zorder=2)
    ax.set_ylabel('Temperature (°C)', fontweight='bold', fontsize=15)
    ax.set_title('Temperature + Precip Type', fontweight='bold', loc='left', fontsize=16)
    ax.grid(True, alpha=0.25, linewidth=0.5)

    handles, labels = ax.get_legend_handles_labels()
    ptype_patches = [
        Patch(facecolor='#5ec4c4', alpha=0.5, label='Snow'),
        Patch(facecolor='#4a90d9', alpha=0.5, label='Rain'),
        Patch(facecolor='#9e9e9e', alpha=0.5, label='Mix'),
    ]
    ax.legend(handles=handles + ptype_patches, loc='upper right',
              fontsize=12, ncol=3)


def _plot_snow_depth(ax, snow_depth_data, w_start, w_end, event_day=None,
                     station='BKLN', snow_data=None, event_color='red',
                     all_params=None, resample_interval=None):
    """Snow depth panel (Mesonet)."""
    mesonet = None
    if all_params:
        mesonet = all_params.get('snow_processed', {}).get('mesonet')
    if mesonet is None:
        mesonet = snow_depth_data.get('mesonet') if snow_depth_data else None

    if mesonet is not None and station in mesonet.columns:
        data = mesonet[station].loc[w_start:w_end]
        if resample_interval and len(data):
            data = data.resample(resample_interval).mean()
        if len(data):
            ax.plot(data.index, data.values, lw=2, color='#1f77b4',
                    marker='o', markersize=2, label='Snow Depth')

    if event_day is not None:
        ax.axvspan(event_day, event_day + pd.Timedelta(days=1),
                   alpha=0.06, color=event_color)
    ax.axhline(0, color='k', lw=0.5, alpha=0.8)
    ax.set_ylabel('Snow Depth (mm)', fontweight='bold', fontsize=15)
    ax.set_title(f'Snow Depth ({station})', fontweight='bold', loc='left', fontsize=16)
    ax.grid(True, alpha=0.25, linewidth=0.5)
    ax.legend(loc='upper right', fontsize=12)


def _plot_scatter_cml_vs_pws(ax, df_cml_dict, precip_data, w_start, w_end,
                              event_day=None, event_color='red',
                              signal_type='attenuation', df_cml_meta=None,
                              pws_stations=None, resample_interval=None,
                              pl_params=None, aligned_data=None):
    """CML power-law R vs PWS precipitation scatter panel."""
    use_aligned = aligned_data is not None
    if use_aligned:
        pl_params = aligned_data['pl_params']
    elif df_cml_meta is not None and pl_params is None:
        pl_params = _get_power_law_params_for_cmls(df_cml_dict, df_cml_meta)

    if not pl_params:
        ax.text(0.5, 0.5, 'No power-law params', transform=ax.transAxes,
                ha='center', va='center', color='gray')
        return

    # PWS rate
    if use_aligned:
        pws_rate = aligned_data.get('precip_rate_mean', {}).get('pws')
        if pws_rate is not None:
            pws_rate = pws_rate.loc[w_start:w_end]
    else:
        pws_rate = None
        if 'pws' in precip_data:
            df_p = precip_data['pws'].loc[w_start:w_end]
            if pws_stations:
                avail = [s for s in pws_stations if s in df_p.columns]
                if avail:
                    df_p = df_p[avail]
            if len(df_p):
                if resample_interval:
                    df_p = df_p.resample(resample_interval).sum()
                ri_h = pd.Timedelta(resample_interval or '1min').total_seconds() / 3600
                pws_rate = df_p.mean(axis=1) / ri_h

    if pws_rate is None or pws_rate.empty:
        ax.text(0.5, 0.5, 'No PWS data', transform=ax.transAxes,
                ha='center', va='center', color='gray')
        return

    # Build scatter
    xs, ys, colors = [], [], []
    cml_colors = plt.cm.tab10(np.linspace(0, 1, min(len(pl_params), 10)))

    if use_aligned:
        cml_R_w = aligned_data['cml_R'].loc[w_start:w_end]
        for ci, ck in enumerate(pl_params):
            if ck not in cml_R_w.columns:
                continue
            R_s = cml_R_w[ck].dropna()
            common = R_s.index.intersection(pws_rate.index)
            if not len(common):
                continue
            pv = pws_rate.loc[common].values
            rv = R_s.loc[common].values
            m  = (pv > 0) | (rv > 0)
            xs.extend(pv[m]); ys.extend(rv[m])
            colors.extend([cml_colors[ci % 10]] * m.sum())
    else:
        for ci, (ck, p) in enumerate(pl_params.items()):
            df = df_cml_dict.get(ck)
            if df is None or signal_type not in df.columns:
                continue
            atten = df.loc[w_start:w_end, signal_type]
            if resample_interval:
                atten = atten.resample(resample_interval).mean()
            R = _calc_R_from_A(atten.values, p['L_km'], p['a'], p['b'])
            common = atten.index.intersection(pws_rate.index)
            if not len(common):
                continue
            pv = pws_rate.loc[common].values
            rv = R[np.isin(atten.index, common)]
            m  = (pv > 0) | (rv > 0)
            xs.extend(pv[m]); ys.extend(rv[m])
            colors.extend([cml_colors[ci % 10]] * m.sum())

    if not xs:
        ax.text(0.5, 0.5, 'No overlapping data', transform=ax.transAxes,
                ha='center', va='center', color='gray')
        return

    xs, ys = np.array(xs), np.array(ys)
    ax.scatter(xs, ys, c=colors, s=30, alpha=0.6, edgecolors='k', lw=0.3, zorder=3)
    mx = max(np.nanmax(xs), np.nanmax(ys)) * 1.2
    ax.plot([0, mx], [0, mx], 'k--', lw=1.5, alpha=0.5, label='1:1')

    valid = np.isfinite(xs) & np.isfinite(ys) & (xs > 0) & (ys > 0)
    if valid.sum() > 2:
        r    = np.corrcoef(xs[valid], ys[valid])[0, 1]
        bias = np.mean(ys[valid] - xs[valid])
        rmse = np.sqrt(np.mean((ys[valid] - xs[valid])**2))
        ax.text(0.03, 0.97,
                f'n={valid.sum()}\nr={r:.2f}\nbias={bias:.2f}\nRMSE={rmse:.2f}',
                transform=ax.transAxes, fontsize=11, va='top',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

    ax.set_xlabel('PWS (mm/h)', fontweight='bold', fontsize=14)
    ax.set_ylabel('CML R (mm/h)', fontweight='bold', fontsize=14)
    ax.set_title(f'CML vs PWS Scatter ({len(pl_params)} links)',
                 fontweight='bold', loc='left', fontsize=15)
    ax.grid(True, alpha=0.25, linewidth=0.5)
    ax.legend(loc='lower right', fontsize=11)
    ax.set_xlim(0); ax.set_ylim(0)


# ============================================================================
# MAIN PLOT FUNCTION
# ============================================================================

def plot_event_day_analysis(
    df_cml_dict: dict,
    event_days=None,
    all_params: dict = None,
    aligned_data: dict = None,
    event_type: str = 'snow',
    signal_type: str = 'attenuation',
    station: str = 'BKLN',
    window_days: int = None,
    window_before: str = '1D',
    window_after: str = '1D',
    max_events: int = None,
    figsize: tuple = None,
    cml_to_pws_map: dict = None,
    df_cml_meta: pd.DataFrame = None,
    emphasize_cml_ids: list = None,
    start_dt=None,
    end_dt=None,
    panels='all',
    day_grid: bool = True,
    aggregate: str = None,
    cml_linewidth: float = 2.5,
    cml_linewidth_emphasized: float = 4.0,
    scatter: bool = False,
    show_title: bool = True,
    official_alpha: float = 0.25,
    label_size: int = 18,
    ylabel_size: int = 16,
    tick_size: int = 14,
    legend_size: int = 13,
    statistics: bool = False,
) -> list:
    """
    Multi-panel CML event day analysis.

    If aligned_data is provided (output of resample_all()), ptype and precip
    are already resampled — the function will not resample again.
    If only all_params is provided, raw data is used and resampled on-the-fly.

    Parameters
    ----------
    df_cml_dict     : {cml_key: DataFrame}
    event_days      : list/DatetimeIndex of event days  (OR use start_dt/end_dt)
    all_params      : raw weather dict  {'precip':..., 'temp':..., 'precip_type':...}
    aligned_data    : output of resample_all()  (preferred, avoids double-resampling)
    event_type      : 'snow' | 'rain' | 'custom'
    aggregate       : resample interval e.g. '5min', '15min', '1H'
    panels          : 'all' | list of panel names:
                        'cml', 'pcpn_merged', 'pcpn_pws', 'pcpn_official',
                        'ptype', 'temp', 'temp_ptype', 'snow', 'scatter'
    aligned_data    : if given, ptype/precip are used as-is (skip_resample=True)
    statistics      : if True, return list of window stats dicts
    """
    # ------------------------------------------------------------------
    # Resolve resample_interval
    # ------------------------------------------------------------------
    resample_interval = aggregate
    if aligned_data is not None and resample_interval is None:
        resample_interval = aligned_data.get('interval')

    # ------------------------------------------------------------------
    # Determine data sources (aligned wins over raw)
    # ------------------------------------------------------------------
    if aligned_data is not None:
        ptype_data  = aligned_data.get('precip_type', {})
        precip_data = aligned_data.get('precip', {})
        temp_data   = aligned_data.get('temp', {})
        _skip_resample = True
    elif all_params is not None:
        ptype_data  = all_params.get('precip_type', {})
        precip_data = all_params.get('precip', {})
        temp_data   = all_params.get('temp', {})
        _skip_resample = False
    else:
        ptype_data = precip_data = temp_data = {}
        _skip_resample = True

    snow_data       = (all_params or {}).get('snow', {})
    snow_depth_data = (all_params or {}).get('snow_depth', {})
    pws_stations    = _get_pws_stations_for_cmls(df_cml_dict, cml_to_pws_map)

    # ------------------------------------------------------------------
    # Window mode
    # ------------------------------------------------------------------
    if start_dt is not None and end_dt is not None:
        windows = [(pd.to_datetime(start_dt), pd.to_datetime(end_dt), None)]
    else:
        if event_days is None:
            raise ValueError("Provide event_days or (start_dt, end_dt)")
        if isinstance(event_days, pd.Timestamp):
            event_days = [event_days]
        event_days = pd.to_datetime(event_days)
        if max_events:
            event_days = event_days[:max_events]
        if window_days is not None:
            window_before = f'{window_days}D'
            window_after  = f'{window_days}D'
        td_b = pd.Timedelta(window_before)
        td_a = pd.Timedelta(window_after)
        windows = [(d - td_b, d + pd.Timedelta(days=1) + td_a, d)
                   for d in event_days]

    # ------------------------------------------------------------------
    # Panel list
    # ------------------------------------------------------------------
    EVENT_CFG = {
        'snow':   {'color': 'red',  'emoji': '❄️'},
        'rain':   {'color': 'blue', 'emoji': '🌧️'},
        'custom': {'color': 'gray', 'emoji': '📅'},
    }
    cfg = EVENT_CFG.get(event_type, EVENT_CFG['custom'])

    if panels == 'all':
        panel_list = ['cml', 'pcpn_merged', 'temp_ptype']
        if event_type == 'snow':
            panel_list.append('snow')
    elif isinstance(panels, str):
        panel_list = [panels]
    else:
        panel_list = list(panels)

    if scatter and 'scatter' not in panel_list:
        panel_list.append('scatter')

    n_rows  = len(panel_list)
    figsize = figsize or (26, 5.5 * n_rows)

    # Pre-compute pl_params once
    _pl_params = None
    if scatter and df_cml_meta is not None:
        _pl_params = _get_power_law_params_for_cmls(df_cml_dict, df_cml_meta)

    # ------------------------------------------------------------------
    # LOOP OVER WINDOWS
    # ------------------------------------------------------------------
    all_stats = []

    for w_start, w_end, event_day in windows:

        fig, axes = plt.subplots(n_rows, 1, figsize=figsize, sharex=True)
        if n_rows == 1:
            axes = [axes]

        plot_event_day = event_day if day_grid else None

        for ax_idx, panel_name in enumerate(panel_list):
            ax = axes[ax_idx]

            if panel_name == 'cml':
                _plot_cml_signal(
                    ax, df_cml_dict, w_start, w_end, plot_event_day,
                    signal_type, cfg['color'], df_cml_meta=df_cml_meta,
                    emphasize_cml_ids=emphasize_cml_ids,
                    resample_interval=resample_interval,
                    linewidth=cml_linewidth,
                    linewidth_emphasized=cml_linewidth_emphasized)

            elif panel_name == 'pcpn_merged':
                _plot_precip_merged(
                    ax, precip_data, w_start, w_end, plot_event_day,
                    station, cfg['color'], pws_stations=pws_stations,
                    resample_interval=resample_interval if not _skip_resample else None,
                    official_alpha=official_alpha)

            elif panel_name == 'pcpn_pws':
                # simple PWS-only panel
                if 'pws' in precip_data:
                    df = precip_data['pws'].loc[w_start:w_end]
                    if pws_stations:
                        avail = [s for s in pws_stations if s in df.columns]
                        if avail:
                            df = df[avail]
                    if not _skip_resample and resample_interval:
                        df = df.resample(resample_interval).sum()
                    mean_p = df.mean(axis=1)
                    ax.plot(mean_p.index, mean_p, color='purple', lw=2.5,
                            label=f'PWS Mean (n={len(df.columns)})')
                    _set_robust_ylim(ax)
                if plot_event_day:
                    ax.axvspan(plot_event_day,
                               plot_event_day + pd.Timedelta(days=1),
                               alpha=0.06, color=cfg['color'])
                ax.set_ylabel('Precip (mm)', fontweight='bold', fontsize=15)
                ax.set_title('PWS Precipitation', fontweight='bold', loc='left', fontsize=16)
                ax.legend(fontsize=12); ax.grid(True, alpha=0.25)

            elif panel_name == 'pcpn_official':
                for src, color in (('mesonet', 'green'), ('asos_1min', 'orange')):
                    if src in precip_data:
                        data = precip_data[src].loc[w_start:w_end].mean(axis=1)
                        if not _skip_resample and resample_interval:
                            data = data.resample(resample_interval).sum()
                        ax.plot(data.index, data, color=color, lw=2, label=src)
                if plot_event_day:
                    ax.axvspan(plot_event_day,
                               plot_event_day + pd.Timedelta(days=1),
                               alpha=0.06, color=cfg['color'])
                _set_robust_ylim(ax)
                ax.set_ylabel('Precip (mm)', fontweight='bold', fontsize=15)
                ax.set_title('Official Precipitation', fontweight='bold', loc='left', fontsize=16)
                ax.legend(fontsize=12); ax.grid(True, alpha=0.25)

            elif panel_name == 'ptype':
                _plot_precip_type(
                    ax, ptype_data, w_start, w_end, plot_event_day,
                    cfg['color'],
                    resample_interval=resample_interval,
                    skip_resample=_skip_resample)

            elif panel_name == 'temp':
                _plot_temperature(
                    ax, temp_data, w_start, w_end, plot_event_day,
                    cfg['color'], resample_interval=None if _skip_resample else resample_interval)

            elif panel_name == 'temp_ptype':
                _plot_temp_ptype_combined(
                    ax, temp_data, ptype_data, w_start, w_end,
                    plot_event_day, cfg['color'],
                    resample_interval=resample_interval,
                    skip_resample=_skip_resample)

            elif panel_name == 'snow':
                _plot_snow_depth(
                    ax, snow_depth_data, w_start, w_end, plot_event_day,
                    station, snow_data, cfg['color'],
                    all_params=all_params,
                    resample_interval=None if _skip_resample else resample_interval)

            elif panel_name == 'scatter':
                _plot_scatter_cml_vs_pws(
                    ax, df_cml_dict, precip_data, w_start, w_end,
                    plot_event_day, cfg['color'], signal_type, df_cml_meta,
                    pws_stations, resample_interval,
                    pl_params=_pl_params, aligned_data=aligned_data)

            else:
                ax.text(0.5, 0.5, f'Unknown panel: {panel_name}',
                        transform=ax.transAxes, ha='center', va='center')

        # X-axis formatting — apply to ALL axes so ticks are always visible
        span_hours = (pd.to_datetime(w_end) - pd.to_datetime(w_start)).total_seconds() / 3600
        if span_hours <= 24:
            major_loc = mdates.HourLocator(interval=3)
            fmt       = mdates.DateFormatter('%m-%d %H:%M')
        elif span_hours <= 72:
            major_loc = mdates.HourLocator(interval=6)
            fmt       = mdates.DateFormatter('%m-%d %H:%M')
        elif span_hours <= 168:
            major_loc = mdates.HourLocator(interval=12)
            fmt       = mdates.DateFormatter('%m-%d %H:%M')
        else:
            major_loc = mdates.DayLocator(interval=1)
            fmt       = mdates.DateFormatter('%m-%d')

        for ax_i, ax in enumerate(axes):
            ax.xaxis.set_major_locator(major_loc)
            ax.xaxis.set_major_formatter(fmt)
            ax.tick_params(axis='x', labelsize=tick_size, rotation=45)
            ax.tick_params(axis='y', labelsize=tick_size)
            # Only show x tick labels on bottom axis (sharex hides them on others)
            # Force them visible on ALL panels
            plt.setp(ax.xaxis.get_majorticklabels(), visible=True,
                     rotation=45, ha='right', fontsize=tick_size)

        axes[-1].set_xlabel('Time', fontweight='bold', fontsize=label_size)

        # Check if any panel has outside legend (needs right margin)
        has_outside_legend = any(
            ax.get_legend() is not None and
            getattr(ax.get_legend(), '_bbox_to_anchor', None) is not None
            for ax in axes
        )

        if show_title:
            agg = f' [{resample_interval}]' if resample_interval else ''
            if event_day is None:
                title = (f'{cfg["emoji"]} Analysis{agg}  '
                         f'{pd.to_datetime(w_start).strftime("%Y-%m-%d %H:%M")} → '
                         f'{pd.to_datetime(w_end).strftime("%Y-%m-%d %H:%M")}')
            else:
                title = (f'{cfg["emoji"]} {event_type.title()} Day{agg}  '
                         f'{event_day.strftime("%B %d, %Y (%A)")}')
            fig.suptitle(title, fontsize=label_size + 4, fontweight='bold')

        # Leave right margin if legend is outside
        n_links = len(df_cml_dict)
        if n_links > 20:
            plt.tight_layout(rect=[0, 0, 0.82, 0.97 if show_title else 1.0])
        else:
            plt.tight_layout(rect=[0, 0, 1.0,  0.97 if show_title else 1.0])

        plt.show()
        print(f"✓ {'custom window' if event_day is None else event_day.strftime('%Y-%m-%d')}")

        # ------------------------------------------------------------------
        # STATISTICS
        # ------------------------------------------------------------------
        if statistics:
            ws = {'window_start': w_start, 'window_end': w_end, 'event_day': event_day}

            # Ptype breakdown
            pt_src = ptype_data.get('asos_1min')
            if pt_src is not None:
                pt_w = pt_src.loc[w_start:w_end]
                if len(pt_w) and len(pt_w.columns):
                    series = pt_w.iloc[:, 0].dropna()
                    n = len(series)
                    if n:
                        vc = series.value_counts()
                        ws['precip_type_pct'] = {k: vc.get(k, 0) / n * 100
                                                  for k in ('rain', 'snow', 'mix', 'dry', 'precip', 'none')}

            # CML NaN %
            nan_pct = {}
            for ck, df in df_cml_dict.items():
                if df is None or df.empty or signal_type not in df.columns:
                    nan_pct[ck] = 100.0; continue
                data = df.loc[w_start:w_end, signal_type]
                nan_pct[ck] = (data.isna().sum() / max(len(data), 1)) * 100
            ws['cml_nan_pct'] = nan_pct
            all_stats.append(ws)

    return all_stats if statistics else None


# ============================================================================
# CONVENIENCE WRAPPERS
# ============================================================================

def plot_time_window(
    df_cml_dict: dict,
    start_dt,
    end_dt,
    all_params: dict = None,
    aligned_data: dict = None,
    panels: list = None,
    aggregate: str = None,
    **kwargs,
):
    """
    Plot a custom time window (no event_days needed).

    Example
    -------
    plot_time_window(
        df_cml_filtered,
        '2024-01-06 00:00', '2024-01-09 12:00',
        all_params=all_params,
        panels=['cml', 'pcpn_merged', 'temp_ptype'],
        aggregate='5min',
        statistics=True,
    )
    """
    return plot_event_day_analysis(
        df_cml_dict=df_cml_dict,
        event_days=None,
        all_params=all_params,
        aligned_data=aligned_data,
        start_dt=start_dt,
        end_dt=end_dt,
        panels=panels or ['cml', 'pcpn_merged', 'temp_ptype'],
        aggregate=aggregate,
        **kwargs,
    )


def plot_quick_overview(df_cml_dict, event_days, all_params, **kwargs):
    """3-panel quick overview: CML + merged precip + temp/ptype."""
    return plot_event_day_analysis(
        df_cml_dict=df_cml_dict,
        event_days=event_days,
        all_params=all_params,
        panels=['cml', 'pcpn_merged', 'temp_ptype'],
        **kwargs,
    )


# ============================================================================
# SNOW DEPTH CLEANING
# ============================================================================

def clean_snow_depth(raw_data, snow_days, stations=None,
                     calibration_hours=24.0, filter_window_minutes=30,
                     max_depth=500.0):
    """
    Clean snow depth:  s(t) = clip(median_filter(x(t) - baseline(t)), 0, max)
    Returns (cleaned_df, baselines_df).
    """
    if stations is None:
        stations = raw_data.columns.tolist()
    snow_times = pd.to_datetime(snow_days)
    cleaned, baselines = pd.DataFrame(index=raw_data.index), pd.DataFrame(index=raw_data.index)

    for st in stations:
        raw = raw_data[st].copy()
        cal_pts = []
        for snow_time in snow_times:
            mask = (raw.index >= snow_time - pd.Timedelta(hours=calibration_hours)) & \
                   (raw.index < snow_time)
            window = raw[mask].dropna()
            if len(window) >= 12:
                cal_pts.append((snow_time, window.median()))

        if not cal_pts:
            bl = pd.Series(raw.median(), index=raw.index)
        else:
            ts, vs = zip(*cal_pts)
            bl_s = pd.Series(dict(zip(ts, vs))).reindex(
                pd.DatetimeIndex(ts).union(raw.index))
            bl = bl_s.interpolate(method='time').ffill().bfill().reindex(raw.index)

        window_samples = max(1, filter_window_minutes // 5)
        smoothed = (raw - bl).rolling(window=window_samples, center=True,
                                       min_periods=1).median()
        cleaned[st]  = smoothed.clip(0, max_depth)
        baselines[st] = bl

    return cleaned, baselines


# ============================================================================
# EVENT CLASSIFICATION PLOT
# ============================================================================

def plot_event_classification(rainy_days, snowy_days, start_date, end_date,
                              daily_precip=None, daily_snow=None, figsize=(18, 8)):
    """Timeline bar chart classifying each day as snow/rain/mix/dry."""
    import matplotlib.patches as mpatches

    rainy  = set(pd.to_datetime(rainy_days).normalize())
    snowy  = set(pd.to_datetime(snowy_days).normalize())
    days   = pd.date_range(start_date, end_date, freq='D')

    COLORS = {'snow': '#00BFFF', 'rain': '#4169E1', 'mix': '#9370DB', 'dry': '#F5F5DC'}

    def _classify(d):
        r, s = d.normalize() in rainy, d.normalize() in snowy
        return 'mix' if r and s else ('snow' if s else ('rain' if r else 'dry'))

    cats = [{'date': d.normalize(), 'cat': _classify(d)} for d in days]
    df_c = pd.DataFrame(cats)

    fig, axes = plt.subplots(3, 1, figsize=figsize,
                              gridspec_kw={'height_ratios': [2, 1, 1]})
    ax1, ax2, ax3 = axes

    for _, row in df_c.iterrows():
        ax1.axvspan(row['date'], row['date'] + pd.Timedelta(days=1),
                    color=COLORS[row['cat']], alpha=0.7)
    ax1.set_xlim(start_date, end_date); ax1.set_ylim(0, 1); ax1.set_yticks([])
    ax1.set_title('Event Classification Timeline', fontsize=14, fontweight='bold')
    ax1.legend(handles=[mpatches.Patch(color=COLORS[k], label=k.capitalize())
                        for k in ('snow', 'rain', 'mix', 'dry')],
               loc='upper right', fontsize=10, ncol=4)

    for ax, src, color, title in [(ax2, daily_precip, None, 'Daily Precipitation'),
                                   (ax3, daily_snow, '#00BFFF', 'Daily Snowfall')]:
        if src is not None:
            vals = src.mean(axis=1) if isinstance(src, pd.DataFrame) else src
            for _, row in df_c.iterrows():
                if row['date'] in vals.index:
                    v = vals.loc[row['date']]
                    if pd.notna(v) and v > 0:
                        ax.bar(row['date'], v, width=0.8,
                               color=color or COLORS[row['cat']],
                               edgecolor='gray', lw=0.5)
        ax.set_xlim(start_date, end_date)
        ax.set_title(title, fontsize=12, fontweight='bold', loc='left')
        ax.grid(True, alpha=0.5, axis='y')

    ax3.set_xlabel('Date', fontweight='bold')
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
    plt.tight_layout(); plt.show()
    return df_c


# ============================================================================
# ASOS 1-MIN PRECIPITATION PLOT
# ============================================================================

def plot_asos_precip_by_event(df_asos_precip, df_asos_type, event_days,
                              window_days=1, max_events=None):
    """Bar chart of ASOS 1-min precip coloured by precip type, per event day."""
    stations   = df_asos_precip.columns.tolist()
    event_days = pd.to_datetime(event_days)
    if max_events:
        event_days = event_days[:max_events]

    TYPE_COLORS = {'dry': 'none', 'rain': 'blue', 'snow': 'cyan',
                   'mix': 'gray', 'precip': 'lightgreen', 'unknown': 'lightgray'}

    for event_day in event_days:
        p_start = event_day - pd.Timedelta(days=window_days)
        p_end   = event_day + pd.Timedelta(days=window_days + 1)
        mask    = (df_asos_precip.index >= p_start) & (df_asos_precip.index <= p_end)
        df_p    = df_asos_precip.loc[mask]
        df_t    = df_asos_type.loc[mask]

        if len(df_p) == 0:
            continue

        fig, axes = plt.subplots(len(stations), 1, figsize=(20, 4 * len(stations)),
                                 sharex=True)
        if len(stations) == 1:
            axes = [axes]

        for ax, station in zip(axes, stations):
            precip = df_p[station]
            ptype  = df_t[station]

            for time, val in precip.items():
                if pd.isna(val) or val == 0:
                    continue
                raw_type = ptype.get(time, 'unknown')
                cat = categorize_precip_type(raw_type) if raw_type not in TYPE_COLORS else raw_type
                color = TYPE_COLORS.get(cat, 'lightgray')
                if color == 'none':
                    continue
                ax.bar(time, val, width=0.0007, color=color, alpha=0.85,
                       edgecolor='navy', linewidth=0.4)

            # Background shading
            for i in range(len(df_t) - 1):
                t0, t1 = df_t.index[i], df_t.index[i + 1]
                cat = categorize_precip_type(ptype.iloc[i])
                bg  = {'rain': ('blue', 0.05), 'snow': ('cyan', 0.10),
                       'mix':  ('gray', 0.05)}.get(cat)
                if bg:
                    ax.axvspan(t0, t1, alpha=bg[1], color=bg[0], zorder=0)

            ax.set_ylabel('Precip (mm)', fontsize=12, fontweight='bold')
            ax.set_title(station.replace('1min_', ''), fontsize=13, fontweight='bold')
            ax.set_ylim(bottom=0)
            ax.set_xlim(p_start, p_end)
            ax.grid(True, alpha=0.3, ls='--')
            ax.legend(handles=[Patch(facecolor=c, alpha=0.8, label=t.capitalize())
                                for t, c in TYPE_COLORS.items()
                                if c not in ('none', 'lightgray')],
                      loc='upper right', fontsize=10, ncol=3)

        axes[-1].set_xlabel('Time', fontsize=12, fontweight='bold')
        axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha='right')
        fig.suptitle(f'ASOS 1-Min Precipitation — {event_day.strftime("%Y-%m-%d")}',
                     fontsize=15, fontweight='bold')
        plt.tight_layout(); plt.show()


# ============================================================================
# PRECIPITATION ACCUMULATION
# ============================================================================

def plot_precipitation_accumulation(precip_data, rainy_days=None, snowy_days=None,
                                     start_date=None, end_date=None,
                                     mode='merged',
                                     figsize_separate=(18, 12),
                                     figsize_merged=(14, 7)):
    """Cumulative precipitation plot (merged = one panel, separate = subplots)."""
    if start_date or end_date:
        filtered = {}
        for src, df in precip_data.items():
            if df is None or len(df) == 0:
                continue
            mask = pd.Series(True, index=df.index)
            if start_date: mask &= (df.index >= start_date)
            if end_date:   mask &= (df.index <= end_date)
            filtered[src] = df[mask]
        precip_data = filtered

    rainy_n = [pd.Timestamp(d).normalize() for d in (rainy_days or [])]
    snowy_n = [pd.Timestamp(d).normalize() for d in (snowy_days or [])]

    # ---- MERGED ----
    if mode == 'merged':
        fig, ax = plt.subplots(figsize=figsize_merged)
        all_idx = [df.index for df in precip_data.values() if df is not None and len(df)]
        if all_idx:
            g_min = min(i.min() for i in all_idx)
            g_max = max(i.max() for i in all_idx)
            for day in rainy_n:
                if day <= g_max:
                    ax.axvspan(day, day + pd.Timedelta(days=1),
                               color='lightblue', alpha=0.15, zorder=0,
                               label='Rain Days' if day == rainy_n[0] else '')
            for day in snowy_n:
                if day <= g_max:
                    ax.axvspan(day, day + pd.Timedelta(days=1),
                               color='lightcyan', alpha=0.20, zorder=0,
                               label='Snow Days' if day == snowy_n[0] else '')

        src_styles = {
            'pws':        ('blue',   'PWS Mean',       3.0),
            'asos_1min':  ('orange', 'ASOS 1min Mean', 3.0),
            'noaa_daily': ('green',  'NOAA Daily',     3.0),
            'mesonet':    ('purple', 'Mesonet Mean',   3.0),
        }
        for src, df in precip_data.items():
            if df is None or len(df) == 0:
                continue
            accum = df.fillna(0).cumsum()
            color, label, lw = src_styles.get(src, ('gray', src, 2.0))
            ax.plot(accum.mean(axis=1), color=color, lw=lw, label=label, zorder=9)
            if src == 'pws':
                ax.plot(accum.median(axis=1), color='navy', lw=2.5,
                        ls='--', label='PWS Median', zorder=9)

        ax.set_xlabel('Date'); ax.set_ylabel('Cumulative Precipitation (mm)')
        ax.set_title('Precipitation Accumulation — All Sources', fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.xticks(rotation=45)
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(dict(zip(labels, handles)).values(),
                  dict(zip(labels, handles)).keys(), fontsize=10)
        plt.tight_layout(); plt.show()
        return fig

    # ---- SEPARATE ----
    order  = [k for k in ('pws', 'asos_1min', 'noaa_daily', 'mesonet')
              if k in precip_data and len(precip_data[k])]
    n      = len(order)
    if n == 0:
        print("No data for accumulation plot")
        return None

    fig, axes = plt.subplots(n, 1, figsize=figsize_separate, sharex=True)
    if n == 1:
        axes = [axes]

    for ax, src in zip(axes, order):
        df    = precip_data[src].fillna(0).cumsum()
        means = df.mean(axis=1)
        for col in df.columns:
            ax.plot(df.index, df[col], 'lightblue', alpha=0.4, lw=0.8)
        ax.plot(means, color='blue', lw=3, label='Mean', zorder=5)
        for day in rainy_n:
            ax.axvline(day, color='blue', ls=':', lw=1.5, alpha=0.7)
        for day in snowy_n:
            ax.axvline(day, color='cyan', ls=':', lw=1.5, alpha=0.7)
        ax.set_ylabel('Cumulative (mm)')
        ax.set_title(src, fontweight='bold', loc='left')
        ax.grid(True, alpha=0.3); ax.legend()

    axes[-1].set_xlabel('Date')
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45, ha='right')
    plt.tight_layout(); plt.show()
    return fig


# ============================================================================
# CML-SENSOR MATCHING MAP
# ============================================================================

def plot_cml_sensor_matching(df_cml_meta, cml_to_sensor_maps=None, cml_ids=None,
                              sensor_types=None, n_cmls=5, base_path=None,
                              figsize=(14, 12), show_distance_for=('PWS',)):
    """Map of selected CMLs with matched sensors and distance labels."""
    if cml_to_sensor_maps is None:
        print("No sensor maps provided"); return

    sensor_styles = {
        'PWS':     {'marker': 'o', 'size': 50,  'color': 'purple', 'alpha': 0.7},
        'ASOS':    {'marker': '^', 'size': 90,  'color': 'red',    'alpha': 0.9},
        'Mesonet': {'marker': 'D', 'size': 70,  'color': 'green',  'alpha': 0.9},
    }
    if sensor_types is None:
        sensor_types = list(cml_to_sensor_maps.keys())

    if cml_ids is None:
        pool = set()
        for sm in cml_to_sensor_maps.values():
            pool.update(sm.keys())
        pool = list(pool) or df_cml_meta['cml_id'].astype(str).tolist()
        cml_ids = list(np.random.choice(pool, size=min(n_cmls, len(pool)), replace=False))

    fig, ax = plt.subplots(figsize=figsize)
    if base_path:
        try:
            import geopandas as gpd
            shp = base_path / 'gis' / 'NYC_boundary' / 'nyc_boundary.shp'
            if shp.exists():
                gpd.read_file(shp).boundary.plot(ax=ax, color='gray', lw=1, alpha=0.5)
        except Exception:
            pass

    cmap = plt.cm.tab10
    colors = {str(c): cmap(i % 10) for i, c in enumerate(cml_ids)}
    plotted = {st: set() for st in sensor_types}
    all_lons, all_lats = [], []

    for cml_id in cml_ids:
        cml_id = str(cml_id)
        rows = df_cml_meta[df_cml_meta['cml_id'].astype(str) == cml_id]
        if len(rows) == 0:
            continue
        r = rows.iloc[0]
        la, lb = r['site_0_lat'], r['site_1_lat']
        loa, lob = r['site_0_lon'], r['site_1_lon']
        mlat, mlon = (la + lb) / 2, (loa + lob) / 2
        all_lons += [loa, lob]; all_lats += [la, lb]

        ax.plot([loa, lob], [la, lb], color=colors[cml_id], lw=4,
                solid_capstyle='round', zorder=5, label=f'CML {cml_id}')
        ax.scatter(mlon, mlat, color=colors[cml_id], s=120, marker='s',
                   edgecolor='black', lw=1.5, zorder=6)

        for st in sensor_types:
            sm = cml_to_sensor_maps.get(st, {})
            matches = sm.get(cml_id) or sm.get(int(cml_id) if cml_id.isdigit() else None)
            if matches is None or (isinstance(matches, pd.DataFrame) and matches.empty):
                continue
            sty = sensor_styles.get(st, {'marker': 'o', 'size': 60, 'color': 'gray', 'alpha': 0.8})
            for _, m in matches.iterrows():
                sid  = m.get('station_id', 'unknown')
                slat = m.get('latitude');  slon = m.get('longitude')
                if slat is None or slon is None:
                    continue
                dist_km = m.get('distance_m', 0) / 1000
                all_lons.append(slon); all_lats.append(slat)
                ax.plot([mlon, slon], [mlat, slat], color=sty['color'],
                        ls='--', lw=1, alpha=0.4, zorder=3)
                if sid not in plotted[st]:
                    ax.scatter(slon, slat, color=sty['color'], s=sty['size'],
                               marker=sty['marker'], edgecolor='black', lw=0.8,
                               zorder=4, alpha=sty['alpha'])
                    plotted[st].add(sid)
                if st in show_distance_for:
                    ax.annotate(f'{dist_km:.1f}km',
                                ((mlon + slon) / 2, (mlat + slat) / 2),
                                fontsize=7, color=sty['color'], ha='center',
                                bbox=dict(boxstyle='round,pad=0.2',
                                          facecolor='white', alpha=0.6))

    if all_lons:
        pad = 0.01
        ax.set_xlim(min(all_lons) - pad, max(all_lons) + pad)
        ax.set_ylim(min(all_lats) - pad, max(all_lats) + pad)

    ax.set_xlabel('Longitude'); ax.set_ylabel('Latitude')
    ax.set_title('CML–Sensor Matching', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3); ax.set_aspect('equal')
    plt.tight_layout(); plt.show()
    return fig



def plot_snow_single_fig(all_params, snowy_days):
    """ONE PLOT: Temp Errorbars (per dataset) | PCPN/Snow/Depth Bars"""
    
    stats = []
    for snow_day in snowy_days:
        day_start = snow_day.normalize()
        row = {'Date': snow_day.strftime('%m-%d')}
        
        # Temps: min/avg/max per dataset
        for source in ['noaa_daily', 'asos_1min', 'mesonet']:
            if source in all_params.get('temp', {}):
                df = all_params['temp'][source]
                mask = (df.index >= day_start) & (df.index < day_start + pd.Timedelta(days=1))
                data = df[mask]
                if len(data) > 0:
                    row[f'{source}_avg'] = data.mean().mean() if isinstance(data, pd.DataFrame) else data.mean()
                    row[f'{source}_min'] = data.min().min() if isinstance(data, pd.DataFrame) else data.min()
                    row[f'{source}_max'] = data.max().max() if isinstance(data, pd.DataFrame) else data.max()
        
        # NOAA Daily: separate sums
        for param, key in [('precip', 'PCPN'), ('snow', 'Snow'), ('snow_depth', 'Depth')]:
            if 'noaa_daily' in all_params.get(param, {}):
                df = all_params[param]['noaa_daily'].clip(lower=0)
                mask = df.index.normalize() == day_start
                data = df[mask]
                if len(data) > 0:
                    row[f'{key}_NOAA'] = data.sum().sum() if isinstance(data, pd.DataFrame) else data.sum()
        
        stats.append(row)
    
    df_stats = pd.DataFrame(stats)
    
    # SINGLE FIGURE WITH 2 SUBPLOTS
    fig, (ax_temp, ax_mm) = plt.subplots(1, 2, figsize=(16, 6))
    x = range(len(df_stats))
    width = 0.3
    
    # === LEFT: TEMP - 1 BAR PER DATASET + RANGE ===
    sources = ['noaa_daily', 'asos_1min', 'mesonet']
    colors = ['red', 'orange', 'green']
    
    for i, source in enumerate(sources):
        avg_col = f'{source}_avg'
        min_col = f'{source}_min'
        max_col = f'{source}_max'
        
        if avg_col in df_stats.columns:
            # SINGLE BAR (avg) + errorbars (min/max range)
            yerr_lower = df_stats[avg_col] - df_stats[min_col]
            yerr_upper = df_stats[max_col] - df_stats[avg_col]
            yerr = [yerr_lower, yerr_upper]
            
            ax_temp.bar(x, df_stats[avg_col], width, 
                       yerr=yerr, capsize=8, error_kw={'elinewidth': 3, 'capthick': 3},
                       label=source.title(), color=colors[i], alpha=0.9)
    
    ax_temp.set_title('TEMPERATURE\nAvg Bar + Min/Max Range (per dataset)', fontweight='bold')
    ax_temp.set_ylabel('°C')
    ax_temp.set_xticks(x)
    ax_temp.set_xticklabels(df_stats['Date'], rotation=45)
    ax_temp.legend()
    ax_temp.grid(axis='y', alpha=0.3)
    
    # === RIGHT: PCPN/SNOW/DEPTH - SEPARATE BARS ===
    mm_cols = ['PCPN_NOAA', 'Snow_NOAA', 'Depth_NOAA']
    colors_mm = ['steelblue', 'dodgerblue', 'lightblue']
    
    for i, col in enumerate(mm_cols):
        if col in df_stats.columns:
            ax_mm.bar([j + i*width for j in x], df_stats[col], width, 
                     label=col.replace('_NOAA', ''), color=colors_mm[i], alpha=0.9)
    
    ax_mm.set_title('PCPN/SNOW/DEPTH\nNOAA Daily (separate bars)', fontweight='bold')
    ax_mm.set_ylabel('mm')
    ax_mm.set_xticks([j + width for j in x])
    ax_mm.set_xticklabels(df_stats['Date'], rotation=45)
    ax_mm.legend()
    ax_mm.grid(axis='y', alpha=0.3)
    
    plt.suptitle(f'SNOW DAY ANALYSIS - {len(snowy_days)} Events', fontsize=16)
    plt.tight_layout()
    plt.show()
    
    print(f"✅ ONE FIGURE: Temp errorbars (1 bar/dataset) + PCPN bars!")
    return fig

def _plot_weather_merged(ax, precip_data, temp_data, ptype_data, w_start, w_end,
                         event_day=None, event_color='red', pws_stations=None,
                         resample_interval=None, skip_resample=False,
                         official_alpha=0.25):
    """
    Single panel with:
    - Precip on left y-axis (PWS highlighted, ASOS/Mesonet bars)
    - Temp on right y-axis (mean ± min/max band)
    - Ptype as background colors
    """
    # --- PTYPE BACKGROUND ---
    TYPE_BG = {'rain': '#4a90d9', 'snow': '#5ec4c4', 'mix': '#9e9e9e', 'precip': '#a8e6a0'}
    
    df_type = ptype_data.get('asos_1min') if ptype_data else None
    if df_type is not None:
        df_plot = df_type.loc[w_start:w_end]
        if len(df_plot) > 0:
            series = df_plot.iloc[:, 0]
            if not skip_resample and resample_interval:
                series = series.resample(resample_interval).apply(_active_wins_resample)
            for idx in range(len(series) - 1):
                t0, t1 = series.index[idx], series.index[idx + 1]
                val = series.iloc[idx]
                if pd.isna(val) or val in ('dry', 'none'):
                    continue
                color = TYPE_BG.get(val)
                if color:
                    ax.axvspan(t0, t1, color=color, alpha=0.25, zorder=0)
    
    # --- PRECIP (left y-axis) ---
    _bw = {'1min': 0.002, '5min': 0.008, '10min': 0.012, '15min': 0.015,
           '30min': 0.025, '1H': 0.04, '1h': 0.04}.get(resample_interval or '', 0.015)
    
    # Official bars
    if 'mesonet' in precip_data:
        df = precip_data['mesonet']
        if 'BKLN' in df.columns:
            data = df['BKLN'].loc[w_start:w_end]
            if resample_interval and not skip_resample:
                data = data.resample(resample_interval).sum()
            if len(data):
                ax.bar(data.index, data.values, width=_bw, color='green',
                       alpha=official_alpha, label='Mesonet', zorder=1,
                       edgecolor='darkgreen', linewidth=0.3)
    
    if 'asos_1min' in precip_data:
        data = precip_data['asos_1min'].loc[w_start:w_end].mean(axis=1)
        if resample_interval and not skip_resample:
            data = data.resample(resample_interval).sum()
        if len(data):
            ax.bar(data.index, data.values, width=_bw, color='orange',
                   alpha=official_alpha, label='ASOS', zorder=1,
                   edgecolor='darkorange', linewidth=0.3)
    
    # PWS
    if 'pws' in precip_data:
        df = precip_data['pws'].loc[w_start:w_end]
        if pws_stations:
            avail = [s for s in pws_stations if s in df.columns]
            if avail:
                df = df[avail]
        if resample_interval and not skip_resample and len(df):
            df = df.resample(resample_interval).sum()
        if len(df):
            mean_p = df.mean(axis=1)
            median_p = df.median(axis=1)
            ax.plot(mean_p.index, mean_p, color='purple', lw=3, alpha=0.95,
                    label=f'PWS Mean (n={len(df.columns)})', zorder=5)
            ax.plot(median_p.index, median_p, color='magenta', lw=2, alpha=0.8,
                    ls='--', label='PWS Median', zorder=4)
    
    if event_day is not None:
        ax.axvspan(event_day, event_day + pd.Timedelta(days=1),
                   alpha=0.06, color=event_color)
    
    ax.set_ylabel('Precip (mm)', fontweight='bold', fontsize=15, color='purple')
    ax.tick_params(axis='y', labelcolor='purple', labelsize=14)
    _set_robust_ylim(ax, quantile=0.98)
    
    # --- TEMP (right y-axis) ---
    ax2 = ax.twinx()
    
    for src in ('asos_1min', 'mesonet'):
        if temp_data and src in temp_data:
            df_t = temp_data[src].loc[w_start:w_end]
            if resample_interval and len(df_t):
                df_t = df_t.resample(resample_interval).mean()
            if len(df_t):
                mean_t = df_t.mean(axis=1)
                min_t = df_t.min(axis=1)
                max_t = df_t.max(axis=1)
                
                ax2.plot(mean_t.index, mean_t, color='red', lw=2.5, alpha=0.9,
                         label='Temp Mean', zorder=6)
                ax2.fill_between(mean_t.index, min_t, max_t, color='red',
                                 alpha=0.15, zorder=2, label='Temp Range')
                break
    
    ax2.axhline(0, color='blue', ls='--', lw=1.5, alpha=0.7, zorder=2)
    ax2.set_ylabel('Temperature (°C)', fontweight='bold', fontsize=15, color='red')
    ax2.tick_params(axis='y', labelcolor='red', labelsize=14)
    
    # Legend
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ptype_h = [Patch(facecolor='#5ec4c4', alpha=0.5, label='Snow'),
               Patch(facecolor='#4a90d9', alpha=0.5, label='Rain'),
               Patch(facecolor='#9e9e9e', alpha=0.5, label='Mix')]
    
    ax.legend(h1 + h2 + ptype_h, l1 + l2 + ['Snow', 'Rain', 'Mix'],
              loc='upper left', fontsize=10, ncol=3)
    
    ax.set_title('Weather (Precip + Temp + Type)', fontweight='bold',
                 loc='left', fontsize=16)
    ax.grid(True, alpha=0.25, linewidth=0.5)


