"""
Create an interactive map of ASOS weather stations using Folium
Location: src/datasets/noaa/meta/map_stations.py
"""

import pandas as pd
import folium
from folium import plugins
import os
from pathlib import Path

def create_stations_map(csv_file=None,  output_file='asos_stations_map.html'):
    """
    Create an interactive Folium map with all ASOS stations.

    Args:
        csv_file: Path to the CSV file with station metadata
        output_file: Output HTML file for the map
    """

    # Read the stations data
    if csv_file is None:
        csv_file = Path(__file__).parent / "asos_stations_all.csv"
    df = pd.read_csv(csv_file)

    # Remove any rows with missing coordinates
    df = df.dropna(subset=['LAT', 'LON'])

    # Create the base map centered on US
    center_lat = df['LAT'].mean()
    center_lon = df['LON'].mean()

    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles='CartoDB positron'  # 'OpenStreetMap'
    )

    # Add different tile layers
    # keep this (light is already base, still fine to keep as a toggle)
    folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)

    # OPTIONAL: keep dark as *optional* only (it won’t be default anymore)
    # folium.TileLayer('CartoDB dark_matter', name='Dark Map').add_to(m)

    # Define NYC target stations for special highlighting
    NYC_STATIONS = ['JFK', 'LGA', 'NYC']

    # Create feature groups for different station types
    nyc_group = folium.FeatureGroup(name='NYC Target Stations')
    ny_group = folium.FeatureGroup(name='NY State Stations')
    other_group = folium.FeatureGroup(name='Other US Stations')

    # Add stations to map
    for idx, row in df.iterrows():
        # Create popup text with station info
        popup_text = f"""
        <b>{row['CALL']}</b><br>
        {row['NAME']}<br>
        State: {row['STATE']}<br>
        Lat: {row['LAT']:.3f}, Lon: {row['LON']:.3f}<br>
        Elevation: {row['ELEV']:.0f} ft / {row['ELEV_M']:.0f} m
        """

        # Determine marker color and group
        if row['CALL'] in NYC_STATIONS:
            # NYC target stations - red markers, larger
            marker = folium.Marker(
                location=[row['LAT'], row['LON']],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=f"{row['CALL']}: {row['NAME']}",
                icon=folium.Icon(color='red', icon='star', prefix='fa')
            )
            marker.add_to(nyc_group)

        elif row['STATE'] == 'NY':
            # Other NY state stations - blue markers
            marker = folium.CircleMarker(
                location=[row['LAT'], row['LON']],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=f"{row['CALL']}: {row['NAME']}",
                radius=6,
                color='blue',
                fill=True,

                fillColor='lightblue',
                fillOpacity=0.7,
                weight=2,
                fill_color='lightblue', fill_opacity=0.7  # for NY group
            )
            marker.add_to(ny_group)

        else:
            # All other stations - small gray markers
            marker = folium.CircleMarker(
                location=[row['LAT'], row['LON']],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=f"{row['CALL']}: {row['NAME']}",
                radius=3,
                color='gray',
                fill=True,
                fillColor='lightgray',
                fillOpacity=0.5,
                weight=1,
                fill_color='lightgray', fill_opacity=0.5  # for Other US
            )
            marker.add_to(other_group)

    # Add groups to map
    other_group.add_to(m)  # Add first (bottom layer)
    ny_group.add_to(m)
    nyc_group.add_to(m)  # Add last (top layer)

    # Add layer control
    folium.LayerControl().add_to(m)

    # Add fullscreen button
    plugins.Fullscreen().add_to(m)

    # Add search functionality for station names
    plugins.Search(
        layer=other_group,
        search_label='NAME',
        search_zoom=10,
        position='topright',
        placeholder='Search stations...'
    ).add_to(m)

    # Add a marker cluster for better performance with many points
    marker_cluster = plugins.MarkerCluster(name='Clustered View', show=False)

    # Add all stations to cluster (optional view)
    for idx, row in df.iterrows():
        folium.Marker(
            location=[row['LAT'], row['LON']],
            popup=f"{row['CALL']}: {row['NAME']}",
            icon=None
        ).add_to(marker_cluster)

    marker_cluster.add_to(m)

    # Create a minimap
    minimap = plugins.MiniMap(toggle_display=True, width=200, height=200)
    m.add_child(minimap)

    # Save the map
    MAPS_DIR = Path(__file__).resolve().parent / "maps"
    output_path = MAPS_DIR / output_file
    m.save(output_path)
    print(f"Map saved to: {output_path}")

    # Print summary
    print(f"Map created: {output_file}")
    print(f"Total stations plotted: {len(df)}")
    print(f"NYC target stations: {len(df[df['CALL'].isin(NYC_STATIONS)])}")
    print(f"NY state stations: {len(df[df['STATE'] == 'NY'])}")
    print(f"\nMap features:")
    print("  - Red stars: NYC target stations (JFK, LGA, NYC)")
    print("  - Blue circles: Other NY state stations")
    print("  - Gray circles: All other US stations")
    print("  - Click stations for details")
    print("  - Use layer control (top right) to toggle station groups")
    print("  - Cluster view available for performance")

    return m


