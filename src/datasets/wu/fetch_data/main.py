"""
Weather Underground PWS Data Fetcher - Main Script
Configure your settings and run to fetch weather data
"""

from datetime import datetime, timedelta
from wu_functions import (
    fetch_all_data,
    save_to_json,
    print_available_parameters,
    validate_date_range,
    print_current_summary
)

# ============================================================================
# CONFIGURATION - EDIT THESE SETTINGS
# ============================================================================

# Your Weather Underground API Key
API_KEY = 'your_api_key_here'  # Get from: https://www.wunderground.com/member/api-keys

# List of station IDs to fetch data from
STATION_IDS = [
    "KNYNEWYO1805"
    # 'KNYNEWYO1127',
    # Add more stations here:
]

# Date range for historical data
START_DATE = datetime(2025, 9, 24)  # Year, Month, Day
END_DATE = datetime(2025, 9, 27)    # Year, Month, Day

# Units: 'e' for English (°F, mph, in), 'm' for metric (°C, km/h, mm)
UNITS = 'm'

# Output directory for JSON files
OUTPUT_DIR = 'output'

# Options for what to fetch
FETCH_OPTIONS = {
    'rapid': True,
    'current': False,
    'hourly': False,
    'daily': False,
}

# Options for output
OUTPUT_OPTIONS = {
    'save_combined': True,      # Save all data in one file
    'save_individual': True,    # Save each station separately
    'save_by_type': True,       # Save by data type (current, hourly, daily, rapid)
    'print_summary': True,      # Print summary to console
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""

    print("=" * 70)
    print("WEATHER UNDERGROUND PWS DATA FETCHER")
    print("=" * 70)

    # Print configuration
    print("\n📋 CONFIGURATION:")
    print(f"  API Key: {API_KEY[:4]}...{API_KEY[-4:]}")
    print(f"  Stations: {len(STATION_IDS)} station(s)")
    for sid in STATION_IDS:
        print(f"    • {sid}")
    print(f"  Date Range: {START_DATE.date()} to {END_DATE.date()}")
    print(f"  Units: {'English (°F, mph, in)' if UNITS == 'e' else 'Metric (°C, km/h, mm)'}")
    print(f"  Output Directory: {OUTPUT_DIR}/")

    # Show available parameters
    if OUTPUT_OPTIONS.get('print_summary'):
        response = input("\n❓ Show all available parameters? (y/n): ").lower()
        if response == 'y':
            print_available_parameters()

    # Validate date range
    start, end = validate_date_range(START_DATE, END_DATE)
    days = (end - start).days

    print(f"\n📅 Fetching data for {days} day(s)")
    print(f"  Start: {start}")
    print(f"  End: {end}")

    # Confirm before proceeding
    response = input("\n▶ Proceed with data fetch? (y/n): ").lower()
    if response != 'y':
        print("❌ Operation cancelled")
        return

    # Fetch all data
    print("\n🌦 FETCHING DATA...")
    all_data = fetch_all_data(API_KEY, STATION_IDS, start, end, UNITS, FETCH_OPTIONS)

    if not all_data:
        print("\n❌ No data fetched")
        return

    # Print summaries
    if OUTPUT_OPTIONS.get('print_summary'):
        print("\n" + "=" * 70)
        print("DATA SUMMARY")
        print("=" * 70)

        for station_id, station_data in all_data.items():
            rapid = station_data.get('rapid') or {}
            rapid_count = len(rapid.get('observations', [])) if rapid else 0

            hourly = station_data.get('hourly') or {}
            hourly_count = len(hourly.get('observations', [])) if hourly else 0

            daily = station_data.get('daily') or {}
            daily_count = len(daily.get('summaries', [])) if daily else 0

            print(f"\n  📍 {station_id}:")
            print(f"    • Current: {'✓' if station_data.get('current') else '✗'}")
            print(f"    • Rapid: {rapid_count} observations" if rapid_count > 0 else "    • Rapid: ✗")
            print(f"    • Hourly: {hourly_count} observations" if hourly_count > 0 else "    • Hourly: ✗")
            print(f"    • Daily: {daily_count} summaries" if daily_count > 0 else "    • Daily: ✗")

            if station_data.get('current'):
                print_current_summary(station_data['current'], UNITS)

    # Save data
    print("\n" + "=" * 70)
    print("SAVING DATA")
    print("=" * 70)

    # Create filename with date range
    date_str = f"{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}"
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    saved_files = []

    # Save combined file (all stations, all data)
    if OUTPUT_OPTIONS.get('save_combined'):
        filename = f'weather_all_stations_{date_str}.json'
        if save_to_json(all_data, filename, OUTPUT_DIR):
            saved_files.append(filename)

    # Save individual station files
    if OUTPUT_OPTIONS.get('save_individual'):
        for station_id, station_data in all_data.items():
            filename = f'weather_{station_id}_{date_str}.json'
            if save_to_json(station_data, filename, OUTPUT_DIR):
                saved_files.append(filename)

    # Save by data type (only if data exists)
    if OUTPUT_OPTIONS.get('save_by_type'):
        # Current conditions
        current_data = {sid: data['current'] for sid, data in all_data.items()
                        if data.get('current')}
        if current_data:
            filename = f'current_{date_str}.json'
            if save_to_json(current_data, filename, OUTPUT_DIR):
                saved_files.append(filename)

        # Rapid history
        rapid_data = {sid: data['rapid'] for sid, data in all_data.items()
                      if data.get('rapid')}
        if rapid_data:
            filename = f'rapid_{date_str}.json'
            if save_to_json(rapid_data, filename, OUTPUT_DIR):
                saved_files.append(filename)

        # Hourly data
        hourly_data = {sid: data['hourly'] for sid, data in all_data.items()
                       if data.get('hourly')}
        if hourly_data:
            filename = f'hourly_{date_str}.json'
            if save_to_json(hourly_data, filename, OUTPUT_DIR):
                saved_files.append(filename)

        # Daily data
        daily_data = {sid: data['daily'] for sid, data in all_data.items()
                      if data.get('daily')}
        if daily_data:
            filename = f'daily_{date_str}.json'
            if save_to_json(daily_data, filename, OUTPUT_DIR):
                saved_files.append(filename)

    # Final summary
    print("\n" + "=" * 70)
    print("✅ DATA FETCH COMPLETE")
    print("=" * 70)

    if saved_files:
        print(f"\n📁 {len(saved_files)} file(s) saved to: {OUTPUT_DIR}/")
        for filename in saved_files:
            print(f"  • {filename}")
    else:
        print("\n⚠️  No files saved (no data to save)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()