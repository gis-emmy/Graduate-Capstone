# iNaturalist Biodiversity Data

**Data Provider:** iNaturalist (California Academy of Sciences + National Geographic)  
**Dataset:** Verified Biodiversity Observations  
**Source URL:** https://api.inaturalist.org/v1

## ETL Functions (`etl_inaturalist_biodiversity.py`)

### `connect_db()`
Establishes a PostgreSQL connection with credentials from environment variables. Logs success or failure and raises an exception if the connection fails.

### `close_db()`
Closes the database connection cleanly. Called at the end of the ETL run to release database resources.

### `get_tn_observations(days_back=30, quality_grade='research')`
Queries the iNaturalist API for biodiversity observations in Tennessee. Filters to research-grade verified observations from the specified time period. Returns list of observation dictionaries.

### `get_endangered_species_observations(limit=300)`
Retrieves observations of threatened or endangered species in Tennessee. Filters by conservation status and returns high-confidence observations useful for environmental impact assessment.

### `extract_observation_data(obs)`
Parses raw iNaturalist observation JSON and extracts relevant fields. Maps species data, location coordinates, photos, and observation metadata into database schema format.

### `insert_citizen_science_observation(obs_data)`
Transforms an observation record and inserts it into the `Citizen_Science_Data` table. Validates coordinates, handles species taxonomy data, and manages duplicate entries.

### `run()`
Main orchestrator function. Connects to database, fetches Tennessee biodiversity observations from iNaturalist, transforms and inserts each record, then closes the connection. Includes error handling and logging throughout.

## Available Data
- Species observations (photos/descriptions)
- Taxonomic information
- Observation dates and locations
- Research-grade verified data
- Community identification and consensus
- User annotations and notes

## REST API Endpoints (Used by Frontend)

### Get Species Observations in Bounding Box
```
GET /api/biodiversity/observations
Query Parameters:
  - north: latitude
  - south: latitude
  - east: longitude
  - west: longitude
  - quality_grade: "research" (recommended for filtering)
  - iconic_taxa: "Animalia", "Plantae", "Fungi", etc. (optional)
  - order_by: "created_at" or "observed_on"
Response: GeoJSON FeatureCollection of observations
```

### Get Observations Near Project
```
GET /api/biodiversity/observations/near/:project_id
Query Parameters:
  - radius_km: search radius (default 5)
  - quality_grade: "research"
Response: Observations near TDOT project location
```

### Search by Species
```
GET /api/biodiversity/species/:taxon_id
Query Parameters:
  - place_id: TN (place ID for Tennessee)
  - year: YYYY (optional, for specific year observations)
Response: All observations of species in area
```

### Get Threatened/Endangered Species Observations
```
GET /api/biodiversity/endangered
Query Parameters:
  - north: latitude
  - south: latitude
  - east: longitude
  - west: longitude
Response: Observations of conservation-status species only
```

## Data Storage
Store observations in `Citizen_Science_Observations` or `Environmental_Data` table:
- `data_category`: "biodiversity_observation" or specific taxa
- `data_type`: "species_observation"
- `data_source`: "iNaturalist"
- `location`: POINT geometry (observation coordinates)
- `species_name`: Common and scientific name
- `protected_status`: If species is T&E
- `data_confidence`: Based on iNaturalist quality_grade
- `last_verified`: When observation was verified by community

## ETL Process
See `etl_inaturalist_biodiversity.py` for automated data ingestion.

### How It Works
1. Query iNaturalist API for Tennessee observations
2. Filter for research-grade quality only (expert verified)
3. Extract taxonomic and location information
4. Identify endangered/threatened species matches
5. Insert into PostgreSQL database
6. Link to nearby TDOT projects if within buffer zone

### Schedule
- Can run daily to capture new observations
- Or run on-demand for specific date ranges
- Query performance improves with quality_grade filter

## Query Examples

### Get all mammal observations in Tennessee
```
https://api.inaturalist.org/v1/observations?place_id=38394&taxon_id=40674&quality_grade=research
```

### Get bird observations near Nashville
```
https://api.inaturalist.org/v1/observations?lat=36.16&lng=-86.78&radius=25&taxon_id=3&quality_grade=research
```

### Get observations with photos
```
https://api.inaturalist.org/v1/observations?place_id=38394&photos=true&quality_grade=research
```

## Limitations & Considerations
- Research-grade filter strongly recommended (removes unverified data)
- Observation accuracy depends on user skill level
- Some species overrepresented (birds, butterflies)
- Sampling bias toward populated areas and accessible habitats
- Photo-based identification preferred for reliability
- Community consensus increases confidence in identification
- iNaturalist place ID 38394 = Tennessee state
