"""
Weather Underground PWS Setup Helper
Run this first to verify your installation and configuration
"""

import sys
import os

print("=" * 70)
print("WEATHER UNDERGROUND PWS SYSTEM SETUP")
print("=" * 70)

# Check Python version
print("\n1. Checking Python version...")
if sys.version_info < (3, 6):
    print("❌ Python 3.6 or higher required")
    print(f"   Current version: {sys.version}")
    sys.exit(1)
else:
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")

# Check required packages
print("\n2. Checking required packages...")

required_packages = {
    'requests': 'Required for API calls',
}

optional_packages = {
    'matplotlib': 'Required for visualizations',
}

missing_required = []
missing_optional = []

for package, description in required_packages.items():
    try:
        __import__(package)
        print(f"✓ {package} - {description}")
    except ImportError:
        print(f"❌ {package} - {description}")
        missing_required.append(package)

for package, description in optional_packages.items():
    try:
        __import__(package)
        print(f"✓ {package} - {description}")
    except ImportError:
        print(f"⚠️  {package} - {description} (optional)")
        missing_optional.append(package)

if missing_required:
    print("\n❌ MISSING REQUIRED PACKAGES")
    print("   Install with:")
    print(f"   pip install {' '.join(missing_required)}")
    sys.exit(1)

if missing_optional:
    print("\n⚠️  MISSING OPTIONAL PACKAGES")
    print("   For full functionality, install with:")
    print(f"   pip install {' '.join(missing_optional)}")

# Check file structure
print("\n3. Checking file structure...")

required_files = [
    'wu_functions.py',
    'main.py',
    'data_analysis.py',
    'analyze.py',
]

optional_files = [
    'visualize.py',
    'README.md',
    'COMPLETE_GUIDE.md.md',
]

all_files_present = True

for file in required_files:
    if os.path.exists(file):
        print(f"✓ {file}")
    else:
        print(f"❌ {file} - MISSING!")
        all_files_present = False

for file in optional_files:
    if os.path.exists(file):
        print(f"✓ {file}")
    else:
        print(f"⚠️  {file} - Not found (optional)")

if not all_files_present:
    print("\n❌ Some required files are missing!")
    print("   Make sure all Python scripts are in the same directory")
    sys.exit(1)

# Create output directory
print("\n4. Creating output directories...")
directories = ['output', 'output/plots']

for directory in directories:
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"✓ Created: {directory}/")
    else:
        print(f"✓ Exists: {directory}/")

# Test API configuration
print("\n5. Testing API configuration...")
print("   Opening main.py to check configuration...")

try:
    with open('main.py', 'r') as f:
        content = f.read()

        # Check for API key
        if "API_KEY = 'your_api_key_here'" in content or "API_KEY = ''" in content:
            print("⚠️  API_KEY needs to be configured in main.py")
            print("   Get your key from: https://www.wunderground.com/member/api-keys")
        else:
            print("✓ API_KEY appears to be configured")

        # Check for station IDs
        if "STATION_IDS = []" in content:
            print("⚠️  STATION_IDS list is empty in main.py")
            print("   Add your station IDs from: https://www.wunderground.com/wundermap")
        else:
            print("✓ STATION_IDS appears to be configured")

except Exception as e:
    print(f"❌ Error reading main.py: {e}")

# Quick connection test
print("\n6. Testing Weather Underground API connection...")
response = input("   Do you want to test your API connection now? (y/n): ").lower()

if response == 'y':
    api_key = input("   Enter your API key: ").strip()
    station_id = input("   Enter a station ID (e.g., KNYNEWYO1127): ").strip()

    if api_key and station_id:
        try:
            import requests

            url = "https://api.weather.com/v2/pws/observations/current"
            params = {
                'stationId': station_id,
                'format': 'json',
                'units': 'e',
                'apiKey': api_key
            }

            print("   Testing API call...")
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'observations' in data and len(data['observations']) > 0:
                    obs = data['observations'][0]
                    print("\n   ✓ SUCCESS! API connection working!")
                    print(f"   Station: {obs.get('stationID')}")
                    print(f"   Location: {obs.get('neighborhood')}")
                    print(f"   Temperature: {obs.get('imperial', {}).get('temp')}°F")
                else:
                    print("\n   ⚠️  API responded but no data found")
                    print("   Check if the station ID is correct")
            elif response.status_code == 401:
                print("\n   ❌ Authentication failed - check your API key")
            elif response.status_code == 404:
                print("\n   ❌ Station not found - check the station ID")
            else:
                print(f"\n   ❌ API error: {response.status_code}")
                print(f"   {response.text}")

        except Exception as e:
            print(f"\n   ❌ Connection error: {e}")
    else:
        print("   ⚠️  API key or station ID not provided")

# Summary
print("\n" + "=" * 70)
print("SETUP SUMMARY")
print("=" * 70)

if missing_required:
    print("\n❌ SETUP INCOMPLETE")
    print(f"   Install missing packages: pip install {' '.join(missing_required)}")
elif not all_files_present:
    print("\n❌ SETUP INCOMPLETE")
    print("   Some required files are missing")
else:
    print("\n✅ SETUP COMPLETE!")
    print("\nNext steps:")
    print("1. Configure your API_KEY and STATION_IDS in main.py")
    print("2. Run: python main.py")
    print("3. Run: python analyze.py")
    print("4. Run: python visualize.py (if matplotlib installed)")
    print("\nFor detailed instructions, see COMPLETE_GUIDE.ymd")

print("\n" + "=" * 70)
print("Quick Reference:")
print("  • API Keys: https://www.wunderground.com/member/api-keys")
print("  • Find Stations: https://www.wunderground.com/wundermap")
print("  • Documentation: See COMPLETE_GUIDE.md")
print("=" * 70)