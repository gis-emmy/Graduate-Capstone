#!/usr/bin/env python3
"""
EPA Water Quality Portal ETL Script
Fetches water quality data from EPA WQP and loads into PostgreSQL
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import psycopg2
from dotenv import load_dotenv

# Configuration
load_dotenv()

EPA_WQP_BASE_URL = "https://www.waterqualitydata.us/webservices"
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

class EPAWaterQualityETL:
    """ETL for EPA Water Quality Portal data"""
    
    def __init__(self):
        self.conn = None
        self.session = requests.Session()
        self.session.timeout = 30
        # Set user agent for EPA
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
    
    def get_wqp_results(self, 
                        state: str = 'TN',
                        days_back: int = 30,
                        limit: int = 1000) -> List[Dict]:
        """Fetch water quality results from EPA WQP"""
        try:
            logger.info(f"Fetching EPA WQP data for {state} (last {days_back} days)...")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            params = {
                'statecode': state,
                'startDateLo': start_date.strftime('%m-%d-%Y'),
                'startDateHi': end_date.strftime('%m-%d-%Y'),
                'mimeType': 'json',
                'zip': 'no'
            }
            
            response = self.session.get(
                f"{EPA_WQP_BASE_URL}/Result/search",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            results = data.get('Results', [])
            logger.info(f"Retrieved {len(results)} water quality results")
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error fetching WQP data: {e}")
            return []
    
    def transform_observation(self, result: Dict) -> Dict:
        """Transform EPA WQP result to our schema"""
        try:
            return {
                'latitude': float(result.get('LatitudeMeasure', 0)),
                'longitude': float(result.get('LongitudeMeasure', 0)),
                'characteristic_name': result.get('CharacteristicName', 'Unknown'),
                'result_value': result.get('ResultMeasureValue'),
                'result_unit': result.get('ResultMeasure', {}).get('MeasureUnitCode', ''),
                'sample_date': result.get('ActivityStartDate', datetime.now().strftime('%Y-%m-%d')),
                'organization_name': result.get('OrganizationFormalName', 'Unknown'),
                'provider': result.get('ProviderName', 'EPA WQP'),
                'site_identifier': result.get('MonitoringLocationIdentifier', ''),
                'sample_type': result.get('ActivityTypeCode', 'Field Msr/Obs')
            }
        except Exception as e:
            logger.warning(f"Error transforming observation: {e}")
            return None
    
    def insert_environmental_data(self, observation: Dict) -> bool:
        """Insert water quality observation into Environmental_Data table"""
        try:
            if not observation:
                return False
            
            cursor = self.conn.cursor()
            
            # Validate coordinates
            lat = observation['latitude']
            lon = observation['longitude']
            if lat < -90 or lat > 90 or lon < -180 or lon > 180:
                logger.warning(f"Invalid coordinates: {lat}, {lon}")
                cursor.close()
                return False
            
            # Try to convert result_value to float
            try:
                value = float(observation['result_value']) if observation['result_value'] else None
            except (ValueError, TypeError):
                value = None
            
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
            ON CONFLICT DO NOTHING
            """
            
            point_wkt = f'POINT({lon} {lat})'
            
            cursor.execute(sql, (
                'water_quality',
                'measurement',
                f"EPA WQP ({observation['provider']})",
                point_wkt,
                value,
                observation['result_unit'],
                observation['sample_date']
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
            logger.info("EPA Water Quality Portal ETL - Starting")
            logger.info("=" * 60)
            
            # Get WQP results
            results = self.get_wqp_results(state='TN', days_back=30)
            if not results:
                logger.warning("No results found")
                return
            
            # Process each result
            total_inserted = 0
            for result in results:
                observation = self.transform_observation(result)
                if self.insert_environmental_data(observation):
                    total_inserted += 1
            
            logger.info("=" * 60)
            logger.info(f"ETL Complete - Inserted {total_inserted} records")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"ETL Failed: {e}")
        finally:
            self.close_db()

if __name__ == "__main__":
    etl = EPAWaterQualityETL()
    etl.run()
