"""
Weather Data Visualization
Create plots and charts from weather data
Requires: matplotlib (pip install matplotlib)
"""

import os
from datetime import datetime
from data_analysis import load_json_file, get_latest_file, extract_temperature_series

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("⚠️  Warning: matplotlib not installed")
    print("   Install with: pip install matplotlib")

# ============================================================================
# CONFIGURATION
# ============================================================================

INPUT_DIR = 'output'
OUTPUT_DIR = 'plots'
UNITS = 'e'

# Plot settings
PLOT_STYLE = 'seaborn-v0_8-darkgrid'  # Try: 'default', 'seaborn-v0_8-darkgrid', 'ggplot'
FIGURE_SIZE = (12, 6)
DPI = 100


# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def setup_plot_style():
    """Setup matplotlib style"""
    if not MATPLOTLIB_AVAILABLE:
        return False

    try:
        plt.style.use(PLOT_STYLE)
    except:
        plt.style.use('default')

    return True


def plot_temperature_timeline(data, station_id, units='e', save=True):
    """Plot temperature over time for a station"""
    if not MATPLOTLIB_AVAILABLE:
        print("❌ matplotlib not installed")
        return None

    temp_series = extract_temperature_series(data, station_id, units)

    if not temp_series:
        print(f"❌ No temperature data for {station_id}")
        return None

    dates = [t[0] for t in temp_series]
    temps = [t[1] for t in temp_series]

    fig, ax = plt.subplots(figsize=FIGURE_SIZE, dpi=DPI)

    ax.plot(dates, temps, linewidth=2, color='#e74c3c', marker='o',
            markersize=3, alpha=0.7)

    ax.set_xlabel('Date/Time', fontsize=12, fontweight='bold')
    ax.set_ylabel(f"Temperature (°{'F' if units == 'e' else 'C'})",
                  fontsize=12, fontweight='bold')
    ax.set_title(f'Temperature Timeline - {station_id}',
                 fontsize=14, fontweight='bold', pad=20)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.xticks(rotation=45, ha='right')

    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    if save:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = f'{station_id}_temperature_timeline.png'
        filepath = os.path.join(OUTPUT_DIR, filename)
        plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
        print(f"✓ Saved: {filename}")

    return fig


def plot_multi_parameter(data, station_id, units='e', save=True):
    """Plot multiple parameters in subplots"""
    if not MATPLOTLIB_AVAILABLE:
        print("❌ matplotlib not installed")
        return None

    if station_id not in data:
        print(f"❌ Station {station_id} not found")
        return None

    hourly = data[station_id].get('hourly', {})
    observations = hourly.get('observations', [])

    if not observations:
        print(f"❌ No observations for {station_id}")
        return None

    unit_type = 'imperial' if units == 'e' else 'metric'

    # Extract data
    dates = []
    temps = []
    humidity = []
    pressure = []
    wind = []

    for obs in observations:
        time_str = obs.get('obsTimeLocal', '')
        if time_str:
            dt = datetime.strptime(time_str[:19], '%Y-%m-%d %H:%M:%S')
            dates.append(dt)

            measurements = obs.get(unit_type, {})
            temps.append(measurements.get('temp'))
            humidity.append(obs.get('humidity'))
            pressure.append(measurements.get('pressure'))
            wind.append(measurements.get('windSpeed'))

    # Create subplots
    fig, axes = plt.subplots(4, 1, figsize=(12, 10), dpi=DPI)
    fig.suptitle(f'Weather Data - {station_id}', fontsize=16, fontweight='bold', y=0.995)

    # Temperature
    axes[0].plot(dates, temps, color='#e74c3c', linewidth=2)
    axes[0].set_ylabel(f"Temp (°{'F' if units == 'e' else 'C'})", fontweight='bold')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_title('Temperature', loc='left', fontsize=11, fontweight='bold')

    # Humidity
    axes[1].plot(dates, humidity, color='#3498db', linewidth=2)
    axes[1].set_ylabel('Humidity (%)', fontweight='bold')
    axes[1].grid(True, alpha=0.3)
    axes[1].set_title('Humidity', loc='left', fontsize=11, fontweight='bold')

    # Pressure
    axes[2].plot(dates, pressure, color='#2ecc71', linewidth=2)
    axes[2].set_ylabel(f"Pressure ({'in' if units == 'e' else 'mb'})", fontweight='bold')
    axes[2].grid(True, alpha=0.3)
    axes[2].set_title('Pressure', loc='left', fontsize=11, fontweight='bold')

    # Wind Speed
    axes[3].plot(dates, wind, color='#9b59b6', linewidth=2)
    axes[3].set_ylabel(f"Wind ({'mph' if units == 'e' else 'km/h'})", fontweight='bold')
    axes[3].set_xlabel('Date/Time', fontweight='bold')
    axes[3].grid(True, alpha=0.3)
    axes[3].set_title('Wind Speed', loc='left', fontsize=11, fontweight='bold')

    # Format x-axis for all subplots
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()

    if save:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = f'{station_id}_multi_parameter.png'
        filepath = os.path.join(OUTPUT_DIR, filename)
        plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
        print(f"✓ Saved: {filename}")

    return fig


