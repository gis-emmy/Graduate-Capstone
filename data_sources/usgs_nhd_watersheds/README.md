# USGS NHDPlus Watershed Data

**Data Provider:** U.S. Geological Survey (USGS)  
**Dataset:** NHDPlus (National Hydrography Dataset Plus)  
**Source URL:** https://www.usgs.gov/national-hydrography

## ETL Functions (`etl_usgs_nhd_watersheds.py`)

### `connect_db()`
Establishes a PostgreSQL connection with PostGIS extension. Validates spatial reference systems and enables geometry operations. Logs success or failure and raises an exception if the connection fails.

### `ensure_tables_exist()`
Creates the three PostGIS tables if they don't already exist: `Watersheds`, `Flowlines`, and `Catchments`. Sets up spatial indexes (GIST) for performance optimization on geographic queries.

### `fetch_wfs_data(feature_type, huc_level=None)`
Queries the WaterGEO WFS service for watershed features. Can fetch HUC boundaries (with optional level filtering) or flowline data. Returns GeoJSON-formatted feature collection.

### `extract_watershed_data(feature)`
Parses a raw WFS feature and extracts watershed/HUC information. Converts geometry to PostGIS format, validates coordinates, and prepares data for database insertion.

### `extract_flowline_data(feature)`
Parses a raw WFS feature and extracts stream/flowline information. Converts LineString geometry, validates connectivity data, and prepares stream network data for insertion.

### `insert_watersheds(features)`
Bulk inserts watershed/HUC boundary features into the `Watersheds` table. Uses ON CONFLICT for deduplication, maintains spatial indexes, and returns count of inserted records.

### `insert_flowlines(features)`
Bulk inserts stream network features into the `Flowlines` table. Manages flow connectivity data, maintains spatial indexes, and returns count of inserted records.

### `run()`
Main orchestrator function. Connects to database, ensures tables exist, fetches watershed and flowline data from WaterGEO WFS service, transforms and inserts records into appropriate tables, then closes the connection. Includes error handling and logging throughout.

### WaterGEO WMS/WFS Services (Public, No Authentication Required)

All watershed data accessed via OGC-compliant web services:
- **WFS Base URL**: `https://www.watergeospatial.org/geoserver/wfs`
- **WMS Base URL**: `https://www.watergeospatial.org/geoserver/wms`
- **Response Formats**: GeoJSON, GML, Shapefile

### HUC Hierarchical Levels

| Level | Name | Example | Avg Size | Count in TN |
|-------|------|---------|----------|------------|
| **HUC-2** | Region | "05" (Tennessee) | ~250,000 sq mi | 1 |
| **HUC-4** | Subregion | "0501" (Cumberland) | ~40,000 sq mi | 5 |
| **HUC-6** | Basin | "050100" (Upper Cumberland) | ~5,000 sq mi | 19 |
| **HUC-8** | Subbasin | "05010001" (Obey River) | ~700 sq mi | 100+ |
| **HUC-10** | Watershed | "0501000101" | ~100 sq mi | 1000+ |
| **HUC-12** | Subwatershed | "050100010101" | ~20 sq mi | 8,378 |

**For TDOT projects, HUC-10 and HUC-12 are most useful for localized watershed identification.**

## REST API Endpoints

### 1. Get All Watersheds in Tennessee (HUC-10)
```
GET /api/watersheds
```

