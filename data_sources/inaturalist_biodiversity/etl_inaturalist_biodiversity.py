#!/usr/bin/env python3
"""
iNaturalist Biodiversity Data ETL Script
Fetches species observations from iNaturalist and loads into PostgreSQL
"""

import os
import logging
import requests
from datetime import datetime
from typing import List, Dict
import psycopg2
from dotenv import load_dotenv

# Configuration
load_dotenv()

INATURALIST_API = "https://api.inaturalist.org/v1"
TN_PLACE_ID = 38394  # iNaturalist place ID for Tennessee

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

class iNaturalistETL:
    """ETL for iNaturalist biodiversity data"""
    
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
    
    def get_tn_observations(self, 
                           days_back: int = 30,
                           limit: int = 500) -> List[Dict]:
        """Fetch recent research-grade observations from Tennessee"""
        try:
            logger.info(f"Fetching iNaturalist observations for TN (last {days_back} days)...")
            
            params = {
                'place_id': TN_PLACE_ID,
                'quality_grade': 'research',  # Only verified observations
                'order_by': 'observed_on',
                'per_page': limit,
                'page': 1
            }
            
            response = self.session.get(
                f"{INATURALIST_API}/observations",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            observations = data.get('results', [])
            logger.info(f"Retrieved {len(observations)} observations")
            
            return observations
            
        except Exception as e:
            logger.error(f"Error fetching iNaturalist data: {e}")
            return []
    
    def get_endangered_species_observations(self, limit: int = 300) -> List[Dict]:
        """Get observations of endangered/threatened species only"""
        try:
            # Define conservation status codes to filter for
            conservation_statuses = [
                'endangered',
                'threatened',
                'vulnerable',
                'near_threatened'
            ]
            
            logger.info("Fetching endangered species observations...")
            
            params = {
                'place_id': TN_PLACE_ID,
                'quality_grade': 'research',
                'conservation_status': ','.join(conservation_statuses),
                'per_page': limit,
                'page': 1
            }
            
            response = self.session.get(
                f"{INATURALIST_API}/observations",
                params=params
            )
            response.raise_for_status()
            
            data = response.json()
            observations = data.get('results', [])
            logger.info(f"Retrieved {len(observations)} endangered species observations")
            
            return observations
            
        except Exception as e:
            logger.error(f"Error fetching endangered species: {e}")
            return []
    
    def extract_observation_data(self, obs: Dict) -> Dict:
        """Extract relevant data from iNaturalist observation"""
        try:
            # Get taxonomy
            taxon = obs.get('taxon', {})
            species_name = taxon.get('name', 'Unknown')
            scientific_name = taxon.get('name', '')
            
            # Get conservation status
            conservation_status = None
            if 'conservation_status' in obs:
                cons = obs['conservation_status']
                conservation_status = cons.get('status', '').replace('_', ' ')
            
            # Get location
            location = obs.get('geom', {})
            coords = location.get('coordinates', [])
            
            return {
                'species_name': species_name,
                'scientific_name': scientific_name,
                'longitude': coords[0] if len(coords) > 0 else None,
                'latitude': coords[1] if len(coords) > 1 else None,
                'observation_date': obs.get('observed_on', datetime.now().strftime('%Y-%m-%d')),
                'conservation_status': conservation_status,
                'inaturalist_id': obs.get('id'),
                'photo_url': obs.get('photos', [{}])[0].get('medium_url') if obs.get('photos') else None,
                'quality_grade': obs.get('quality_grade', 'unknown'),
                'description': obs.get('description', '')
            }
        except Exception as e:
            logger.warning(f"Error extracting observation data: {e}")
            return None
    
    def insert_citizen_science_observation(self, obs_data: Dict) -> bool:
        """Insert observation into Citizen_Science_Observations table"""
        try:
            if not obs_data or not obs_data.get('latitude') or not obs_data.get('longitude'):
                return False
            
            cursor = self.conn.cursor()
            
            sql = """
            INSERT INTO Citizen_Science_Observations (
                species_observed, observation_type, location,
                observation_date, photo_url, observation_description,
                status, verified
            ) VALUES (
                %s, %s, ST_GeomFromText(%s, 4326),
                %s, %s, %s,
                'verified', TRUE
            )
            ON CONFLICT DO NOTHING
            """
            
            point_wkt = f"POINT({obs_data['longitude']} {obs_data['latitude']})"
            
            cursor.execute(sql, (
                obs_data['species_name'],
                'species_sighting',
                point_wkt,
                obs_data['observation_date'],
                obs_data['photo_url'],
                obs_data['description'],
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
            logger.info("iNaturalist Biodiversity ETL - Starting")
            logger.info("=" * 60)
            
            # Get all observations
            observations = self.get_tn_observations()
            
            # Also get endangered species
            endangered_obs = self.get_endangered_species_observations()
            all_observations = observations + endangered_obs
            
            logger.info(f"Processing {len(all_observations)} total observations...")
            
            total_inserted = 0
            for obs in all_observations:
                obs_data = self.extract_observation_data(obs)
                if self.insert_citizen_science_observation(obs_data):
                    total_inserted += 1
            
            logger.info("=" * 60)
            logger.info(f"ETL Complete - Inserted {total_inserted} observations")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"ETL Failed: {e}")
        finally:
            self.close_db()

if __name__ == "__main__":
    etl = iNaturalistETL()
    etl.run()
