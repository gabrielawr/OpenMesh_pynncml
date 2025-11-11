"""
NOAA ASOS 5-Minute Data Fetcher

Downloads raw .dat files from NOAA NCEI for specified stations and date ranges.
"""

import requests
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import List, Dict, Tuple
import time

from config import STATIONS, BASE_URL, RAW_DATA_DIR, START_DATE, END_DATE

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ASOSFetcher:
    """
    Fetches ASOS 5-minute data files from NOAA NCEI
    """
    
    def __init__(self, stations: Dict = None, start_date: datetime = None, 
                 end_date: datetime = None, output_dir: Path = None):
        """
        Initialize the fetcher
        
        Args:
            stations: Dictionary of station configurations
            start_date: Start date for data fetching
            end_date: End date for data fetching
            output_dir: Directory to save downloaded files
        """
        self.stations = stations or STATIONS
        self.start_date = start_date or START_DATE
        self.end_date = end_date or END_DATE
        self.output_dir = output_dir or RAW_DATA_DIR
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized fetcher for {len(self.stations)} stations")
        logger.info(f"Date range: {self.start_date.date()} to {self.end_date.date()}")
    
    def generate_file_urls(self, station_id: str) -> List[Tuple[str, str, str]]:
        """
        Generate URLs for all monthly files within the date range
        
        Args:
            station_id: 4-letter station identifier (e.g., 'KJFK')
            
        Returns:
            List of tuples: (url, year, month)
        """
        if station_id not in self.stations:
            raise ValueError(f"Unknown station: {station_id}")
        
        wban = self.stations[station_id]['wban']
        urls = []
        
        # Generate monthly file URLs
        current_date = self.start_date.replace(day=1)
        end_month = self.end_date.replace(day=1)
        
        while current_date <= end_month:
            year = current_date.year
            month = current_date.strftime('%m')
            
            # File naming: {YEAR}/64010{STATION_ID}{YYYYMM}.dat
            # The "64010" prefix appears to be the WBAN format indicator
            filename = f"64010{station_id}{year}{month}.dat"
            url = f"{BASE_URL}/{year}/{filename}"
            
            urls.append((url, str(year), month))
            
            # Move to next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        logger.info(f"Generated {len(urls)} URLs for station {station_id}")
        return urls
    
    def download_file(self, url: str, output_path: Path, retry_count: int = 3) -> bool:
        """
        Download a single data file
        
        Args:
            url: URL of the file to download
            output_path: Local path to save the file
            retry_count: Number of retry attempts for failed downloads
            
        Returns:
            True if download successful, False otherwise
        """
        for attempt in range(retry_count):
            try:
                logger.info(f"Downloading: {url} (attempt {attempt + 1}/{retry_count})")
                
                response = requests.get(url, timeout=30)
                
                if response.status_code == 200:
                    # Save the file
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    file_size = output_path.stat().st_size
                    logger.info(f"Successfully downloaded: {output_path.name} ({file_size:,} bytes)")
                    return True
                
                elif response.status_code == 404:
                    logger.warning(f"File not found (404): {url}")
                    return False
                
                else:
                    logger.warning(f"HTTP {response.status_code}: {url}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error: {e}")
                if attempt < retry_count - 1:
                    time.sleep(2 ** attempt)
        
        logger.error(f"Failed to download after {retry_count} attempts: {url}")
        return False
    
    def fetch_station_data(self, station_id: str) -> Dict[str, bool]:
        """
        Fetch all data files for a single station
        
        Args:
            station_id: 4-letter station identifier
            
        Returns:
            Dictionary mapping filenames to download success status
        """
        logger.info(f"Fetching data for station: {station_id} - {self.stations[station_id]['name']}")
        
        # Generate URLs for this station
        urls = self.generate_file_urls(station_id)
        
        # Download each file
        results = {}
        for url, year, month in urls:
            filename = f"{station_id}_{year}{month}.dat"
            output_path = self.output_dir / filename
            
            # Skip if file already exists
            if output_path.exists():
                logger.info(f"File already exists: {filename}")
                results[filename] = True
                continue
            
            # Download the file
            success = self.download_file(url, output_path)
            results[filename] = success
            
            # Brief pause between downloads to be respectful to the server
            time.sleep(0.5)
        
        # Summary
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Station {station_id} complete: {successful}/{len(results)} files downloaded")
        
        return results
    
    def fetch_all_stations(self) -> Dict[str, Dict[str, bool]]:
        """
        Fetch data for all configured stations
        
        Returns:
            Dictionary mapping station IDs to their download results
        """
        logger.info("="*60)
        logger.info("Starting NOAA ASOS data fetch")
        logger.info(f"Stations: {', '.join(self.stations.keys())}")
        logger.info(f"Date range: {self.start_date.date()} to {self.end_date.date()}")
        logger.info("="*60)
        
        all_results = {}
        for station_id in self.stations.keys():
            results = self.fetch_station_data(station_id)
            all_results[station_id] = results
            logger.info("")  # Blank line between stations
        
        # Overall summary
        total_files = sum(len(r) for r in all_results.values())
        total_success = sum(sum(1 for v in r.values() if v) for r in all_results.values())
        
        logger.info("="*60)
        logger.info("Fetch complete!")
        logger.info(f"Total files: {total_success}/{total_files} successfully downloaded")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info("="*60)
        
        return all_results


def main():
    """
    Main entry point for data fetching
    """
    # Create fetcher instance
    fetcher = ASOSFetcher()
    
    # Fetch data for all stations
    results = fetcher.fetch_all_stations()
    
    return results


if __name__ == "__main__":
    main()