**Parameters**:
- `level` (required): HUC level ('huc10', 'huc12', default: 'huc10')
- `limit` (optional): Results per page (default: 100, max: 1000)
- `offset` (optional): Pagination offset (default: 0)

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "watershed_id": "uuid",
      "huc_code": "0501000101",
      "huc_level": "huc10",
      "name": "Obey River Headwaters",
      "area_sqmi": 487.23,
      "location": {
        "type": "Polygon",
        "coordinates": [[[-85.5, 36.2], ...]]
      },
      "centroid": [36.25, -85.5],
      "data_source": "USGS NHDPlus",
      "created_at": "2024-10-18T15:00:00Z"
    }
  ],
  "pagination": {
    "total": 1847,
    "limit": 100,
    "offset": 0,
    "hasMore": true
  }
}
```

### 2. Get Watershed by HUC Code
```
GET /api/watersheds/:huc_code
```

**Example**: `GET /api/watersheds/0501000101`

**Response**:
```json
{
  "success": true,
  "data": {
    "watershed_id": "uuid",
    "huc_code": "0501000101",
    "huc_level": "huc10",
    "name": "Obey River Headwaters",
    "area_sqmi": 487.23,
    "description": "Located in Upper Cumberland region, encompasses headwaters of Obey River",
    "parent_huc": "050100010",
    "child_hucs": ["0501000101", "0501000102"],
    "location": { "type": "Polygon", "coordinates": [...] },
    "centroid": [36.25, -85.5],
    "data_source": "USGS NHDPlus"
  }
}
```

### 3. Get Watersheds Intersecting Bounding Box
```
GET /api/watersheds/bbox
```

**Parameters**:
- `north` (required): North boundary latitude
- `south` (required): South boundary latitude
- `east` (required): East boundary longitude
- `west` (required): West boundary longitude
- `level` (optional): HUC level ('huc10', 'huc12', default: 'huc10')

**Example**: `GET /api/watersheds/bbox?north=36.5&south=36.0&east=-85.0&west=-85.5&level=huc10`

**Response**: Returns array of watersheds intersecting bbox

### 4. Get Catchment for a Point (Pour Point Analysis)
```
GET /api/watersheds/catchment
```

**Parameters**:
- `latitude` (required): Point latitude
- `longitude` (required): Point longitude

**Response**:
```json
{
  "success": true,
  "data": {
    "point": [36.25, -85.5],
    "catchment_id": "uuid",
    "huc_12": "050100010101",
    "huc_10": "0501000101",
    "huc_8": "05010001",
    "area_sqmi": 18.5,
    "location": { "type": "Polygon", "coordinates": [...] },
    "upslope_area_sqmi": 247.3
  }
}
```

### 5. Get Flowlines in Region (Stream Network)
```
GET /api/watersheds/flowlines
```

**Parameters**:
- `latitude` (required): Center latitude
- `longitude` (required): Center longitude
- `radius_miles` (optional): Search radius (default: 10, max: 50)

**Response**: Array of NHD flowlines with stream order, length, direction

## Database Schema

### New Tables Created

#### `Watersheds` Table
```sql
CREATE TABLE Watersheds (
  watershed_id UUID PRIMARY KEY,
  huc_code VARCHAR(12) UNIQUE NOT NULL,
  huc_level VARCHAR(10) NOT NULL,
  name VARCHAR(200),
  description TEXT,
  parent_huc VARCHAR(12),
  area_sqmi DECIMAL(10, 2),
  location GEOMETRY(Polygon, 4326),
  centroid GEOMETRY(Point, 4326),
  data_source VARCHAR(50),
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  
  INDEX idx_huc_code (huc_code),
  INDEX idx_huc_level (huc_level),
  INDEX idx_location (location)
);
```

#### `Flowlines` Table
```sql
CREATE TABLE Flowlines (
  flowline_id UUID PRIMARY KEY,
  reach_code VARCHAR(14),
  stream_name VARCHAR(200),
  stream_order INT,
  length_miles DECIMAL(10, 2),
  huc_12 VARCHAR(12),
  geometry GEOMETRY(LineString, 4326),
  data_source VARCHAR(50),
  created_at TIMESTAMP,
  
  INDEX idx_huc_12 (huc_12),
  INDEX idx_stream_name (stream_name),
  INDEX idx_geometry (geometry)
);
```

#### `Catchments` Table
```sql
CREATE TABLE Catchments (
  catchment_id UUID PRIMARY KEY,
  huc_12 VARCHAR(12),
  area_sqmi DECIMAL(10, 2),
  upslope_area_sqmi DECIMAL(10, 2),
  location GEOMETRY(Polygon, 4326),
  pour_point GEOMETRY(Point, 4326),
  data_source VARCHAR(50),
  created_at TIMESTAMP,
  
  INDEX idx_huc_12 (huc_12),
  INDEX idx_location (location)
);
```

## ETL Process

### Data Flow

```
WaterGEO WFS Service (USGS NHDPlus)
    ↓
