// API Server
// ================================================

const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const { Pool } = require('pg');

// Load .env only if file exists (for local dev)
// On EB, environment variables are already set in OS
try {
  dotenv.config();
} catch (err) {
  console.log('No .env file (expected on EB)');
}

// initialize express
const app = express();
const PORT = process.env.PORT || 3001;

// Initialize PostgreSQL connection pool
const pool = new Pool({
  user: process.env.DB_USER || 'postgres',
  password: process.env.RDS_PASSWORD || process.env.DB_PASSWORD || 'dev-password',
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'tdot_env',
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

// Handle pool errors
pool.on('error', (err) => {
  console.error('Unexpected error on idle client', err);
});

// Database query helper function
async function queryDatabase(sql, params = []) {
  try {
    const result = await pool.query(sql, params);
    return { success: true, data: result.rows, rowCount: result.rowCount };
  } catch (error) {
    console.error('Database query error:', error);
    return { success: false, error: error.message };
  }
}

// middleware
app.use(cors());
app.use(express.json());

// generic status endpoint
app.get('/api/health', async (req, res) => {
  try {
    // Test database connection
    await pool.query('SELECT NOW()');
    const dbStatus = 'connected';
    
    res.status(200).json({
      status: 'Backend is running!',
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'development',
      database: {
        status: dbStatus,
        host: process.env.DB_HOST || 'localhost',
        port: process.env.DB_PORT || 5432,
        name: process.env.DB_NAME || 'tdot_env'
      }
    });
  } catch (error) {
    res.status(503).json({
      status: 'Backend running, database unavailable',
      timestamp: new Date().toISOString(),
      environment: process.env.NODE_ENV || 'development',
      database: {
        status: 'disconnected',
        error: error.message,
        host: process.env.DB_HOST || 'localhost',
        port: process.env.DB_PORT || 5432,
        name: process.env.DB_NAME || 'tdot_env'
      }
    });
  }
});

// define root
app.get('/', (req, res) => {
  res.status(200).json({
    message: 'TDOT Environmental Data Viewer - Backend API',
    version: '1.0.0',
    status: 'active',
    endpoints: {
      health: 'GET /api/health',
      projects: 'GET /api/projects?limit=20&offset=0&county=Knox&status=In Progress',
      environmental: 'GET /api/environmental-data?limit=50&category=water_quality',
      waterQuality: 'GET /api/water-quality',
      biodiversity: 'GET /api/biodiversity',
      watersheds: 'GET /api/watersheds',
      dataSummary: 'GET /api/data-summary'
    },
    database: {
      host: process.env.DB_HOST || 'localhost',
      port: process.env.DB_PORT || 5432,
      database: process.env.DB_NAME || 'tdot_env'
    }
  });
});

// Placeholders
app.get('/api/projects', async (req, res) => {
  try {
    // Get query parameters
    const limit = Math.min(parseInt(req.query.limit) || 20, 100); // Max 100
    const offset = parseInt(req.query.offset) || 0;
    const status = req.query.status; // Filter by status
    const county = req.query.county; // Filter by county
    const region = req.query.region; // Filter by region

    // Build WHERE clause
    let whereClause = '';
    let params = [];

    if (status) {
      whereClause += `status = $${params.length + 1} AND `;
      params.push(status);
    }
    if (county) {
      whereClause += `county = $${params.length + 1} AND `;
      params.push(county);
    }
    if (region) {
      whereClause += `region = $${params.length + 1} AND `;
      params.push(region);
    }

    // Remove trailing AND
    if (whereClause) {
      whereClause = whereClause.slice(0, -5); // Remove ' AND '
      whereClause = ' WHERE ' + whereClause;
    }

    // Get total count
    const countResult = await queryDatabase(`SELECT COUNT(*) FROM TDOT_Projects${whereClause}`, params);
    const total = countResult.success ? countResult.data[0].count : 0;

    // Get paginated results
    const sql = `SELECT 
      project_id, project_name, project_number, description, status, 
      project_type, start_date, completion_date, region, county,
      project_cost, data_confidence, updated_at
      FROM TDOT_Projects${whereClause}
      ORDER BY updated_at DESC
      LIMIT $${params.length + 1} OFFSET $${params.length + 2}`;
    
    params.push(limit, offset);
    const result = await queryDatabase(sql, params);

    if (result.success) {
      res.status(200).json({
        success: true,
        data: result.data,
        pagination: {
          total,
          limit,
          offset,
          hasMore: offset + limit < total
        }
      });
    } else {
      res.status(500).json({
        success: false,
        error: 'Failed to retrieve projects',
        message: result.error
      });
    }
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Internal server error',
      message: error.message
    });
  }
});

