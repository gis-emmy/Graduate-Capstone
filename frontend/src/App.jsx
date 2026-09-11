import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Popup, Marker } from 'react-leaflet'
import L from 'leaflet'
import axios from 'axios'
import './App.css'

// Fix for default marker icons in react-leaflet
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

function App() {
  const [backendStatus, setBackendStatus] = useState('checking')
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)

  // Center coordinates for Tennessee
  const center = [35.7478, -86.6923]
  const zoom = 7

  useEffect(() => {
    checkBackendStatus()
    fetchProjects()
  }, [])

  const checkBackendStatus = async () => {
    try {
      const response = await axios.get('http://localhost:3001/api/health')
      setBackendStatus('running')
    } catch (error) {
      setBackendStatus('offline')
    }
  }

  const fetchProjects = async () => {
    try {
      const response = await axios.get('http://localhost:3001/api/projects')
      setProjects(response.data.projects || [])
    } catch (error) {
      console.error('Error fetching projects:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1>TDOT Environmental Data Visualization Platform</h1>
          <div className="status-indicator">
            <span className={`status ${backendStatus}`}></span>
            <span className="status-text">Backend: {backendStatus === 'running' ? '✓ Running' : '✗ Offline'}</span>
          </div>
        </div>
      </header>

      <main className="main-content">
        <div className="map-container">
          <MapContainer center={center} zoom={zoom} style={{ height: '100%', width: '100%' }}>
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            />
            {projects.map((project, idx) => (
              <Marker key={idx} position={[project.lat, project.lng]}>
                <Popup>
                  <div>
                    <h3>{project.name}</h3>
                    <p>{project.description}</p>
                  </div>
                </Popup>
              </Marker>
            ))}
          </MapContainer>
        </div>

        <aside className="sidebar">
          <h2>Project Information</h2>
          {loading ? (
            <p>Loading projects...</p>
          ) : projects.length === 0 ? (
            <p>No projects available yet.</p>
          ) : (
            <ul className="projects-list">
              {projects.map((project, idx) => (
                <li key={idx} className="project-item">
                  <h4>{project.name}</h4>
                  <p>{project.description}</p>
                </li>
              ))}
            </ul>
          )}
        </aside>
      </main>
    </div>
  )
}

export default App
