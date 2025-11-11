"""
Example: Basic Usage of NOAA ASOS Module

This script demonstrates how to use the NOAA ASOS module to:
1. Fetch data for a single month
2. Process the data
3. Analyze the results
"""

from datetime import datetime
from pathlib import Path

# Import module components
from fetcher import ASOSFetcher
from processor import ASOSProcessor
from analyzer import ASOSAnalyzer


def example_fetch_single_month():
    """
    Example: Fetch data for a single month
    """
    print("\n" + "="*60)
    print("EXAMPLE 1: Fetching Single Month Data")
    print("="*60)
    
    # Initialize fetcher for January 2024
    fetcher = ASOSFetcher(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 31)
    )
    
    # Fetch data for JFK only
    results = fetcher.fetch_station_data('KJFK')
    
    print(f"\nFetch Results:")
    for filename, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {filename}")


def example_process_and_analyze():
    """
    Example: Process downloaded data and analyze it
    """
    print("\n" + "="*60)
    print("EXAMPLE 2: Processing and Analysis")
    print("="*60)
    
    # Process the data
    processor = ASOSProcessor()
    process_results = processor.process_file(
        Path('data/noaa/asos/raw/KJFK_202401.dat')
    )
    
    if process_results is not None:
        print(f"\nProcessed {len(process_results)} records")
        print("\nSample data:")
        print(process_results.head())
        
        # Analyze the data
        analyzer = ASOSAnalyzer()
        
        # Load the processed data
        df = analyzer.load_station_data('KJFK', 
                                       start_date='2024-01-01',
                                       end_date='2024-01-31')
        
        if df is not None:
            # Compute daily statistics
            daily = analyzer.compute_daily_statistics(df, 'KJFK')
            
            print("\nDaily Statistics:")
            print(daily[['datetime', 'temp_mean', 'temp_min', 'temp_max', 
                        'wind_mean', 'completeness_pct']].head())
            
            # Summary statistics
            summary = analyzer.generate_summary_statistics('KJFK')
            print("\nSummary Statistics:")
            print(summary.to_string(index=False))


def example_custom_date_range():
    """
    Example: Fetch and process data for a custom date range
    """
    print("\n" + "="*60)
    print("EXAMPLE 3: Custom Date Range")
    print("="*60)
    
    # Fetch Q1 2024 data
    fetcher = ASOSFetcher(
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 3, 31)
    )
    
    # Fetch only for Central Park
    print("\nFetching Q1 2024 data for Central Park (KNYC)...")
    results = fetcher.fetch_station_data('KNYC')
    
    successful = sum(1 for v in results.values() if v)
    print(f"Successfully fetched {successful}/{len(results)} files")


def example_quick_analysis():
    """
    Example: Quick temperature analysis
    """
    print("\n" + "="*60)
    print("EXAMPLE 4: Quick Temperature Analysis")
    print("="*60)
    
    analyzer = ASOSAnalyzer()
    
    # Load data for all stations
    for station_id in ['KJFK', 'KLGA', 'KNYC']:
        df = analyzer.load_station_data(station_id)
        
        if df is not None and len(df) > 0:
            temp_mean = df['temp_c'].mean()
            temp_min = df['temp_c'].min()
            temp_max = df['temp_c'].max()
            
            print(f"\n{station_id}:")
            print(f"  Mean Temperature: {temp_mean:.1f}°C")
            print(f"  Min Temperature:  {temp_min:.1f}°C")
            print(f"  Max Temperature:  {temp_max:.1f}°C")
            print(f"  Total Records:    {len(df):,}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("NOAA ASOS MODULE - USAGE EXAMPLES")
    print("="*80)
    
    print("\nNote: These examples assume you have already:")
    print("  1. Configured the module (see config.py)")
    print("  2. Have network access to download data")
    print("\nTo run a specific example, uncomment the function call below.\n")
    
    # Uncomment the examples you want to run:
    
    # example_fetch_single_month()
    # example_process_and_analyze()
    # example_custom_date_range()
    # example_quick_analysis()
    
    print("\nTo run the full pipeline, use: python main.py")
    print("For help: python main.py --help")
