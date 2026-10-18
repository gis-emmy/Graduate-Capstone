import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Popup, Marker, LayerGroup } from 'react-leaflet'
import L from 'leaflet'
import './App.css'
import { projectsAPI, environmentalAPI, healthAPI } from './services/api'

// Fix for default marker icons in react-leaflet
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

// Custom marker colors for different project statuses
const getStatusColor = (status) => {
  const colors = {
    'planned': '#FFA500',
    'under_review': '#FFD700',
    'under_construction': '#FF6347',
    'completed': '#32CD32',
    'archived': '#808080'
  }
  return colors[status] || '#0078D4'
}

// Create custom marker icon with color
const createStatusMarker = (status) => {
  const color = getStatusColor(status)
  return L.icon({
    iconUrl: `data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSI0MCIgdmlld0JveD0iMCAwIDI0IDQwIj48cGF0aCBkPSJNMTIgMGM2LjYyNyAwIDEyIDUuMzczIDEyIDEyIDAgNi42MjctMTIgMjgtMTIgMjgtMCAwLTEyLTIxLjM3My0xMi0yOEMwIDUuMzczIDUuMzczIDAgMTIgMHoiIGZpbGw9IiR7Y29sb3J9IiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiLz48L3N2Zz4=`,
    iconSize: [24, 40],
    iconAnchor: [12, 40],
    popupAnchor: [0, -40]
  })
}

