import { MapContainer, TileLayer, Marker, Popup, Circle } from 'react-leaflet'
import L from 'leaflet'

// Fix default marker icons under Vite bundling
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

export default function GeoMap({ geolocation }) {
  const lat = geolocation?.latitude
  const lon = geolocation?.longitude

  if (!lat || !lon) {
    return (
      <div className="h-56 rounded-lg border border-dashed border-base-600 flex items-center justify-center text-center px-4">
        <p className="text-xs text-slate-500 font-mono">
          No resolvable public IP / geolocation for this message.
          <br />Origin: {geolocation?.probable_origin || 'Unknown'}
        </p>
      </div>
    )
  }

  return (
    <div className="h-56 rounded-lg overflow-hidden border border-base-700">
      <MapContainer center={[lat, lon]} zoom={4} scrollWheelZoom={false} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        <Circle center={[lat, lon]} radius={80000} pathOptions={{ color: '#ff5d5d', fillOpacity: 0.15 }} />
        <Marker position={[lat, lon]}>
          <Popup>
            <span className="font-mono text-xs">
              {geolocation.probable_origin}<br />
              IP: {geolocation.ip}<br />
              ISP: {geolocation.isp || 'Unknown'}
            </span>
          </Popup>
        </Marker>
      </MapContainer>
    </div>
  )
}
