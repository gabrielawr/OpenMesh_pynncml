"""
ASOS Analysis Examples

Run individual examples to see functionality in action.

Before running:
1. Download ASOS data from https://mesonet.agron.iastate.edu/request/asos/1min.phtml
2. Save files as [STATION_ID].txt (e.g., KJFK.txt, KLGA.txt)
3. Place in './asos_data' directory
4. Run: python examples.py
"""

from asos_processor import (
    read_asos_files, 
    filter_by_date_range,
    analyze_data,
    print_analysis,
    plot_variable,
    compare_stations,
    get_summary_table
)
import pandas as pd


# ============================================================================
# EXAMPLE 1: Load and Summarize Data
# ============================================================================

def example_1_load_and_summarize():
    """Load ASOS data and display summary statistics."""
    
    print("\n" + "="*75)
    print("EXAMPLE 1: Load and Summarize Data")
    print("="*75 + "\n")
    
    # Load all files
    data = read_asos_files('./asos_data')
    
    # Display summary
    print("\nSummary Table:")
    print(get_summary_table(data))


# ============================================================================
# EXAMPLE 2: Analyze Single Station
# ============================================================================

def example_2_analyze_station():
    """Analyze data for a single station."""
    
    print("\n" + "="*75)
    print("EXAMPLE 2: Analyze Single Station")
    print("="*75 + "\n")
    
    data = read_asos_files('./asos_data')
    
    # Get first station
    station_id = list(data.keys())[0]
    df = data[station_id]
    
    # Full analysis
    analysis = analyze_data(df, station_id)
    print_analysis(analysis)
    
    # Additional insights
    if 'tmpf_mean' in analysis:
        print(f"Temperature Analysis for {station_id}:")
        print(f"  Average: {analysis['tmpf_mean']:.1f}°F")
        print(f"  Range: {analysis['tmpf_min']:.1f}°F to {analysis['tmpf_max']:.1f}°F")
        print(f"  Std Dev: {analysis['tmpf_std']:.1f}°F\n")
    
    if 'precip_mm_mean' in analysis:
        total_precip = analysis['precip_mm_count'] * analysis['precip_mm_mean']
        print(f"Precipitation Analysis for {station_id}:")
        print(f"  Total: {total_precip:.1f} mm")
        print(f"  Max event: {analysis['precip_mm_max']:.1f} mm\n")


# ============================================================================
# EXAMPLE 3: Date Range Filtering
# ============================================================================

def example_3_date_filtering():
    """Filter data by date range."""
    
    print("\n" + "="*75)
    print("EXAMPLE 3: Date Range Filtering")
    print("="*75 + "\n")
    
    data = read_asos_files('./asos_data')
    station_id = list(data.keys())[0]
    df = data[station_id]
    
    # Get date range from data
    all_dates = df['valid_time'].dt.date
    start_date = str(all_dates.min())
    end_date = str(all_dates.min() + pd.Timedelta(days=7))
    
    print(f"Full dataset: {len(df)} records")
    print(f"Date range: {df['valid_time'].min()} to {df['valid_time'].max()}\n")
    
    # Filter
    filtered = filter_by_date_range(df, start_date, end_date)
    print(f"After filtering to {start_date} to {end_date}:")
    print(f"  Records: {len(filtered)}")
    
    analysis_full = analyze_data(df, f"{station_id} (full)")
    analysis_filtered = analyze_data(filtered, f"{station_id} ({start_date} to {end_date})")
    
    print(f"\nTemperature comparison:")
    print(f"  Full: {analysis_full.get('tmpf_mean', 'N/A')}")
    print(f"  Filtered: {analysis_filtered.get('tmpf_mean', 'N/A')}\n")


# ============================================================================
# EXAMPLE 4: Plot Single Variable
# ============================================================================

def example_4_plot_variable():
    """Create time-series plot for temperature."""
    
    print("\n" + "="*75)
    print("EXAMPLE 4: Plot Temperature Variable")
    print("="*75 + "\n")
    
    data = read_asos_files('./asos_data')
    
    print("Creating temperature plot...")
    print("Saving as: temperature_plot.png\n")
    
    # Plot temperature
    plot_variable(data, 'tmpf', save_path='temperature_plot.png')


# ============================================================================
# EXAMPLE 5: Plot Precipitation
# ============================================================================

def example_5_plot_precipitation():
    """Create time-series plot for precipitation."""
    
    print("\n" + "="*75)
    print("EXAMPLE 5: Plot Precipitation")
    print("="*75 + "\n")
    
    data = read_asos_files('./asos_data')
    
    print("Creating precipitation plot...")
    print("Saving as: precipitation_plot.png\n")
    
    plot_variable(data, 'precip_mm', save_path='precipitation_plot.png')


# ============================================================================
# EXAMPLE 6: Compare Multiple Stations
# ============================================================================

