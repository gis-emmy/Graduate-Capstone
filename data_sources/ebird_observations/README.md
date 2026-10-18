# eBird Observations Data

**Data Provider:** Cornell Lab of Ornithology  
**Dataset:** Real-time Bird Sightings  
**Source URL:** https://api.ebird.org/v2

## ETL Functions (`etl_ebird_observations.py`)

### `connect_db()`
Establishes a PostgreSQL connection with credentials from environment variables. Logs success or failure and raises an exception if the connection fails.

### `close_db()`
Closes the database connection cleanly. Called at the end of the ETL run to release database resources.

### `get_recent_observations(region, days_back=7, category=None)`
Queries the eBird API for recent bird observations in the specified region. Filters by time period and optional species category. Returns observations sorted by date and location.

### `get_hotspots(region='US-TN')`
Retrieves a list of popular birding hotspots (well-documented observation locations) in the specified region. Returns location coordinates, names, and recent sighting counts.

### `get_species_info(species_code)`
Fetches detailed species information from eBird including common/scientific names, taxonomy, and conservation status for the specified species code.

### `extract_observation_data(obs, species_info)`
Parses raw eBird observation JSON and enriches with species metadata. Maps location coordinates, species details, confidence levels, and observation metadata into database schema format.

### `insert_environmental_data(obs_data)`
Transforms an observation record and inserts it into the `Environmental_Data` table. Validates coordinates, handles species taxonomy, and manages duplicate entries.

### `run()`
Main orchestrator function. Connects to database, fetches Tennessee bird observations from eBird, transforms and inserts each record, then closes the connection. Includes error handling and logging throughout.

## Available Data
- Species observations with location and date
- Species abundance maps (seasonal patterns)
- Hotspot locations (popular birding areas)
- Historical trends and species lists
- Migratory patterns and phenology
- Species demographic data

## REST API Endpoints (Used by Frontend)

### Get Recent Bird Observations
```
GET /api/birds/recent
Query Parameters:
  - latitude: decimal degrees
  - longitude: decimal degrees
  - radius_km: search radius (default 10)
  - back_days: days to look back (default 14)
Response: GeoJSON FeatureCollection of bird sightings
```

### Get Species Observations Near Project
```
GET /api/birds/species/:species_code
Query Parameters:
  - latitude: decimal degrees
  - longitude: decimal degrees
  - radius_km: search radius
Response: All observations of specific species
```

### Get Hotspots in Area
```
GET /api/birds/hotspots
Query Parameters:
  - latitude: decimal degrees
  - longitude: decimal degrees
  - radius_km: search radius
Response: GeoJSON of popular birding locations
```

### Get Seasonal Species Patterns
```
GET /api/birds/seasonal/:species_code
Query Parameters:
  - latitude: decimal degrees
  - longitude: decimal degrees
Response: Monthly abundance patterns and migration timing
```

## Data Storage
Store bird observations in `Environmental_Data` table:
- `data_category`: "bird_observation"
- `data_type`: "species_observation"
- `data_source`: "eBird"
- `location`: POINT geometry (observation coordinates)
- `species_name`: Common name
- `protected_status`: "threatened" if migratory vulnerable species
- `measurement_date`: Observation date
- `data_confidence`: "high" (eBird has verification system)

## ETL Process
See `etl_ebird_observations.py` for automated data ingestion.

### How It Works
1. Query eBird API for recent observations in Tennessee
2. Filter by date range (typically last 30 days)
3. Extract species, location, and date information
4. Identify migratory or protected species
5. Insert into PostgreSQL database
6. Flag observations near TDOT projects

### Schedule
- Can run daily for recent sightings
- Run weekly for historical trends
- Query performance is good even for large date ranges

## Species Codes
Common Tennessee bird species codes:
- blja = Blue Jay
- carw = Carolina Wren
- rsbnw = Brown Nuthatch
- nrwsw = Northern Saw-whet Owl
- baegl = Bald Eagle (protected)
- gwhow = Great Horned Owl

Full species list: https://ebird.org/data/download/

## Important Bird Areas (IBAs) in Tennessee
eBird identifies Important Bird Areas - significant locations for birds. Should filter for observations in/near these areas as priority for conservation impact.

## Limitations & Considerations
- Observer skill level varies (affects ID accuracy)
- Some species reported more frequently (publication bias)
- Hotspots may show observer bias (more accessible areas)
- Migratory patterns shift year-to-year
- Rare species require documentation/photos
- eBird has moderation to prevent false reports
- Sensitive species may have coordinates obscured
