# Week 1 (Sept 4-8)
 - Reworked project idea based on feedback and input from intern supervision regarding position-sensitive information related to original study topic.
 - Spoke with Dr. Li and determined creation of TDOT Project Viewer with added context of external environmental datasets as a web tool would serve as a sufficient project.
 - Developed Scope, ideal datasets, and submitted new proposal inline with the updated scope of capstone project

# Week 2 (Sept 9-15)
 - Developed tentative development plan and tooling
    - Hosting and publishing using AWS Free Tier
    - Backend development using Express (node.js) with React front end for web platform
    - Mapping platform will utilize Leaflet. Other tooling may be applied as the application develops.
 - Identified key project information datasets available through Public TDOT endpoints
 - Determined use of PostGIS and PostgreSQL for hosting developed datasets or queried datasets that don't already have robust API support
 - Developed initial templating and development environment on local machine
 - Developed and published GitHub repository for transparent development and tracking.
 - Implemented full-stack infrastructure:
    - Node.js v24.21.0 backend running on port 3001
    - React 18.2.0 frontend with Vite on port 3000
    - Docker Desktop installed with PostgreSQL 15 configuration
    - GitHub Actions CI/CD pipeline (7-job workflow)
    - Comprehensive documentation (20+ markdown files in guides/)

# Weeks 3-6 (Sept 16 - Oct 18) - Phase 2: Database Integration
 - Designed comprehensive PostgreSQL schema with 6 main tables:
    - TDOT_Projects (project data with geospatial support)
    - Environmental_Data (multi-source environmental datasets)
    - Citizen_Science_Observations (crowdsourced field data)
    - NEPA_Compliance (environmental compliance documentation)
    - Endangered_Species_Reference (protected species reference data)
    - API_Audit_Log (request performance tracking)
 - Implemented database schema with PostGIS spatial support, UUID keys, and comprehensive indexes
 - Created database schema loader script (database/load-schema.ps1)
 - Connected backend to PostgreSQL:
    - Added pg connection pooling to Express server
    - Implemented database query helper function with error handling
    - Updated health endpoint to report database connection status
    - Graceful shutdown with pool cleanup
 - Implemented API endpoints with full functionality:
    - `/api/projects` - Query TDOT_Projects with filtering and pagination
    - `/api/environmental-data` - Query Environmental_Data with filtering and pagination
    - Filtering by status/county/region for projects
    - Filtering by category/source for environmental data
    - Pagination with limit/offset and hasMore indicators
 - Created Phase 2 completion documentation (PHASE_2_COMPLETE.md)
 - Created Phase 3 frontend guide (PHASE_3_FRONTEND_GUIDE.md)