def plot_station_comparison(data, parameter='temp', units='e', save=True):
    """Compare a parameter across multiple stations"""
    if not MATPLOTLIB_AVAILABLE:
        print("❌ matplotlib not installed")
        return None

    stations = list(data.keys())

    if len(stations) < 2:
        print("❌ Need at least 2 stations for comparison")
        return None

    fig, ax = plt.subplots(figsize=FIGURE_SIZE, dpi=DPI)

    unit_type = 'imperial' if units == 'e' else 'metric'
    colors = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']

    for i, station_id in enumerate(stations[:6]):  # Limit to 6 stations
        hourly = data[station_id].get('hourly', {})
        observations = hourly.get('observations', [])

        dates = []
        values = []

        for obs in observations:
            time_str = obs.get('obsTimeLocal', '')
            if time_str:
                dt = datetime.strptime(time_str[:19], '%Y-%m-%d %H:%M:%S')
                dates.append(dt)

                if parameter in ['humidity', 'uv', 'winddir', 'solarRadiation']:
                    value = obs.get(parameter)
                else:
                    measurements = obs.get(unit_type, {})
                    value = measurements.get(parameter)

                values.append(value)

        color = colors[i % len(colors)]
        ax.plot(dates, values, linewidth=2, label=station_id,
                color=color, alpha=0.7)

    # Labels and formatting
    param_labels = {
        'temp': f"Temperature (°{'F' if units == 'e' else 'C'})",
        'humidity': 'Humidity (%)',
        'windSpeed': f"Wind Speed ({'mph' if units == 'e' else 'km/h'})",
        'pressure': f"Pressure ({'in' if units == 'e' else 'mb'})",
        'dewpt': f"Dew Point (°{'F' if units == 'e' else 'C'})",
    }

    ylabel = param_labels.get(parameter, parameter.title())
    ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
    ax.set_xlabel('Date/Time', fontsize=12, fontweight='bold')
    ax.set_title(f'{parameter.title()} Comparison Across Stations',
                 fontsize=14, fontweight='bold', pad=20)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.xticks(rotation=45, ha='right')

    ax.legend(loc='best', framealpha=0.9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    if save:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = f'comparison_{parameter}.png'
        filepath = os.path.join(OUTPUT_DIR, filename)
        plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
        print(f"✓ Saved: {filename}")

    return fig


def plot_daily_summary(data, station_id, units='e', save=True):
    """Plot daily high/low temperatures"""
    if not MATPLOTLIB_AVAILABLE:
        print("❌ matplotlib not installed")
        return None

    if station_id not in data:
        print(f"❌ Station {station_id} not found")
        return None

    daily = data[station_id].get('daily', {})
    summaries = daily.get('summaries', [])

    if not summaries:
        print(f"❌ No daily summary for {station_id}")
        return None

    unit_type = 'imperial' if units == 'e' else 'metric'

    dates = []
    highs = []
    lows = []
    avgs = []

    for summary in summaries:
        date_str = summary.get('obsTimeLocal', '')[:10]
        if date_str:
            dates.append(datetime.strptime(date_str, '%Y-%m-%d'))

            measurements = summary.get(unit_type, {})
            highs.append(measurements.get('tempHigh'))
            lows.append(measurements.get('tempLow'))
            avgs.append(measurements.get('tempAvg'))

    fig, ax = plt.subplots(figsize=FIGURE_SIZE, dpi=DPI)

    # Plot high and low temps
    ax.plot(dates, highs, 'o-', color='#e74c3c', linewidth=2.5,
            markersize=8, label='High', alpha=0.8)
    ax.plot(dates, lows, 'o-', color='#3498db', linewidth=2.5,
            markersize=8, label='Low', alpha=0.8)
    ax.plot(dates, avgs, 's--', color='#f39c12', linewidth=2,
            markersize=6, label='Average', alpha=0.7)

    # Fill between high and low
    ax.fill_between(dates, highs, lows, alpha=0.2, color='gray')

    ax.set_xlabel('Date', fontsize=12, fontweight='bold')
    ax.set_ylabel(f"Temperature (°{'F' if units == 'e' else 'C'})",
                  fontsize=12, fontweight='bold')
    ax.set_title(f'Daily Temperature Summary - {station_id}',
                 fontsize=14, fontweight='bold', pad=20)

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.xticks(rotation=45, ha='right')

    ax.legend(loc='best', framealpha=0.9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    if save:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = f'{station_id}_daily_summary.png'
        filepath = os.path.join(OUTPUT_DIR, filename)
        plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
        print(f"✓ Saved: {filename}")

    return fig


def plot_wind_rose(data, station_id, save=True):
    """Create a wind rose diagram"""
    if not MATPLOTLIB_AVAILABLE:
        print("❌ matplotlib not installed")
        return None

    if station_id not in data:
        print(f"❌ Station {station_id} not found")
        return None

    hourly = data[station_id].get('hourly', {})
    observations = hourly.get('observations', [])

    if not observations:
        print(f"❌ No observations for {station_id}")
        return None

    # Extract wind data
    wind_dirs = []
    wind_speeds = []

    for obs in observations:
        wind_dir = obs.get('winddir')
        wind_speed = obs.get('imperial', {}).get('windSpeed') or obs.get('metric', {}).get('windSpeed')

        if wind_dir is not None and wind_speed is not None and wind_speed > 0:
            wind_dirs.append(wind_dir)
            wind_speeds.append(wind_speed)

    if not wind_dirs:
        print(f"❌ No wind data for {station_id}")
        return None

    # Create polar plot
    fig = plt.figure(figsize=(10, 10), dpi=DPI)
    ax = fig.add_subplot(111, projection='polar')

    # Convert degrees to radians
    import numpy as np
    theta = np.radians(wind_dirs)

    # Create scatter plot with color based on speed
    scatter = ax.scatter(theta, wind_speeds, c=wind_speeds,
                         cmap='YlOrRd', alpha=0.6, s=50)

    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_title(f'Wind Rose - {station_id}',
                 fontsize=14, fontweight='bold', pad=20)

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax, pad=0.1)
    cbar.set_label('Wind Speed (mph/km/h)', fontweight='bold')

    if save:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        filename = f'{station_id}_wind_rose.png'
        filepath = os.path.join(OUTPUT_DIR, filename)
        plt.savefig(filepath, dpi=DPI, bbox_inches='tight')
        print(f"✓ Saved: {filename}")

    return fig


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Generate all visualizations"""

    if not MATPLOTLIB_AVAILABLE:
        print("❌ matplotlib is required for visualizations")
        print("   Install with: pip install matplotlib")
        return

    print("=" * 70)
    print("WEATHER DATA VISUALIZATION")
    print("=" * 70)

    setup_plot_style()

    # Find data file
    print(f"\n📂 Looking for data in: {INPUT_DIR}")
    data_file = get_latest_file(INPUT_DIR, 'weather_data_all_stations')

    if not data_file:
        data_file = get_latest_file(INPUT_DIR, 'hourly_history')

    if not data_file:
        print("❌ No data files found!")
        return

    print(f"✓ Found: {os.path.basename(data_file)}")

    # Load data
    print("\n📊 Loading data...")
    data = load_json_file(data_file)

    if not data:
        print("❌ Failed to load data")
        return

    stations = list(data.keys())
    print(f"✓ Found {len(stations)} station(s)")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"\n🎨 Generating visualizations...")
    print(f"   Output directory: {OUTPUT_DIR}/")

    # Generate plots for each station
    for station in stations:
        print(f"\n📍 {station}:")

        # Temperature timeline
        plot_temperature_timeline(data, station, UNITS)

        # Multi-parameter plot
        plot_multi_parameter(data, station, UNITS)

        # Daily summary
        plot_daily_summary(data, station, UNITS)

        # Wind rose
        plot_wind_rose(data, station)

    # Station comparison (if multiple stations)
    if len(stations) > 1:
        print(f"\n🔄 Generating comparison plots...")
        plot_station_comparison(data, 'temp', UNITS)
        plot_station_comparison(data, 'humidity', UNITS)
        plot_station_comparison(data, 'windSpeed', UNITS)

    print("\n" + "=" * 70)
    print("✅ VISUALIZATION COMPLETE")
    print("=" * 70)
    print(f"\n📁 All plots saved to: {OUTPUT_DIR}/")

    # List generated files
    plot_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.png')]
    print(f"\n📊 Generated {len(plot_files)} plots:")
    for f in sorted(plot_files):
        print(f"  • {f}")


if __name__ == "__main__":
    main()