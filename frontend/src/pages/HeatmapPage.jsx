import { useState, useEffect, useMemo } from 'react';
import api from '../lib/api';
import GeoMap from '../components/GeoMap';
import { 
  Map as MapIcon, Server, Globe, 
  Activity, Crosshair, ShieldAlert 
} from 'lucide-react';

export default function HeatmapPage() {
  const [geoData, setGeoData] = useState({ heatmapPoints: [], infraClusters: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/geo/infra')
      .then(res => {
        setGeoData({
          heatmapPoints: res.data.heatmap_points || [],
          infraClusters: res.data.infra_clusters || []
        });
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  // Compute stats for the side panel based on clusters
  const { topASNs, topCountries, totalThreats } = useMemo(() => {
    if (!geoData.infraClusters.length) return { topASNs: [], topCountries: [], totalThreats: 0 };

    const asnMap = {};
    const countryMap = {};
    let threats = 0;

    geoData.infraClusters.forEach(cluster => {
      threats += (cluster.email_count || 1);
      
      const asn = cluster.asn || 'Unknown ASN';
      asnMap[asn] = (asnMap[asn] || 0) + (cluster.email_count || 1);
      
      const country = cluster.country || 'Unknown Region';
      countryMap[country] = (countryMap[country] || 0) + (cluster.email_count || 1);
    });

    return {
      totalThreats: threats,
      topASNs: Object.entries(asnMap).sort((a, b) => b[1] - a[1]).slice(0, 5),
      topCountries: Object.entries(countryMap).sort((a, b) => b[1] - a[1]).slice(0, 5)
    };
  }, [geoData]);

  if (loading) {
    return (
      <div className="h-screen bg-[#0B0F19] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-[#1F2937] border-t-[#06B6D4] rounded-full animate-spin"></div>
          <p className="text-slate-400 text-sm tracking-widest uppercase">Initializing Global Radar...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-[#0B0F19] text-gray-100 font-sans overflow-hidden">
      
      {/* Top Header */}
      <div className="bg-[#111827] border-b border-[#1F2937] px-6 py-4 flex justify-between items-center shadow-sm shrink-0">
        <div className="flex items-center gap-3">
          <div className="bg-[#10B981]/10 p-2 rounded-lg border border-[#10B981]/20">
            <MapIcon className="text-[#10B981]" size={24} />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-wide">Global Threat Infrastructure</h1>
            <p className="text-xs text-slate-400 mt-0.5 uppercase tracking-widest">Live IP Geolocation & Heatmap</p>
          </div>
        </div>
        
        <div className="flex gap-4">
          <div className="flex items-center gap-2 bg-[#0B0F19] border border-[#1F2937] px-4 py-2 rounded-lg">
            <Crosshair className="text-[#EF4444]" size={16} />
            <span className="text-sm font-bold text-white">{totalThreats}</span>
            <span className="text-xs text-slate-400 uppercase tracking-wider">Active Nodes</span>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        
        {/* Left: Map Container (70%) */}
        <div className="flex-1 relative bg-[#0B0F19]">
          <div className="absolute inset-0 z-0">
            <GeoMap 
              heatmapPoints={geoData.heatmapPoints} 
              infraClusters={geoData.infraClusters} 
            />
          </div>
          {/* Map Overlay HUD elements can go here if needed */}
          <div className="absolute top-4 left-4 z-10 pointer-events-none">
            <div className="bg-[#111827]/80 backdrop-blur-md border border-[#1F2937] p-3 rounded-lg flex flex-col gap-2 shadow-lg">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-300 uppercase tracking-wider">
                <Activity size={14} className="text-[#06B6D4]" /> Radar Status: <span className="text-[#10B981]">ONLINE</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Infrastructure Breakdown Panel (30%) */}
        <div className="w-full lg:w-80 bg-[#111827] border-l border-[#1F2937] flex flex-col shrink-0 overflow-y-auto custom-scrollbar shadow-2xl z-10">
          <div className="p-5 border-b border-[#1F2937]">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <ShieldAlert size={16} className="text-[#F59E0B]" /> Threat Origins
            </h2>
          </div>

          <div className="p-5 flex-1 space-y-6">
            
            {/* Top Countries */}
            <div>
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                <Globe size={14} /> Top Targeted Regions
              </h3>
              <div className="space-y-3">
                {topCountries.length === 0 ? (
                  <p className="text-sm text-slate-500">No region data available.</p>
                ) : (
                  topCountries.map(([country, count], idx) => (
                    <div key={country} className="flex items-center justify-between bg-[#0B0F19] border border-[#1F2937] p-2.5 rounded-lg">
                      <span className="text-sm font-medium text-slate-300 truncate pr-2">
                        {idx + 1}. {country}
                      </span>
                      <span className="text-xs font-bold bg-[#EF4444]/10 text-[#EF4444] px-2 py-1 rounded border border-[#EF4444]/20">
                        {count} hits
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Top ASNs */}
            <div>
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-2">
                <Server size={14} /> Malicious ASNs
              </h3>
              <div className="space-y-3">
                {topASNs.length === 0 ? (
                  <p className="text-sm text-slate-500">No ASN data available.</p>
                ) : (
                  topASNs.map(([asn, count], idx) => (
                    <div key={asn} className="flex items-center justify-between bg-[#0B0F19] border border-[#1F2937] p-2.5 rounded-lg">
                      <span className="text-sm font-medium text-slate-300 truncate pr-2" title={asn}>
                        {asn}
                      </span>
                      <span className="text-xs font-bold bg-[#F59E0B]/10 text-[#F59E0B] px-2 py-1 rounded border border-[#F59E0B]/20">
                        {count} IPs
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}