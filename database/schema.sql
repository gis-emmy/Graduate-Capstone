-- TDOT Environmental Data Visualization Platform
-- PostgreSQL 15 - Corrected Schema

-- TDOT_Projects Table
CREATE TABLE IF NOT EXISTS TDOT_Projects (
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_name VARCHAR(255) NOT NULL,
    project_number VARCHAR(50) UNIQUE,
    description TEXT,
    status VARCHAR(50),
    project_type VARCHAR(100),
    start_date DATE,
    completion_date DATE,
    estimated_completion DATE,
    latitude NUMERIC(10, 8),
    longitude NUMERIC(11, 8),
    region VARCHAR(100),
    county VARCHAR(100),
    municipalities TEXT,
    project_cost DECIMAL(12, 2),
    funding_source VARCHAR(255),
    contractor_name VARCHAR(255),
    estimated_impact_area DECIMAL(10, 2),
    project_manager VARCHAR(255),
    contact_email VARCHAR(255),
    contact_phone VARCHAR(20),
    data_source VARCHAR(255),
    data_confidence VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tdot_status ON TDOT_Projects(status);
CREATE INDEX IF NOT EXISTS idx_tdot_county ON TDOT_Projects(county);
CREATE INDEX IF NOT EXISTS idx_tdot_region ON TDOT_Projects(region);
CREATE INDEX IF NOT EXISTS idx_tdot_location ON TDOT_Projects(latitude, longitude);

-- Environmental_Data Table
CREATE TABLE IF NOT EXISTS Environmental_Data (
    env_data_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    data_category VARCHAR(100),
    data_type VARCHAR(100),
    data_source VARCHAR(255),
    latitude NUMERIC(10, 8),
    longitude NUMERIC(11, 8),
    value NUMERIC(12, 4),
    unit VARCHAR(50),
    measurement_date TIMESTAMP,
    data_quality_flag VARCHAR(50),
    is_validated BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_env_category ON Environmental_Data(data_category);
CREATE INDEX IF NOT EXISTS idx_env_source ON Environmental_Data(data_source);
CREATE INDEX IF NOT EXISTS idx_env_date ON Environmental_Data(measurement_date);
CREATE INDEX IF NOT EXISTS idx_env_location ON Environmental_Data(latitude, longitude);

-- Watersheds Table (USGS NHDPlus)
CREATE TABLE IF NOT EXISTS Watersheds (
    watershed_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    huc12 VARCHAR(12) UNIQUE NOT NULL,
    huc_name VARCHAR(255),
    states_list VARCHAR(500),
    total_area_sqkm NUMERIC(12, 2),
    area_sqkm NUMERIC(12, 2),
    center_lat NUMERIC(10, 8),
    center_lon NUMERIC(11, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_watershed_huc ON Watersheds(huc12);
CREATE INDEX IF NOT EXISTS idx_watershed_location ON Watersheds(center_lat, center_lon);

-- Flowlines Table (USGS NHDPlus)
CREATE TABLE IF NOT EXISTS Flowlines (
    flowline_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gnis_id VARCHAR(10),
    gnis_name VARCHAR(255),
    flowline_type VARCHAR(100),
    length_m NUMERIC(12, 2),
    huc12 VARCHAR(12),
    start_lat NUMERIC(10, 8),
    start_lon NUMERIC(11, 8),
    end_lat NUMERIC(10, 8),
    end_lon NUMERIC(11, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_flowline_name ON Flowlines(gnis_name);
CREATE INDEX IF NOT EXISTS idx_flowline_huc ON Flowlines(huc12);

-- Catchments Table (USGS NHDPlus)
CREATE TABLE IF NOT EXISTS Catchments (
    catchment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    catchment_code VARCHAR(50) UNIQUE NOT NULL,
    huc12 VARCHAR(12),
    area_sqkm NUMERIC(12, 2),
    center_lat NUMERIC(10, 8),
    center_lon NUMERIC(11, 8),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_catchment_huc ON Catchments(huc12);
CREATE INDEX IF NOT EXISTS idx_catchment_location ON Catchments(center_lat, center_lon);
