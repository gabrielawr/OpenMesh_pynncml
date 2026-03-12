import os
import urllib.request
import zipfile
from functools import partial
import math

import numpy as np
import pandas as pd
import xarray as xr
import netCDF4 as nc
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter
from matplotlib.patches import Patch
import matplotlib.dates as mdates
from scipy.interpolate import interp1d
from tqdm import tqdm

import pynncml
import pynncml as pnc
from pynncml import plot_wet_dry_detection_mark
from pynncml.datasets.dataset import LinkDataset
from pynncml.datasets.gauge_data import PointSensor
from pynncml.datasets import PointSet
from pynncml.datasets.xarray_processing import xarray2link, LinkSelection
from pynncml.datasets.link_data import Link
from pynncml.datasets.meta_data import MetaData
from pynncml.datasets.sensors_set import LinkSet
    


def read_netcdf_groups_to_xarray_dict(ds):
    """
    Convert open netCDF4 groups to dict of xarray Datasets.
    """
    print(f"\n{'=' * 70}")
    print("CONVERTING NETCDF GROUPS TO XARRAY DICT")
    print(f"{'=' * 70}\n")

    stations = {}

    for station_id in ds.groups.keys():
        try:
            station_ds = xr.open_dataset(ds.filepath(), group=station_id, engine='netcdf4')
            stations[station_id] = station_ds
            print(f"  ✓ {station_id}: {len(station_ds.time)} records")
        except Exception as e:
            print(f"  ❌ {station_id}: {e}")

    print(f"\n✓ Converted {len(stations)} stations")
    print(f"{'=' * 70}\n")

    return stations



def guage_to_linkset(gaugemetapath, gaugespath):
    # Load gauge metadata
    gauge_metadata = pd.read_csv(gaugemetapath, index_col=0)

    # Load gauge data
    ds_gauge = nc.Dataset(gaugespath, 'r')
    
    gauge = read_netcdf_groups_to_xarray_dict(ds_gauge)
    
    # 5-minute sampling
    rain_gauge_time_base = 300  # seconds

    # Create PointSensors directly from each gauge's individual data
    # This avoids the problem of merging all gauges which creates many NaNs
    gauge_list = []
    for station_id, ds_gauge_temp in gauge.items():
        # Match with metadata by "Station ID"
        i = gauge_metadata.index[gauge_metadata["Station ID"] == station_id].tolist()
        if not i:
            print(f"⚠️ Skipping '{station_id}' (no matching Station ID in metadata)")
            continue
        i = i[0]

        # Get coordinates from metadata
        lon = gauge_metadata.loc[i, "Longitude"]
        lat = gauge_metadata.loc[i, "Latitude"]

        # Get the first data variable (usually rainfall_rate)
        var_name = list(ds_gauge_temp.data_vars)[0]
        da = ds_gauge_temp[var_name]

        # Extract time and data values directly from this gauge
        time_values = ds_gauge_temp.time.values
        data_values = da.values

        # Convert time to datetime if needed, then to Unix timestamp
        if hasattr(time_values, 'dtype') and 'datetime64' not in str(time_values.dtype):
            # If time is in Unix timestamp format
            if np.issubdtype(time_values.dtype, np.number):
                time_array_unix = time_values.astype(np.int64)
            else:
                time_array = pd.to_datetime(time_values)
                time_array = time_array.dt.tz_localize(None).to_numpy()
                time_array = time_array.astype("datetime64[s]")
                time_array_unix = time_array.astype(np.int64)
        else:
            # Already datetime64
            time_array = pd.to_datetime(time_values)
            if hasattr(time_array, 'dt'):
                time_array = time_array.dt.tz_localize(None).to_numpy()
            time_array = time_array.astype("datetime64[s]")
            time_array_unix = time_array.astype(np.int64)

        # Extract rainfall data (preserve NaN values - don't convert to zero)
        rain_rate_gauge = data_values.flatten() if data_values.ndim > 1 else data_values
        # DO NOT convert NaN to 0 - preserve NaN to distinguish missing data from zero rainfall

        # Only build PointSensor if data has at least some valid (non-NaN) values
        if not np.all(np.isnan(rain_rate_gauge)):
            ps = PointSensor(
                rain_rate_gauge,
                time_array_unix,
                lon=lon,
                lat=lat
            )
            #ps = ps.change_time_base(rain_gauge_time_base)
            gauge_list.append(ps)
        else:
            print(f"⚠️ Skipping '{station_id}' (all data is NaN)")

    # Combine all into PointSet
    ps = PointSet(gauge_list)
    return ps


