import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { Navigate } from "react-router-dom";
import { api } from "../lib/api";
import RegulatoryInsightPanel from "../components/RegulatoryInsightPanel";
import { RefreshCcw } from "lucide-react";

export default function RegulatoryHistoryPage() {
  const { user } = useAuth();
  const [impacts, setImpacts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [selectedImpact, setSelectedImpact] = useState<any | null>(null);

  const fetchHistory = async () => {
    try {
      const res = await api.get("/regulatory-watch/impacts");
      setImpacts(res.data);
    } catch (err) {
      console.error("Failed to fetch regulatory history", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user?.role === "consultant") {
      fetchHistory();
    }
  }, [user]);

  const handleSync = async () => {
    if (syncing) return;
    setSyncing(true);
    try {
      await api.post("/regulatory-watch/sync");
      await fetchHistory();
    } catch (err) {
      console.error("Failed to sync regulatory updates", err);
      alert("Failed to synchronize. Please check server status.");
    } finally {
      setSyncing(false);
    }
  };

  if (!user || user.role !== "consultant") {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-800">
          Regulatory History & Inbox
        </h1>
        <button
          onClick={handleSync}
          disabled={syncing}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg shadow-sm border transition-all duration-300 ${
            syncing
              ? "bg-slate-50 border-slate-200 text-slate-400 cursor-not-allowed"
              : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50 active:scale-95 hover:border-slate-300"
          }`}
        >
          <RefreshCcw
            className={`w-4 h-4 text-brand-600 ${syncing ? "animate-spin text-slate-400" : ""}`}
          />
          {syncing ? "Synchronisation..." : "Synchroniser maintenant"}
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-slate-200 overflow-hidden flex-1 flex flex-col">
        {loading ? (
          <div className="p-8 text-center text-slate-500">Loading history...</div>
        ) : impacts.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No regulatory updates recorded yet.</div>
        ) : (
          <div className="overflow-auto flex-1">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 sticky top-0">
                <tr>
                  <th className="py-3 px-4 font-medium">Date</th>
                  <th className="py-3 px-4 font-medium">Severity</th>
                  <th className="py-3 px-4 font-medium">Update Title</th>
                  <th className="py-3 px-4 font-medium">Impact Status</th>
                  <th className="py-3 px-4 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {impacts.map((impact) => (
                  <tr key={impact.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4 text-slate-500">
                      {new Date(impact.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        impact.update?.severity === 'critical' ? 'bg-red-100 text-red-800' :
                        impact.update?.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                        impact.update?.severity === 'low' ? 'bg-green-100 text-green-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {impact.update?.severity?.toUpperCase() || 'MEDIUM'}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-700 max-w-xs truncate">
                      {impact.update?.title || "Unknown Update"}
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-slate-500 capitalize">{impact.status.replace('_', ' ')}</span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => setSelectedImpact(impact)}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        Review
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedImpact && (
        <RegulatoryInsightPanel 
          impact={selectedImpact} 
          onClose={() => setSelectedImpact(null)} 
        />
      )}
    </div>
  );
}
