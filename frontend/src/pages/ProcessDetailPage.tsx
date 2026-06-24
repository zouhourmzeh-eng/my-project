import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

interface Process {
  id: number; project_id: number; name: string; description: string; version: string;
  file_url: string | null; file_name: string | null;
  process_owner: string; objective: string; inputs: string; outputs: string;
  activities: string; resources: string; kpis: string;
  risks_opportunities: string; related_documents: string;
  created_at: string; updated_at: string; validated_at: string | null; progress: number;
}
interface Document { id: number; title: string; description: string; status: "draft"|"validated"|"approved"; current_version: string; updated_at: string; }

const SHEET_FIELDS: { key: keyof Process; label: string; rows?: number }[] = [
  { key: "process_owner", label: "Process Owner", rows: 1 },
  { key: "objective", label: "Objective", rows: 2 },
  { key: "inputs", label: "Inputs", rows: 3 },
  { key: "outputs", label: "Outputs", rows: 3 },
  { key: "activities", label: "Activities", rows: 4 },
  { key: "resources", label: "Resources", rows: 3 },
  { key: "kpis", label: "Performance Indicators (KPIs)", rows: 3 },
  { key: "risks_opportunities", label: "Risks & Opportunities", rows: 3 },
  { key: "related_documents", label: "Related Documents", rows: 2 },
];