def example_6_compare_stations():
    """Compare same variable across multiple stations."""
    
    print("\n" + "="*75)
    print("EXAMPLE 6: Compare Multiple Stations")
    print("="*75 + "\n")
    
    data = read_asos_files('./asos_data')
    
    if len(data) > 1:
        print(f"Comparing {len(data)} stations\n")
        
        # Plot comparison
        compare_stations(data, 'tmpf', save_path='station_comparison.png')
        
        # Print individual statistics
        print("\nIndividual Statistics:\n")
        for station_id, df in data.items():
            analysis = analyze_data(df, station_id)
            if 'tmpf_mean' in analysis:
                print(f"{station_id}: Avg Temp = {analysis['tmpf_mean']:.1f}°F")
    
    else:
        print("Need multiple stations to compare.")
        print("Download data for more than one station from NOAA Mesonet.\n")


# ============================================================================
# EXAMPLE 7: Export Data to CSV
# ============================================================================

def example_7_export_csv():
    """Export filtered data to CSV."""
    
    print("\n" + "="*75)
    print("EXAMPLE 7: Export Data to CSV")
    print("="*75 + "\n")
    
    data = read_asos_files('./asos_data')
    
    # Create export
    results = []
    
    for station_id, df in data.items():
        # Get first 100 records
        df_sample = df.head(100)
        
        for idx, row in df_sample.iterrows():
            results.append({
                'Station': station_id,
                'Time': row.get('valid_time'),
                'Temperature_F': row.get('tmpf'),
                'Dewpoint_F': row.get('dwpf'),
                'Wind_Speed_knots': row.get('sknt'),
                'Wind_Direction_deg': row.get('drct'),
                'Precipitation_mm': row.get('precip_mm'),
                'Visibility_sm': row.get('vsby'),
            })
    
    export_df = pd.DataFrame(results)
    export_df.to_csv('asos_export.csv', index=False)
    
    print(f"Exported {len(export_df)} records to asos_export.csv")
    print(f"\nFirst 5 rows:")
    print(export_df.head())


# ============================================================================
# EXAMPLE 8: Statistical Summary
# ============================================================================

def example_8_statistics():
    """Calculate custom statistics."""
    
    print("\n" + "="*75)
    print("EXAMPLE 8: Statistical Summary")
    print("="*75 + "\n")
    
    data = read_asos_files('./asos_data')
    station_id = list(data.keys())[0]
    df = data[station_id]
    
    print(f"Statistics for {station_id}\n")
    
    # Temperature stats
    print("Temperature Statistics:")
    print(f"  Mean: {df['tmpf'].mean():.1f}°F")
    print(f"  Median: {df['tmpf'].median():.1f}°F")
    print(f"  Std Dev: {df['tmpf'].std():.1f}°F")
    print(f"  25th percentile: {df['tmpf'].quantile(0.25):.1f}°F")
    print(f"  75th percentile: {df['tmpf'].quantile(0.75):.1f}°F")
    
    # Precipitation stats
    print("\nPrecipitation Statistics:")
    precip_events = df[df['precip_mm'] > 0]
    print(f"  Records with rain: {len(precip_events)} ({len(precip_events)/len(df)*100:.1f}%)")
    print(f"  Total precipitation: {df['precip_mm'].sum():.1f} mm")
    print(f"  Max event: {df['precip_mm'].max():.1f} mm")
    if len(precip_events) > 0:
        print(f"  Avg per event: {precip_events['precip_mm'].mean():.2f} mm")
    
    # Wind stats
    print("\nWind Statistics:")
    print(f"  Mean speed: {df['sknt'].mean():.1f} knots")
    print(f"  Max gust: {df['sknt'].max():.1f} knots")
    print(f"  Std Dev: {df['sknt'].std():.1f} knots\n")


# ============================================================================
# Main Menu
# ============================================================================

def main():
    """Run selected examples."""
    
    print("\n" + "="*75)
    print("ASOS Data Analysis Examples")
    print("="*75)
    print("\nAvailable examples:")
    print("1. Load and summarize data")
    print("2. Analyze single station")
    print("3. Date range filtering")
    print("4. Plot temperature")
    print("5. Plot precipitation")
    print("6. Compare multiple stations")
    print("7. Export data to CSV")
    print("8. Statistical summary")
    print("0. Run all")
    print("-" * 75)
    
    choice = input("Select example (0-8): ").strip()
    
    try:
        if choice == '1':
            example_1_load_and_summarize()
        elif choice == '2':
            example_2_analyze_station()
        elif choice == '3':
            example_3_date_filtering()
        elif choice == '4':
            example_4_plot_variable()
        elif choice == '5':
            example_5_plot_precipitation()
        elif choice == '6':
            example_6_compare_stations()
        elif choice == '7':
            example_7_export_csv()
        elif choice == '8':
            example_8_statistics()
        elif choice == '0':
            example_1_load_and_summarize()
            example_2_analyze_station()
            example_3_date_filtering()
            example_7_export_csv()
            example_8_statistics()
        else:
            print("Invalid selection")
    
    except FileNotFoundError:
        print("Error: './asos_data' directory not found or no .txt files present")
        print("Please:")
        print("1. Create './asos_data' directory")
        print("2. Download ASOS files from https://mesonet.agron.iastate.edu/request/asos/1min.phtml")
        print("3. Save files as [STATION_ID].txt (e.g., KJFK.txt)")


if __name__ == '__main__':
    main()
