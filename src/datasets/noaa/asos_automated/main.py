"""
NOAA ASOS Data Pipeline - Main Orchestration Script

Complete workflow for fetching, processing, validating, and analyzing ASOS data.
"""

import argparse
import logging
from datetime import datetime
from pathlib import Path

from config import STATIONS, START_DATE, END_DATE
from fetcher import ASOSFetcher
from processor import ASOSProcessor
from validator import ASOSValidator
from analyzer import ASOSAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('noaa_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_full_pipeline(start_date: datetime = None, end_date: datetime = None,
                     stations: list = None, skip_fetch: bool = False,
                     skip_process: bool = False, skip_validate: bool = False,
                     skip_analyze: bool = False):
    """
    Run the complete data pipeline
    
    Args:
        start_date: Start date for data fetching
        end_date: End date for data fetching
        stations: List of station IDs to process (None = all)
        skip_fetch: Skip data fetching step
        skip_process: Skip data processing step
        skip_validate: Skip validation step
        skip_analyze: Skip analysis step
    """
    logger.info("="*80)
    logger.info("NOAA ASOS DATA PIPELINE")
    logger.info("="*80)
    logger.info(f"Pipeline started at: {datetime.now()}")
    
    # Use default dates if not specified
    start_date = start_date or START_DATE
    end_date = end_date or END_DATE
    
    # Use all stations if not specified
    station_list = stations or list(STATIONS.keys())
    
    logger.info(f"Stations: {', '.join(station_list)}")
    logger.info(f"Date range: {start_date.date()} to {end_date.date()}")
    logger.info("")
    
    # Step 1: Fetch data
    if not skip_fetch:
        logger.info("STEP 1: FETCHING DATA")
        logger.info("-" * 80)
        try:
            fetcher = ASOSFetcher(
                start_date=start_date,
                end_date=end_date
            )
            fetch_results = fetcher.fetch_all_stations()
            logger.info("✓ Data fetching complete\n")
        except Exception as e:
            logger.error(f"✗ Data fetching failed: {e}\n")
            return False
    else:
        logger.info("STEP 1: SKIPPED (fetching)\n")
    
    # Step 2: Process data
    if not skip_process:
        logger.info("STEP 2: PROCESSING DATA")
        logger.info("-" * 80)
        try:
            processor = ASOSProcessor()
            process_results = processor.process_all_files()
            logger.info("✓ Data processing complete\n")
        except Exception as e:
            logger.error(f"✗ Data processing failed: {e}\n")
            return False
    else:
        logger.info("STEP 2: SKIPPED (processing)\n")
    
    # Step 3: Validate data
    if not skip_validate:
        logger.info("STEP 3: VALIDATING DATA")
        logger.info("-" * 80)
        try:
            validator = ASOSValidator()
            validation_report = validator.validate_all_stations()
            validator.save_report(validation_report)
            logger.info("✓ Data validation complete\n")
        except Exception as e:
            logger.error(f"✗ Data validation failed: {e}\n")
            return False
    else:
        logger.info("STEP 3: SKIPPED (validation)\n")
    
    # Step 4: Analyze data
    if not skip_analyze:
        logger.info("STEP 4: ANALYZING DATA")
        logger.info("-" * 80)
        try:
            analyzer = ASOSAnalyzer()
            for station_id in station_list:
                logger.info(f"Analyzing {station_id}...")
                df = analyzer.load_station_data(station_id)
                if df is not None and len(df) > 0:
                    daily = analyzer.compute_daily_statistics(df, station_id)
                    summary = analyzer.generate_summary_statistics(station_id)
            logger.info("✓ Data analysis complete\n")
        except Exception as e:
            logger.error(f"✗ Data analysis failed: {e}\n")
            return False
    else:
        logger.info("STEP 4: SKIPPED (analysis)\n")
    
    logger.info("="*80)
    logger.info("PIPELINE COMPLETE")
    logger.info(f"Finished at: {datetime.now()}")
    logger.info("="*80)
    
    return True


def main():
    """
    Main entry point with command-line interface
    """
    parser = argparse.ArgumentParser(
        description='NOAA ASOS 5-minute data pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline for default date range
  python main.py
  
  # Run for specific date range
  python main.py --start-date 2024-01-01 --end-date 2024-03-31
  
  # Run only specific steps
  python main.py --skip-fetch  # Skip fetching, process existing data
  python main.py --skip-analyze  # Fetch, process, validate but don't analyze
  
  # Process specific stations only
  python main.py --stations KJFK KLGA
        """
    )
    
    parser.add_argument('--start-date', type=str,
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--stations', nargs='+', 
                       help='Station IDs to process (default: all)')
    parser.add_argument('--skip-fetch', action='store_true',
                       help='Skip data fetching step')
    parser.add_argument('--skip-process', action='store_true',
                       help='Skip data processing step')
    parser.add_argument('--skip-validate', action='store_true',
                       help='Skip validation step')
    parser.add_argument('--skip-analyze', action='store_true',
                       help='Skip analysis step')
    
    args = parser.parse_args()
    
    # Parse dates
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d') if args.start_date else None
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d') if args.end_date else None
    
    # Run pipeline
    success = run_full_pipeline(
        start_date=start_date,
        end_date=end_date,
        stations=args.stations,
        skip_fetch=args.skip_fetch,
        skip_process=args.skip_process,
        skip_validate=args.skip_validate,
        skip_analyze=args.skip_analyze
    )
    
    if success:
        print("\n✓ Pipeline completed successfully!")
        return 0
    else:
        print("\n✗ Pipeline failed. Check logs for details.")
        return 1


if __name__ == "__main__":
    exit(main())
