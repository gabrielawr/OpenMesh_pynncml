# NOAA ASOS Data Module

## 1. Overview

This module is responsible for fetching, processing, and managing weather data from the **NOAA Automated Surface Observing System (ASOS)** network.

The primary focus is on downloading high-frequency **5-minute interval data** for a specific set of weather stations located in the **New York City area**, particularly covering Manhattan and the areas surrounding Brooklyn. The module is designed to retrieve data for a user-defined time period.

## 2. Data Source

* **Dataset Name**: Automated Surface Observing System (ASOS) 5-Minute Data
* **Hosting Agency**: NOAA National Centers for Environmental Information (NCEI)
* **Source URL**: [https://www.ncei.noaa.gov/data/automated-surface-observing-system-five-minute/](https://www.ncei.noaa.gov/data/automated-surface-observing-system-five-minute/)

## 3. Geographic Focus & Target Stations

This module is configured to target stations providing coverage for Manhattan and Brooklyn. The primary stations are:

| Station ID | Name / Location                       | Borough Coverage |
| :--------- | :------------------------------------ | :--------------- |
| `KNYC`     | Central Park                          | Manhattan        |
| `KJFK`     | John F. Kennedy International Airport | Queens (serves Brooklyn) |
| `KLGA`     | LaGuardia Airport                     | Queens (serves Brooklyn) |

**Note**: While there are no major ASOS stations of this type located directly within Brooklyn, the stations at JFK and LGA in Queens provide the most relevant and comprehensive coverage for the borough.

## 4. Module Components

* `fetcher.py`: Handles the connection to the NCEI data server and downloads the raw, fixed-width `.dat` files for the specified stations and date ranges.
* `processor.py`: Reads the raw `.dat` files, parses the fixed-width format, cleans the data, and outputs it into a structured format (e.g., CSV or Parquet).
* `config.py`: Contains key configuration variables such as the list of target station IDs, start and end dates for data fetching, and file paths.
* `validator.py`: (Optional) Performs data quality checks on the processed data to ensure completeness and accuracy.

## 5. Usage

The scripts within this module are designed to be called by a master pipeline script. The typical workflow is:

1.  Configure the desired stations and date range in `config.py`.
2.  The orchestration script will first run the `fetcher.py` to download the raw data.
3.  Following a successful download, the `processor.py` is run to convert the raw data into a clean, analyzable format.

## 6. Data Format

* **Raw Format**: Fixed-width text (`.dat`) files, with a structure defined by NOAA.
* **Processed Format**: Comma-Separated Values (`.csv`) files, with clearly defined columns for timestamp, temperature, precipitation, etc.