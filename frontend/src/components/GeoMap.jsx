import { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet'
import MarkerClusterGroup from 'react-leaflet-cluster'
import L from 'leaflet'
import 'leaflet.heat'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'

// Fix default marker icons under Vite bundling
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

/**
 * react-leaflet has no built-in heatmap component, so this adds a
 * Leaflet.heat layer directly onto the underlying map instance via
 * useMap(), and cleans it up on unmount / when points change.
 */
function HeatmapLayer({ points }) {
  const map = useMap()

  useEffect(() => {
    if (!points || points.length === 0) return undefined

    const heatPoints = points.map((p) => [p.lat, p.lon, p.weight ?? 0.5])
    const heatLayer = L.heatLayer(heatPoints, { radius: 28, blur: 22, maxZoom: 8 })
    heatLayer.addTo(map)

    return () => {
      map.removeLayer(heatLayer)
    }
  }, [map, points])

  return null
}

/**
 * GeoMap supports two modes, which can be used independently or together:
 *
 * 1. Single-case mode (unchanged behavior): pass `geolocation` for one
 *    case's marker + radius circle — used on the case-detail page.
 *
 * 2. Dashboard infra mode (new): pass `heatmapPoints` and/or
 *    `infraClusters` (both come straight from GET /api/v1/geo/infra) to
 *    show attacker infrastructure spread across ALL analyzed cases.
 *
 * Existing callers that only pass `geolocation` need NO changes.
 */
export default function GeoMap({ geolocation, heatmapPoints = [], infraClusters = [] }) {
  const lat = geolocation?.latitude
  const lon = geolocation?.longitude

  const hasSingleCase = Boolean(lat && lon)
  const hasHeatmap = heatmapPoints.length > 0
  const hasClusters = infraClusters.length > 0
  const hasDashboardData = hasHeatmap || hasClusters

  if (!hasSingleCase && !hasDashboardData) {
    return (
      <div className="h-56 rounded-lg border border-dashed border-base-600 flex items-center justify-center text-center px-4">
        <p className="text-xs text-slate-500 font-mono">
          No resolvable public IP / geolocation data yet.
          <br />Origin: {geolocation?.probable_origin || 'Unknown'}
        </p>
      </div>
    )
  }

  const center = hasSingleCase
    ? [lat, lon]
    : hasClusters
      ? [infraClusters[0].latitude, infraClusters[0].longitude]
      : [20, 0]
  const zoom = hasSingleCase ? 4 : 2

  return (
    <div className="h-56 rounded-lg overflow-hidden border border-base-700">
      <MapContainer center={center} zoom={zoom} scrollWheelZoom={false} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />

        {hasHeatmap && <HeatmapLayer points={heatmapPoints} />}

        {hasClusters && (
          <MarkerClusterGroup chunkedLoading>
            {infraClusters.map((cluster) => (
              <Marker key={`${cluster.asn}-${cluster.isp}`} position={[cluster.latitude, cluster.longitude]}>
                <Popup>
                  <span className="font-mono text-xs">
                    ASN: {cluster.asn}<br />
                    ISP: {cluster.isp}<br />
                    Country: {cluster.country}<br />
                    Emails from here: {cluster.email_count}<br />
                    Highest risk score: {cluster.max_risk_score}/100
                  </span>
                </Popup>
              </Marker>
            ))}
          </MarkerClusterGroup>
        )}

        {hasSingleCase && (
          <>
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
          </>
        )}
      </MapContainer>
    </div>
  )
}