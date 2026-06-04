import { useState, useRef, useEffect } from "react";
import { X, Send, Bot, User, AlertCircle, FileText, CheckCircle2 } from "lucide-react";
import { api } from "../lib/api";

interface RegulatoryInsightPanelProps {
  impact: any;
  onClose: () => void;
}

export default function RegulatoryInsightPanel({ impact, onClose }: RegulatoryInsightPanelProps) {
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll chat
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Initial AI greeting based on impact
  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await api.get(`/regulatory-watch/chat/${impact.id}`);
        if (res.data && res.data.length > 0) {
          setMessages(res.data);
        } else {
          setMessages([
            {
              role: "assistant",
              content: `Bonjour. J'ai analysé la mise à jour "${impact.update?.title || 'récente'}". Comment puis-je vous aider à gérer cet impact pour le projet concerné ?`
            }
          ]);
        }
      } catch (err) {
        console.error("Failed to fetch chat history", err);
        setMessages([
          {
            role: "assistant",
            content: `Bonjour. J'ai analysé la mise à jour "${impact.update?.title || 'récente'}". Comment puis-je vous aider à gérer cet impact pour le projet concerné ?`
          }
        ]);
      }
    };
    fetchHistory();
  }, [impact]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.post("/regulatory-watch/chat", {
        impact_id: impact.id,
        message: userMessage.content
      });
      setMessages((prev) => [...prev, { role: "assistant", content: res.data.reply }]);
    } catch (err) {
      console.error("Chat error", err);
      setMessages((prev) => [...prev, { role: "assistant", content: "Désolé, une erreur est survenue." }]);
    } finally {
      setLoading(false);
    }
  };

  const parseJsonArray = (str: string) => {
    try { return JSON.parse(str); } catch { return []; }
  };

  const standardsUpdated = parseJsonArray(impact.standards_updated);
  const proceduresImpacted = parseJsonArray(impact.procedures_impacted);
  const suggestedActions = parseJsonArray(impact.suggested_actions);
  const capaRecommendations = parseJsonArray(impact.capa_recommendations);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/50 backdrop-blur-sm transition-opacity">
      <div className="w-full max-w-2xl bg-white shadow-2xl h-full flex flex-col transform transition-transform">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex justify-between items-center bg-slate-50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 text-blue-600 rounded-lg">
              <AlertCircle size={20} />
            </div>
            <h2 className="text-lg font-bold text-slate-800">Regulatory Insight</h2>
          </div>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-200 transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Content Area - Scrollable */}
        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
          
          {/* Update Details Card */}
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div className="flex items-start justify-between mb-2">
              <h3 className="font-semibold text-slate-800 text-lg leading-tight pr-4">
                {impact.update?.title}
              </h3>
              <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider shrink-0 ${
                impact.update?.severity === 'critical' ? 'bg-red-100 text-red-800' :
                impact.update?.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                impact.update?.severity === 'low' ? 'bg-green-100 text-green-800' :
                'bg-yellow-100 text-yellow-800'
              }`}>
                {impact.update?.severity}
              </span>
            </div>
            
            <div className="flex items-center gap-4 mb-4">
              <span className="text-sm font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full border border-blue-100">
                🎯 Projet concerné : {impact.project?.company_name}
              </span>
              <a href={impact.update?.original_url} target="_blank" rel="noreferrer" className="text-sm text-slate-500 hover:text-blue-600 hover:underline">
                Voir la source officielle
              </a>
            </div>
            <div className="bg-slate-50 p-4 rounded-lg border border-slate-100">
              <h4 className="text-xs font-bold text-slate-500 uppercase mb-2 flex items-center gap-2">
                <Bot size={14} /> AI Impact Summary
              </h4>
              <p className="text-sm text-slate-700 leading-relaxed mb-4">
                {impact.impact_summary}
              </p>
              
              {impact.impact_justification && (
                <>
                  <h4 className="text-xs font-bold text-slate-500 uppercase mb-2 flex items-center gap-2 border-t border-slate-200 pt-4">
                    <AlertCircle size={14} className="text-blue-500" /> Pourquoi ce projet est-il impacté ?
                  </h4>
                  <p className="text-sm text-slate-700 leading-relaxed italic">
                    {impact.impact_justification}
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Impact & Actions */}
          <div className="flex flex-col gap-4">
            
            {/* Standards Updated */}
            <div className="border border-slate-200 rounded-xl p-4 bg-white">
              <h4 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <FileText size={16} className="text-blue-500" /> Normes & Règlements Mis à Jour
              </h4>
              <ul className="space-y-2">
                {standardsUpdated.map((std: string, i: number) => (
                  <li key={i} className="text-sm text-slate-600 flex items-start gap-2">
                    <span className="text-blue-500 mt-0.5">•</span> 
                    <span className="font-medium text-slate-700">{std}</span>
                  </li>
                ))}
                {standardsUpdated.length === 0 && <li className="text-sm text-slate-400 italic">Aucune norme spécifique identifiée.</li>}
              </ul>
            </div>

            {/* Procedures Impacted */}
            <div className="border border-slate-200 rounded-xl p-4 bg-white">
              <h4 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <FileText size={16} className="text-orange-500" /> Procédures (SOP) Impactées & Changements Requis
              </h4>
              <div className="space-y-4">
                {proceduresImpacted.map((proc: any, i: number) => (
                  <div key={i} className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                    <div className="font-bold text-slate-700 text-sm mb-1">{proc.procedure_name}</div>
                    <div className="text-sm text-slate-600">{proc.changes_needed}</div>
                  </div>
                ))}
                {proceduresImpacted.length === 0 && <p className="text-sm text-slate-400 italic">Aucune procédure directement impactée.</p>}
              </div>
            </div>
            
            {/* Suggested Actions */}
            <div className="border border-slate-200 rounded-xl p-4 bg-white">
              <h4 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
                <CheckCircle2 size={16} className="text-emerald-500" /> Actions Générales
              </h4>
              <ul className="space-y-2">
                {suggestedActions.map((action: string, i: number) => (
                  <li key={i} className="text-sm text-slate-600 flex items-start gap-2">
                    <input type="checkbox" className="mt-1 rounded text-emerald-600 focus:ring-emerald-500 border-slate-300 cursor-pointer" />
                    <span>{action}</span>
                  </li>
                ))}
                {suggestedActions.length === 0 && <li className="text-sm text-slate-400 italic">Aucune action générale suggérée.</li>}
              </ul>
            </div>

            {/* CAPA Recommendations */}
            <div className="border border-slate-200 rounded-xl p-4 bg-red-50 border-red-100">
              <h4 className="font-semibold text-red-800 mb-3 flex items-center gap-2">
                <AlertCircle size={16} className="text-red-600" /> Recommandations CAPA
              </h4>
              <ul className="space-y-2">
                {capaRecommendations.map((capa: string, i: number) => (
                  <li key={i} className="text-sm text-red-700 flex items-start gap-2 bg-white p-2 rounded border border-red-100 shadow-sm">
                    <span className="text-red-500 font-bold mt-0.5">!</span>
                    <span>{capa}</span>
                  </li>
                ))}
                {capaRecommendations.length === 0 && <li className="text-sm text-slate-400 italic">Aucune CAPA requise identifiée.</li>}
              </ul>
            </div>
          </div>

          <hr className="border-slate-100" />

          {/* Interactive Chat */}
          <div className="flex flex-col border border-slate-200 rounded-xl overflow-hidden bg-slate-50 mt-2 shrink-0">
            <div className="bg-slate-100 px-4 py-3 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-2">
              <Bot size={16} className="text-blue-500" /> Consultant AI Assistant
            </div>
            <div className="p-5 space-y-5 min-h-[200px]">
              {messages.map((m, i) => (
                <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : ''}`}>
                  {m.role === 'assistant' && (
                     <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0 mt-1">
                      <Bot size={16} />
                    </div>
                  )}
                  <div className={`max-w-[85%] rounded-2xl p-3.5 text-sm shadow-sm ${
                    m.role === 'user' ? 'bg-blue-600 text-white rounded-tr-sm' : 'bg-white text-slate-700 border border-slate-200 rounded-tl-sm'
                  }`}>
                    {m.content}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0 mt-1">
                    <Bot size={16} />
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-3.5 text-sm text-slate-500 shadow-sm animate-pulse">
                    En train d'écrire...
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            <div className="p-4 bg-white border-t border-slate-200">
              <form onSubmit={handleSendMessage} className="relative">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Posez une question sur cet impact..."
                  className="w-full pl-5 pr-14 py-3.5 bg-slate-50 border border-slate-200 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm transition-all shadow-inner"
                />
                <button
                  type="submit"
                  disabled={!input.trim() || loading}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors shadow-md"
                >
                  <Send size={16} />
                </button>
              </form>
            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
