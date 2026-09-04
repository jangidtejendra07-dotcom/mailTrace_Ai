import { useEffect, useState, useMemo, useCallback, useRef } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import ForceGraph2D from 'react-force-graph-2d'
import { Waypoints, Loader2, X, RefreshCw, Info } from 'lucide-react'
import { getFullCampaignGraph, getCaseCampaignGraph } from '../lib/api.js'
import PageHeader from '../components/PageHeader.jsx'

const NODE_COLORS = {
  EMAIL: '#7c9cff',
  SENDER: '#3ddc97',
  REPLY_TO: '#f5b942',
  IP: '#ff5d5d',
  GEO: '#c084fc',
  ASN: '#f472b6',
  DOMAIN: '#38bdf8',
  ATTACHMENT: '#ff2d55',
}
const DEFAULT_COLOR = '#64748b'

export default function CampaignGraphPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const caseId = searchParams.get('caseId')
  const [graph, setGraph] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState(null)
  const [showLegend, setShowLegend] = useState(true)
  const fgRef = useRef()
  const containerRef = useRef(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    const fetcher = caseId ? getCaseCampaignGraph(caseId) : getFullCampaignGraph()
    fetcher
      .then((data) => {
        setGraph(data)
        // Zoom-to-fit after data load
        setTimeout(() => {
          if (fgRef.current) {
            fgRef.current.zoomToFit(400, 50)
          }
        }, 200)
      })
      .catch(() =>
        setError(
          'Could not load the campaign graph. Make sure Neo4j is configured on the backend (NEO4J_URI / NEO4J_PASSWORD).'
        )
      )
      .finally(() => setLoading(false))
  }, [caseId])

  useEffect(() => { load() }, [load])

  // Calculate node degree (number of connections) to dynamically size critical nodes
  const graphData = useMemo(() => {
    if (!graph) return { nodes: [], links: [] }
    const nodeIds = new Set(graph.nodes.map((n) => n.id))
    
    // Count connections per node for dynamic sizing
    const degrees = {}
    graph.edges.forEach((e) => {
      degrees[e.from] = (degrees[e.from] || 0) + 1
      degrees[e.to] = (degrees[e.to] || 0) + 1
    })

    return {
      nodes: graph.nodes.map((n) => ({ 
        ...n, 
        val: Math.max(3, Math.min(12, (degrees[n.id] || 1) * 1.5)) 
      })),
      links: graph.edges
        .filter((e) => nodeIds.has(e.from) && nodeIds.has(e.to))
        .map((e) => ({ source: e.from, target: e.to, relation: e.relation, cases: e.cases })),
    }
  }, [graph])

  const isEmpty = !loading && !error && graphData.nodes.length === 0

  return (
    <div className="h-screen flex flex-col">
      <div className="max-w-7xl mx-auto w-full px-8 pt-10">
        <PageHeader
          icon={Waypoints}
          title="Campaign Graph"
          subtitle="Cross-case correlation of attacker infrastructure — repeated IPs, domains, ASNs, and attachments automatically link related campaigns together."
          right={
            <div className="flex items-center gap-2">
              {caseId && (
                <button
                  onClick={() => setSearchParams({})}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-base-600 text-slate-400 text-xs font-medium px-3 py-2 hover:bg-base-800 transition-colors"
                >
                  <X size={13} /> Clear case filter ({caseId})
                </button>
              )}
              <button
                onClick={load}
                disabled={loading}
                className="inline-flex items-center gap-1.5 rounded-lg border border-trace/40 bg-trace/10 text-trace text-xs font-medium px-3 py-2 hover:bg-trace/20 transition-colors disabled:opacity-60"
              >
                <RefreshCw size={13} className={loading ? 'animate-spin' : ''} /> Refresh
              </button>
            </div>
          }
        />
      </div>

      <div className="flex-1 relative max-w-7xl mx-auto w-full px-8 pb-8 min-h-0">
        <div ref={containerRef} className="relative h-full w-full rounded-xl border border-base-700 bg-base-900/40 overflow-hidden shadow-2xl">
          
          {/* Legend Overlay */}
          {!loading && !error && graphData.nodes.length > 0 && (
            <div className="absolute top-4 left-4 bg-base-900/80 backdrop-blur-md border border-base-700/80 rounded-xl p-3 z-10 max-w-xs shadow-lg">
              <div className="flex items-center justify-between mb-2 pb-1 border-b border-base-800">
                <span className="text-[11px] font-mono tracking-wider text-slate-300 uppercase font-semibold flex items-center gap-1.5">
                  <Info size={12} className="text-trace" /> Infrastructure Legend
                </span>
              </div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 text-[11px] font-mono">
                {Object.entries(NODE_COLORS).map(([type, color]) => (
                  <div key={type} className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0 shadow-sm" style={{ backgroundColor: color }} />
                    <span className="text-slate-400 truncate">{type}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {loading && (
            <div className="absolute inset-0 flex items-center justify-center gap-2 text-slate-400 text-sm font-mono z-10 bg-base-900/60 backdrop-blur-sm">
              <Loader2 className="animate-spin text-trace" size={18} /> Building threat correlation map…
            </div>
          )}
          
          {error && (
            <div className="absolute inset-0 flex items-center justify-center px-8 text-center z-10">
              <p className="text-signal-danger text-sm font-mono max-w-md bg-signal-danger/10 border border-signal-danger/20 p-4 rounded-xl">{error}</p>
            </div>
          )}
          
          {isEmpty && (
            <div className="absolute inset-0 flex items-center justify-center px-8 text-center z-10">
              <p className="text-slate-400 text-sm max-w-md">
                {caseId
                  ? `No correlated indicators found yet for ${caseId}.`
                  : 'No campaign graph data yet — analyze a few emails to see correlated infrastructure appear here.'}
              </p>
            </div>
          )}

          {!loading && !error && graphData.nodes.length > 0 && (
            <ForceGraph2D
              ref={fgRef}
              graphData={graphData}
              backgroundColor="transparent"
              nodeLabel={(n) => `${n.type || 'NODE'}: ${n.label || n.id}`}
              nodeColor={(n) => NODE_COLORS[n.type] || DEFAULT_COLOR}
              nodeVal={(n) => n.val}
              nodeRelSize={4}
              linkColor={() => 'rgba(148,163,184,0.18)'}
              linkWidth={1}
              linkDirectionalParticles={1}
              linkDirectionalParticleWidth={1.5}
              linkDirectionalParticleColor={() => '#3ddc97'}
              onNodeClick={(n) => setSelectedNode(n)}
              cooldownTicks={100}
              onEngineStop={() => {
                if (fgRef.current) fgRef.current.zoomToFit(400, 50);
              }}
              width={containerRef.current?.clientWidth}
              height={containerRef.current?.clientHeight}
            />
          )}

          {/* Selected Node Details Drawer */}
          {selectedNode && (
            <div className="absolute top-4 right-4 w-80 rounded-xl border border-base-700 bg-base-900/95 backdrop-blur-md p-4 z-20 shadow-2xl animate-in fade-in zoom-in-95 duration-150">
              <div className="flex items-center justify-between mb-3 pb-2 border-b border-base-800">
                <span
                  className="text-[10px] font-mono uppercase tracking-widest px-2.5 py-1 rounded-md border font-medium"
                  style={{
                    color: NODE_COLORS[selectedNode.type] || DEFAULT_COLOR,
                    borderColor: `${NODE_COLORS[selectedNode.type] || DEFAULT_COLOR}44`,
                    backgroundColor: `${NODE_COLORS[selectedNode.type] || DEFAULT_COLOR}15`,
                  }}
                >
                  {selectedNode.type || 'NODE'}
                </span>
                <button 
                  onClick={() => setSelectedNode(null)} 
                  className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-base-800 transition-colors"
                >
                  <X size={15} />
                </button>
              </div>
              
              <div className="mb-4">
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider block mb-1">Indicator Value</span>
                <p className="text-xs font-mono text-slate-200 bg-base-950 p-2.5 rounded-lg border border-base-800 break-all select-all">
                  {selectedNode.label || selectedNode.id}
                </p>
              </div>

              {selectedNode.cases?.length > 0 && (
                <div>
                  <p className="text-[10px] font-mono uppercase tracking-wider text-slate-400 mb-2 flex items-center justify-between">
                    <span>Correlated Cases</span>
                    <span className="bg-trace/20 text-trace px-1.5 py-0.5 rounded text-[9px] font-bold">
                      {selectedNode.cases.length}
                    </span>
                  </p>
                  <div className="space-y-1.5 max-h-44 overflow-y-auto pr-1">
                    {selectedNode.cases.map((cid) => (
                      <Link
                        key={cid}
                        to={`/cases/${cid}`}
                        className="block text-xs font-mono text-trace bg-base-950/60 hover:bg-trace/10 border border-base-800/60 hover:border-trace/30 p-2 rounded-lg transition-all truncate"
                      >
                        {cid}
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}