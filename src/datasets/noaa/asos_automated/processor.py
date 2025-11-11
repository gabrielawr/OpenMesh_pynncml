"""
NOAA ASOS 5-Minute Data Processor

Parses fixed-width .dat files and converts them to structured CSV format.
Based on ASOS 5-minute data format specifications.
"""

import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
from typing import Optional, List, Dict
import re

from config import RAW_DATA_DIR, PROCESSED_DATA_DIR, MISSING_CODES, OUTPUT_FORMAT, QC_PARAMS

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ASOSProcessor:
    """
    Processes ASOS 5-minute fixed-width format data files
    """
    
    # Fixed-width column specifications for ASOS 5-minute data
    # These are approximate and may need adjustment based on actual data format
    COLUMN_SPECS = [
        ('station_id', 0, 4),       # Station identifier
        ('wban', 5, 10),            # WBAN number
        ('date', 11, 19),           # Date (YYYYMMDD)
        ('time', 20, 24),           # Time (HHMM)
        ('data_type', 25, 28),      # Data type code
        ('wind_dir', 29, 32),       # Wind direction (degrees)
        ('wind_speed', 33, 36),     # Wind speed (knots)
        ('wind_gust', 37, 40),      # Wind gust (knots)
        ('visibility', 41, 46),     # Visibility (statute miles)
        ('temp', 47, 52),           # Temperature (°F * 10)
        ('dewpoint', 53, 58),       # Dew point (°F * 10)
        ('altimeter', 59, 64),      # Altimeter setting (inches Hg * 100)
        ('present_wx', 65, 68),     # Present weather code
    ]
    
    def __init__(self, input_dir: Path = None, output_dir: Path = None):
        """
        Initialize the processor
        
        Args:
            input_dir: Directory containing raw .dat files
            output_dir: Directory for processed output files
        """
        self.input_dir = input_dir or RAW_DATA_DIR
        self.output_dir = output_dir or PROCESSED_DATA_DIR
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized processor")
        logger.info(f"Input directory: {self.input_dir}")
        logger.info(f"Output directory: {self.output_dir}")
    
    def parse_fixed_width_line(self, line: str) -> Optional[Dict]:
        """
        Parse a single line of fixed-width format data
        
        Args:
            line: Raw data line from .dat file
            
        Returns:
            Dictionary of parsed values, or None if line is invalid
        """
        if not line or len(line) < 50:
            return None
        
        try:
            # Extract fields based on fixed positions
            data = {}
            for field_name, start, end in self.COLUMN_SPECS:
                value = line[start:end].strip()
                
                # Handle missing data
                if value in MISSING_CODES or not value:
                    data[field_name] = None
                else:
                    data[field_name] = value
            
            return data
            
        except Exception as e:
            logger.warning(f"Error parsing line: {e}")
            return None
    
    def convert_temperature(self, temp_str: Optional[str]) -> Optional[float]:
        """
        Convert ASOS temperature format to Celsius
        
        ASOS temps are in tenths of degrees F
        
        Args:
            temp_str: Temperature string from data
            
        Returns:
            Temperature in Celsius, or None if invalid
        """
        if temp_str is None:
            return None
        
        try:
            # Convert from tenths of °F to °F, then to °C
            temp_f = float(temp_str) / 10.0
            temp_c = (temp_f - 32.0) * 5.0 / 9.0
            return round(temp_c, 2)
        except (ValueError, TypeError):
            return None
    
    def convert_wind_speed(self, speed_str: Optional[str]) -> Optional[float]:
        """
        Convert wind speed from knots to m/s
        
        Args:
            speed_str: Wind speed string (knots)
            
        Returns:
            Wind speed in m/s, or None if invalid
        """
        if speed_str is None:
            return None
        
        try:
            knots = float(speed_str)
            ms = knots * 0.51444  # 1 knot = 0.51444 m/s
            return round(ms, 2)
        except (ValueError, TypeError):
            return None
    
    def convert_pressure(self, pressure_str: Optional[str]) -> Optional[float]:
        """
        Convert altimeter setting to hPa
        
        ASOS pressure is in hundredths of inches Hg
        
        Args:
            pressure_str: Pressure string from data
            
        Returns:
            Pressure in hPa, or None if invalid
        """
        if pressure_str is None:
            return None
        
        try:
            # Convert from hundredths of inHg to inHg, then to hPa
            inhg = float(pressure_str) / 100.0
            hpa = inhg * 33.8639  # 1 inHg = 33.8639 hPa
            return round(hpa, 2)
        except (ValueError, TypeError):
            return None
    
    def process_file(self, input_file: Path) -> Optional[pd.DataFrame]:
        """
        Process a single .dat file
        
        Args:
            input_file: Path to raw .dat file
            
        Returns:
            DataFrame with processed data, or None if processing failed
        """
        logger.info(f"Processing file: {input_file.name}")
        
        try:
            # Read the file line by line
            records = []
            with open(input_file, 'r', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    parsed = self.parse_fixed_width_line(line)
                    if parsed:
                        records.append(parsed)
            
            if not records:
                logger.warning(f"No valid records found in {input_file.name}")
                return None
            
            # Create DataFrame
            df = pd.DataFrame(records)
            
            # Create datetime column
            df['datetime'] = pd.to_datetime(
                df['date'].astype(str) + df['time'].astype(str).str.zfill(4),
                format='%Y%m%d%H%M',
                errors='coerce'
            )
            
            # Convert units
            df['temp_c'] = df['temp'].apply(self.convert_temperature)
            df['dewpoint_c'] = df['dewpoint'].apply(self.convert_temperature)
            df['wind_speed_ms'] = df['wind_speed'].apply(self.convert_wind_speed)
            df['wind_gust_ms'] = df['wind_gust'].apply(self.convert_wind_speed)
            df['pressure_hpa'] = df['altimeter'].apply(self.convert_pressure)
            
            # Convert wind direction to numeric
            df['wind_dir_deg'] = pd.to_numeric(df['wind_dir'], errors='coerce')
            
            # Convert visibility to numeric (statute miles)
            df['visibility_mi'] = pd.to_numeric(df['visibility'], errors='coerce')
            
            # Select and rename final columns
            output_df = df[[
                'datetime', 'station_id', 
                'temp_c', 'dewpoint_c',
                'wind_speed_ms', 'wind_gust_ms', 'wind_dir_deg',
                'pressure_hpa', 'visibility_mi', 'present_wx'
            ]].copy()
            
            # Sort by datetime
            output_df = output_df.sort_values('datetime')
            
            # Remove duplicates
            output_df = output_df.drop_duplicates(subset=['datetime', 'station_id'])
            
            logger.info(f"Processed {len(output_df)} records from {input_file.name}")
            return output_df
            
        except Exception as e:
            logger.error(f"Error processing {input_file.name}: {e}")
            return None
    
    def apply_quality_control(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply basic quality control checks
        
        Args:
            df: DataFrame with processed data
            
        Returns:
            DataFrame with QC flags applied
        """
        if df is None or len(df) == 0:
            return df
        
        # Flag suspicious values
        df['qc_flag'] = ''
        
        # Temperature checks
        temp_mask = (df['temp_c'] < QC_PARAMS['temp_min']) | (df['temp_c'] > QC_PARAMS['temp_max'])
        df.loc[temp_mask, 'qc_flag'] = df.loc[temp_mask, 'qc_flag'] + 'T'
        
        # Pressure checks
        pressure_mask = (df['pressure_hpa'] < QC_PARAMS['pressure_min']) | (df['pressure_hpa'] > QC_PARAMS['pressure_max'])
        df.loc[pressure_mask, 'qc_flag'] = df.loc[pressure_mask, 'qc_flag'] + 'P'
        
        # Wind speed checks
        wind_mask = df['wind_speed_ms'] > (QC_PARAMS['wind_speed_max'] * 0.51444)  # Convert mph to m/s
        df.loc[wind_mask, 'qc_flag'] = df.loc[wind_mask, 'qc_flag'] + 'W'
        
        flagged_count = (df['qc_flag'] != '').sum()
        if flagged_count > 0:
            logger.info(f"QC: Flagged {flagged_count} records ({flagged_count/len(df)*100:.1f}%)")
        
        return df
    
    def process_all_files(self, station_id: Optional[str] = None) -> Dict[str, bool]:
        """
        Process all .dat files in the input directory
        
        Args:
            station_id: Optional station ID to filter files
            
        Returns:
            Dictionary mapping filenames to processing success status
        """
        # Find all .dat files
        if station_id:
            pattern = f"{station_id}_*.dat"
        else:
            pattern = "*.dat"
        
        input_files = sorted(self.input_dir.glob(pattern))
        
        if not input_files:
            logger.warning(f"No .dat files found in {self.input_dir}")
            return {}
        
        logger.info(f"Found {len(input_files)} files to process")
        
        results = {}
        for input_file in input_files:
            # Process the file
            df = self.process_file(input_file)
            
            if df is not None and len(df) > 0:
                # Apply QC
                df = self.apply_quality_control(df)
                
                # Save processed data
                output_filename = input_file.stem + f".{OUTPUT_FORMAT}"
                output_path = self.output_dir / output_filename
                
                try:
                    if OUTPUT_FORMAT == 'csv':
                        df.to_csv(output_path, index=False)
                    elif OUTPUT_FORMAT == 'parquet':
                        df.to_parquet(output_path, index=False)
                    
                    logger.info(f"Saved: {output_path.name}")
                    results[input_file.name] = True
                    
                except Exception as e:
                    logger.error(f"Error saving {output_path.name}: {e}")
                    results[input_file.name] = False
            else:
                results[input_file.name] = False
        
        # Summary
        successful = sum(1 for v in results.values() if v)
        logger.info(f"Processing complete: {successful}/{len(results)} files processed successfully")
        
        return results


def main():
    """
    Main entry point for data processing
    """
    processor = ASOSProcessor()
    results = processor.process_all_files()
    return results


if __name__ == "__main__":
    main()
