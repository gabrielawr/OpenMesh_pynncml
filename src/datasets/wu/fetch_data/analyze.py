"""
Weather Data Analysis Runner
Load and analyze fetched weather data
"""

import os
from data_analysis import (
    load_json_file,
    get_latest_file,
    print_summary_report,
    calculate_statistics,
    compare_stations,
    find_extremes,
    export_to_csv,
    extract_temperature_series
)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Input settings
INPUT_DIR = 'output'
UNITS = 'e'  # 'e' for English, 'm' for metric

# Analysis options
ANALYSIS_OPTIONS = {
    'summary_report': True,  # Print detailed summary
    'station_comparison': True,  # Compare across stations
    'export_csv': True,  # Export to CSV
    'temperature_analysis': True,  # Temperature-specific analysis
}

# Stations to analyze (empty list = analyze all)
STATIONS_TO_ANALYZE = [
    # Leave empty to analyze all stations in the data file
    # Or specify: ['KNYNEWYO1127', 'KNYNEWYO2197']
]


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main analysis execution"""

    print("=" * 70)
    print("WEATHER DATA ANALYSIS")
    print("=" * 70)

    # Find the latest data file
    print(f"\n📂 Looking for data in: {INPUT_DIR}")

    # Look for combined data file first
    data_file = get_latest_file(INPUT_DIR, 'weather_data_all_stations')

    if not data_file:
        # Look for hourly history file
        data_file = get_latest_file(INPUT_DIR, 'hourly_history')

    if not data_file:
        print("❌ No data files found!")
        print("   Run main.py first to fetch data")
        return

    print(f"✓ Found data file: {os.path.basename(data_file)}")

    # Load data
    print("\n📊 Loading data...")
    data = load_json_file(data_file)

    if not data:
        print("❌ Failed to load data")
        return

    # Determine stations to analyze
    if STATIONS_TO_ANALYZE:
        stations = [s for s in STATIONS_TO_ANALYZE if s in data]
    else:
        stations = list(data.keys())

    if not stations:
        print("❌ No valid stations found in data")
        return

    print(f"✓ Found {len(stations)} station(s) to analyze:")
    for station in stations:
        print(f"  • {station}")

    # ========================================================================
    # SUMMARY REPORTS
    # ========================================================================

    if ANALYSIS_OPTIONS.get('summary_report'):
        for station in stations:
            print_summary_report(data, station, UNITS)

    # ========================================================================
    # STATION COMPARISON
    # ========================================================================

    if ANALYSIS_OPTIONS.get('station_comparison') and len(stations) > 1:
        print("\n" + "=" * 70)
        print("STATION COMPARISON")
        print("=" * 70)

        # Compare temperatures
        print("\n🌡️  TEMPERATURE COMPARISON")
        temp_comparison = compare_stations(data, 'temp', UNITS)

        print(f"\n{'Station':<20} {'Min':>8} {'Max':>8} {'Avg':>8} {'Unit'}")
        print("-" * 50)
        for station_id, stats in temp_comparison.items():
            unit = '°F' if UNITS == 'e' else '°C'
            print(f"{station_id:<20} {stats['min']:>8.1f} {stats['max']:>8.1f} "
                  f"{stats['mean']:>8.1f} {unit}")

        # Compare humidity
        print("\n💧 HUMIDITY COMPARISON")
        humidity_comparison = compare_stations(data, 'humidity', UNITS)

        print(f"\n{'Station':<20} {'Min':>8} {'Max':>8} {'Avg':>8}")
        print("-" * 50)
        for station_id, stats in humidity_comparison.items():
            print(f"{station_id:<20} {stats['min']:>8.0f}% {stats['max']:>8.0f}% "
                  f"{stats['mean']:>8.1f}%")

        # Compare wind
        print("\n💨 WIND SPEED COMPARISON")
        wind_comparison = compare_stations(data, 'windSpeed', UNITS)

        print(f"\n{'Station':<20} {'Min':>8} {'Max':>8} {'Avg':>8} {'Unit'}")
        print("-" * 50)
        for station_id, stats in wind_comparison.items():
            unit = 'mph' if UNITS == 'e' else 'km/h'
            print(f"{station_id:<20} {stats['min']:>8.1f} {stats['max']:>8.1f} "
                  f"{stats['mean']:>8.1f} {unit}")

    # ========================================================================
    # TEMPERATURE ANALYSIS
    # ========================================================================

    if ANALYSIS_OPTIONS.get('temperature_analysis'):
        print("\n" + "=" * 70)
        print("TEMPERATURE ANALYSIS")
        print("=" * 70)

        for station in stations:
            temp_series = extract_temperature_series(data, station, UNITS)

            if temp_series:
                print(f"\n📈 {station}")
                print(f"  Data points: {len(temp_series)}")
                print(f"  Period: {temp_series[0][0]} to {temp_series[-1][0]}")

                temps = [t[1] for t in temp_series]
                print(f"  Temperature range: {min(temps):.1f}°{'F' if UNITS == 'e' else 'C'} "
                      f"to {max(temps):.1f}°{'F' if UNITS == 'e' else 'C'}")

                # Calculate temperature change
                if len(temp_series) > 1:
                    temp_change = temp_series[-1][1] - temp_series[0][1]
                    hours = (temp_series[-1][0] - temp_series[0][0]).total_seconds() / 3600
                    if hours > 0:
                        rate = temp_change / hours
                        print(f"  Temperature change: {temp_change:+.1f}°{'F' if UNITS == 'e' else 'C'} "
                              f"({rate:+.2f}°/hour)")

    # ========================================================================
    # EXPORT TO CSV
    # ========================================================================

    if ANALYSIS_OPTIONS.get('export_csv'):
        print("\n" + "=" * 70)
        print("EXPORTING TO CSV")
        print("=" * 70)

        for station in stations:
            csv_filename = f"{station}_data.csv"
            csv_path = os.path.join(INPUT_DIR, csv_filename)

            if export_to_csv(data, station, csv_path, UNITS):
                print(f"  {station} → {csv_filename}")

    # ========================================================================
    # SUMMARY
    # ========================================================================

    print("\n" + "=" * 70)
    print("✅ ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\n📁 All files in: {INPUT_DIR}/")

    # List CSV files created
    if ANALYSIS_OPTIONS.get('export_csv'):
        print("\n📄 CSV files created:")
        for station in stations:
            print(f"  • {station}_data.csv")


def interactive_mode():
    """Interactive analysis mode"""

    print("=" * 70)
    print("INTERACTIVE WEATHER DATA ANALYSIS")
    print("=" * 70)

    # Find data file
    data_file = get_latest_file(INPUT_DIR, 'weather_data_all_stations')
    if not data_file:
        data_file = get_latest_file(INPUT_DIR, 'hourly_history')

    if not data_file:
        print("\n❌ No data files found!")
        return

    print(f"\n✓ Loading: {os.path.basename(data_file)}")
    data = load_json_file(data_file)

    if not data:
        print("❌ Failed to load data")
        return

    stations = list(data.keys())
    print(f"\n✓ Found {len(stations)} station(s)")

    while True:
        print("\n" + "=" * 70)
        print("ANALYSIS MENU")
        print("=" * 70)
        print("\n1. View summary report for a station")
        print("2. Compare all stations")
        print("3. Find extreme values")
        print("4. Calculate statistics for a parameter")
        print("5. Export station data to CSV")
        print("6. Exit")

        choice = input("\nSelect option (1-6): ").strip()

        if choice == '1':
            print("\nAvailable stations:")
            for i, station in enumerate(stations, 1):
                print(f"  {i}. {station}")

            idx = input(f"\nSelect station (1-{len(stations)}): ").strip()
            try:
                station = stations[int(idx) - 1]
                print_summary_report(data, station, UNITS)
            except (ValueError, IndexError):
                print("❌ Invalid selection")

        elif choice == '2':
            if len(stations) > 1:
                temp_comp = compare_stations(data, 'temp', UNITS)
                print("\n🌡️  TEMPERATURE COMPARISON")
                for station_id, stats in temp_comp.items():
                    print(f"\n{station_id}:")
                    print(f"  Min: {stats['min']:.1f}°{'F' if UNITS == 'e' else 'C'}")
                    print(f"  Max: {stats['max']:.1f}°{'F' if UNITS == 'e' else 'C'}")
                    print(f"  Avg: {stats['mean']:.1f}°{'F' if UNITS == 'e' else 'C'}")
            else:
                print("❌ Need multiple stations for comparison")

        elif choice == '3':
            print("\nAvailable stations:")
            for i, station in enumerate(stations, 1):
                print(f"  {i}. {station}")

            idx = input(f"\nSelect station (1-{len(stations)}): ").strip()
            try:
                station = stations[int(idx) - 1]
                extremes = find_extremes(data, station, UNITS)

                print(f"\n🏆 EXTREME VALUES for {station}:")
                for key, value in extremes.items():
                    if value:
                        label = key.replace('_', ' ').title()
                        print(f"\n{label}:")
                        print(f"  Value: {value['value']} {value['unit']}")
                        print(f"  Time: {value['time']}")
            except (ValueError, IndexError):
                print("❌ Invalid selection")

        elif choice == '4':
            print("\nAvailable parameters:")
            print("  temp, humidity, windSpeed, pressure, dewpt, precipRate")

            param = input("\nEnter parameter name: ").strip()

            print("\nAvailable stations:")
            for i, station in enumerate(stations, 1):
                print(f"  {i}. {station}")

            idx = input(f"\nSelect station (1-{len(stations)}): ").strip()
            try:
                station = stations[int(idx) - 1]
                stats = calculate_statistics(data, station, param, UNITS)

                if stats:
                    print(f"\n📊 Statistics for {param} at {station}:")
                    print(f"  Count: {stats['count']}")
                    print(f"  Min: {stats['min']:.2f}")
                    print(f"  Max: {stats['max']:.2f}")
                    print(f"  Mean: {stats['mean']:.2f}")
                    print(f"  Median: {stats['median']:.2f}")
                    if 'stdev' in stats:
                        print(f"  Std Dev: {stats['stdev']:.2f}")
                else:
                    print("❌ No data available for this parameter")
            except (ValueError, IndexError):
                print("❌ Invalid selection")

        elif choice == '5':
            print("\nAvailable stations:")
            for i, station in enumerate(stations, 1):
                print(f"  {i}. {station}")

            idx = input(f"\nSelect station (1-{len(stations)}): ").strip()
            try:
                station = stations[int(idx) - 1]
                filename = input("Enter filename (default: station_id_data.csv): ").strip()
                if not filename:
                    filename = f"{station}_data.csv"

                filepath = os.path.join(INPUT_DIR, filename)
                export_to_csv(data, station, filepath, UNITS)
            except (ValueError, IndexError):
                print("❌ Invalid selection")

        elif choice == '6':
            print("\n👋 Goodbye!")
            break

        else:
            print("❌ Invalid option")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        interactive_mode()
    else:
        main()