def patched_xarray2link_with_gauges(ds, ps, max_distance=5000, change2min_max=False, time_slice=False, start=None, end=None):
    """
    Convert xarray to LinkSet with gauge references
    Skips links with NaN coordinates or no valid RSL data
    """
    link_list = []
    skipped_coords = 0
    skipped_data = 0
    
    if time_slice:
        ds = ds.sel(time=slice(start, end))
        
    for i in tqdm(range(len(ds.sublink_id)), desc="Processing sublinks"):
        sublink_name = ds.sublink_id.values[i]
        
        # Loop through each cml_id
        for cid in ds.cml_id.values:
            ds_one = ds.sel(cml_id=cid, sublink_id=sublink_name).squeeze(drop=True)
            
            # Extract coordinates
            site_0_lon = float(ds_one.site_0_lon.values)
            site_0_lat = float(ds_one.site_0_lat.values)
            site_1_lon = float(ds_one.site_1_lon.values)
            site_1_lat = float(ds_one.site_1_lat.values)
            
            # Skip if coordinates are NaN
            if (np.isnan(site_0_lat) or np.isnan(site_0_lon) or 
                np.isnan(site_1_lat) or np.isnan(site_1_lon)):
                skipped_coords += 1
                continue
            
            # Extract RSL data
            rsl = np.squeeze(ds_one["rsl"].values)
            
            # Skip if all RSL values are NaN (no valid data)
            if np.all(np.isnan(rsl)):
                skipped_data += 1
                continue
            
            # Extract other metadata
            frequency = float(ds_one.frequency.values)
            length = float(ds_one.length.values)
            polarization = str(ds_one.polarization.values)
            
            # Build metadata
            md = MetaData(
                frequency / 1000,  # MHz to GHz
                "Vertical" in polarization or "v" in polarization.lower(),
                length / 1000,  # meters to km
                height_far=None,
                height_near=None,
                lon_lat_site_zero=[site_0_lon, site_0_lat],
                lon_lat_site_one=[site_1_lon, site_1_lat],
            )
            
            # Add cml_id and sublink_id to metadata
            md.cml_id = str(cid)
            md.sublink_id = str(sublink_name)
            
            # Extract TSL data
            tsl = np.squeeze(ds_one["tsl"].values) if "tsl" in ds_one else np.zeros_like(rsl)
            
            # Find all gauges within max_distance
            distances, gauges = ps.find_near_gauges(md.xy_center(), max_distance)
            gauge_ref = None
            
            # If we have gauges within range, create averaged gauge
            if len(gauges) > 0:
                
                # Get the union of all gauge time ranges (min to max across all gauges)
                # Collect all gauge time arrays to find the overall min/max
                all_gauge_times = []
                for g in gauges:
                    gauge_time = g.time_array.astype("datetime64[s]").astype(np.int64)
                    all_gauge_times.append(gauge_time)
                
                if len(all_gauge_times) == 0:
                    # No gauges, skip
                    averaged_gauge = None
                    gauge_ref = None
                else:
                    # Find the overall min and max time across all gauges
                    overall_time_min = min(gt.min() for gt in all_gauge_times)
                    overall_time_max = max(gt.max() for gt in all_gauge_times)
                    
                    # Create a common time array from min to max with consistent 5 min time-step
                    # Use the same time resolution as the link (or you could use a fixed resolution)
                    time_step = 300
                    num_steps = int((overall_time_max - overall_time_min) // time_step)
                    time_max = overall_time_min + (num_steps * time_step)
                    
                    # Create common time array from min to max with the determined step
                    snapped_start = (overall_time_min // time_step) * time_step
                    common_time_array = np.arange(snapped_start, overall_time_max + time_step, time_step, dtype=np.int64)
                    
                    # Clip common_time_array to start no earlier than the link's start time
                    link_start_time = ds_one.time.to_numpy().astype("datetime64[s]").astype(np.int64).min()
                    common_time_array = common_time_array[common_time_array >= link_start_time]

                    # Interpolate each gauge's data to the common time base
                    aligned_arrays = []
                    for g in gauges:
                        gauge_time = g.time_array.astype("datetime64[s]").astype(np.int64)
                        
                        # Find overlapping time period with common time array
                        time_min = max(gauge_time.min(), common_time_array.min())
                        time_max = min(gauge_time.max(), common_time_array.max())
                        
                        if time_max <= time_min:
                            # No overlap, create array of NaNs with same length as common_time_array
                            aligned_data = np.full(len(common_time_array), np.nan)
                            aligned_arrays.append(aligned_data)
                            continue
                        
                        # Get gauge data in overlapping period
                        gauge_mask = (gauge_time >= time_min) & (gauge_time <= time_max)
                        gauge_time_overlap = gauge_time[gauge_mask]
                        gauge_data_overlap = g.data_array[gauge_mask]
                        
                        # Interpolate gauge data to common time array
                        # Use linear interpolation, fill NaN outside bounds
                        interp_func = interp1d(gauge_time_overlap, gauge_data_overlap, 
                                              kind='linear', bounds_error=False, 
                                              fill_value=np.nan, assume_sorted=True)
                        # Interpolate to the common time array
                        aligned_data = interp_func(common_time_array)
                        
                        aligned_arrays.append(aligned_data)
                    
                    if len(aligned_arrays) == 0:
                        # No overlapping data, skip averaging
                        averaged_gauge = None
                        gauge_ref = None
                    else:
                        # Stack arrays for averaging (now they all have the same shape - all aligned to common_time_array)
                        stacked_arrays = np.stack(aligned_arrays, axis=0)
                        
                        # Average the data arrays using nanmean to properly handle NaN values
                        averaged_data = np.nanmean(stacked_arrays, axis=0)
                        
                        # Use the common time array (union of all gauge time ranges)
                        time_array = common_time_array
                    
                    # Calculate average location
                    avg_lon = np.mean([g.lon for g in gauges])
                    avg_lat = np.mean([g.lat for g in gauges])
                    
                    # Create averaged PointSensor
                    from pynncml.datasets.gauge_data import PointSensor
                    averaged_gauge = PointSensor(
                        data_array=averaged_data,
                        time_array=time_array,
                        lon=avg_lon,
                        lat=avg_lat,
                        force_zone_number=gauges[0].force_zone_number,
                        force_zone_letter=gauges[0].force_zone_letter
                    )
                    
                    gauge_ref = [averaged_gauge]
                # Store number of gauges used in metadata for later reference
                md.num_gauges_used = len(gauges)
            else:
                # No gauges found
                md.num_gauges_used = 0
            
            
            # Create Link
            link = Link(
                link_rsl=rsl,
                time_array=ds_one.time.to_numpy().astype("datetime64[s]").astype("int"),
                meta_data=md,
                link_tsl=tsl
            )
            
            # Add gauge reference to the link
            link.add_reference(gauge_ref=gauge_ref)

            if change2min_max and link is not None:
                rounded_time = (np.round(link.time_array / 900) * 900).astype(np.int64)
                link.time_array = rounded_time
                link = link.create_min_max_link(900)

                
            if link is not None: link_list.append(link)

    
    # Summary
    print(f"\n{'='*60}")
    print(f"Processing Summary:")
    print(f"  ✅ Valid links created: {len(link_list)}")
    print(f"  ⚠️  Skipped (missing coordinates): {skipped_coords}")
    print(f"  ⚠️  Skipped (no RSL data): {skipped_data}")
    print(f"  📊 Total processed: {skipped_coords + skipped_data + len(link_list)}")
    print(f"{'='*60}\n")
    
    return LinkSet(link_list)



def classification_plot(link, threshold, window, is_minmax=True, plot=True):

    swd = pnc.scm.wet_dry.statistics_wet_dry(threshold, window)  # init classification model
    wd_classification, std_vector = swd(link.attenuation())  # run classification method

    if is_minmax:
        #   Gauge data to 15 min resolution
        ref = gauge_to15(link.gauge_ref[0])['gauge_data']
        gauge_time = ref.index
        gauge_data = ref.values

        #   Find overlapping time
        link_time = link.time_array.astype('datetime64[s]')
        start_time = max(link_time.min(), gauge_time.min())
        end_time = min(link_time.max(), gauge_time.max())

        link_mask = (link_time >= start_time) & (link_time <= end_time)
        gauge_mask = (gauge_time >= start_time) & (gauge_time <= end_time)

        link_time_trimmed = link_time[:-2]

        link_mask = (link_time_trimmed >= start_time) & (link_time_trimmed <= end_time)
        gauge_mask = (gauge_time >= start_time) & (gauge_time <= end_time)

        wd = wd_classification.numpy()[0, :-2][link_mask]
        std = std_vector.numpy()[0, :-2][link_mask]
        ref_trimmed = gauge_data[gauge_mask]
        
        plot_time = gauge_time[gauge_mask]

        if plot:

            _, ax = plt.subplots(3, 1)
            ax[0].plot(link_time_trimmed[link_mask], wd)
            ax[0].set_xlabel('index')
            ax[0].set_ylabel('Detection')
            ax[0].grid()

            ax[1].set_ylabel(r'$\sigma_n$')
            ax[1].plot(link_time_trimmed[link_mask], std)

            ax[2].plot(plot_time, ref_trimmed)
            plot_wet_dry_detection_mark(ax[2], plot_time, wd, np.nan_to_num(ref_trimmed, nan=0.0)) # only first and last are nan
            ax[2].legend()
            ax[2].set_xlabel('Time')
            ax[2].set_ylabel(r'Rain Rate[mm/hr]')

            for a in ax:
                a.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
                a.xaxis.set_major_locator(mdates.DayLocator())

            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()

        tp = ((wd == 1) & (ref_trimmed > 0)).sum()
        fp = ((wd == 1) & (ref_trimmed == 0)).sum()
        fn = ((wd == 0) & (ref_trimmed > 0)).sum()
        tn = ((wd == 0) & (ref_trimmed == 0)).sum()

        accuracy = (tp + tn) / len(wd)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0

    
    else:
        ref_times = pd.to_datetime(link.time_array, unit='s')
        wd_vals = wd_classification.squeeze()
        std_vals = std_vector.squeeze()
        base_times = pd.to_datetime(link.gauge_ref[0].time_array, unit='s')

        buckets_std = {t: [] for t in base_times}
        buckets_wd = {t: [] for t in base_times}

        for i, r_time in enumerate(ref_times):
            # Find which baseline time is the absolute closest to this 1-min point
            diffs = np.abs(base_times - r_time)
            closest_time = base_times[np.argmin(diffs)]
            
            # Drop the value into that bucket
            buckets_wd[closest_time].append(wd_vals[i])
            buckets_std[closest_time].append(std_vals[i])

        wd_5min = np.array([int(any(buckets_wd[t])) if buckets_wd[t] else 0 for t in base_times])
        std_5min = np.array([np.nanmean(buckets_std[t]) if buckets_std[t] else 0.0 for t in base_times])

        ref = link.gauge_ref[0].data_array
        plot_time = base_times

        if plot:
            _, ax = plt.subplots(3, 1)
            ax[0].plot(plot_time, wd_5min)
            ax[0].set_xlabel('index')
            ax[0].set_ylabel('Detection')
            ax[0].grid()

            ax[1].set_ylabel(r'$\sigma_n$')
            ax[1].plot(plot_time, std_5min)

            ax[2].plot(plot_time, ref)
            plot_wet_dry_detection_mark(ax[2], plot_time, wd_5min, np.nan_to_num(ref, nan=0.0))
            ax[2].legend()
            ax[2].set_xlabel('Time')
            ax[2].set_ylabel(r'Rain Rate[mm/hr]')

            for a in ax:
                a.xaxis.set_major_formatter(mdates.DateFormatter('%d-%m'))
                a.xaxis.set_major_locator(mdates.DayLocator())

            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()

        tp = ((wd_5min == 1) & (ref > 0)).sum()
        fp = ((wd_5min == 1) & (ref == 0)).sum()
        fn = ((wd_5min == 0) & (ref > 0)).sum()
        tn = ((wd_5min == 0) & (ref == 0)).sum()
    
        accuracy = (tp + tn) / len(wd_5min)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    
    stats = {"TPR":tp/(tp+fn), "FPR":fp/(fp+tn)}

    print(f"Accuracy:  {accuracy*100:.1f}%")
    print(f"Precision: {precision*100:.1f}%")
    print(f"Recall:    {recall*100:.1f}%")
    return stats
                

def gauge_to15(gauge, is_minmax=False):

    import math
    
    gauge_data = gauge.data_array
    gauge_time = gauge.time_array.astype("datetime64[s]")



    # Calculate the number of trios
    n_trios = math.ceil(len(gauge.data_array) / 3)

    # Initialize arrays for averages and time indices
    averages = np.zeros(n_trios)
    time_indices = []

    # Calculate average of every 3 values
    for i in range(n_trios):
        start_idx = i * 3
        end_idx = min(start_idx + 3, len(gauge.data_array))  # Handle last incomplete trio
        
        # Calculate average of the trio
        averages[i] = np.mean(gauge.data_array[start_idx:end_idx])
        
        # Get the time index of the first element in the trio
        time_indices.append(pd.to_datetime(gauge_time[start_idx]))

    # Create DataFrame with time index
    gauge_15 = pd.DataFrame({
        'value': averages
    }, index=pd.DatetimeIndex(time_indices))

    return {'time_array': gauge_15.index, 'gauge_data': gauge_15['value']}


def rain_detection(link, statistics_wet_dry_threshold, statistics_window_size, plot=True, is_min_max=False):

    # rain detection algorithm
    swd = pnc.scm.wet_dry.statistics_wet_dry(statistics_wet_dry_threshold, statistics_window_size)
    wd_classification, std_vector = swd(link.attenuation())

    wd_array = wd_classification.numpy()[0, :-2]
    std_array = std_vector.numpy()[0, :-2]

    # GAUGE DATA (real rain)
    gauge_ref = link.gauge_ref
    if gauge_ref and len(gauge_ref) > 0:
        gauge = gauge_ref[0]

        # Get 15 minute window
        gauge15 = gauge_to15(gauge)
        gauge_time = gauge15['time_array'].astype("datetime64[s]")
    
        # Get time arrays as datetime64
        link_time_full = link.time().astype("datetime64[s]")
        link_time = link_time_full[:-2]
        #gauge_time = gauge.time_array.astype("datetime64[s]")

        # Find overlapping time period
        start_time = max(link_time.min(), gauge_time.min())
        end_time = min(link_time.max(), gauge_time.max())

        # Create masks for overlap period
        link_mask = (link_time >= start_time) & (link_time <= end_time)
        gauge_mask = (gauge_time >= start_time) & (gauge_time <= end_time)

        # Apply masks
        wd_filtered = wd_array[link_mask]
        std_filtered = std_array[link_mask]
        ref_filtered = gauge15['gauge_data'][gauge_mask]
        #ref_filtered = gauge.data_array[gauge_mask]
        time_filtered_link = link_time[link_mask] 
        time_filtered_gauge = gauge_time[gauge_mask]
        
        # Create DataFrame for link predictions
        link_df = pd.DataFrame({
            'prediction': wd_filtered,
            'time': pd.to_datetime(time_filtered_link)
        }).set_index('time')
        
        # Create DataFrame for gauge data
        gauge_df = pd.DataFrame({
            'rainfall': ref_filtered,
            'time': pd.to_datetime(time_filtered_gauge)
        }).set_index('time')
        
        if is_min_max:
            link_resampled = link_df
        else:
            # 1-min resolution, resample to 15-min to match gauge
            link_resampled = link_df.resample('15min', label='left', closed='left').agg({
                'prediction': lambda x: 1 if (len(x) > 0 and x.max() == 1) else 0
            })

        combined = link_resampled.join(gauge_df, how='inner')
        combined = combined.dropna()
        
        # Resample link data to 5-minute intervals: if ANY prediction in window is 1, result is 1
        link_resampled = link_df.resample('5min', label='left', closed='left').agg({
            'prediction': lambda x: 1 if (len(x) > 0 and x.max() == 1) else 0
        })
        

        # Align the two datasets
        combined = link_resampled.join(gauge_df, how='inner')
        combined = combined.dropna()
        
        # Extract arrays for comparison
        predicted_rain_array = combined['prediction'].values
        rain_threshold = 0  # mm
        actual_rain_array = (combined['rainfall'].values > rain_threshold).astype(int)
        result_times = combined.index.values
        
        # Vectorized comparison (no loop needed!)
        categories = np.zeros(len(predicted_rain_array), dtype=int)
        
        # True Positive: predicted=1, actual=1
        tp_mask = (predicted_rain_array == 1) & (actual_rain_array == 1)
        categories[tp_mask] = 1
        
        # True Negative: predicted=0, actual=0
        tn_mask = (predicted_rain_array == 0) & (actual_rain_array == 0)
        categories[tn_mask] = 0
        
        # False Positive: predicted=1, actual=0
        fp_mask = (predicted_rain_array == 1) & (actual_rain_array == 0)
        categories[fp_mask] = 2
        
        # False Negative: predicted=0, actual=1
        fn_mask = (predicted_rain_array == 0) & (actual_rain_array == 1)
        categories[fn_mask] = 3
        
        # Calculate metrics
        true_positives = np.sum(tp_mask)
        true_negatives = np.sum(tn_mask)
        false_positives = np.sum(fp_mask)
        false_negatives = np.sum(fn_mask)
        correct = true_positives + true_negatives
        total = len(categories)
        
        accuracy = correct / total if total > 0 else 0
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        # ← OPTIMIZATION END
        
        if plot == True:
            # Create figure with 3 subplots stacked vertically
            fig, (ax_std, ax_gauge, ax_perf) = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
            
            # ===== TOP PLOT: STANDARD DEVIATION =====
            ax_std.plot(time_filtered_link, std_filtered, color='blue', linewidth=0.8)
            ax_std.set_ylabel('Standard Deviation', color='blue')
            ax_std.tick_params(axis='y', labelcolor='blue')
            ax_std.grid(True, alpha=0.3)
            ax_std.set_title('Standard Deviation and Gauge Rainfall Over Time')
            
            # ===== MIDDLE PLOT: GAUGE DATA =====
            ax_gauge.plot(time_filtered_gauge, ref_filtered, color='red', linewidth=0.8)
            ax_gauge.set_ylabel('Rainfall (mm)', color='red')
            ax_gauge.tick_params(axis='y', labelcolor='red')
            ax_gauge.grid(True, alpha=0.3)
            
            # ===== BOTTOM PLOT: RAIN DETECTION PERFORMANCE =====
            # Define colors for each category
            colors = {
                0: 'lightgreen',   # True Negative (no rain, no rain)
                1: 'darkgreen',    # True Positive (rain, rain)
                2: 'orange',       # False Positive (predicted rain, no rain)
                3: 'red'           # False Negative (no rain predicted, rain)
            }
            
            labels = {
                0: 'True Negative (Correct: No Rain)',
                1: 'True Positive (Correct: Rain)',
                2: 'False Positive (False Alarm)',
                3: 'False Negative (Missed Rain)'
            }
            
            # Plot colored zones
            for i in range(len(result_times)):
                start = result_times[i]
                if i < len(result_times) - 1:
                    end = result_times[i + 1]
                else:
                    end = start + np.timedelta64(5, 'm')
                
                category = categories[i]
                ax_perf.axvspan(start, end, color=colors[category], alpha=0.7)
            
            # Create legend
            legend_elements = [Patch(facecolor=colors[cat], label=labels[cat], alpha=0.7) 
                            for cat in sorted(colors.keys())]
            ax_perf.legend(handles=legend_elements, loc='upper right')
            
            ax_perf.set_xlabel('Time')
            ax_perf.set_ylabel('Category')
            ax_perf.set_title(f'Rain Detection Performance Over Time (Accuracy: {accuracy*100:.1f}%)')
            ax_perf.set_ylim(-0.5, 1.5)
            ax_perf.set_yticks([])
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.show()
        
        wd_array, std_array  # print some values around the Jan 28 rain event
        rain_event_mask = (link_time >= np.datetime64('2024-01-28')) & (link_time <= np.datetime64('2024-01-29'))
        print("WD classifications during rain event:", wd_array[rain_event_mask])
        print("Std values during rain event:", std_array[rain_event_mask])
        
        return {
            'accuracy': float(accuracy),
            'positive_acc': float(true_positives / (true_positives + false_negatives)),
            'negative_acc': float(true_negatives / (true_negatives + false_positives)),
            'categories': categories,
            'time_array': result_times,
            'true_positives': int(true_positives),
            'true_negatives': int(true_negatives),
            'false_positives': int(false_positives),
            'false_negatives': int(false_negatives)
        }
        
    else:
        print("Could not filter data or no gauge available")
        return None  

def del_links(link_set, idx_list, is_minmax=False):
    indexes = [i for i in range(0,len(link_set))]
    for idx in idx_list:
        indexes.remove(idx)
    
    links = [link_set.get_link(j) for j in indexes]
    return LinkSet(links)

def keep_links(link_set, idx_list, is_minmax=False):
    links = [link_set.get_link(j) for j in idx_list]
    return LinkSet(links)

def gaugetime_5to15(link):
    ref_times = pd.to_datetime(link.gauge_ref[0].time_array, unit='s')
    ref_vals = link.gauge_ref[0].data_array.flatten()
    base_times = pd.to_datetime(link.time_array, unit='s')

    buckets = {t: [] for t in base_times}

    for i, r_time in enumerate(ref_times):
        # Find which baseline time is the absolute closest to this 5-min point
        diffs = np.abs(base_times - r_time)
        closest_time = base_times[np.argmin(diffs)]
        
        # Drop the value into that bucket
        buckets[closest_time].append(ref_vals[i])

    ref_15min = np.array([np.nanmean(buckets[t]) if buckets[t] else 0.0 for t in base_times])
    return ref_15min