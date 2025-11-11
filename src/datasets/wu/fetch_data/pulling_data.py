# No special packages needed - just requests (usually pre-installed)
# If requests is not installed: pip install requests
import requests
from datetime import datetime, timedelta
import json

# --- CREDENTIALS ---
MY_API_KEY = ' ' # REPLACE with your API key#
MY_STATION_ID = "KNYNEWYO1127" #"KNYNEWYO2197" #"KNYNEWYO1127" # "KNYNEWYO2197"

# Base URL for Weather Underground PWS API
BASE_URL = "https://api.weather.com/v2/pws"


def get_current_conditions():
    """Fetch and display current weather conditions"""
    print("=== CURRENT CONDITIONS ===")

    url = f"{BASE_URL}/observations/current"
    params = {
        'stationId': MY_STATION_ID,
        'format': 'json',
        'units': 'e',  # 'e' for English units, 'm' for metric
        'apiKey': MY_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'observations' in data and len(data['observations']) > 0:
            obs = data['observations'][0]

            print(f"Station: {obs.get('stationID', 'N/A')}")
            print(f"Time: {obs.get('obsTimeLocal', 'N/A')}")
            print(f"Neighborhood: {obs.get('neighborhood', 'N/A')}")

            # Imperial measurements
            imperial = obs.get('imperial', {})
            print(f"Temperature: {imperial.get('temp', 'N/A')}°F")
            print(f"Heat Index: {imperial.get('heatIndex', 'N/A')}°F")
            print(f"Dew Point: {imperial.get('dewpt', 'N/A')}°F")
            print(f"Wind Chill: {imperial.get('windChill', 'N/A')}°F")
            print(f"Wind Speed: {imperial.get('windSpeed', 'N/A')} mph")
            print(f"Wind Gust: {imperial.get('windGust', 'N/A')} mph")
            print(f"Pressure: {imperial.get('pressure', 'N/A')} in")
            print(f"Precipitation Rate: {imperial.get('precipRate', 'N/A')} in/hr")
            print(f"Precipitation Total: {imperial.get('precipTotal', 'N/A')} in")

            # Other measurements
            print(f"Humidity: {obs.get('humidity', 'N/A')}%")
            print(f"Wind Direction: {obs.get('winddir', 'N/A')}°")
            print(f"UV Index: {obs.get('uv', 'N/A')}")
            print(f"Solar Radiation: {obs.get('solarRadiation', 'N/A')} W/m²")

            return data
        else:
            print("No observations found")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching current conditions: {e}")
        return None


def get_hourly_history(num_days=1):
    """Fetch hourly historical observations"""
    print(f"\n=== HOURLY HISTORY (Last {num_days} day(s)) ===")

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=num_days)

    url = f"{BASE_URL}/observations/hourly/7day"
    params = {
        'stationId': MY_STATION_ID,
        'format': 'json',
        'units': 'e',
        'apiKey': MY_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'observations' in data:
            observations = data['observations']
            print(f"Total observations: {len(observations)}")

            # Filter by date range
            filtered_obs = []
            for obs in observations:
                obs_time = datetime.strptime(obs['obsTimeLocal'][:19], '%Y-%m-%d %H:%M:%S')
                if start_date <= obs_time <= end_date:
                    filtered_obs.append(obs)

            print(f"Observations in last {num_days} day(s): {len(filtered_obs)}")

            # Show first 5 observations
            print("\nFirst 5 observations:")
            for obs in filtered_obs[:5]:
                imperial = obs.get('imperial', {})
                print(f"\n  Time: {obs.get('obsTimeLocal', 'N/A')}")
                print(f"    Temp: {imperial.get('temp', 'N/A')}°F")
                print(f"    Humidity: {obs.get('humidity', 'N/A')}%")
                print(f"    Pressure: {imperial.get('pressure', 'N/A')} in")
                print(f"    Wind: {imperial.get('windSpeed', 'N/A')} mph")

            if len(filtered_obs) > 5:
                print(f"\n  ... and {len(filtered_obs) - 5} more observations")

            return data
        else:
            print("No observations found")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching hourly history: {e}")
        return None


def get_daily_summary():
    """Fetch daily summary (7 days)"""
    print("\n=== DAILY SUMMARY (Last 7 days) ===")

    url = f"{BASE_URL}/dailysummary/7day"
    params = {
        'stationId': MY_STATION_ID,
        'format': 'json',
        'units': 'e',
        'apiKey': MY_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'summaries' in data:
            for summary in data['summaries']:
                imperial = summary.get('imperial', {})
                print(f"\nDate: {summary.get('obsTimeLocal', 'N/A')[:10]}")
                print(f"  High: {imperial.get('tempHigh', 'N/A')}°F")
                print(f"  Low: {imperial.get('tempLow', 'N/A')}°F")
                print(f"  Avg: {imperial.get('tempAvg', 'N/A')}°F")
                print(f"  Precipitation: {imperial.get('precipTotal', 'N/A')} in")
                print(f"  Avg Wind: {imperial.get('windspeedAvg', 'N/A')} mph")

            return data
        else:
            print("No summary data found")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching daily summary: {e}")
        return None


def save_to_json(data, filename):
    """Save data to a JSON file"""
    if data:
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\nData saved to {filename}")
        except Exception as e:
            print(f"Error saving to file: {e}")


def main():
    print("Weather Underground PWS Data Fetcher")
    print("=" * 60)
    print(f"Station ID: {MY_STATION_ID}")
    print("=" * 60)

    # Fetch current conditions
    current = get_current_conditions()
    if current:
        save_to_json(current, 'current_conditions.json')

    # Fetch hourly history
    hourly = get_hourly_history(num_days=2)
    if hourly:
        save_to_json(hourly, 'hourly_history.json')

    # Fetch daily summary
    daily = get_daily_summary()
    if daily:
        save_to_json(daily, 'daily_summary.json')

    print("\n" + "=" * 60)
    print("DATA FETCH COMPLETE")
    print("=" * 60)
    print("\nTroubleshooting tips:")
    print("1. Verify your API key at: https://www.wunderground.com/member/api-keys")
    print("2. Check station status at: https://www.wunderground.com/dashboard/pws/" + MY_STATION_ID)
    print("3. Make sure station is actively reporting data")
    print("4. API key must be registered for PWS API access")


if __name__ == "__main__":
    main()