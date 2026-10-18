# USGS Water Quality Data

**Data Provider:** U.S. Geological Survey (USGS)  
**Dataset:** NWIS Water Quality Portal  
**Source URL:** https://waterservices.usgs.gov/

## ETL Functions (`etl_usgs_water_quality.py`)

### `connect_db()`
Establishes a PostgreSQL connection with credentials from environment variables. Logs success or failure and raises an exception if the connection fails.

### `close_db()`
Closes the database connection cleanly. Called at the end of the ETL run to release database resources.

### `get_tn_stations()`
Queries the USGS NWIS API to retrieve all water quality monitoring stations located in Tennessee. Returns a list of station dictionaries with site IDs, names, and geographic coordinates.

### `get_recent_measurements(site_id, days_back=30)`
Fetches water quality measurements from a specific monitoring station for the specified time period (default: last 30 days). Returns time series data with values, dates, and parameter codes.

### `extract_measurements(timeseries)`
Parses raw USGS JSON time series data and extracts individual measurements. Cleans up parameter metadata and prepares measurement records for database insertion.

### `insert_environmental_data(measurement, station)`
Transforms a measurement record and inserts it into the `Environmental_Data` table. Maps USGS parameter codes to our database schema, validates coordinates, and handles duplicate entries.

### `run()`
Main orchestrator function. Connects to database, fetches all Tennessee stations, retrieves recent measurements for each station, extracts and inserts the data, then closes the connection. Includes error handling and logging throughout.
