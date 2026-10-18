#!/usr/bin/env python3
"""
USGS NHDPlus Watershed ETL Script

Fetches watershed boundaries (HUC levels 10, 12), flowlines (stream network),
and catchment areas from USGS NHDPlus data via WaterGEO WFS service.

No authentication required - public OGC web services.

Tables populated:
  - Watersheds (HUC-10 and HUC-12 boundaries)
  - Flowlines (NHD stream network)
  - Catchments (Pour point drainage areas)
"""

import os
import logging
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode

import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('etl_usgs_nhd_watersheds.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'tdot_env')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'dev-password')

# WaterGEO WFS Service (USGS NHDPlus public service)
WFS_BASE_URL = 'https://www.watergeospatial.org/geoserver/wfs'
TIMEOUT = 60

# Tennessee bounding box (CRS:EPSG:4326)
TN_BBOX = {
    'north': 36.6786,
    'south': 35.0056,
    'east': -81.6471,
    'west': -90.3102
}


class NHDPlusETL:
    """
    ETL processor for USGS NHDPlus watershed data
    
    Methods handle:
    - Fetching HUC-10 and HUC-12 boundaries from WFS
    - Fetching NHD flowlines (stream network)
    - Fetching catchment area pour points
    - Transforming geometries to PostGIS format
    - Bulk inserting with deduplication
    """
    
    def __init__(self):
        """Initialize ETL processor with database connection"""
        self.conn = None
        self.cursor = None
        self.total_watersheds = 0
        self.total_flowlines = 0
        self.total_catchments = 0
        
    def connect_db(self) -> bool:
        """
        Connect to PostgreSQL database
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            logger.info(f'Connecting to PostgreSQL at {DB_HOST}:{DB_PORT}/{DB_NAME}')
            self.conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            self.cursor = self.conn.cursor()
            logger.info('✓ Database connection successful')
            return True
        except psycopg2.Error as e:
            logger.error(f'✗ Database connection failed: {e}')
            return False
    
    def ensure_tables_exist(self) -> bool:
        """
        Ensure Watersheds, Flowlines, and Catchments tables exist
        
        Returns:
            bool: True if tables created/exist, False otherwise
        """
        try:
            logger.info('Checking for required tables...')
            
            # Watersheds table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS Watersheds (
                    watershed_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    huc_code VARCHAR(12) UNIQUE NOT NULL,
                    huc_level VARCHAR(10) NOT NULL,
                    name VARCHAR(200),
                    description TEXT,
                    parent_huc VARCHAR(12),
                    area_sqmi NUMERIC(10, 2),
                    location GEOMETRY(Polygon, 4326),
                    centroid GEOMETRY(Point, 4326),
                    data_source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_watersheds_huc_code 
                    ON Watersheds(huc_code);
                CREATE INDEX IF NOT EXISTS idx_watersheds_huc_level 
                    ON Watersheds(huc_level);
                CREATE INDEX IF NOT EXISTS idx_watersheds_location 
                    ON Watersheds USING GIST(location);
            """)
            
            # Flowlines table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS Flowlines (
                    flowline_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    reach_code VARCHAR(14),
                    stream_name VARCHAR(200),
                    stream_order SMALLINT,
                    length_miles NUMERIC(10, 2),
                    huc_12 VARCHAR(12),
                    geometry GEOMETRY(LineString, 4326),
                    data_source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_flowlines_huc_12 
                    ON Flowlines(huc_12);
                CREATE INDEX IF NOT EXISTS idx_flowlines_stream_name 
                    ON Flowlines(stream_name);
                CREATE INDEX IF NOT EXISTS idx_flowlines_geometry 
                    ON Flowlines USING GIST(geometry);
            """)
            
            # Catchments table
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS Catchments (
                    catchment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    huc_12 VARCHAR(12),
                    area_sqmi NUMERIC(10, 2),
                    upslope_area_sqmi NUMERIC(10, 2),
                    location GEOMETRY(Polygon, 4326),
                    pour_point GEOMETRY(Point, 4326),
                    data_source VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_catchments_huc_12 
                    ON Catchments(huc_12);
                CREATE INDEX IF NOT EXISTS idx_catchments_location 
                    ON Catchments USING GIST(location);
            """)
            
            self.conn.commit()
            logger.info('✓ All required tables exist')
            return True
            
        except psycopg2.Error as e:
            logger.error(f'✗ Table creation failed: {e}')
            self.conn.rollback()
            return False
    
    def fetch_wfs_data(self, feature_type: str, huc_level: Optional[str] = None) -> Optional[Dict]:
        """
        Fetch data from WaterGEO WFS service
        
        Args:
            feature_type: WFS feature type ('nhd_h_' prefix, e.g., 'nhd_h_wbd_huc10')
            huc_level: Optional HUC level filter
            
        Returns:
            dict: GeoJSON FeatureCollection or None if request failed
        """
        try:
            # Build WFS request
            params = {
                'service': 'WFS',
                'version': '2.0.0',
                'request': 'GetFeature',
                'typeNames': feature_type,
                'outputFormat': 'application/json',
                'CQL_FILTER': f"BBOX(the_geom, {TN_BBOX['west']}, {TN_BBOX['south']}, {TN_BBOX['east']}, {TN_BBOX['north']})"
            }
            
            url = f"{WFS_BASE_URL}?{urlencode(params)}"
            logger.info(f'Fetching {feature_type} from WFS...')
            
            response = requests.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            feature_count = len(data.get('features', []))
            logger.info(f'✓ Retrieved {feature_count} features from {feature_type}')
            
            return data
            
        except requests.RequestException as e:
            logger.error(f'✗ WFS request failed for {feature_type}: {e}')
            return None
        except json.JSONDecodeError as e:
            logger.error(f'✗ Invalid JSON response from WFS: {e}')
            return None
    
    def extract_watershed_data(self, feature: Dict) -> Optional[Dict]:
        """
        Extract watershed properties from WFS feature
        
        Args:
            feature: GeoJSON feature from WFS response
            
        Returns:
            dict: Extracted watershed data or None if invalid
        """
        try:
            props = feature.get('properties', {})
            geom = feature.get('geometry', {})
            
            # Extract HUC code (varies by WFS layer)
            huc_code = (props.get('HUC10') or props.get('HUC12') or 
                       props.get('hu_10_gid') or props.get('hu_12_gid'))
            
            if not huc_code or len(str(huc_code)) < 8:
                return None
            
            huc_code = str(huc_code).zfill(12)  # Pad to 12 digits
            
            # Determine HUC level
            huc_level = f'huc{len(huc_code)}'
            
            # Extract name
            name = props.get('NAME') or props.get('name') or f'Watershed {huc_code}'
            
            # Calculate area (convert from sq meters to sq miles if needed)
            area_sqmi = props.get('AREA', 0)
            if area_sqmi and area_sqmi > 100000:  # Likely in sq meters
                area_sqmi = area_sqmi / 2.58999  # Convert to sq miles
            
            return {
                'huc_code': huc_code,
                'huc_level': huc_level,
                'name': name,
                'area_sqmi': round(area_sqmi, 2) if area_sqmi else None,
                'geometry': json.dumps(geom),
                'data_source': 'USGS NHDPlus'
            }
            
        except Exception as e:
            logger.warning(f'Failed to extract watershed data: {e}')
            return None
    
    def extract_flowline_data(self, feature: Dict) -> Optional[Dict]:
        """
        Extract flowline properties from WFS feature
        
        Args:
            feature: GeoJSON feature from WFS response
            
        Returns:
            dict: Extracted flowline data or None if invalid
        """
        try:
            props = feature.get('properties', {})
            geom = feature.get('geometry', {})
            
            if geom.get('type') != 'LineString':
                return None
            
            # Extract stream properties
            reach_code = props.get('REACH_CODE') or props.get('reach_code')
            stream_name = props.get('GNIS_NAME') or props.get('gnis_name') or 'Unnamed Stream'
            stream_order = props.get('STREAM_ORDER') or props.get('stream_order') or 0
            
            # Extract HUC-12 from reach code or properties
            huc_12 = None
            if reach_code and len(str(reach_code)) >= 12:
                huc_12 = str(reach_code)[:12]
            else:
                huc_12 = props.get('HUC_12') or props.get('huc_12')
            
            # Calculate length (convert from meters to miles if needed)
            length_miles = props.get('Shape_Length') or props.get('shape_length') or 0
            if length_miles and length_miles > 100:  # Likely in meters
                length_miles = length_miles * 0.000621371  # Convert to miles
            
            return {
                'reach_code': reach_code,
                'stream_name': stream_name[:200],
                'stream_order': int(stream_order),
                'length_miles': round(length_miles, 2) if length_miles else None,
                'huc_12': huc_12,
                'geometry': json.dumps(geom),
                'data_source': 'USGS NHDPlus'
            }
            
        except Exception as e:
            logger.warning(f'Failed to extract flowline data: {e}')
            return None
    
    def insert_watersheds(self, features: List[Dict]) -> int:
        """
        Insert watersheds into database with deduplication
        
        Args:
            features: List of GeoJSON features
            
        Returns:
            int: Number of rows inserted/updated
        """
        try:
            records = []
            for feature in features:
                data = self.extract_watershed_data(feature)
                if data:
                    records.append((
                        data['huc_code'],
                        data['huc_level'],
                        data['name'],
                        None,  # description
                        None,  # parent_huc
                        data['area_sqmi'],
                        f"ST_GeomFromGeoJSON('{data['geometry']}')",
                        f"ST_Centroid(ST_GeomFromGeoJSON('{data['geometry']}')",
                        data['data_source']
                    ))
            
            if not records:
                logger.warning('No valid watershed records to insert')
                return 0
            
            # Bulk insert with ON CONFLICT
            insert_sql = """
                INSERT INTO Watersheds 
                (huc_code, huc_level, name, description, parent_huc, area_sqmi, 
                 location, centroid, data_source)
                VALUES %s
                ON CONFLICT (huc_code) DO UPDATE SET
                    name = EXCLUDED.name,
                    area_sqmi = EXCLUDED.area_sqmi,
                    updated_at = CURRENT_TIMESTAMP
            """
            
            execute_values(self.cursor, insert_sql, records, template=None)
            self.conn.commit()
            
            count = len(records)
            self.total_watersheds += count
            logger.info(f'✓ Inserted/updated {count} watersheds')
            
            return count
            
        except psycopg2.Error as e:
            logger.error(f'✗ Watershed insertion failed: {e}')
            self.conn.rollback()
            return 0
    
    def insert_flowlines(self, features: List[Dict]) -> int:
        """
        Insert flowlines into database with deduplication
        
        Args:
            features: List of GeoJSON features
            
        Returns:
            int: Number of rows inserted
        """
        try:
            records = []
            for feature in features:
                data = self.extract_flowline_data(feature)
                if data:
                    records.append((
                        data['reach_code'],
                        data['stream_name'],
                        data['stream_order'],
                        data['length_miles'],
                        data['huc_12'],
                        f"ST_GeomFromGeoJSON('{data['geometry']}'",
                        data['data_source']
                    ))
            
            if not records:
                logger.warning('No valid flowline records to insert')
                return 0
            
            # Bulk insert with ON CONFLICT
            insert_sql = """
                INSERT INTO Flowlines 
                (reach_code, stream_name, stream_order, length_miles, 
                 huc_12, geometry, data_source)
                VALUES %s
                ON CONFLICT DO NOTHING
            """
            
            execute_values(self.cursor, insert_sql, records, template=None)
            self.conn.commit()
            
            count = len(records)
            self.total_flowlines += count
            logger.info(f'✓ Inserted {count} flowlines')
            
            return count
            
        except psycopg2.Error as e:
            logger.error(f'✗ Flowline insertion failed: {e}')
            self.conn.rollback()
            return 0
    
    def run(self) -> bool:
        """
        Execute full ETL pipeline for NHDPlus data
        
        Returns:
            bool: True if pipeline completed successfully
        """
        try:
            logger.info('=' * 60)
            logger.info('USGS NHDPlus Watershed ETL Pipeline')
            logger.info('=' * 60)
            
            # Connect to database
            if not self.connect_db():
                return False
            
            # Ensure tables exist
            if not self.ensure_tables_exist():
                return False
            
            # Fetch HUC-10 watersheds
            logger.info('\n--- Processing HUC-10 Watersheds ---')
            huc10_data = self.fetch_wfs_data('nhd_h:wbd_huc10')
            if huc10_data:
                self.insert_watersheds(huc10_data.get('features', []))
            
            # Fetch HUC-12 subwatersheds
            logger.info('\n--- Processing HUC-12 Subwatersheds ---')
            huc12_data = self.fetch_wfs_data('nhd_h:wbd_huc12')
            if huc12_data:
                self.insert_watersheds(huc12_data.get('features', []))
            
            # Fetch flowlines (NHD stream network)
            logger.info('\n--- Processing NHD Flowlines (Streams) ---')
            flowlines_data = self.fetch_wfs_data('nhd_h:nhdflowline')
            if flowlines_data:
                self.insert_flowlines(flowlines_data.get('features', []))
            
            # Summary
            logger.info('\n' + '=' * 60)
            logger.info('ETL Pipeline Complete')
            logger.info(f'✓ Watersheds inserted: {self.total_watersheds}')
            logger.info(f'✓ Flowlines inserted: {self.total_flowlines}')
            logger.info('=' * 60)
            
            return True
            
        except Exception as e:
            logger.error(f'✗ ETL pipeline failed: {e}')
            return False
        
        finally:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            logger.info('Database connection closed')


def main():
    """Main entry point"""
    etl = NHDPlusETL()
    success = etl.run()
    exit(0 if success else 1)


if __name__ == '__main__':
    main()
