// API Server
// ================================================

const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const { Pool } = require('pg');

// load .env
dotenv.config();

// initialize express
const app = express();
const PORT = process.env.PORT || 3001;

// Initialize PostgreSQL connection pool
const pool = new Pool({
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'dev-password',
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'tdot_env'
});

// Handle pool errors
pool.on('error', (err) => {
  console.error('Unexpected error on idle client', err);
});

// Test database connection
pool.query('SELECT NOW()', (err, res) => {
  if (err) {
    console.warn('Database connection warning:', err.message);
  } else {
    console.log('✓ Database connected successfully');
  }
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
    message: 'TDOT Project Viewer - Backend API',
    version: '1.0.0',
    endpoints: {
      health: '/api/health',
      projects: '/api/projects',
      environmental: '/api/environmental-data'
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
    const limit = Math.min(parseInt(req.query.limit) || 20, 100);
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
    const countResult = await queryDatabase(`SELECT COUNT(*) FROM Environmental_Data${whereClause}`, params);
    const total = countResult.success ? countResult.data[0].count : 0;

    // Get paginated results
    const sql = `SELECT 
      env_data_id, data_category, data_type, data_source, 
      species_name, protected_status, habitat_type, measurement_value,
      measurement_unit, measurement_date, data_confidence, updated_at
      FROM Environmental_Data${whereClause}
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
app.listen(PORT, () => {
  console.log(`

    Backend Server
    Environment: ${(process.env.NODE_ENV || 'development').padEnd(35)}
    Server running on: http://localhost:${PORT}
    Health check: http://localhost:${PORT}/api/health

  `);
});

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\nShutting down gracefully...');
  await pool.end();
  process.exit(0);
});

module.exports = app;
