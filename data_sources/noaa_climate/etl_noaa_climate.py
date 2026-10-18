#!/usr/bin/env python3
"""
NOAA Climate Data ETL Script
Fetches climate and weather data from NOAA and stores with TDOT projects
"""

import os
import logging
import requests
from typing import Dict, Tuple
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

# Configuration
load_dotenv()

NOAA_POINTS_URL = "https://api.weather.gov/points"
NOAA_GRID_DATA_URL = "https://api.weather.gov/gridpoints"
CLIMATE_API_URL = "https://www.ncei.noaa.gov/access/services/data/v1"

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

class NOAAClimateETL:
    """ETL for NOAA climate and weather data"""
    
    def __init__(self):
        self.conn = None
        self.session = requests.Session()
        self.session.timeout = 30
        self.session.headers.update({
            'User-Agent': 'TDOT-Environmental-Viewer/1.0'
        })
    
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
    
    def get_noaa_points(self, lat: float, lon: float) -> Dict:
        """Get NOAA grid point data for location"""
        try:
            response = self.session.get(
                f"{NOAA_POINTS_URL}/{lat},{lon}"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching NOAA points: {e}")
            return {}
    
    def get_current_weather(self, lat: float, lon: float) -> Dict:
        """Get current weather at specific location"""
        try:
            points = self.get_noaa_points(lat, lon)
            properties = points.get('properties', {})
            
            # Get grid point forecast
            forecast_url = properties.get('forecast')
            if not forecast_url:
                return {}
            
            forecast_response = self.session.get(forecast_url)
            forecast_response.raise_for_status()
            
            forecast_data = forecast_response.json()
            periods = forecast_data.get('properties', {}).get('periods', [])
            
            if periods:
                # Return first period (current/next forecast)
                return {
                    'temperature': periods[0].get('temperature'),
                    'temperature_unit': periods[0].get('temperatureUnit'),
                    'wind_speed': periods[0].get('windSpeed'),
                    'wind_direction': periods[0].get('windDirection'),
                    'short_forecast': periods[0].get('shortForecast'),
                    'timestamp': datetime.now().isoformat()
                }
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            return {}
    
    def get_climate_normals(self, lat: float, lon: float) -> Dict:
        """Get historical climate normals for location"""
        try:
            # Use NOAA normals database
            params = {
                'dataset': 'normal_dly',
                'dataTypes': 'TMAX,TMIN,PRCP',
                'startDate': '1991-01-01',
                'endDate': '2020-12-31',
                'boundingBox': f"{lat},{lon},{lat},{lon}",
                'units': 'metric',
                'format': 'json'
            }
            
            response = self.session.get(
                CLIMATE_API_URL,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            
            # Process normals data
            normals = {
                'annual_max_temp': None,
                'annual_min_temp': None,
                'annual_precipitation': None
            }
            
            if 'results' in data:
                results = data['results']
                # Parse aggregated values
                # (NOAA returns detailed daily data, would need aggregation)
                pass
            
            return normals
            
        except Exception as e:
            logger.error(f"Error fetching climate normals: {e}")
            return {}
    
    def get_drought_status(self, state: str = 'TN') -> Dict:
        """Get current drought status for state"""
        try:
            # US Drought Monitor provides data
            # For simplicity, query a known endpoint or return state-level drought index
            params = {
                'dataset': 'drought',
                'stateCode': state,
                'format': 'json'
            }
            
            response = self.session.get(
                CLIMATE_API_URL,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.warning(f"Could not fetch drought data: {e}")
            return {}
    
    def store_project_climate_context(self, 
                                      project_id: str,
                                      lat: float,
                                      lon: float) -> bool:
        """Store climate context for a TDOT project"""
        try:
            weather = self.get_current_weather(lat, lon)
            normals = self.get_climate_normals(lat, lon)
            
            cursor = self.conn.cursor()
            
            # Update project with climate context
            # This would require adding a climate_context JSONB field or separate table
            # For now, log the data
            logger.info(f"Climate context for project {project_id}:")
            logger.info(f"  Current temp: {weather.get('temperature')}°{weather.get('temperature_unit')}")
            logger.info(f"  Wind: {weather.get('wind_speed')} from {weather.get('wind_direction')}")
            logger.info(f"  Forecast: {weather.get('short_forecast')}")
            
            cursor.close()
            return True
            
        except Exception as e:
            logger.error(f"Error storing climate context: {e}")
            return False
    
    def run(self):
        """Execute ETL pipeline for climate data"""
        try:
            self.connect_db()
            
            logger.info("=" * 60)
            logger.info("NOAA Climate Data ETL - Starting")
            logger.info("=" * 60)
            
            # Get all TDOT projects and fetch climate context
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT project_id, 
                       ST_Y(location) as lat, 
                       ST_X(location) as lon
                FROM TDOT_Projects 
                WHERE location IS NOT NULL
                LIMIT 10
            """)
            
            projects = cursor.fetchall()
            cursor.close()
            
            for project_id, lat, lon in projects:
                logger.info(f"Fetching climate for project {project_id}")
                self.store_project_climate_context(project_id, lat, lon)
            
            logger.info("=" * 60)
            logger.info(f"ETL Complete - Processed {len(projects)} projects")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"ETL Failed: {e}")
        finally:
            self.close_db()

if __name__ == "__main__":
    etl = NOAAClimateETL()
    etl.run()
