# NOAA Climate Data

**Data Provider:** National Oceanic and Atmospheric Administration (NOAA)  
**Datasets:** Weather API + Climate Data Online  
**Source URLs:** https://www.weather.gov/documentation/services-web-api

## ETL Functions (`etl_noaa_climate.py`)

### `connect_db()`
Establishes a PostgreSQL connection with credentials from environment variables. Logs success or failure and raises an exception if the connection fails.

### `close_db()`
Closes the database connection cleanly. Called at the end of the ETL run to release database resources.

### `get_noaa_points(lat, lon)`
Queries the NOAA Weather API for geographic points data at the specified latitude/longitude coordinates. Returns metadata about the closest NOAA weather station grid point.

### `get_current_weather(lat, lon)`
Fetches current weather conditions (temperature, wind, precipitation forecast) for the specified location from the NOAA Weather API.

### `get_climate_normals(lat, lon)`
Retrieves historical climate normals and statistics for the specified location from NOAA's Climate Data Online service. Includes temperature ranges, precipitation, and other climatological data.

### `get_drought_status(state='TN')`
Queries drought monitoring data for the specified state. Returns current drought status and drought category information.

### `store_project_climate_context(project_id, lat, lon)`
Stores climate context metadata for a specific TDOT project. Looks up climate normals and drought status for the project location and saves to the database.

### `run()`
Main orchestrator function. Connects to database, retrieves climate data from NOAA services, and stores relevant context. Includes error handling and logging throughout.

## Available Data
- Temperature (historical, current, forecast)
- Precipitation (observed, forecast)
- Wind data (speed, direction)
- Drought monitoring (U.S. Drought Monitor)
- Flooding/flood risk information
- Climate normals
- Snow water equivalent
- Severe weather alerts

## REST API Endpoints (Used by Frontend)

### Get Current Weather at Location
```
GET /api/weather/current
Query Parameters:
  - latitude: decimal degrees
  - longitude: decimal degrees
Response: Current conditions (temp, precip, wind)
```

### Get Historical Climate Data
```
GET /api/weather/climate
Query Parameters:
  - latitude: decimal degrees
  - longitude: decimal degrees
  - start_year: YYYY
  - end_year: YYYY
Response: Historical normals and statistics
```

### Get Drought Index
```
GET /api/weather/drought
Query Parameters:
  - latitude: decimal degrees
  - longitude: decimal degrees
Response: Current drought status and category
```

### Get Weather Forecast
```
GET /api/weather/forecast
Query Parameters:
  - latitude: decimal degrees
  - longitude: decimal degrees
  - days: 1-7 (default 7)
Response: Forecasted conditions for specified period
```

## Data Storage
Environmental context data can be stored for TDOT projects:
- Climate classification
- Annual precipitation
- Average temperature range
- Drought risk level
- Flood risk zone
- Historical weather extremes

Store in project metadata or separate climate_context table with:
- `project_id`: FK to TDOT_Projects
- `annual_precipitation_mm`: mm/year
- `avg_temp_winter`: °C
- `avg_temp_summer`: °C
- `drought_risk`: low/medium/high
- `flood_risk`: low/medium/high
- `frost_free_days`: number of days

## Integration Strategy
- Query NOAA for each project location on demand (cache results)
- Store climate data linked to projects for environmental impact assessment
- Real-time weather for current conditions context
- Historical climate data for before/after impact analysis

## Limitations & Considerations
- Some data endpoints have geographic resolution limits
- Climate normals update every 10 years
- Forecast accuracy decreases beyond 7 days
- Severe weather alerts may need subscription for production use
- Rate limiting on API is per IP address