function App() {
  // State management
  const [backendStatus, setBackendStatus] = useState('checking')
  const [projects, setProjects] = useState([])
  const [environmentalData, setEnvironmentalData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  
  // Filter state
  const [filters, setFilters] = useState({
    status: '',
    county: '',
    region: ''
  })
  
  // Pagination state
  const [pagination, setPagination] = useState({
    currentPage: 1,
    totalPages: 1,
    total: 0,
    hasMore: false
  })
  
  // Layer visibility
  const [showProjects, setShowProjects] = useState(true)
  const [showEnvironmental, setShowEnvironmental] = useState(true)
  const [selectedProject, setSelectedProject] = useState(null)

  // Center coordinates for Tennessee
  const center = [35.7478, -86.6923]
  const zoom = 7
  const pageSize = 20

  // Initialize - check backend and load data
  useEffect(() => {
    initializeApp()
  }, [])

  // Reload data when filters change
  useEffect(() => {
    if (!loading) {
      fetchProjects(1)
    }
  }, [filters])

  const initializeApp = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Check backend status
      const health = await healthAPI.check()
      setBackendStatus(health.database?.status === 'connected' ? 'running' : 'offline')
      
      // Fetch initial data
      await Promise.all([
        fetchProjects(1),
        fetchEnvironmentalData()
      ])
    } catch (err) {
      console.error('Error initializing app:', err)
      setError('Failed to load data. Please refresh the page.')
    } finally {
      setLoading(false)
    }
  }

  const fetchProjects = async (page = 1) => {
    try {
      setLoading(true)
      const offset = (page - 1) * pageSize
      
      const response = await projectsAPI.getAll({
        limit: pageSize,
        offset: offset,
        status: filters.status || undefined,
        county: filters.county || undefined,
        region: filters.region || undefined
      })

      if (response.success) {
        setProjects(response.data)
        setPagination({
          currentPage: page,
          totalPages: Math.ceil(response.pagination.total / pageSize),
          total: response.pagination.total,
          hasMore: response.pagination.hasMore
        })
      }
    } catch (err) {
      console.error('Error fetching projects:', err)
      setError('Failed to fetch projects')
    } finally {
      setLoading(false)
    }
  }

  const fetchEnvironmentalData = async () => {
    try {
      const response = await environmentalAPI.getAll({
        limit: 100
      })

      if (response.success) {
        setEnvironmentalData(response.data)
      }
    } catch (err) {
      console.error('Error fetching environmental data:', err)
    }
  }

  const handleFilterChange = (filterName, value) => {
    setFilters(prev => ({
      ...prev,
      [filterName]: value
    }))
  }

  const clearFilters = () => {
    setFilters({
      status: '',
      county: '',
      region: ''
    })
  }

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.totalPages) {
      fetchProjects(newPage)
      window.scrollTo(0, 0)
    }
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <h1>TDOT Environmental Data Visualization Platform</h1>
          <div className="status-indicator">
            <div className={`status-dot ${backendStatus === 'running' ? 'online' : 'offline'}`}></div>
            <span className="status-text">
              Backend {backendStatus === 'running' ? '✓ Connected' : '✗ Offline'}
            </span>
          </div>
        </div>
      </header>

      {/* Main content */}
      <div className="main-container">
        {/* Sidebar */}
        <aside className="sidebar">
          {/* Map controls */}
          <div className="sidebar-section">
            <h3>Map Layers</h3>
            <label className="checkbox-label">
              <input 
                type="checkbox" 
                checked={showProjects}
                onChange={(e) => setShowProjects(e.target.checked)}
              />
              Show Projects ({projects.length})
            </label>
            <label className="checkbox-label">
              <input 
                type="checkbox" 
                checked={showEnvironmental}
                onChange={(e) => setShowEnvironmental(e.target.checked)}
              />
              Show Environmental Data ({environmentalData.length})
            </label>
          </div>

          {/* Filters */}
          <div className="sidebar-section">
            <h3>Filters</h3>
            <div className="filter-group">
              <label>Status:</label>
              <select 
                value={filters.status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
              >
                <option value="">All Statuses</option>
                <option value="planned">Planned</option>
                <option value="under_review">Under Review</option>
                <option value="under_construction">Under Construction</option>
                <option value="completed">Completed</option>
                <option value="archived">Archived</option>
              </select>
            </div>

            <div className="filter-group">
              <label>Region:</label>
              <select 
                value={filters.region}
                onChange={(e) => handleFilterChange('region', e.target.value)}
              >
                <option value="">All Regions</option>
                <option value="East TN">East TN</option>
                <option value="Middle TN">Middle TN</option>
                <option value="West TN">West TN</option>
              </select>
            </div>

            <div className="filter-group">
              <label>County:</label>
              <input 
                type="text" 
                placeholder="Enter county name"
                value={filters.county}
                onChange={(e) => handleFilterChange('county', e.target.value)}
              />
            </div>

            <button className="btn-clear" onClick={clearFilters}>Clear Filters</button>
          </div>

          {/* Project list */}
          <div className="sidebar-section">
            <h3>Projects ({pagination.total})</h3>
            {loading && <div className="loading">Loading...</div>}
            {error && <div className="error">{error}</div>}
            
            <div className="project-list">
              {projects.map(project => (
                <div 
                  key={project.project_id} 
                  className={`project-item ${selectedProject?.project_id === project.project_id ? 'selected' : ''}`}
                  onClick={() => setSelectedProject(project)}
                >
                  <div className="project-name">{project.project_name}</div>
                  <div className="project-meta">
                    <span className={`status-badge ${project.status}`}>{project.status}</span>
                    <span className="county">{project.county}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {pagination.totalPages > 1 && (
              <div className="pagination">
                <button 
                  onClick={() => handlePageChange(pagination.currentPage - 1)}
                  disabled={pagination.currentPage === 1}
                >
                  Previous
                </button>
                <span>Page {pagination.currentPage} of {pagination.totalPages}</span>
                <button 
                  onClick={() => handlePageChange(pagination.currentPage + 1)}
                  disabled={!pagination.hasMore}
                >
                  Next
                </button>
              </div>
            )}
          </div>
        </aside>

        {/* Map */}
        <main className="map-container">
          <MapContainer center={center} zoom={zoom} className="map">
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; OpenStreetMap contributors'
            />

            {/* Project markers */}
            {showProjects && (
              <LayerGroup>
                {projects.map(project => (
                  project.location && (
                    <Marker
                      key={project.project_id}
                      position={[
                        typeof project.location === 'object' ? project.location.y || project.location.coordinates?.[1] : 0,
                        typeof project.location === 'object' ? project.location.x || project.location.coordinates?.[0] : 0
                      ]}
                      icon={createStatusMarker(project.status)}
                      eventHandlers={{
                        click: () => setSelectedProject(project)
                      }}
                    >
                      <Popup>
                        <div className="popup-content">
                          <h4>{project.project_name}</h4>
                          <p><strong>Number:</strong> {project.project_number}</p>
                          <p><strong>Status:</strong> {project.status}</p>
                          <p><strong>County:</strong> {project.county}</p>
                          <p><strong>Type:</strong> {project.project_type}</p>
                          {project.start_date && <p><strong>Start:</strong> {project.start_date}</p>}
                          {project.completion_date && <p><strong>Completion:</strong> {project.completion_date}</p>}
                          {project.project_cost && <p><strong>Cost:</strong> ${project.project_cost.toLocaleString()}</p>}
                        </div>
                      </Popup>
                    </Marker>
                  )
                ))}
              </LayerGroup>
            )}

            {/* Environmental data markers */}
            {showEnvironmental && (
              <LayerGroup>
                {environmentalData.map((data, idx) => (
                  data.location && (
                    <Marker
                      key={`env-${data.env_data_id || idx}`}
                      position={[
                        typeof data.location === 'object' ? data.location.y || data.location.coordinates?.[1] : 0,
                        typeof data.location === 'object' ? data.location.x || data.location.coordinates?.[0] : 0
                      ]}
                      icon={L.icon({
                        iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
                        iconSize: [16, 16],
                        iconAnchor: [8, 8],
                        popupAnchor: [0, -8]
                      })}
                    >
                      <Popup>
                        <div className="popup-content">
                          <h4>{data.data_category}</h4>
                          {data.species_name && <p><strong>Species:</strong> {data.species_name}</p>}
                          {data.protected_status && <p><strong>Status:</strong> {data.protected_status}</p>}
                          <p><strong>Source:</strong> {data.data_source}</p>
                          <p><strong>Confidence:</strong> {data.data_confidence}</p>
                        </div>
                      </Popup>
                    </Marker>
                  )
                ))}
              </LayerGroup>
            )}
          </MapContainer>
        </main>
      </div>
    </div>
  )
}

export default App
