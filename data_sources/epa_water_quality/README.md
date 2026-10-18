# EPA Water Quality Portal

**Data Provider:** U.S. Environmental Protection Agency (EPA)  
**Dataset:** Water Quality Portal (USGS + STORET + state agencies)  
**Source URL:** https://www.waterqualitydata.us/webservices

## ETL Functions (`etl_epa_water_quality.py`)

### `connect_db()`
Establishes a PostgreSQL connection with credentials from environment variables. Logs success or failure and raises an exception if the connection fails.

### `close_db()`
Closes the database connection cleanly. Called at the end of the ETL run to release database resources.

### `get_wqp_results(state, characteristic, start_date, end_date)`
Queries the EPA Water Quality Portal API for observations matching the given filters (state, parameter type, date range). Handles pagination and returns all results from the WQP service.

### `transform_observation(result)`
Converts a raw EPA WQP observation into the format expected by our database schema. Maps EPA characteristic names to standard parameter codes and validates geographic coordinates.

### `insert_environmental_data(observation)`
Transforms an observation record and inserts it into the `Environmental_Data` table. Handles deduplication, validates data quality flags, and manages coordinate systems.

### `run()`
Main orchestrator function. Connects to database, queries EPA WQP for Tennessee water quality observations, transforms and inserts each record, then closes the connection. Includes error handling and logging throughout.

## What We Measure
The EPA portal covers a wide range of water quality data:
- **Physical measurements**: Temperature, pH, conductivity, dissolved oxygen
- **Chemical analysis**: Nutrients (nitrogen, phosphorus), pesticides, heavy metals
- **Biological data**: Algae, bacteria, phytoplankton (how alive is the water?)
- **Sediment & tissue data**: What's in the bottom of the river, what's in the fish
- **Quality assurance**: Data validation info so you know how reliable each measurement is

The data comes from many different programs and agencies, so you get a pretty complete picture of what's going on with water quality.

## How to Use This Data

### Get water quality data near a specific location
```
GET /api/water-quality/portal
```
Tell it where you care about:
  - `latitude`: center point latitude
  - `longitude`: center point longitude
  - `radius_km`: how far to search (defaults to 5km)
  - `start_date`: YYYY-MM-DD (optional)
  - `end_date`: YYYY-MM-DD (optional)

Returns: All measurements from that area

### Get data from a geographic box
```
GET /api/water-quality/portal/bbox
```
Define your box:
  - `north`: top boundary
  - `south`: bottom boundary
  - `east`: right boundary
  - `west`: left boundary
  - `organization`: filter by who collected it (EPA, USGS, etc.) - optional

Returns: Everything measured in that area

### Search by what you're measuring
```
GET /api/water-quality/portal/search
```
Looking for specific measurements:
  - `characteristic_name`: What you want to find (e.g., "Dissolved oxygen", "pH", "Temperature")
  - `state`: TN (we're focused on Tennessee)
  - `start_date`: YYYY-MM-DD

Returns: All observations of that parameter in Tennessee

## Where the Data Lives
EPA data ends up in the same `Environmental_Data` table as our USGS data. Here's what we track:
- **data_category**: "water_quality" (so we know what this is)
- **data_type**: Could be "measurement" or "biological_sample" depending on what was collected
- **data_source**: "EPA WQP" (so we know it came from the EPA portal)
- **location**: GPS coordinates of the monitoring site
- **measurement_value**: The actual reading
- **measurement_unit**: What it's measured in
- **measurement_date**: When the sample was collected
- **data_confidence**: "high" (EPA verifies observations before they get in the portal)

## How the Data Gets Here
See `etl_epa_water_quality.py` for the technical details.

In plain English:
1. Ask EPA API for Tennessee monitoring locations
2. Pull recent observations (last 90 days)
3. Filter out unverified observations (we want good data)
4. Fix coordinates if needed
5. Throw it in the database
6. If anything breaks, we keep going and try again later

We run this daily, usually overnight, to keep the data fresh without hammering the EPA servers during the day.
3. Filter by data quality (remove unverified observations)
4. Transform coordinate system if needed
5. Insert into PostgreSQL `Environmental_Data` table
6. Deduplicate to avoid USGS duplicate records

### Schedule
- Should run daily to capture new observations
- Can be run on-demand for specific date ranges
- Caches last sync date to avoid redundant pulls

## Supported Characteristics
Common water quality parameters available through EPA WQP:
- Dissolved oxygen
- Temperature
- pH
- Specific conductance
- Total phosphorus
- Nitrate
- Chloride
- Turbidity
- E. coli
- Fecal coliform

Full list: https://www.waterqualitydata.us/webservices#api_Characteristics

## Limitations & Considerations
- Some observations may be provisional (flag in original data)
- Multiple organizations may report same location
- Data quality varies by collector
- Some sampling methods are more reliable than others
- Consider filtering by "ProviderName" to prefer authoritative sources
- Portal includes data from neighboring states (filter by state needed)
