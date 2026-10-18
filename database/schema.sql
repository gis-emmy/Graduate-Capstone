-- TDOT Environmental Data Visualization Platform
-- PostgreSQL 15

-- Extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS uuid-ossp;

-- TDOT_Projects
CREATE TABLE IF NOT EXISTS TDOT_Projects (
    project_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_name VARCHAR(255) NOT NULL,
    project_number VARCHAR(50) UNIQUE,
    description TEXT,
    status VARCHAR(50),
    project_type VARCHAR(100),
    start_date DATE,
    completion_date DATE,
    estimated_completion DATE,
    location GEOMETRY(POINT, 4326),
    bounding_box GEOMETRY(POLYGON, 4326),
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
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_confidence VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_status (status),
    INDEX idx_county (county),
    INDEX idx_region (region),
    INDEX idx_location USING GIST (location)
);

-- Environmental_Data
CREATE TABLE IF NOT EXISTS Environmental_Data (
    env_data_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    data_category VARCHAR(100),
    data_type VARCHAR(100),
    data_source VARCHAR(255),
    location GEOMETRY(GEOMETRY, 4326),
    bounding_box GEOMETRY(POLYGON, 4326),
    species_name VARCHAR(255),
    protected_status VARCHAR(50),
    habitat_type VARCHAR(100),
    habitat_condition VARCHAR(50),
    measurement_value DECIMAL(10, 4),
    measurement_unit VARCHAR(50),
    measurement_date DATE,
    related_project_id UUID REFERENCES TDOT_Projects(project_id) ON DELETE SET NULL,
    data_confidence VARCHAR(50),
    last_verified DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_category (data_category),
    INDEX idx_source (data_source),
    INDEX idx_related_project (related_project_id),
    INDEX idx_location USING GIST (location)
);

-- Citizen_Science_Observations
CREATE TABLE IF NOT EXISTS Citizen_Science_Observations (
    observation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    observer_name VARCHAR(255),
    observer_email VARCHAR(255),
    observer_phone VARCHAR(20),
    is_anonymous BOOLEAN DEFAULT FALSE,
    observation_type VARCHAR(100),
    species_observed VARCHAR(255),
    observation_description TEXT,
    location GEOMETRY(POINT, 4326),
    observation_date DATE,
    observation_time TIME,
    photo_url VARCHAR(255),
    photo_uploaded BOOLEAN DEFAULT FALSE,
    related_project_id UUID REFERENCES TDOT_Projects(project_id) ON DELETE SET NULL,
    related_env_data_id UUID REFERENCES Environmental_Data(env_data_id) ON DELETE SET NULL,
    verified BOOLEAN DEFAULT FALSE,
    verified_by VARCHAR(255),
    verification_notes TEXT,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_status (status),
    INDEX idx_verified (verified),
    INDEX idx_related_project (related_project_id),
    INDEX idx_location USING GIST (location)
);

-- NEPA_Compliance
CREATE TABLE IF NOT EXISTS NEPA_Compliance (
    compliance_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES TDOT_Projects(project_id) ON DELETE CASCADE,
    document_type VARCHAR(100),
    species_id VARCHAR(100),
    species_name VARCHAR(255),
    protected_status VARCHAR(50),
    habitat_impact_assessment TEXT,
    mitigation_measures TEXT,
    wetlands_present BOOLEAN,
    wetland_acreage DECIMAL(10, 2),
    water_body_impact TEXT,
    historic_resources_present BOOLEAN,
    cultural_resources_assessment TEXT,
    document_date DATE,
    public_comment_end_date DATE,
    approval_date DATE,
    responsible_agency VARCHAR(255),
    document_link VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_project (project_id),
    INDEX idx_species (species_name)
);

-- Endangered_Species_Reference
CREATE TABLE IF NOT EXISTS Endangered_Species_Reference (
    species_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scientific_name VARCHAR(255) UNIQUE NOT NULL,
    common_name VARCHAR(255),
    protected_status VARCHAR(50),
    habitat_type TEXT,
    geographic_range TEXT,
    critical_habitat_polygons GEOMETRY(MULTIPOLYGON, 4326),
    recovery_plan_link VARCHAR(255),
    management_notes TEXT,
    data_source VARCHAR(100),
    last_updated DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API_Audit_Log
CREATE TABLE IF NOT EXISTS API_Audit_Log (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    endpoint VARCHAR(255),
    method VARCHAR(10),
    status_code INT,
    response_time_ms INT,
    query_parameters TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_endpoint (endpoint),
    INDEX idx_timestamp (timestamp)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tdot_projects_updated ON TDOT_Projects(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_env_data_category ON Environmental_Data(data_category);
CREATE INDEX IF NOT EXISTS idx_env_data_updated ON Environmental_Data(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_citizen_status ON Citizen_Science_Observations(status);
CREATE INDEX IF NOT EXISTS idx_nepa_project_id ON NEPA_Compliance(project_id);

-- Sample data
INSERT INTO TDOT_Projects (
    project_name, project_number, description, status, project_type,
    start_date, completion_date, location, region, county, project_cost,
    data_source, data_confidence
) VALUES (
    'I-40 Bridge Rehabilitation - Knoxville',
    'TDOT-001',
    'Comprehensive rehabilitation of I-40 bridge structure over Tennessee River',
    'under_construction',
    'bridge',
    '2025-03-15',
    '2026-09-30',
    ST_GeomFromText('POINT(-83.9207 35.9606)', 4326),
    'East TN',
    'Knox',
    2500000.00,
    'TDOT Public API',
    'high'
) ON CONFLICT DO NOTHING;

INSERT INTO Environmental_Data (
    data_category, data_type, data_source, location, species_name,
    protected_status, data_confidence
) VALUES (
    'endangered_species',
    'habitat',
    'USFWS',
    ST_GeomFromText('POINT(-83.9207 35.9606)', 4326),
    'Gray Bat',
    'endangered',
    'high'
) ON CONFLICT DO NOTHING;

INSERT INTO Endangered_Species_Reference (
    scientific_name, common_name, protected_status, habitat_type,
    data_source
) VALUES (
    'Myotis grisescens',
    'Gray Bat',
    'Endangered',
    'Karst caves and mines; streams with riparian habitat',
    'USFWS'
) ON CONFLICT DO NOTHING;
