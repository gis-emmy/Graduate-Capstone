#!/usr/bin/env python3
"""
eBird Observations ETL Script
Fetches bird observation data from eBird API and loads into PostgreSQL
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import psycopg2
from dotenv import load_dotenv

# Configuration
load_dotenv()

EBIRD_API = "https://api.ebird.org/v2"
TN_REGION = "US-TN"  # Region code for Tennessee

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

class eBirdETL:
    """ETL for eBird observation data"""
    
    def __init__(self):
        self.conn = None
        self.session = requests.Session()
        self.session.timeout = 30
        self.session.headers.update({
            'User-Agent': 'TDOT-Environmental-Viewer/1.0'
        })
        
        # Protected/threatened bird species
        self.protected_species = [
            'baegl',  # Bald Eagle
            'gwhow',  # Great Horned Owl
            'puma',   # Puma
            'kipe',   # Kestrel (some populations)
        ]
    
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
    
    def get_recent_observations(self, 
                               region: str = TN_REGION,
                               days_back: int = 14) -> List[Dict]:
        """Fetch recent bird observations from eBird"""
        try:
            logger.info(f"Fetching eBird observations for {region} (last {days_back} days)...")
            
            params = {
                'back': days_back,
                'maxResults': 500,
                'fmt': 'json'
            }
            
            response = self.session.get(
                f"{EBIRD_API}/data/obs/{region}/recent",
                params=params
            )
            response.raise_for_status()
            
            observations = response.json()
            logger.info(f"Retrieved {len(observations)} recent observations")
            
            return observations
            
        except Exception as e:
            logger.error(f"Error fetching eBird observations: {e}")
            return []
    
    def get_hotspots(self, region: str = TN_REGION) -> List[Dict]:
        """Fetch popular birding locations (hotspots)"""
        try:
            logger.info(f"Fetching eBird hotspots for {region}...")
            
            response = self.session.get(
                f"{EBIRD_API}/ref/hotspot/{region}",
                params={'fmt': 'json'}
            )
            response.raise_for_status()
            
            hotspots = response.json()
            logger.info(f"Retrieved {len(hotspots)} hotspots")
            
            return hotspots
            
        except Exception as e:
            logger.error(f"Error fetching hotspots: {e}")
            return []
    
    def get_species_info(self, species_code: str) -> Dict:
        """Get species information from eBird taxonomy"""
        try:
            response = self.session.get(
                f"{EBIRD_API}/ref/taxonomy/ebird",
                params={'fmt': 'json', 'cat': 'species'}
            )
            response.raise_for_status()
            
            species_list = response.json()
            
            # Find species by code
            for species in species_list:
                if species.get('code') == species_code:
                    return species
            
            return {}
            
        except Exception as e:
            logger.error(f"Error fetching species info: {e}")
            return {}
    
    def extract_observation_data(self, obs: Dict, species_info: Dict) -> Dict:
        """Extract relevant data from eBird observation"""
        try:
            species_code = obs.get('speciesCode')
            common_name = obs.get('comName', 'Unknown')
            scientific_name = obs.get('sciName', '')
            
            # Determine if protected
            is_protected = species_code in self.protected_species
            
            return {
                'species_code': species_code,
                'common_name': common_name,
                'scientific_name': scientific_name,
                'latitude': obs.get('lat'),
                'longitude': obs.get('lng'),
                'observation_date': obs.get('obsDt', datetime.now().strftime('%Y-%m-%d')),
                'location_name': obs.get('locName', 'Unknown'),
                'observation_count': obs.get('howMany', 1),
                'protected_status': 'threatened' if is_protected else None,
                'ebird_id': obs.get('obsID')
            }
        except Exception as e:
            logger.warning(f"Error extracting observation data: {e}")
            return None
    
    def insert_environmental_data(self, obs_data: Dict) -> bool:
        """Insert bird observation into Environmental_Data table"""
        try:
            if not obs_data or not obs_data.get('latitude') or not obs_data.get('longitude'):
                return False
            
            cursor = self.conn.cursor()
            
            sql = """
            INSERT INTO Environmental_Data (
                data_category, data_type, data_source, location,
                species_name, protected_status, measurement_date,
                data_confidence, last_verified
            ) VALUES (
                %s, %s, %s, ST_GeomFromText(%s, 4326),
                %s, %s, %s,
                'high', CURRENT_DATE
            )
            ON CONFLICT DO NOTHING
            """
            
            point_wkt = f"POINT({obs_data['longitude']} {obs_data['latitude']})"
            
            cursor.execute(sql, (
                'bird_observation',
                'species_observation',
                'eBird',
                point_wkt,
                f"{obs_data['common_name']} ({obs_data['scientific_name']})",
                obs_data['protected_status'],
                obs_data['observation_date']
            ))
            
            self.conn.commit()
            cursor.close()
            return True
            
        except Exception as e:
            logger.error(f"Error inserting observation: {e}")
            self.conn.rollback()
            return False
    
    def run(self):
        """Execute full ETL pipeline"""
        try:
            self.connect_db()
            
            logger.info("=" * 60)
            logger.info("eBird Observations ETL - Starting")
            logger.info("=" * 60)
            
            # Get recent observations
            observations = self.get_recent_observations()
            
            # Get hotspots (store separately or with their own records)
            hotspots = self.get_hotspots()
            
            logger.info(f"Processing {len(observations)} observations and {len(hotspots)} hotspots...")
            
            total_inserted = 0
            for obs in observations:
                # Get species info
                species_info = self.get_species_info(obs.get('speciesCode'))
                
                obs_data = self.extract_observation_data(obs, species_info)
                if self.insert_environmental_data(obs_data):
                    total_inserted += 1
            
            logger.info("=" * 60)
            logger.info(f"ETL Complete - Inserted {total_inserted} observations")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"ETL Failed: {e}")
        finally:
            self.close_db()

if __name__ == "__main__":
    etl = eBirdETL()
    etl.run()