app.get('/api/environmental-data', async (req, res) => {
  try {
    const limit = Math.min(parseInt(req.query.limit) || 50, 5000);
    const offset = parseInt(req.query.offset) || 0;
    const category = req.query.category;
    const source = req.query.source;

    let whereClause = '';
    let params = [];

    if (category) {
      whereClause += `data_category = $${params.length + 1} AND `;
      params.push(category);
    }
    if (source) {
      whereClause += `data_source = $${params.length + 1} AND `;
      params.push(source);
    }

    if (whereClause) {
      whereClause = whereClause.slice(0, -5);
      whereClause = ' WHERE ' + whereClause;
    }

    // Get total count
    const countResult = await queryDatabase(`SELECT COUNT(*) FROM environmental_data${whereClause}`, params);
    const total = countResult.success ? countResult.data[0].count : 0;

    // Get paginated results
    const sql = `SELECT 
      env_data_id, data_category, data_type, data_source, 
      latitude, longitude, value, unit, measurement_date, updated_at
      FROM environmental_data${whereClause}
      ORDER BY measurement_date DESC
      LIMIT $${params.length + 1} OFFSET $${params.length + 2}`;
    
    params.push(limit, offset);
    const result = await queryDatabase(sql, params);

    if (result.success) {
      res.status(200).json({
        success: true,
        count: result.data.length,
        data: result.data,
        pagination: {
          total,
          limit,
          offset,
          hasMore: offset + limit < total
        }
      });
    } else {
      res.status(500).json({
        success: false,
        error: 'Failed to retrieve environmental data',
        message: result.error
      });
    }
  } catch (error) {
    res.status(500).json({
      success: false,
      error: 'Internal server error',
      message: error.message
    });
  }
});

// Get water quality data specifically
app.get('/api/water-quality', async (req, res) => {
  try {
    const result = await queryDatabase(
      `SELECT env_data_id, data_type, latitude, longitude, value, unit, measurement_date, data_source
       FROM environmental_data 
       WHERE data_category = 'water_quality' 
       ORDER BY measurement_date DESC LIMIT 100`
    );
    
    if (result.success) {
      res.status(200).json({
        success: true,
        category: 'water_quality',
        count: result.data.length,
        data: result.data
      });
    } else {
      res.status(500).json({ success: false, error: result.error });
    }
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get biodiversity data
app.get('/api/biodiversity', async (req, res) => {
  try {
    const result = await queryDatabase(
      `SELECT env_data_id, data_type, latitude, longitude, value, unit, measurement_date, data_source
       FROM environmental_data 
       WHERE data_category = 'biodiversity' 
       ORDER BY measurement_date DESC LIMIT 100`
    );
    
    if (result.success) {
      res.status(200).json({
        success: true,
        category: 'biodiversity',
        count: result.data.length,
        data: result.data
      });
    } else {
      res.status(500).json({ success: false, error: result.error });
    }
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get watersheds
app.get('/api/watersheds', async (req, res) => {
  try {
    const result = await queryDatabase(
      `SELECT watershed_id, huc12, huc_name, center_lat, center_lon, area_sqkm
       FROM watersheds 
       ORDER BY area_sqkm DESC LIMIT 50`
    );
    
    if (result.success) {
      res.status(200).json({
        success: true,
        count: result.data.length,
        data: result.data
      });
    } else {
      res.status(500).json({ success: false, error: result.error });
    }
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get data summary (counts by category)
app.get('/api/data-summary', async (req, res) => {
  try {
    const sql = `
      SELECT 
        'environmental_data' as type,
        data_category,
        COUNT(*) as count,
        COUNT(DISTINCT data_source) as sources
      FROM environmental_data
      GROUP BY data_category
      UNION ALL
      SELECT 
        'watersheds' as type,
        'watershed' as data_category,
        COUNT(*) as count,
        1 as sources
      FROM watersheds
      ORDER BY type, data_category
    `;
    
    const result = await queryDatabase(sql);
    
    if (result.success) {
      // Calculate totals
      let totalRecords = 0;
      let categories = {};
      
      for (const row of result.data) {
        totalRecords += row.count;
        if (row.data_category === 'watershed') {
          categories.watershed = { count: row.count, sources: row.sources };
        } else {
          categories[row.data_category] = { count: row.count, sources: row.sources };
        }
      }
      
      res.status(200).json({
        success: true,
        totalRecords,
        byCategory: categories,
        timestamp: new Date().toISOString()
      });
    } else {
      res.status(500).json({ success: false, error: result.error });
    }
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(500).json({
    error: 'Internal server error',
    message: process.env.NODE_ENV === 'development' ? err.message : 'Something went wrong'
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'Not found',
    message: `Route ${req.path} does not exist`
  });
});

// Start server
const server = app.listen(PORT, () => {
  console.log(`

    Backend Server
    Environment: ${(process.env.NODE_ENV || 'development').padEnd(35)}
    Server running on: http://localhost:${PORT}
    Health check: http://localhost:${PORT}/api/health
    Database: ${process.env.DB_HOST || 'localhost'}:${process.env.DB_PORT || 5432}

  `);
});

// Handle startup errors
server.on('error', (err) => {
  console.error('Server error:', err);
  process.exit(1);
});

process.on('uncaughtException', (err) => {
  console.error('Uncaught exception:', err);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled rejection at:', promise, 'reason:', reason);
  // Don't exit - let the app continue
});

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\nShutting down gracefully...');
  await pool.end();
  process.exit(0);
});

module.exports = app;