Python ETL Script (requests, geopandas)
    ↓
Data Transformation & Validation
    ↓
PostgreSQL Database (psycopg2)
    ↓
Backend REST Endpoints
    ↓
Frontend Map Visualization (Leaflet)
```

### Execution Steps

The `etl_usgs_nhd_watersheds.py` script performs:

1. **Connect to Database**: PostgreSQL connection pooling
2. **Fetch HUC-10 Watersheds**: Query WaterGEO WFS for HUC-10 boundaries in Tennessee
3. **Fetch HUC-12 Subwatersheds**: Query for finer-grain watershed data
4. **Fetch Flowlines**: Download NHD stream network for TN
5. **Fetch Catchments**: Download pour point catchment boundaries
6. **Transform Geometries**: Convert GeoJSON to PostGIS GEOMETRY objects
7. **Insert into Database**: Batch insert with ON CONFLICT deduplication
8. **Build Spatial Indexes**: Create PostGIS GIST indexes for performance

### Scheduling

Recommended run frequency: **Monthly** (watershed boundaries rarely change)

```bash
# Run manually
python data_sources/usgs_nhd_watersheds/etl_usgs_nhd_watersheds.py

# Or add to cron (Unix/Linux)
0 2 1 * * cd /path/to/project && python data_sources/usgs_nhd_watersheds/etl_usgs_nhd_watersheds.py

# Or Windows Task Scheduler
# Task: "TDOT NHDPlus ETL" → Run monthly at 2 AM
```

## Features

### Deduplication
- Uses `ON CONFLICT DO UPDATE` to prevent duplicate HUC codes
- Only updates if watershed data has changed (area, geometry, etc.)

### Spatial Queries
All queries leverage PostGIS spatial operators:
- Point-in-polygon (which watershed contains this project?)
- Bounding box intersection (show all watersheds in view)
- Distance calculations (nearest watershed)

### Hierarchical Relationships
- Parent/child HUC relationships maintained
- Can traverse from HUC-12 up to HUC-2 (local to regional)
- Upstream/downstream connectivity available

### Data Quality
- Filters out invalid geometries
- Validates HUC codes (12-digit format)
- Removes waterbodies from flowline analysis
- Only includes research-grade data

## Usage Examples

### Find Watershed for a TDOT Project
```python
# Given project location (35.85, -86.45), find its watershed
SELECT * FROM Watersheds 
WHERE huc_level = 'huc10' 
  AND ST_Contains(location, ST_GeomFromText('POINT(-86.45 35.85)', 4326))
LIMIT 1;
```

### List All Streams in a Watershed
```python
SELECT * FROM Flowlines 
WHERE huc_12 IN (
  SELECT huc_code FROM Watersheds 
  WHERE huc_code = '050100010101'
);
```

### Show Drainage Area for a Point
```python
SELECT area_sqmi, upslope_area_sqmi FROM Catchments
WHERE ST_Contains(location, ST_GeomFromText('POINT(-86.45 35.85)', 4326));
```

## Data Limitations

- **Temporal**: Updated annually by USGS (current: 2021 version)
- **Resolution**: HUC-12 catchments represent ~20 sq miles (suitable for regional analysis)
- **Accuracy**: National-scale dataset; some detail loss in mountainous regions
- **Stream Detail**: Excludes very small seasonal streams

## Resources

- **USGS NHDPlus Official**: https://www.usgs.gov/programs/VHP/NHD_Plus.html
- **WaterGEO**: https://www.watergeospatial.org/
- **OGC WFS Specification**: https://www.opengeospatial.org/standards/wfs
- **PostGIS Spatial Operators**: https://postgis.net/docs/reference/

## Next Steps

1. Run ETL script to populate Watersheds, Flowlines, Catchments tables
2. Create backend REST endpoints in Express server
3. Implement frontend watershed layer toggle in map
4. Add watershed filtering to project search
5. Implement upstream/downstream analysis features

