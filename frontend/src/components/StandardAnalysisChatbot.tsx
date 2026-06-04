import React, { useState, useEffect, useRef } from "react";
import { X, Send, CheckCircle, MessageSquare, Sparkles, ChevronRight, Loader2, Trash2, Plus, RefreshCcw } from "lucide-react";
import { api } from "../lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface StandardAnalysisChatbotProps {
  project: any;
  onClose: () => void;
  onConfirm: (standards: string) => void;
}

export default function StandardAnalysisChatbot({ project, onClose, onConfirm }: StandardAnalysisChatbotProps) {
  const [standards, setStandards] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  console.log("Rendering StandardAnalysisChatbot", { project });

  const [sessions, setSessions] = useState<{id: string, title: string, created_at: string}[]>([]);
  
  // Use localStorage to remember the last active session for this project
  const storageKey = project.id ? `active_session_${project.id}` : null;
  const [currentSessionId, setCurrentSessionId] = useState<string>(() => {
    if (storageKey) {
      return localStorage.getItem(storageKey) || "default";
    }
    return "default";
  });

  useEffect(() => {
    if (storageKey) {
      localStorage.setItem(storageKey, currentSessionId);
    }
  }, [currentSessionId, storageKey]);

  useEffect(() => {
    const initData = async () => {
      try {
        // If the project already has standards, use them and don't re-analyze automatically
        if (project.standards && project.standards.trim().length > 0) {
          const existingStandards = project.standards.split(",").map((s: string) => s.trim()).filter((s: string) => s.length > 0);
          setStandards(existingStandards);
          setAnalyzing(false);
        } else {
          setAnalyzing(true);
          // Call analyze even if project.id is missing (for new projects)
          const analyzeRes = await api.post("/ai/analyze", { project_data: project, session_id: currentSessionId });
          setStandards(analyzeRes.data.standards);
        }

        if (project.id) {
          const sessRes = await api.get(`/ai/projects/${project.id}/sessions`);
          if (sessRes.data && sessRes.data.length > 0) {
            setSessions(sessRes.data);
            // Only auto-switch to most recent if we are on "default" and have no saved session
            if (currentSessionId === "default" && !localStorage.getItem(storageKey!)) {
              setCurrentSessionId(sessRes.data[0].id);
            }
          }
        }
      } catch (e) {
        console.error(e);
        // Fallback if AI fails and we have nothing
        if (standards.length === 0) {
          setStandards(["ISO 13485:2016", "ISO 9001:2015"]);
        }
      } finally {
        setAnalyzing(false);
      }
    };
    initData();
  }, [project.id, project.company_name, project.product, project.activity_sector, project.market, project.company_role]);

  useEffect(() => {
    const fetchHistory = async () => {
      if (!project.id) {
        setMessages([{ role: "assistant", content: "Bonjour ! J'ai analysé votre projet. Voici les normes recommandées pour votre secteur et produit. Avez-vous des questions sur ces normes ou souhaitez-vous des explications ?" }]);
        return;
      }
      setLoading(true);
      try {
        const res = await api.get(`/ai/projects/${project.id}/chat-history?session_id=${currentSessionId}`);
        if (res.data && res.data.length > 0) {
          setMessages(res.data);
        } else {
          setMessages([{ role: "assistant", content: "Bonjour ! J'ai analysé votre projet. Voici les normes recommandées pour votre secteur et produit. Avez-vous des questions sur ces normes ou souhaitez-vous des explications ?" }]);
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [currentSessionId, project.id]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg = { role: "user" as const, content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.post("/ai/chat", {
        // Spread project and override standards with the current analyzed state
        project_data: { ...project, standards: standards.join(", ") },
        message: input,
        session_id: currentSessionId,
      });
      
      let aiContent = res.data.response;
      
      // Check if AI suggested a standards update
      if (aiContent.includes("[UPDATE_STANDARDS]:")) {
        const parts = aiContent.split("[UPDATE_STANDARDS]:");
        aiContent = parts[0].trim();
        try {
          const newStandards = JSON.parse(parts[1].trim());
          if (Array.isArray(newStandards)) {
            setStandards(newStandards);
          }
        } catch (e) {
          console.error("Failed to parse suggested standards", e);
        }
      }

      setMessages((prev) => [...prev, { role: "assistant", content: aiContent }]);
      
      if (project.id && !sessions.find(s => s.id === currentSessionId)) {
        api.get(`/ai/projects/${project.id}/sessions`).then(r => setSessions(r.data));
      }
    } catch (error) {
      setMessages((prev) => [...prev, { role: "assistant", content: "Désolé, je rencontre une difficulté technique." }]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    setCurrentSessionId(Date.now().toString());
  };

  const handleClearChat = async () => {
    if (!project.id) {
      setMessages([{ role: "assistant", content: "Bonjour ! J'ai analysé votre projet. Voici les normes recommandées pour votre secteur et produit. Avez-vous des questions sur ces normes ou souhaitez-vous des explications ?" }]);
      return;
    }
    
    if (confirm("Voulez-vous vraiment effacer cette conversation ?")) {
      try {
        await api.delete(`/ai/projects/${project.id}/chat-history?session_id=${currentSessionId}`);
        setMessages([{ role: "assistant", content: "Bonjour ! J'ai analysé votre projet. Voici les normes recommandées pour votre secteur et produit. Avez-vous des questions sur ces normes ou souhaitez-vous des explications ?" }]);
        api.get(`/ai/projects/${project.id}/sessions`).then(r => setSessions(r.data));
      } catch (error) {
        console.error("Failed to clear chat", error);
      }
    }
  };

  const handleReanalyze = async () => {
    try {
      setAnalyzing(true);
      const analyzeRes = await api.post("/ai/analyze", { project_data: project, session_id: currentSessionId });
      setStandards(analyzeRes.data.standards);
    } catch (e) {
      console.error(e);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleValidate = () => {
    onConfirm(standards.join(", "));
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end p-4 pointer-events-none">
      <div className="bg-white w-full max-w-4xl h-[600px] shadow-2xl rounded-2xl border flex overflow-hidden pointer-events-auto animate-in slide-in-from-right duration-500">
        
        {/* Left Column: Recommended Norms */}
        <div className="w-1/3 bg-slate-50 border-r flex flex-col">
          <div className="p-4 border-b bg-white flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-brand-600" />
              <h3 className="font-semibold text-slate-800">Auto-Analyse</h3>
            </div>
            {!analyzing && (
              <button 
                onClick={handleReanalyze}
                title="Relancer l'analyse"
                className="p-1.5 text-slate-400 hover:text-brand-600 hover:bg-brand-50 rounded-md transition-colors"
              >
                <RefreshCcw className={`w-4 h-4 ${analyzing ? 'animate-spin' : ''}`} />
              </button>
            )}
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            <p className="text-xs text-slate-500 uppercase font-bold">Normes recommandées</p>
            {analyzing ? (
              <div className="flex flex-col items-center justify-center py-10 gap-3">
                <Loader2 className="w-6 h-6 animate-spin text-brand-500" />
                <span className="text-sm text-slate-400">Analyse en cours...</span>
              </div>
            ) : (
              standards.map((s, i) => (
                <div key={i} className="bg-white p-3 rounded-lg border shadow-sm hover:border-brand-300 transition-colors group">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-700">{s}</span>
                    <ChevronRight className="w-4 h-4 text-slate-300 group-hover:text-brand-500" />
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="p-4 bg-white border-t">
            <button 
              onClick={handleValidate}
              className="w-full bg-brand-600 hover:bg-brand-700 text-white py-2 rounded-lg flex items-center justify-center gap-2 text-sm font-medium transition-all"
            >
              <CheckCircle className="w-4 h-4" />
              Valider les normes
            </button>
          </div>
        </div>

        {/* Right Column: Chat */}
        <div className="flex-1 flex flex-col bg-white">
          <div className="p-4 border-b flex items-center justify-between bg-white shadow-sm relative z-10">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-brand-100 flex items-center justify-center shrink-0">
                <MessageSquare className="w-4 h-4 text-brand-600" />
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-slate-800 leading-none">Consultant IA</h3>
                  <span className="text-[10px] text-green-500 font-medium bg-green-50 px-1.5 py-0.5 rounded-full border border-green-100">En ligne</span>
                </div>
                {sessions.length > 0 && (
                  <select 
                    value={currentSessionId}
                    onChange={(e) => setCurrentSessionId(e.target.value)}
                    className="text-xs text-slate-500 bg-transparent border-none p-0 pr-4 mt-0.5 cursor-pointer focus:ring-0 w-48 truncate"
                  >
                    {sessions.map(s => (
                      <option key={s.id} value={s.id}>
                        {new Date(s.created_at).toLocaleDateString()} - {s.title}
                      </option>
                    ))}
                    {!sessions.find(s => s.id === currentSessionId) && (
                      <option value={currentSessionId}>Nouvelle conversation...</option>
                    )}
                  </select>
                )}
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              <button onClick={handleNewChat} title="Nouvelle conversation" className="p-1.5 text-brand-600 hover:bg-brand-50 rounded-md transition-colors">
                <Plus className="w-4 h-4" />
              </button>
              <button onClick={handleClearChat} title="Effacer cette session" className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors">
                <Trash2 className="w-4 h-4" />
              </button>
              <div className="w-px h-4 bg-slate-200 mx-1"></div>
              <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-md transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/50">
            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-[85%] p-3 rounded-2xl text-sm ${
                  m.role === "user" 
                    ? "bg-brand-600 text-white rounded-tr-none" 
                    : "bg-white border shadow-sm text-slate-700 rounded-tl-none"
                }`}>
                  {m.content}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-white border shadow-sm p-3 rounded-2xl rounded-tl-none flex gap-1">
                  <span className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce"></span>
                  <span className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce [animation-delay:0.2s]"></span>
                  <span className="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce [animation-delay:0.4s]"></span>
                </div>
              </div>
            )}
          </div>

          <div className="p-4 bg-white border-t">
            <div className="relative">
              <input 
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
                placeholder="Posez une question sur ces normes..."
                className="w-full pl-4 pr-12 py-3 bg-slate-100 border-none rounded-xl text-sm focus:ring-2 focus:ring-brand-500 transition-all"
              />
              <button 
                onClick={handleSend}
                disabled={loading || !input.trim()}
                className="absolute right-2 top-1.5 bg-brand-600 text-white p-2 rounded-lg hover:bg-brand-700 disabled:opacity-50 transition-all"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
