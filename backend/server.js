// API Server
// ================================================

const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');

// load .env
dotenv.config();

// initialize express
const app = express();
const PORT = process.env.PORT || 3001;

// middleware
app.use(cors());
app.use(express.json());

// generic status endpoint
app.get('/api/health', (req, res) => {
  res.status(200).json({
    status: 'Backend is running!',
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV || 'development'
  });
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
app.get('/api/projects', (req, res) => {
  res.status(200).json({
    message: 'Proj Endpoint',
    status: 'placeholder'
  });
});

app.get('/api/environmental-data', (req, res) => {
  res.status(200).json({
    message: 'Environ Endpoint',
    status: 'placeholder'
  });
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

module.exports = app;
