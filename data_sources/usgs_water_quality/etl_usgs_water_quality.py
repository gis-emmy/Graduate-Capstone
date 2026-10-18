#!/usr/bin/env python3
"""
USGS Water Quality Data ETL Script
Fetches water quality data from USGS NWIS and loads into PostgreSQL
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Configuration
load_dotenv()

USGS_BASE_URL = "https://waterservices.usgs.gov/nwis"
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'tdot_env')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'dev-password')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class USGSWaterQualityETL:
    """ETL for USGS water quality data"""
    
    def __init__(self):
        self.conn = None
        self.session = requests.Session()
        self.session.timeout = 30
    
    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD
            )
            logger.info("✓ Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"✗ Database connection failed: {e}")
            raise
    
    def close_db(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def get_tn_stations(self) -> List[Dict]:
        """Fetch all water quality monitoring stations in Tennessee"""
        try:
            logger.info("Fetching USGS monitoring stations in Tennessee...")
            
            params = {
                'stateCd': 'TN',
                'siteType': 'ST',  # Stream
                'format': 'json',
                'hasDataTypeCd': 'qw'  # Quality water data
            }
            
            response = self.session.get(
                f"{USGS_BASE_URL}/qwdata",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            if 'value' in data and 'sites' in data['value']:
                stations = data['value']['sites']
                logger.info(f"Found {len(stations)} stations with water quality data")
                return stations
            else:
                logger.warning("No stations found in USGS response")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching stations: {e}")
            return []
    
    def get_recent_measurements(self, site_id: str, days_back: int = 30) -> List[Dict]:
        """Fetch recent water quality measurements for a station"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            params = {
                'sites': site_id,
                'startDT': start_date.strftime('%Y-%m-%d'),
                'endDT': end_date.strftime('%Y-%m-%d'),
                'format': 'json'
            }
            
            response = self.session.get(
                f"{USGS_BASE_URL}/qwdata",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            if 'value' in data and 'timeSeries' in data['value']:
                return data['value']['timeSeries']
            return []
            
        except Exception as e:
            logger.error(f"Error fetching measurements for {site_id}: {e}")
            return []
    
    def extract_measurements(self, timeseries: Dict) -> List[Dict]:
        """Extract individual measurements from USGS timeseries"""
        measurements = []
        
        try:
            if 'sourceInfo' not in timeseries or 'values' not in timeseries:
                return measurements
            
            source = timeseries['sourceInfo']
            site_id = source.get('siteName', 'Unknown')
            lat = source.get('geoLocation', {}).get('geogLocation', {}).get('srs', 'POINT')
            
            # Extract parameter info
            param_code = source.get('variable', {}).get('variableCode', 'unknown')
            param_name = source.get('variable', {}).get('variableName', 'Unknown')
            unit = source.get('variable', {}).get('unit', {}).get('unitCode', '')
            
            # Extract values
            for value_set in timeseries.get('values', []):
                for value in value_set.get('value', []):
                    measurements.append({
                        'site_id': site_id,
                        'parameter_code': param_code,
                        'parameter_name': param_name,
                        'unit': unit,
                        'value': value.get('value'),
                        'date_time': value.get('dateTime'),
                        'quality_codes': value.get('qualityControlLevelCode', [])
                    })
        
        except Exception as e:
            logger.warning(f"Error extracting measurements: {e}")
        
        return measurements
    
    def insert_environmental_data(self, measurement: Dict, station: Dict) -> bool:
        """Insert water quality measurement into Environmental_Data table"""
        try:
            cursor = self.conn.cursor()
            
            # Get coordinates
            lat = station.get('geoLocation', {}).get('geogLocation', {}).get('latitude')
            lon = station.get('geoLocation', {}).get('geogLocation', {}).get('longitude')
            
            if not lat or not lon:
                logger.warning(f"Missing coordinates for {measurement['site_id']}")
                return False
            
            # Map USGS parameter to our schema
            measurement_value = float(measurement['value']) if measurement['value'] else None
            measurement_unit = measurement['unit']
            measurement_date = measurement['date_time'][:10]  # YYYY-MM-DD
            
            # Determine category and data_type based on parameter
            param_code = measurement['parameter_code']
            category_map = {
                '00060': 'stream_flow',
                '00010': 'temperature',
                '00095': 'conductance',
                '00300': 'dissolved_oxygen',
                '00403': 'ph'
            }
            data_category = category_map.get(param_code, 'water_quality')
            
            sql = """
            INSERT INTO Environmental_Data (
                data_category, data_type, data_source, location,
                measurement_value, measurement_unit, measurement_date,
                data_confidence, last_verified
            ) VALUES (
                %s, %s, %s, ST_GeomFromText(%s, 4326),
                %s, %s, %s,
                'high', CURRENT_DATE
            )
            """
            
            point_wkt = f'POINT({lon} {lat})'
            
            cursor.execute(sql, (
                data_category,
                'measurement',
                'USGS NWIS',
                point_wkt,
                measurement_value,
                measurement_unit,
                measurement_date
            ))
            
            self.conn.commit()
            cursor.close()
            return True
            
        except Exception as e:
            logger.error(f"Error inserting data: {e}")
            self.conn.rollback()
            return False
    
    def run(self):
        """Execute full ETL pipeline"""
        try:
            self.connect_db()
            
            logger.info("=" * 60)
            logger.info("USGS Water Quality ETL - Starting")
            logger.info("=" * 60)
            
            # Get all Tennessee stations
            stations = self.get_tn_stations()
            if not stations:
                logger.warning("No stations found")
                return
            
            # Process each station
            total_inserted = 0
            for station in stations[:10]:  # Limit to first 10 for testing
                site_id = station.get('siteName')
                logger.info(f"Processing station: {site_id}")
                
                # Get recent measurements
                timeseries = self.get_recent_measurements(site_id)
                
                for ts in timeseries:
                    measurements = self.extract_measurements(ts)
                    
                    for measurement in measurements:
                        if self.insert_environmental_data(measurement, station):
                            total_inserted += 1
            
            logger.info("=" * 60)
            logger.info(f"ETL Complete - Inserted {total_inserted} records")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"ETL Failed: {e}")
        finally:
            self.close_db()

if __name__ == "__main__":
    etl = USGSWaterQualityETL()
    etl.run()