def create_nyc_focused_map(csv_file='asos_stations.csv', output_file='nyc_stations_map.html'):
    """
    Create a zoomed-in map focused on just NYC area stations.
    """

    # Read NYC stations
    df = pd.read_csv(csv_file)

    if len(df) == 0:
        print("No NYC stations found in CSV!")
        return None

    # Center map on NYC area
    center_lat = 40.7128
    center_lon = -74.0060

    # Create map zoomed to NYC area
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles='OpenStreetMap'
    )

    # Add tile layers
    folium.TileLayer('CartoDB positron', name='Light Map').add_to(m)

    # Add NYC boundary (approximate)
    nyc_boundary = [
        [40.917577, -73.700272],  # NE
        [40.917577, -74.259090],  # NW
        [40.477399, -74.259090],  # SW
        [40.477399, -73.700272],  # SE
        [40.917577, -73.700272],  # Close polygon
    ]

    folium.PolyLine(
        nyc_boundary,
        color='green',
        weight=2,
        opacity=0.5,
        fill=True,
        fillOpacity=0.1,
        popup='NYC Approximate Boundary'
    ).add_to(m)

    # Add stations
    for idx, row in df.iterrows():
        popup_text = f"""
        <b>{row['CALL']}</b><br>
        <b>{row['NAME']}</b><br>
        Coordinates: {row['LAT']:.4f}, {row['LON']:.4f}<br>
        Elevation: {row['ELEV']:.0f} ft / {row['ELEV_M']:.0f} m<br>
        Station ID: {row['NCDCID']}
        """

        folium.Marker(
            location=[row['LAT'], row['LON']],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=f"{row['CALL']}: {row['NAME']}",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)

        # Add a circle showing approximate coverage area (10km radius)
        folium.Circle(
            location=[row['LAT'], row['LON']],
            radius=10000,  # 10km in meters
            popup=f"~10km coverage area for {row['CALL']}",
            color='blue',
            fill=True,
            fillOpacity=0.1,
            fill_opacity=0.1
        ).add_to(m)

    # Save map

    MAPS_DIR = Path(__file__).resolve().parent / "maps"
    MAPS_DIR.mkdir(parents=True, exist_ok=True)  # creates meta/maps if missing

    output_path = MAPS_DIR / output_file
    m.save(output_path)
    print(f"Map saved to: {output_path}")

    # print(f"NYC focused map created: {output_file}")
    print(f"Stations plotted: {len(df)}")

    return m


if __name__ == "__main__":
    # Change to the meta directory if needed
    # os.chdir('src/datasets/noaa/meta')


    # Create main map with all stations
    print("Creating main map with all ASOS stations...")
    create_stations_map()

    # Create NYC focused map
    print("\nCreating NYC focused map...")
    create_nyc_focused_map()

    print("\n✓ Maps created successfully!")
    print("Open the HTML files in your browser to view the interactive maps.")