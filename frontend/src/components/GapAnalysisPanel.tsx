import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { Play, FileText, CheckCircle2, AlertCircle, Download, Clock } from "lucide-react";

export default function GapAnalysisPanel({ project, documentId, onClose }: { project: any; documentId?: number; onClose: () => void }) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"new" | "history" | "capas">("new");
  const [option, setOption] = useState<"all" | "specific">("all");
  const [selectedStandard, setSelectedStandard] = useState("");
  const [viewReport, setViewReport] = useState<any>(null);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);

  const handleDownloadPDF = async () => {
    if (isDownloadingPdf || !viewReport?.id) return;
    setIsDownloadingPdf(true);
    try {
      const response = await api.get(`/gap-analysis/report/${viewReport.id}/pdf`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Rapport_Gap_${viewReport.id}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download PDF", err);
      alert("Une erreur est survenue lors du téléchargement du PDF.");
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  const standardsList = (project.standards || "").split(",").map((s: string) => s.trim()).filter((s: string) => s);

  // Queries
  const { data: history = [], isLoading: isLoadingHistory } = useQuery({
    queryKey: ["gap-history", project.id, documentId],
    queryFn: async () => (await api.get(documentId ? `/gap-analysis/document/${documentId}` : `/gap-analysis/project/${project.id}`)).data,
  });

  const { data: reportDetails, isLoading: isLoadingReport } = useQuery({
    queryKey: ["gap-report", viewReport?.id],
    queryFn: async () => (await api.get(`/gap-analysis/report/${viewReport.id}`)).data,
    enabled: !!viewReport,
  });

  const { data: capas = [], isLoading: isLoadingCapas } = useQuery({
    queryKey: ["gap-capas", project.id, documentId],
    queryFn: async () => (await api.get(documentId ? `/gap-analysis/document/${documentId}/capas` : `/gap-analysis/project/${project.id}/capas`)).data,
  });

  // Mutations
  const analyze = useMutation({
    mutationFn: async () => {
      const payload = option === "all" ? {} : { standard: selectedStandard };
      const url = documentId ? `/gap-analysis/document/${documentId}` : `/gap-analysis/project/${project.id}`;
      return (await api.post(url, payload)).data;
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["gap-history", project.id, documentId] });
      qc.invalidateQueries({ queryKey: ["gap-capas", project.id, documentId] });
      setTab("history");
      setViewReport({ id: data.report_id });
    },
  });

  const toggleCapa = useMutation({
    mutationFn: async (capaId: number) => {
      return (await api.patch(`/gap-analysis/capa/${capaId}/toggle`)).data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["gap-capas", project.id, documentId] });
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/50 backdrop-blur-sm transition-opacity">
      <div className="w-full max-w-3xl bg-white shadow-2xl h-full flex flex-col border-l border-slate-200">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-100 bg-white">
          <div className="flex items-center gap-3">
            <div className="bg-brand-100 p-2 rounded-xl border border-brand-200">
              <AlertCircle className="w-6 h-6 text-brand-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-800">Analyse de Gap</h2>
              <p className="text-sm text-slate-500">Procédures vs Normes ({project.company_name})</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-100 rounded-full transition-colors">
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-200 px-6 mt-2">
          <button
            onClick={() => setTab("new")}
            className={`pb-3 px-4 font-medium text-sm transition-colors border-b-2 ${
              tab === "new" ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            Nouvelle Analyse
          </button>
          <button
            onClick={() => { setTab("history"); setViewReport(null); }}
            className={`pb-3 px-4 font-medium text-sm transition-colors border-b-2 flex items-center gap-2 ${
              tab === "history" ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            <Clock size={16} /> Historique & Rapports
          </button>
          <button
            onClick={() => setTab("capas")}
            className={`pb-3 px-4 font-medium text-sm transition-colors border-b-2 flex items-center gap-2 ${
              tab === "capas" ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            <CheckCircle2 size={16} /> Actions CAPA ({capas.filter((c: any) => c.status === "open").length})
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto bg-slate-50/50 p-6">
          
          {tab === "new" && (
            <div className="max-w-xl mx-auto space-y-6">
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <h3 className="font-semibold text-slate-800 mb-4">Périmètre de l'analyse</h3>
                
                <div className="space-y-4">
                  <label className={`flex items-start gap-3 p-4 border rounded-lg cursor-pointer transition-colors ${option === "all" ? 'bg-brand-50 border-brand-200' : 'hover:bg-slate-50'}`}>
                    <input 
                      type="radio" 
                      name="option" 
                      checked={option === "all"} 
                      onChange={() => setOption("all")} 
                      className="mt-1 w-4 h-4 text-brand-600 border-slate-300 focus:ring-brand-500"
                    />
                    <div>
                      <div className="font-medium text-slate-800">Toutes les normes du projet</div>
                      <div className="text-sm text-slate-500 mt-1">L'IA analysera vos documents contre toutes vos normes déclarées : {project.standards || "Aucune"}</div>
                    </div>
                  </label>

                  <label className={`flex items-start gap-3 p-4 border rounded-lg cursor-pointer transition-colors ${option === "specific" ? 'bg-brand-50 border-brand-200' : 'hover:bg-slate-50'}`}>
                    <input 
                      type="radio" 
                      name="option" 
                      checked={option === "specific"} 
                      onChange={() => setOption("specific")} 
                      className="mt-1 w-4 h-4 text-brand-600 border-slate-300 focus:ring-brand-500"
                    />
                    <div className="w-full">
                      <div className="font-medium text-slate-800 mb-2">Sélectionner une norme spécifique</div>
                      <select 
                        disabled={option !== "specific"}
                        className="w-full border-slate-300 rounded-md text-sm disabled:bg-slate-100 disabled:text-slate-400"
                        value={selectedStandard}
                        onChange={(e) => setSelectedStandard(e.target.value)}
                      >
                        <option value="">-- Choisir une norme --</option>
                        {standardsList.map((s: string) => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </div>
                  </label>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-sm text-blue-800">
                L'IA va extraire le texte brut de tous les documents SMQ (PDF, Word, Excel) téléversés et les confronter aux normes choisies. Cette analyse peut prendre de 1 à 3 minutes.
              </div>

              {analyze.isError && (
                <div className="bg-red-50 border border-red-200 text-red-800 rounded-xl p-4 text-sm flex items-start gap-2">
                  <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold">Erreur de l'analyse</div>
                    <div className="mt-1">
                      {(analyze.error as any).response?.data?.detail || "Une erreur est survenue lors du traitement."}
                    </div>
                  </div>
                </div>
              )}

              <button
                onClick={() => analyze.mutate()}
                disabled={analyze.isPending || (option === "specific" && !selectedStandard) || standardsList.length === 0}
                className="w-full flex items-center justify-center gap-2 bg-brand-600 hover:bg-brand-700 disabled:bg-brand-300 text-white font-medium py-3 px-4 rounded-xl shadow-sm transition-all"
              >
                {analyze.isPending ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Analyse de Gap en cours...
                  </>
                ) : (
                  <>
                    <Play size={18} /> Lancer l'Analyse IA
                  </>
                )}
              </button>
            </div>
          )}

          {tab === "history" && !viewReport && (
            <div className="space-y-4">
              {isLoadingHistory ? (
                <div className="text-center text-slate-500 py-10">Chargement de l'historique...</div>
              ) : history.length === 0 ? (
                <div className="text-center text-slate-500 py-10 bg-white rounded-xl border border-dashed border-slate-300">
                  Aucune analyse de Gap n'a encore été réalisée pour ce projet.
                </div>
              ) : (
                history.map((rep: any) => (
                  <div key={rep.id} className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-bold text-slate-800 text-lg mb-1">Rapport #{rep.id}</h3>
                        <div className="text-sm text-slate-500 flex items-center gap-2">
                          <FileText size={14} /> Normes : <span className="font-medium text-slate-700">{rep.target_standards}</span>
                        </div>
                        <div className="text-xs text-slate-400 mt-2">
                          Réalisé le : {new Date(rep.created_at).toLocaleString()}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button 
                          onClick={() => setViewReport(rep)}
                          className="px-4 py-2 bg-brand-50 text-brand-700 text-sm font-medium rounded-lg hover:bg-brand-100 border border-brand-200"
                        >
                          Voir le détail
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {tab === "history" && viewReport && (
            <div className="space-y-6">
              <button onClick={() => setViewReport(null)} className="text-sm text-brand-600 hover:underline flex items-center gap-1">
                ← Retour à l'historique
              </button>

              {isLoadingReport ? (
                <div className="text-center text-slate-500 py-10">Génération du rapport...</div>
              ) : reportDetails ? (
                <>
                  <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm flex items-start justify-between">
                    <div>
                      <h3 className="text-xl font-bold text-slate-800 mb-2">Rapport de Gap #{reportDetails.id}</h3>
                      <p className="text-sm text-slate-500">Cible : {reportDetails.target_standards}</p>
                    </div>
                    <button 
                      onClick={handleDownloadPDF}
                      disabled={isDownloadingPdf}
                      className="flex items-center gap-2 bg-slate-800 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-700 disabled:bg-slate-400"
                    >
                      {isDownloadingPdf ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          Génération...
                        </>
                      ) : (
                        <>
                          <Download size={16} /> Exporter PDF
                        </>
                      )}
                    </button>
                  </div>

                  <div className="space-y-4">
                    {reportDetails.items.map((item: any) => (
                      <div key={item.id} className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
                        <div className="bg-slate-50 px-5 py-3 border-b border-slate-200 flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <FileText size={18} className="text-slate-400" />
                            <h4 className="font-semibold text-slate-800">{item.document_title}</h4>
                          </div>
                          {item.compliance_score !== undefined && (
                            <div className="flex items-center gap-2">
                              <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                                item.compliance_status === "Conforme" 
                                  ? "bg-emerald-100 text-emerald-800 border border-emerald-200" 
                                  : "bg-amber-100 text-amber-800 border border-amber-200"
                              }`}>
                                {item.compliance_status}
                              </span>
                              <span className="text-sm font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border">
                                {item.compliance_score}%
                              </span>
                            </div>
                          )}
                        </div>
                        
                        <div className="p-5 space-y-4">
                          {item.missing_clauses.length > 0 ? (
                            <div className="bg-red-50 border border-red-100 rounded-lg p-4">
                              <h5 className="font-semibold text-red-800 text-sm flex items-center gap-2 mb-2">
                                <AlertCircle size={16} /> Clauses Manquantes / Écarts
                              </h5>
                              <ul className="list-disc list-inside space-y-1">
                                {item.missing_clauses.map((c: string, i: number) => (
                                  <li key={i} className="text-sm text-red-700">{c}</li>
                                ))}
                              </ul>
                            </div>
                          ) : (
                            <div className="bg-green-50 border border-green-100 rounded-lg p-4 flex items-center gap-2">
                              <CheckCircle2 className="text-green-600" size={20} />
                              <span className="font-medium text-green-800 text-sm">Ce document est conforme à la cible analysée.</span>
                            </div>
                          )}

                          <div>
                            <h5 className="font-semibold text-slate-700 text-sm mb-2">Suggestions de mise à jour</h5>
                            <div className="text-sm text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100 leading-relaxed whitespace-pre-wrap">
                              {item.update_suggestions}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              ) : null}
            </div>
          )}

          {tab === "capas" && (
            <div className="space-y-4">
              {isLoadingCapas ? (
                <div className="text-center text-slate-500 py-10">Chargement des actions CAPA...</div>
              ) : capas.length === 0 ? (
                <div className="text-center text-slate-500 py-10 bg-white rounded-xl border border-dashed border-slate-300">
                  Aucune action CAPA n'a été générée pour le moment. Lancez une analyse de Gap.
                </div>
              ) : (
                capas.map((capa: any) => (
                  <div key={capa.id} className={`bg-white border rounded-xl p-5 shadow-sm transition-all border-l-4 ${capa.status === 'open' ? 'border-l-amber-500' : 'border-l-green-500'}`}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${capa.status === 'open' ? 'bg-amber-100 text-amber-800' : 'bg-green-100 text-green-800'}`}>
                            {capa.status === 'open' ? 'À faire / Ouvert' : 'Résolu'}
                          </span>
                          <span className="text-xs text-slate-400">
                            Créée le : {new Date(capa.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <h4 className={`font-bold text-slate-800 text-base ${capa.status === 'closed' ? 'line-through text-slate-400' : ''}`}>
                          {capa.title}
                        </h4>
                        <p className="text-sm text-slate-600 leading-relaxed">
                          {capa.description}
                        </p>
                      </div>
                      <button
                        onClick={() => toggleCapa.mutate(capa.id)}
                        disabled={toggleCapa.isPending}
                        className={`shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all ${
                          capa.status === 'open' 
                            ? 'bg-green-50 border-green-200 text-green-700 hover:bg-green-100' 
                            : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                        }`}
                      >
                        {capa.status === 'open' ? 'Marquer résolu' : 'Rouvrir'}
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