export default function ProcessDetailPage() {
  const { id } = useParams();
  const processId = Number(id);
  const { user } = useAuth();
  const qc = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const isConsultant = user?.role === "consultant";

  const { data: process } = useQuery<Process>({
    queryKey: ["process", processId],
    queryFn: async () => (await api.get(`/processes/${processId}`)).data,
  });
  const { data: documents = [] } = useQuery<Document[]>({
    queryKey: ["documents", processId],
    queryFn: async () => (await api.get(`/processes/${processId}/documents`)).data,
  });

  const [showDoc, setShowDoc] = useState(false);
  const [docForm, setDocForm] = useState({ title: "", description: "" });
  const [search, setSearch] = useState("");

  const filtered = documents.filter((d) =>
    [d.title, d.description].some(v => v?.toLowerCase().includes(search.toLowerCase()))
  );

  const createDoc = useMutation({
    mutationFn: async () => (await api.post(`/processes/${processId}/documents`, docForm)).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["documents", processId] }); setShowDoc(false); setDocForm({ title: "", description: "" }); },
  });

  // Process Sheet form state
  const [tab, setTab] = useState<"upload" | "form">("form");
  const [sheet, setSheet] = useState<Record<string, string>>({});
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => {
    if (!process) return;
    const initial: Record<string, string> = {};
    SHEET_FIELDS.forEach((f) => { initial[f.key as string] = (process as any)[f.key] || ""; });
    initial.name = process.name;
    initial.description = process.description;
    initial.version = process.version;
    initial.progress = process.progress?.toString() || "0";
    setSheet(initial);
    setTab(process.file_url ? "upload" : "form");
  }, [process?.id]);

  const saveSheet = useMutation({
    mutationFn: async () => (await api.patch(`/processes/${processId}`, sheet)).data,
    onSuccess: () => {
      setSavedAt(new Date().toLocaleTimeString());
      qc.invalidateQueries({ queryKey: ["process", processId] });
    },
  });

  const deleteProcess = useMutation({
    mutationFn: async () => (await api.delete(`/processes/${processId}`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["processes", process?.project_id] });
      window.location.href = `/projects/${process?.project_id}`;
    },
  });

  async function uploadProcessFile(file: File) {
    const fd = new FormData();
    fd.append("file", file);
    const { data } = await api.post("/uploads/direct", fd, { headers: { "Content-Type": "multipart/form-data" } });
    await api.post(`/processes/${processId}/file`, null, { params: { file_url: data.file_url, file_name: data.file_name } });
    qc.invalidateQueries({ queryKey: ["process", processId] });
  }

  if (!process) return <div className="text-slate-500">Loading…</div>;

  const hasFormContent = SHEET_FIELDS.some((f) => (process as any)[f.key]);

  return (
    <div className="space-y-6">
      <Link to={`/projects/${process.project_id}`} className="text-sm text-brand-600 hover:underline">← Back to project</Link>

      <div className="bg-white p-6 rounded-lg shadow-sm border">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold">{process.name}</h1>
              <div className="flex items-center gap-2 bg-slate-50 px-2 py-1 rounded border">
                <div className="w-16 bg-slate-200 rounded-full h-1.5">
                  <div className="bg-brand-500 h-1.5 rounded-full" style={{ width: `${process.progress}%` }}></div>
                </div>
                <span className="text-xs font-medium text-slate-600">{process.progress}%</span>
              </div>
            </div>
            <p className="text-sm text-slate-500 mt-1">v{process.version}</p>
            <p className="mt-2 text-sm">{process.description}</p>
            <div className="flex flex-wrap gap-x-6 gap-y-1 mt-4 text-[11px] text-slate-400 border-t pt-2">
              <span>Created: {new Date(process.created_at).toLocaleString()}</span>
              <span>Last modified: {new Date(process.updated_at).toLocaleString()}</span>
              {process.validated_at && <span className="text-emerald-600 font-medium">Validated: {new Date(process.validated_at).toLocaleString()}</span>}
            </div>
          </div>
          {isConsultant && (
            <button
              onClick={() => { if (confirm("Are you sure you want to delete this process?")) deleteProcess.mutate(); }}
              className="text-sm bg-red-50 text-red-600 hover:bg-red-100 px-3 py-1.5 rounded border border-red-200">
              🗑 Delete Process
            </button>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border">
        <div className="px-5 py-3 border-b flex items-center justify-between">
          <h2 className="font-medium">Process Sheet</h2>
          <div className="flex items-center gap-1 bg-slate-100 rounded p-1 text-sm">
            <button onClick={() => setTab("form")}
              className={`px-3 py-1 rounded ${tab === "form" ? "bg-white shadow text-brand-700" : "text-slate-600"}`}>
              Fill form
            </button>
            <button onClick={() => setTab("upload")}
              className={`px-3 py-1 rounded ${tab === "upload" ? "bg-white shadow text-brand-700" : "text-slate-600"}`}>
              Upload sheet
            </button>
          </div>
        </div>

        {tab === "form" ? (
          <div className="p-5 space-y-4">
            {!isConsultant && !hasFormContent && (
              <div className="text-sm text-slate-500">No process sheet has been filled in yet.</div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-1">
                <label className="block text-xs uppercase text-slate-500 mb-1">Process Name</label>
                <input
                  className="w-full border rounded px-3 py-2 disabled:bg-slate-50"
                  disabled={!isConsultant}
                  value={sheet.name || ""}
                  onChange={(e) => setSheet({ ...sheet, name: e.target.value })}
                />
              </div>
              <div className="md:col-span-1">
                <label className="block text-xs uppercase text-slate-500 mb-1">Version</label>
                <input
                  className="w-full border rounded px-3 py-2 disabled:bg-slate-50"
                  disabled={!isConsultant}
                  value={sheet.version || ""}
                  onChange={(e) => setSheet({ ...sheet, version: e.target.value })}
                />
              </div>
              <div className="md:col-span-1">
                <label className="block text-xs uppercase text-slate-500 mb-1">Progress: {sheet.progress || 0}%</label>
                <input
                  type="range" min="0" max="100"
                  className="w-full accent-brand-600 h-10"
                  disabled={!isConsultant}
                  value={sheet.progress || 0}
                  onChange={(e) => setSheet({ ...sheet, progress: e.target.value })}
                />
              </div>
              <div className="md:col-span-1">
                <label className="block text-xs uppercase text-slate-500 mb-1">Description</label>
                <textarea
                  className="w-full border rounded px-3 py-2 disabled:bg-slate-50"
                  rows={2}
                  disabled={!isConsultant}
                  value={sheet.description || ""}
                  onChange={(e) => setSheet({ ...sheet, description: e.target.value })}
                />
              </div>
              {SHEET_FIELDS.map((f) => (
                <div key={f.key as string} className={f.rows && f.rows > 2 ? "md:col-span-2" : ""}>
                  <label className="block text-xs uppercase text-slate-500 mb-1">{f.label}</label>
                  {f.rows === 1 ? (
                    <input
                      className="w-full border rounded px-3 py-2 disabled:bg-slate-50"
                      disabled={!isConsultant}
                      value={sheet[f.key as string] || ""}
                      onChange={(e) => setSheet({ ...sheet, [f.key as string]: e.target.value })}
                    />
                  ) : (
                    <textarea
                      className="w-full border rounded px-3 py-2 disabled:bg-slate-50"
                      rows={f.rows}
                      disabled={!isConsultant}
                      value={sheet[f.key as string] || ""}
                      onChange={(e) => setSheet({ ...sheet, [f.key as string]: e.target.value })}
                    />
                  )}
                </div>
              ))}
            </div>
            {isConsultant && (
              <div className="flex items-center justify-end gap-3 pt-2 border-t">
                {savedAt && <span className="text-xs text-emerald-600">Saved at {savedAt}</span>}
                <button
                  onClick={() => saveSheet.mutate()}
                  disabled={saveSheet.isPending}
                  className="bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white px-4 py-2 rounded text-sm">
                  {saveSheet.isPending ? "Saving…" : "Save process sheet"}
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="p-5 space-y-3">
            {process.file_url ? (
              <a href={process.file_url} target="_blank" rel="noreferrer"
                className="inline-flex items-center gap-2 text-brand-700 hover:underline">
                📄 {process.file_name}
              </a>
            ) : (
              <div className="text-sm text-slate-500">No process sheet uploaded.</div>
            )}
            {isConsultant && (
              <div>
                <input ref={fileInput} type="file" hidden onChange={(e) => e.target.files && uploadProcessFile(e.target.files[0])} />
                <button onClick={() => fileInput.current?.click()} className="text-sm bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded">
                  {process.file_name ? "Replace sheet" : "Upload sheet"}
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg shadow-sm border">
        <div className="px-5 py-3 border-b flex flex-col md:flex-row md:items-center justify-between gap-3">
          <h2 className="font-medium">SMQ Documents</h2>
          <div className="flex gap-2">
            <input
              className="border rounded px-3 py-1.5 text-sm w-full md:w-64"
              placeholder="Search documents…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {(user?.role === "consultant" || user?.role === "assistant") && (
              <button onClick={() => setShowDoc(true)} className="text-sm bg-brand-600 hover:bg-brand-700 text-white px-3 py-1.5 rounded shrink-0">New document</button>
            )}
          </div>
        </div>
        <div className="divide-y">
          {filtered.length === 0 && <div className="p-6 text-sm text-slate-500">{documents.length === 0 ? "No documents yet." : "No documents match your search."}</div>}
          {filtered.map((d) => (
            <Link key={d.id} to={`/documents/${d.id}`} className="flex items-center justify-between px-5 py-3 hover:bg-slate-50">
              <div>
                <div className="font-medium">{d.title}</div>
                <div className="text-xs text-slate-500">v{d.current_version} · updated {new Date(d.updated_at).toLocaleDateString()}</div>
              </div>
              <StatusPill status={d.status} />
            </Link>
          ))}
        </div>
      </div>

      {showDoc && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-20" onClick={() => setShowDoc(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={(e) => { e.preventDefault(); createDoc.mutate(); }}
            className="bg-white p-6 rounded-lg shadow w-full max-w-md space-y-3">
            <h2 className="text-lg font-semibold">New document</h2>
            <input className="w-full border rounded px-3 py-2" placeholder="Title" value={docForm.title} onChange={(e) => setDocForm({ ...docForm, title: e.target.value })} required />
            <textarea className="w-full border rounded px-3 py-2" placeholder="Description" rows={3} value={docForm.description} onChange={(e) => setDocForm({ ...docForm, description: e.target.value })} />
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setShowDoc(false)} className="px-4 py-2">Cancel</button>
              <button className="bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded">Create</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}

export function StatusPill({ status }: { status: "draft" | "validated" | "approved" }) {
  const map = {
    draft: "bg-amber-100 text-amber-700",
    validated: "bg-blue-100 text-blue-700",
    approved: "bg-emerald-100 text-emerald-700",
  };
  return <span className={`text-xs uppercase tracking-wide px-2 py-1 rounded ${map[status]}`}>{status}</span>;
}
