"""
NOAA ASOS Data Analyzer

Basic analysis and visualization of processed ASOS data.
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import logging
from typing import Optional, List
import numpy as np

from config import PROCESSED_DATA_DIR, STATIONS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ASOSAnalyzer:
    """
    Analyzes processed ASOS data
    """
    
    def __init__(self, data_dir: Path = None):
        """
        Initialize the analyzer
        
        Args:
            data_dir: Directory containing processed data files
        """
        self.data_dir = data_dir or PROCESSED_DATA_DIR
        logger.info(f"Initialized analyzer for directory: {self.data_dir}")
    
    def load_station_data(self, station_id: str, 
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Load processed data for a station with optional date filtering
        
        Args:
            station_id: 4-letter station identifier
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            
        Returns:
            DataFrame with station data
        """
        files = sorted(self.data_dir.glob(f"{station_id}_*.csv"))
        
        if not files:
            logger.warning(f"No files found for station {station_id}")
            return None
        
        # Read all files
        dfs = []
        for file in files:
            try:
                df = pd.read_csv(file, parse_dates=['datetime'])
                dfs.append(df)
            except Exception as e:
                logger.error(f"Error reading {file.name}: {e}")
        
        if not dfs:
            return None
        
        # Combine and sort
        combined = pd.concat(dfs, ignore_index=True)
        combined = combined.sort_values('datetime').drop_duplicates(subset=['datetime'])
        
        # Filter by date if specified
        if start_date:
            combined = combined[combined['datetime'] >= start_date]
        if end_date:
            combined = combined[combined['datetime'] <= end_date]
        
        logger.info(f"Loaded {len(combined)} records for {station_id}")
        return combined
    
    def compute_daily_statistics(self, df: pd.DataFrame, station_id: str) -> pd.DataFrame:
        """
        Compute daily statistics from 5-minute data
        
        Args:
            df: DataFrame with 5-minute data
            station_id: Station identifier
            
        Returns:
            DataFrame with daily statistics
        """
        if df is None or len(df) == 0:
            return pd.DataFrame()
        
        # Set datetime as index
        df = df.set_index('datetime')
        
        # Resample to daily
        daily = pd.DataFrame()
        
        # Temperature statistics
        if 'temp_c' in df.columns:
            daily['temp_mean'] = df['temp_c'].resample('D').mean()
            daily['temp_min'] = df['temp_c'].resample('D').min()
            daily['temp_max'] = df['temp_c'].resample('D').max()
        
        # Wind statistics
        if 'wind_speed_ms' in df.columns:
            daily['wind_mean'] = df['wind_speed_ms'].resample('D').mean()
            daily['wind_max'] = df['wind_speed_ms'].resample('D').max()
        
        if 'wind_gust_ms' in df.columns:
            daily['gust_max'] = df['wind_gust_ms'].resample('D').max()
        
        # Pressure statistics
        if 'pressure_hpa' in df.columns:
            daily['pressure_mean'] = df['pressure_hpa'].resample('D').mean()
            daily['pressure_min'] = df['pressure_hpa'].resample('D').min()
            daily['pressure_max'] = df['pressure_hpa'].resample('D').max()
        
        # Data availability
        daily['obs_count'] = df['temp_c'].resample('D').count()
        daily['expected_count'] = 288  # 24 hours * 12 obs/hour
        daily['completeness_pct'] = (daily['obs_count'] / daily['expected_count']) * 100
        
        daily['station_id'] = station_id
        daily = daily.reset_index()
        
        logger.info(f"Computed daily statistics: {len(daily)} days")
        return daily
    
    def plot_temperature_timeseries(self, df: pd.DataFrame, station_id: str, 
                                   output_file: Optional[str] = None):
        """
        Plot temperature time series
        
        Args:
            df: DataFrame with data
            station_id: Station identifier
            output_file: Optional output filename for saving plot
        """
        if df is None or len(df) == 0 or 'temp_c' not in df.columns:
            logger.warning("No temperature data to plot")
            return
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(df['datetime'], df['temp_c'], linewidth=0.5, alpha=0.7)
        ax.set_xlabel('Date')
        ax.set_ylabel('Temperature (°C)')
        ax.set_title(f'{STATIONS[station_id]["name"]} - Temperature')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            logger.info(f"Saved plot to {output_file}")
        else:
            plt.show()
        
        plt.close()
    
    def plot_wind_rose(self, df: pd.DataFrame, station_id: str,
                      output_file: Optional[str] = None):
        """
        Create a simple wind rose plot
        
        Args:
            df: DataFrame with data
            station_id: Station identifier
            output_file: Optional output filename for saving plot
        """
        if df is None or len(df) == 0:
            return
        
        if 'wind_dir_deg' not in df.columns or 'wind_speed_ms' not in df.columns:
            logger.warning("No wind data to plot")
            return
        
        # Remove missing values
        wind_data = df[['wind_dir_deg', 'wind_speed_ms']].dropna()
        
        if len(wind_data) == 0:
            logger.warning("No valid wind data")
            return
        
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        # Bin wind directions (16 directions)
        directions = np.linspace(0, 360, 17)
        dir_bins = pd.cut(wind_data['wind_dir_deg'], bins=directions, include_lowest=True)
        
        # Count occurrences in each bin
        dir_counts = dir_bins.value_counts().sort_index()
        
        # Convert to radians for polar plot
        theta = np.deg2rad(directions[:-1])
        width = np.deg2rad(360/16)
        
        bars = ax.bar(theta, dir_counts.values, width=width, alpha=0.8)
        
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        ax.set_title(f'{STATIONS[station_id]["name"]} - Wind Rose\n'
                    f'(Based on {len(wind_data)} observations)', pad=20)
        
        plt.tight_layout()
        
        if output_file:
            plt.savefig(output_file, dpi=150, bbox_inches='tight')
            logger.info(f"Saved wind rose to {output_file}")
        else:
            plt.show()
        
        plt.close()
    
    def generate_summary_statistics(self, station_id: str) -> pd.DataFrame:
        """
        Generate summary statistics for a station
        
        Args:
            station_id: Station identifier
            
        Returns:
            DataFrame with summary statistics
        """
        df = self.load_station_data(station_id)
        
        if df is None or len(df) == 0:
            return pd.DataFrame()
        
        summary = pd.DataFrame({
            'station_id': [station_id],
            'total_records': [len(df)],
            'start_date': [df['datetime'].min()],
            'end_date': [df['datetime'].max()],
            'temp_mean': [df['temp_c'].mean()],
            'temp_min': [df['temp_c'].min()],
            'temp_max': [df['temp_c'].max()],
            'temp_std': [df['temp_c'].std()],
            'wind_mean': [df['wind_speed_ms'].mean()],
            'wind_max': [df['wind_speed_ms'].max()],
            'pressure_mean': [df['pressure_hpa'].mean()],
        })
        
        logger.info(f"Generated summary statistics for {station_id}")
        return summary


def main():
    """
    Example analysis workflow
    """
    analyzer = ASOSAnalyzer()
    
    # Analyze each station
    for station_id in ['KJFK', 'KLGA', 'KNYC']:
        logger.info(f"\nAnalyzing {station_id}...")
        
        # Load data
        df = analyzer.load_station_data(station_id)
        
        if df is not None and len(df) > 0:
            # Compute daily statistics
            daily = analyzer.compute_daily_statistics(df, station_id)
            
            # Save daily statistics
            output_file = PROCESSED_DATA_DIR / f"{station_id}_daily_stats.csv"
            daily.to_csv(output_file, index=False)
            logger.info(f"Saved daily statistics to {output_file}")
            
            # Generate plots (optional - uncomment to create)
            # analyzer.plot_temperature_timeseries(df, station_id, 
            #                                     f"{station_id}_temperature.png")
            # analyzer.plot_wind_rose(df, station_id, f"{station_id}_wind_rose.png")
            
            # Print summary
            summary = analyzer.generate_summary_statistics(station_id)
            print(f"\n{station_id} Summary:")
            print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
