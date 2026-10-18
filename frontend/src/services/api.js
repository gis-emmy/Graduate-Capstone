import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';

/**
 * TDOT Projects API Service
 * Handles all API calls related to TDOT projects
 */
export const projectsAPI = {
  /**
   * Get all projects with optional filtering and pagination
   * @param {Object} params - Query parameters
   * @param {number} params.limit - Results per page (1-100, default 20)
   * @param {number} params.offset - Pagination offset (default 0)
   * @param {string} params.status - Filter by project status
   * @param {string} params.county - Filter by county
   * @param {string} params.region - Filter by region
   * @returns {Promise} API response with projects and pagination info
   */
  getAll: async (params = {}) => {
    try {
      const defaultParams = {
        limit: 20,
        offset: 0,
        ...params
      };
      const response = await axios.get(`${API_BASE_URL}/api/projects`, {
        params: defaultParams
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching projects:', error);
      throw error;
    }
  },

  /**
   * Get projects by status
   * @param {string} status - Project status to filter by
   * @param {number} limit - Results per page
   * @param {number} offset - Pagination offset
   * @returns {Promise} Filtered projects
   */
  getByStatus: async (status, limit = 20, offset = 0) => {
    return projectsAPI.getAll({ status, limit, offset });
  },

  /**
   * Get projects by county
   * @param {string} county - County name to filter by
   * @param {number} limit - Results per page
   * @param {number} offset - Pagination offset
   * @returns {Promise} Filtered projects
   */
  getByCounty: async (county, limit = 20, offset = 0) => {
    return projectsAPI.getAll({ county, limit, offset });
  },

  /**
   * Get projects by region
   * @param {string} region - Region to filter by (East TN, Middle TN, West TN)
   * @param {number} limit - Results per page
   * @param {number} offset - Pagination offset
   * @returns {Promise} Filtered projects
   */
  getByRegion: async (region, limit = 20, offset = 0) => {
    return projectsAPI.getAll({ region, limit, offset });
  }
};

/**
 * Environmental Data API Service
 * Handles all API calls related to environmental data
 */
export const environmentalAPI = {
  /**
   * Get all environmental data with optional filtering and pagination
   * @param {Object} params - Query parameters
   * @param {number} params.limit - Results per page (1-100, default 20)
   * @param {number} params.offset - Pagination offset (default 0)
   * @param {string} params.category - Filter by data category
   * @param {string} params.source - Filter by data source
   * @returns {Promise} API response with environmental data and pagination info
   */
  getAll: async (params = {}) => {
    try {
      const defaultParams = {
        limit: 20,
        offset: 0,
        ...params
      };
      const response = await axios.get(`${API_BASE_URL}/api/environmental-data`, {
        params: defaultParams
      });
      return response.data;
    } catch (error) {
      console.error('Error fetching environmental data:', error);
      throw error;
    }
  },

  /**
   * Get environmental data by category
   * @param {string} category - Data category to filter by
   * @param {number} limit - Results per page
   * @param {number} offset - Pagination offset
   * @returns {Promise} Filtered environmental data
   */
  getByCategory: async (category, limit = 20, offset = 0) => {
    return environmentalAPI.getAll({ category, limit, offset });
  },

  /**
   * Get environmental data by source
   * @param {string} source - Data source to filter by (USGS, TDEC, EPA, etc.)
   * @param {number} limit - Results per page
   * @param {number} offset - Pagination offset
   * @returns {Promise} Filtered environmental data
   */
  getBySource: async (source, limit = 20, offset = 0) => {
    return environmentalAPI.getAll({ source, limit, offset });
  }
};

/**
 * Health Check Service
 * Monitors backend and database connectivity
 */
export const healthAPI = {
  /**
   * Check backend and database status
   * @returns {Promise} Health status object
   */
  check: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/health`);
      return response.data;
    } catch (error) {
      console.error('Health check failed:', error);
      return {
        status: 'offline',
        error: error.message
      };
    }
  }
};

export default {
  projectsAPI,
  environmentalAPI,
  healthAPI
};
