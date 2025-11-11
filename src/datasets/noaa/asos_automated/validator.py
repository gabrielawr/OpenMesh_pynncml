"""
NOAA ASOS Data Validator

Performs data quality checks and generates validation reports.
"""

import pandas as pd
from pathlib import Path
import logging
from typing import Dict, List, Optional
from datetime import timedelta

from config import PROCESSED_DATA_DIR, STATIONS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ASOSValidator:
    """
    Validates processed ASOS data for completeness and quality
    """
    
    def __init__(self, data_dir: Path = None):
        """
        Initialize the validator
        
        Args:
            data_dir: Directory containing processed data files
        """
        self.data_dir = data_dir or PROCESSED_DATA_DIR
        logger.info(f"Initialized validator for directory: {self.data_dir}")
    
    def load_station_data(self, station_id: str) -> Optional[pd.DataFrame]:
        """
        Load all processed data for a station
        
        Args:
            station_id: 4-letter station identifier
            
        Returns:
            Combined DataFrame with all data, or None if no files found
        """
        files = sorted(self.data_dir.glob(f"{station_id}_*.csv"))
        
        if not files:
            logger.warning(f"No processed files found for station {station_id}")
            return None
        
        # Read and concatenate all files
        dfs = []
        for file in files:
            try:
                df = pd.read_csv(file, parse_dates=['datetime'])
                dfs.append(df)
            except Exception as e:
                logger.error(f"Error reading {file.name}: {e}")
        
        if not dfs:
            return None
        
        combined = pd.concat(dfs, ignore_index=True)
        combined = combined.sort_values('datetime').drop_duplicates(subset=['datetime'])
        
        logger.info(f"Loaded {len(combined)} records for {station_id}")
        return combined
    
    def check_temporal_coverage(self, df: pd.DataFrame, station_id: str) -> Dict:
        """
        Check temporal coverage and identify gaps
        
        Args:
            df: DataFrame with station data
            station_id: Station identifier
            
        Returns:
            Dictionary with coverage statistics
        """
        if df is None or len(df) == 0:
            return {'status': 'no_data'}
        
        # Expected 5-minute interval
        expected_interval = timedelta(minutes=5)
        
        # Calculate time differences
        df = df.sort_values('datetime')
        time_diffs = df['datetime'].diff()
        
        # Find gaps (where difference > 5 minutes)
        gaps = time_diffs[time_diffs > expected_interval * 1.5]  # Allow 50% tolerance
        
        # Calculate statistics
        start_date = df['datetime'].min()
        end_date = df['datetime'].max()
        total_duration = end_date - start_date
        expected_records = int(total_duration.total_seconds() / 300)  # 300 seconds = 5 minutes
        actual_records = len(df)
        completeness = (actual_records / expected_records * 100) if expected_records > 0 else 0
        
        results = {
            'station_id': station_id,
            'start_date': start_date,
            'end_date': end_date,
            'total_records': actual_records,
            'expected_records': expected_records,
            'completeness_pct': round(completeness, 2),
            'num_gaps': len(gaps),
            'largest_gap_hours': round(gaps.max().total_seconds() / 3600, 2) if len(gaps) > 0 else 0
        }
        
        logger.info(f"{station_id} temporal coverage: {completeness:.1f}% complete")
        if len(gaps) > 0:
            logger.warning(f"{station_id} has {len(gaps)} gaps, largest: {results['largest_gap_hours']:.1f} hours")
        
        return results
    
    def check_variable_completeness(self, df: pd.DataFrame, station_id: str) -> Dict:
        """
        Check completeness of individual variables
        
        Args:
            df: DataFrame with station data
            station_id: Station identifier
            
        Returns:
            Dictionary with variable completeness statistics
        """
        if df is None or len(df) == 0:
            return {}
        
        # Variables to check
        variables = ['temp_c', 'dewpoint_c', 'pressure_hpa', 
                     'wind_speed_ms', 'wind_dir_deg', 'visibility_mi']
        
        results = {'station_id': station_id}
        
        for var in variables:
            if var in df.columns:
                non_null = df[var].notna().sum()
                completeness = (non_null / len(df)) * 100
                results[f'{var}_completeness'] = round(completeness, 2)
                results[f'{var}_missing'] = len(df) - non_null
                
                logger.info(f"{station_id} - {var}: {completeness:.1f}% complete")
            else:
                results[f'{var}_completeness'] = 0
                results[f'{var}_missing'] = len(df)
        
        return results
    
    def check_value_ranges(self, df: pd.DataFrame, station_id: str) -> Dict:
        """
        Check if values are within reasonable ranges
        
        Args:
            df: DataFrame with station data
            station_id: Station identifier
            
        Returns:
            Dictionary with range check results
        """
        if df is None or len(df) == 0:
            return {}
        
        results = {'station_id': station_id}
        
        # Temperature checks
        if 'temp_c' in df.columns:
            temp_stats = df['temp_c'].describe()
            results['temp_min'] = round(temp_stats['min'], 2)
            results['temp_max'] = round(temp_stats['max'], 2)
            results['temp_mean'] = round(temp_stats['mean'], 2)
            
            # Flag extreme values
            results['temp_below_minus30'] = (df['temp_c'] < -30).sum()
            results['temp_above_40'] = (df['temp_c'] > 40).sum()
        
        # Wind speed checks
        if 'wind_speed_ms' in df.columns:
            wind_stats = df['wind_speed_ms'].describe()
            results['wind_max'] = round(wind_stats['max'], 2)
            results['wind_mean'] = round(wind_stats['mean'], 2)
            
            # Flag extreme winds
            results['wind_above_25ms'] = (df['wind_speed_ms'] > 25).sum()
        
        # Pressure checks  
        if 'pressure_hpa' in df.columns:
            pressure_stats = df['pressure_hpa'].describe()
            results['pressure_min'] = round(pressure_stats['min'], 2)
            results['pressure_max'] = round(pressure_stats['max'], 2)
            results['pressure_mean'] = round(pressure_stats['mean'], 2)
        
        # QC flag summary
        if 'qc_flag' in df.columns:
            results['qc_flagged'] = (df['qc_flag'] != '').sum()
            results['qc_flagged_pct'] = round((results['qc_flagged'] / len(df)) * 100, 2)
        
        return results
    
    def validate_station(self, station_id: str) -> Dict:
        """
        Run complete validation for a station
        
        Args:
            station_id: 4-letter station identifier
            
        Returns:
            Complete validation report dictionary
        """
        logger.info(f"Validating station: {station_id}")
        
        # Load data
        df = self.load_station_data(station_id)
        
        if df is None:
            return {
                'station_id': station_id,
                'status': 'no_data',
                'message': 'No processed data files found'
            }
        
        # Run checks
        temporal = self.check_temporal_coverage(df, station_id)
        variables = self.check_variable_completeness(df, station_id)
        ranges = self.check_value_ranges(df, station_id)
        
        # Combine results
        report = {
            **temporal,
            **variables,
            **ranges,
            'status': 'complete'
        }
        
        logger.info(f"Validation complete for {station_id}")
        return report
    
    def validate_all_stations(self) -> pd.DataFrame:
        """
        Validate all configured stations
        
        Returns:
            DataFrame with validation results for all stations
        """
        logger.info("="*60)
        logger.info("Starting validation for all stations")
        logger.info("="*60)
        
        reports = []
        for station_id in STATIONS.keys():
            report = self.validate_station(station_id)
            reports.append(report)
            logger.info("")  # Blank line between stations
        
        # Create summary DataFrame
        df_report = pd.DataFrame(reports)
        
        logger.info("="*60)
        logger.info("Validation complete!")
        logger.info("="*60)
        
        return df_report
    
    def save_report(self, report: pd.DataFrame, output_file: str = "validation_report.csv"):
        """
        Save validation report to file
        
        Args:
            report: DataFrame with validation results
            output_file: Output filename
        """
        output_path = self.data_dir.parent / output_file
        report.to_csv(output_path, index=False)
        logger.info(f"Validation report saved to: {output_path}")


def main():
    """
    Main entry point for data validation
    """
    validator = ASOSValidator()
    report = validator.validate_all_stations()
    validator.save_report(report)
    
    # Print summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    print(report.to_string())
    
    return report


if __name__ == "__main__":
    main()
