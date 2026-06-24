import { FormEvent, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, WS_URL } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import { StatusPill } from "./ProcessDetailPage";
import GapAnalysisPanel from "../components/GapAnalysisPanel";

type Status = "draft" | "validated" | "approved";
interface Doc { id: number; process_id: number; title: string; description: string; status: Status; current_version: string; created_at: string; updated_at: string; validated_at: string | null; }
interface Version { id: number; version: string; file_url: string; file_name: string; status: Status; note: string; created_at: string; uploaded_by: number; }
interface Attachment { id: number; file_url: string; file_name: string; content_type: string; }
interface Message { id: number; user_id: number; body: string; created_at: string; attachments: Attachment[]; }
interface User { id: number; full_name: string; role: string; }

export default function DocumentDetailPage() {
  const { id } = useParams();
  const docId = Number(id);
  const { user } = useAuth();
  const qc = useQueryClient();

  const { data: doc } = useQuery<Doc>({ queryKey: ["doc", docId], queryFn: async () => (await api.get(`/documents/${docId}`)).data });

  const { data: process } = useQuery({
    queryKey: ["process", doc?.process_id],
    queryFn: async () => (await api.get(`/processes/${doc!.process_id}`)).data,
    enabled: !!doc?.process_id,
  });

  const { data: project } = useQuery({
    queryKey: ["project", process?.project_id],
    queryFn: async () => (await api.get(`/projects/${process!.project_id}`)).data,
    enabled: !!process?.project_id,
  });

  const { data: versions = [] } = useQuery<Version[]>({ queryKey: ["versions", docId], queryFn: async () => (await api.get(`/documents/${docId}/versions`)).data });
  const { data: messages = [] } = useQuery<Message[]>({ queryKey: ["messages", docId], queryFn: async () => (await api.get(`/documents/${docId}/messages`)).data });
  
  const { data: users = [] } = useQuery<User[]>({
    queryKey: ["members", process?.project_id],
    queryFn: async () => (await api.get(`/projects/${process!.project_id}/members`)).data,
    enabled: !!process?.project_id,
  });
  const [showGap, setShowGap] = useState(false);

  const userMap = new Map(users.map((u) => [u.id, u]));

  // ── Role/status helpers ────────────────────────────────────────────────────
  const isConsultant = user?.role === "consultant";
  const isAssistant  = user?.role === "assistant";
  // Document is locked once validated or approved
  const isLocked     = doc?.status === "validated" || doc?.status === "approved";
  // Assistant can perform write operations only on draft documents
  const canAssistantWrite = isAssistant && !isLocked;
  // Either consultant (always) or assistant on draft
  const canWrite = isConsultant || canAssistantWrite;
  // ──────────────────────────────────────────────────────────────────────────

  const setStatus = useMutation({
    mutationFn: async (status: Status) => (await api.patch(`/documents/${docId}/status`, { status })).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["doc", docId] }); qc.invalidateQueries({ queryKey: ["versions", docId] }); },
  });
  
  const deleteDoc = useMutation({
    mutationFn: async () => (await api.delete(`/documents/${docId}`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents", doc?.process_id] });
      window.location.href = `/processes/${doc?.process_id}`;
    },
  });

  const [isEditing, setIsEditing] = useState(false);
  const [docForm, setDocForm] = useState({ title: "", description: "" });

  const editDoc = useMutation({
    mutationFn: async () => (await api.patch(`/documents/${docId}`, docForm)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["doc", docId] });
      setIsEditing(false);
    },
  });

  function startEditing() {
    if (doc) {
      setDocForm({ title: doc.title, description: doc.description });
      setIsEditing(true);
    }
  }

  const deleteVersion = useMutation({
    mutationFn: async (vid: number) => (await api.delete(`/documents/versions/${vid}`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["versions", docId] });
      qc.invalidateQueries({ queryKey: ["doc", docId] });
    },
  });

  const versionFile = useRef<HTMLInputElement>(null);
  const [verNum, setVerNum] = useState("1.1");
  const [verNote, setVerNote] = useState("");

  async function uploadVersion(file: File) {
    const fd = new FormData();
    fd.append("file", file);
    const { data } = await api.post("/uploads/direct", fd, { headers: { "Content-Type": "multipart/form-data" } });
    await api.post(`/documents/${docId}/versions`, null, { params: { version: verNum, file_url: data.file_url, file_name: data.file_name, note: verNote } });
    setVerNote(""); if (versionFile.current) versionFile.current.value = "";
    qc.invalidateQueries({ queryKey: ["versions", docId] });
    qc.invalidateQueries({ queryKey: ["doc", docId] });
  }

  // chat
  const [msg, setMsg] = useState("");
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEnd = useRef<HTMLDivElement | null>(null);
  const chatFileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    const ws = new WebSocket(`${WS_URL}/ws/documents/${docId}?token=${token}`);
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data);
        if (payload.type === "message" || payload.type === "message_deleted" || payload.type === "chat_cleared") {
          qc.invalidateQueries({ queryKey: ["messages", docId] });
        }
      } catch {}
    };
    return () => ws.close();
  }, [docId, qc]);

  useEffect(() => { messagesEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [messages.length]);

  const post = useMutation({
    mutationFn: async () => {
      if (pendingFiles.length === 0) {
        return (await api.post(`/documents/${docId}/messages`, { body: msg })).data;
      }
      const fd = new FormData();
      fd.append("body", msg);
      pendingFiles.forEach((f) => fd.append("files", f));
      return (await api.post(`/documents/${docId}/messages/upload`, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      })).data;
    },
    onSuccess: () => {
      setMsg(""); setPendingFiles([]);
      if (chatFileInput.current) chatFileInput.current.value = "";
      qc.invalidateQueries({ queryKey: ["messages", docId] });
    },
  });

  const deleteMessage = useMutation({
    mutationFn: async (mid: number) => (await api.delete(`/messages/${mid}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["messages", docId] }),
  });

  const clearChat = useMutation({
    mutationFn: async () => (await api.delete(`/documents/${docId}/messages`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["messages", docId] }),
  });

  const [chatSearch, setChatSearch] = useState("");
  const filteredMessages = messages.filter((m) =>
    m.body.toLowerCase().includes(chatSearch.toLowerCase()) ||
    m.attachments.some(a => a.file_name.toLowerCase().includes(chatSearch.toLowerCase()))
  );

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (msg.trim() || pendingFiles.length > 0) post.mutate();
  }

  if (!doc) return <div className="text-slate-500">Loading…</div>;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-2 space-y-6">
        <div className="bg-white p-6 rounded-lg shadow-sm border">
          {isEditing ? (
            <form onSubmit={(e) => { e.preventDefault(); editDoc.mutate(); }} className="space-y-4">
              <input className="w-full border rounded px-3 py-2" placeholder="Title" value={docForm.title} onChange={(e) => setDocForm({ ...docForm, title: e.target.value })} required />
              <textarea className="w-full border rounded px-3 py-2" placeholder="Description" rows={3} value={docForm.description} onChange={(e) => setDocForm({ ...docForm, description: e.target.value })} />
              <div className="flex justify-end gap-2">
                <button type="button" onClick={() => setIsEditing(false)} className="px-4 py-2 border rounded">Cancel</button>
                <button className="bg-brand-600 text-white px-4 py-2 rounded">Save</button>
              </div>
            </form>
          ) : (
            <>
              <div className="flex items-start justify-between">
                <div>
                  <h1 className="text-2xl font-semibold">{doc.title}</h1>
                  <p className="text-sm text-slate-500 mt-1">v{doc.current_version}</p>
                  <p className="mt-3 text-sm">{doc.description}</p>
                  <div className="flex flex-wrap gap-x-6 gap-y-1 mt-4 text-[11px] text-slate-400 border-t pt-2">
                    <span>Created: {new Date(doc.created_at).toLocaleString()}</span>
                    <span>Last modified: {new Date(doc.updated_at).toLocaleString()}</span>
                    {doc.validated_at && <span className="text-emerald-600 font-medium">Validated: {new Date(doc.validated_at).toLocaleString()}</span>}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <StatusPill status={doc.status} />
                  {/* Edit / Delete — visible for consultant always, for assistant only on draft */}
                  {canWrite && (
                    <div className="flex gap-1">
                      <button onClick={startEditing} className="text-xs bg-slate-50 text-slate-600 hover:bg-slate-100 px-2 py-1 rounded border">✎ Edit</button>
                      <button
                        onClick={() => { if (confirm("Are you sure you want to delete this document?")) deleteDoc.mutate(); }}
                        className="text-xs bg-red-50 text-red-600 hover:bg-red-100 px-2 py-1 rounded border border-red-200">
                        🗑 Delete
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* ── Lock banner for assistant on validated/approved docs ── */}
              {isAssistant && isLocked && (
                <div className="mt-4 flex items-start gap-3 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
                  <span className="text-amber-500 text-lg mt-0.5">🔒</span>
                  <div>
                    <p className="text-sm font-medium text-amber-800">
                      {doc.status === "approved"
                        ? "Ce document est archivé (approuvé par le consultant)."
                        : "Ce document a été validé par le consultant."}
                    </p>
                    <p className="text-xs text-amber-700 mt-0.5">
                      Vous ne pouvez plus modifier, supprimer ni analyser ce document. Vous pouvez uniquement télécharger le fichier.
                    </p>
                  </div>
                </div>
              )}

              {/* ── Status / action buttons — consultant only ── */}
              {isConsultant && (
                <div className="mt-4 flex flex-wrap gap-2">
                  <button onClick={() => setStatus.mutate("draft")} className="px-3 py-1.5 text-sm rounded bg-amber-100 text-amber-700 hover:bg-amber-200">Mark draft</button>
                  <button onClick={() => setStatus.mutate("validated")} className="px-3 py-1.5 text-sm rounded bg-blue-100 text-blue-700 hover:bg-blue-200">Validate</button>
                  <button onClick={() => setStatus.mutate("approved")} className="px-3 py-1.5 text-sm rounded bg-emerald-100 text-emerald-700 hover:bg-emerald-200">Approve (Archive)</button>
                  {versions.length > 0 && (
                    <button onClick={() => setShowGap(true)} className="px-3 py-1.5 text-sm rounded bg-indigo-600 text-white hover:bg-indigo-700 font-medium flex items-center gap-1 shadow-sm transition-colors ml-auto">
                      🎯 Analyse de Gap
                    </button>
                  )}
                </div>
              )}

              {/* ── Gap analysis button for assistant — only on draft + file uploaded ── */}
              {canAssistantWrite && versions.length > 0 && (
                <div className="mt-4">
                  <button onClick={() => setShowGap(true)} className="px-3 py-1.5 text-sm rounded bg-indigo-600 text-white hover:bg-indigo-700 font-medium flex items-center gap-1 shadow-sm transition-colors">
                    🎯 Analyse de Gap
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        <div className="bg-white rounded-lg shadow-sm border">
          <div className="px-5 py-3 border-b"><h2 className="font-medium">Versions</h2></div>
          <div className="p-5 space-y-3">
            {/* Upload form — consultant always, assistant only on draft */}
            {canWrite && versions.length === 0 && (
              <div className="flex flex-wrap gap-2 items-center bg-slate-50 p-3 rounded">
                <input className="border rounded px-2 py-1 w-24" value={verNum} onChange={(e) => setVerNum(e.target.value)} placeholder="1.0" />
                <input className="border rounded px-2 py-1 flex-1 min-w-[160px]" value={verNote} onChange={(e) => setVerNote(e.target.value)} placeholder="Initial version note" />
                <input ref={versionFile} type="file" onChange={(e) => e.target.files && uploadVersion(e.target.files[0])} className="text-sm" />
              </div>
            )}
            {canWrite && versions.length > 0 && (
              <div className="bg-blue-50 border border-blue-100 text-blue-700 p-3 rounded text-sm">
                A file is already uploaded. Delete it if you want to upload a different one.
              </div>
            )}
            {versions.length === 0 && <div className="text-sm text-slate-500">No versions yet.</div>}
            <ul className="divide-y">
              {versions.map((v) => (
                <li key={v.id} className="py-2 flex items-center justify-between">
                  <div>
                    {/* Download link — always visible for everyone */}
                    <a href={v.file_url} target="_blank" rel="noreferrer" className="font-medium text-brand-700 hover:underline">
                      ⬇ v{v.version} · {v.file_name}
                    </a>
                    {v.note && <div className="text-xs text-slate-500">{v.note}</div>}
                    <div className="text-xs text-slate-400">{new Date(v.created_at).toLocaleString()} · by {userMap.get(v.uploaded_by)?.full_name || "user"}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <StatusPill status={v.status} />
                    {/* Remove button — consultant always, assistant only on draft */}
                    {canWrite && (
                      <button
                        onClick={() => { if (confirm("Delete this uploaded file?")) deleteVersion.mutate(v.id); }}
                        className="text-red-500 hover:text-red-700 text-xs">
                        Remove
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border flex flex-col h-[640px]">
        <div className="px-5 py-3 border-b">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-medium">Discussion</h2>
              <p className="text-xs text-slate-500">Real-time chat</p>
            </div>
            {messages.length > 0 && (
              <button
                onClick={() => { if (confirm(isConsultant ? "Clear the entire discussion for EVERYONE? This cannot be undone." : "Clear discussion for your view? The consultant will still see these messages.")) clearChat.mutate(); }}
                className="text-[11px] text-red-600 hover:underline">
                {isConsultant ? "Clear for all" : "Clear my view"}
              </button>
            )}
          </div>
          <input
            className="w-full mt-2 border rounded px-2 py-1 text-xs"
            placeholder="Search in chat…"
            value={chatSearch}
            onChange={(e) => setChatSearch(e.target.value)}
          />
        </div>
        <div className="flex-1 overflow-auto p-4 space-y-3">
          {filteredMessages.length === 0 && (
            <div className="text-center text-slate-400 text-sm mt-10">
              {messages.length === 0 ? "No messages yet." : "No matches found."}
            </div>
          )}
          {filteredMessages.map((m) => {
            const author = userMap.get(m.user_id);
            const mine = m.user_id === user?.id;
            return (
              <div key={m.id} className={`group flex ${mine ? "justify-end" : "justify-start"}`}>
                <div className={`relative max-w-[80%] rounded-lg px-3 py-2 ${mine ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-800"}`}>
                  <div className="text-[11px] opacity-80 mb-0.5">{author?.full_name || "user"} · {author?.role}</div>
                  <div className="text-sm whitespace-pre-wrap">{m.body}</div>
                  {m.attachments.map((a) => (
                    <a key={a.id} href={a.file_url} target="_blank" rel="noreferrer"
                      className={`block mt-1 text-xs underline ${mine ? "text-white/90" : "text-brand-700"}`}>📎 {a.file_name}</a>
                  ))}
                  <div className="flex items-center justify-between mt-1 gap-4">
                    <div className="text-[10px] opacity-70">{new Date(m.created_at).toLocaleTimeString()}</div>
                    <button
                      onClick={() => { if (confirm("Delete this message?")) deleteMessage.mutate(m.id); }}
                      className="opacity-0 group-hover:opacity-100 text-[10px] underline hover:no-underline">
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
          <div ref={messagesEnd} />
        </div>
        <form onSubmit={onSubmit} className="border-t p-3 space-y-2">
          {pendingFiles.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {pendingFiles.map((f, i) => (
                <span key={i} className="inline-flex items-center gap-1 bg-slate-100 text-slate-700 text-xs px-2 py-1 rounded">
                  📎 {f.name}
                  <button type="button" onClick={() => setPendingFiles(pendingFiles.filter((_, j) => j !== i))}
                    className="ml-1 text-slate-500 hover:text-red-600">x</button>
                </span>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <input value={msg} onChange={(e) => setMsg(e.target.value)} placeholder="Write a message…" className="flex-1 border rounded px-3 py-2" />
            <label className="cursor-pointer text-sm bg-slate-100 hover:bg-slate-200 px-3 py-2 rounded" title="Attach files">
              📎
              <input ref={chatFileInput} type="file" hidden multiple onChange={(e) => {
                if (e.target.files) setPendingFiles([...pendingFiles, ...Array.from(e.target.files)]);
              }} />
            </label>
            <button disabled={post.isPending} className="bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white px-4 py-2 rounded">
              {post.isPending ? "…" : "Send"}
            </button>
          </div>
        </form>
      </div>
      {showGap && project && (
        <GapAnalysisPanel
          project={project}
          documentId={docId}
          onClose={() => setShowGap(false)}
        />
      )}
    </div>
  );
}
