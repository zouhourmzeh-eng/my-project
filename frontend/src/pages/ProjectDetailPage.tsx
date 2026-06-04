import { FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import StandardAnalysisChatbot from "../components/StandardAnalysisChatbot";
import { UserSearch, UserPlus, X, Loader2 } from "lucide-react";

interface Project {
  id: number; company_name: string; company_role: string; activity_sector: string;
  product: string; market: string; standards: string; member_ids: number[]; owner_id: number;
  is_validated: boolean; validated_at: string | null; created_at: string; updated_at: string; progress: number;
}
interface UserLite { id: number; full_name: string; email: string; role: string; }
interface MemberInfo { id: number; full_name: string; email: string; role: string; }
interface Process {
  id: number; name: string; description: string; version: string;
  file_url: string | null; file_name: string | null; progress: number;
}

export default function ProjectDetailPage() {
  const { id } = useParams();
  const projectId = Number(id);
  const { user } = useAuth();
  const qc = useQueryClient();

  const { data: project } = useQuery<Project>({
    queryKey: ["project", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}`)).data,
  });
  const { data: processes = [] } = useQuery<Process[]>({
    queryKey: ["processes", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/processes`)).data,
  });

  const { data: members = [], refetch: refetchMembers } = useQuery<MemberInfo[]>({
    queryKey: ["members", projectId],
    queryFn: async () => (await api.get(`/projects/${projectId}/members`)).data,
    enabled: user?.role === "consultant",
  });

  // Member search state
  const [memberEmail, setMemberEmail] = useState("");
  const [foundUser, setFoundUser] = useState<UserLite | null | undefined>(undefined);
  const [searchError, setSearchError] = useState("");
  const [isSearching, setIsSearching] = useState(false);

  async function searchMember() {
    if (!memberEmail.trim()) return;
    setIsSearching(true);
    setSearchError("");
    setFoundUser(undefined);
    try {
      const res = await api.get(`/auth/users/search`, { params: { email: memberEmail.trim() } });
      if (res.data) {
        setFoundUser(res.data as UserLite);
      } else {
        setFoundUser(null);
        setSearchError(`Aucun utilisateur trouvé avec l'email : ${memberEmail}`);
      }
    } catch {
      setFoundUser(null);
      setSearchError("Erreur lors de la recherche. Vérifiez l'email saisi.");
    } finally {
      setIsSearching(false);
    }
  }

  function handleAddFoundUser() {
    if (foundUser) {
      addMember.mutate(foundUser.email);
    }
  }

  const validate = useMutation({
    mutationFn: async () => (await api.post(`/projects/${projectId}/validate`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["project", projectId] });
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });
  const unvalidate = useMutation({
    mutationFn: async () => (await api.post(`/projects/${projectId}/unvalidate`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["project", projectId] });
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const addMember = useMutation({
    mutationFn: async (email: string) =>
      (await api.post(`/projects/${projectId}/members`, { email })).data,
    onSuccess: () => {
      refetchMembers();
      setMemberEmail("");
      setFoundUser(undefined);
      setSearchError("");
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.detail ?? "Erreur lors de l'ajout du membre.";
      setSearchError(msg);
    },
  });
  const removeMember = useMutation({
    mutationFn: async (uid: number) =>
      (await api.delete(`/projects/${projectId}/members/${uid}`)).data,
    onSuccess: () => refetchMembers(),
  });

  const deleteProject = useMutation({
    mutationFn: async () => (await api.delete(`/projects/${projectId}`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      window.location.href = "/projects";
    },
  });

  const [isEditing, setIsEditing] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [projectForm, setProjectForm] = useState({
    company_name: "", company_role: "", activity_sector: "", product: "", market: "", standards: "", progress: 0
  });

  const editProject = useMutation({
    mutationFn: async () => (await api.patch(`/projects/${projectId}`, projectForm)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["project", projectId] });
      setIsEditing(false);
    },
  });

  function startEditing() {
    if (project) {
      setProjectForm({
        company_name: project.company_name,
        company_role: project.company_role,
        activity_sector: project.activity_sector,
        product: project.product,
        market: project.market,
        standards: project.standards,
        progress: project.progress,
      });
      setIsEditing(true);
    }
  }

  const [show, setShow] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", version: "1.0" });
  const [search, setSearch] = useState("");

  const filtered = processes.filter((p) =>
    [p.name, p.description].some(v => v?.toLowerCase().includes(search.toLowerCase()))
  );

  const create = useMutation({
    mutationFn: async () => (await api.post(`/projects/${projectId}/processes`, form)).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["processes", projectId] }); setShow(false); setForm({ name: "", description: "", version: "1.0" }); },
  });

  function onSubmit(e: FormEvent) { e.preventDefault(); create.mutate(); }

  if (!project) return <div className="text-slate-500">Loading…</div>;

  return (
    <div className="space-y-6">
      <Link to="/projects" className="text-sm text-brand-600 hover:underline">← All projects</Link>
      {project.is_validated && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 rounded-lg p-3 text-sm flex items-center justify-between">
          <span>🔒 This project is <b>validated</b> and read-only{project.validated_at ? ` since ${new Date(project.validated_at).toLocaleDateString()}` : ""}. Only consultants can see or modify it.</span>
          {user?.role === "consultant" && (
            <button onClick={() => unvalidate.mutate()} className="text-xs px-3 py-1 rounded bg-white border hover:bg-amber-100">Unlock</button>
          )}
        </div>
      )}
      <div className="bg-white p-6 rounded-lg shadow-sm border">
        {isEditing ? (
          <form onSubmit={(e) => { e.preventDefault(); editProject.mutate(); }} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <input className="border rounded px-3 py-2 w-full" placeholder="Company Name" value={projectForm.company_name} onChange={(e) => setProjectForm({ ...projectForm, company_name: e.target.value })} required />
              <input className="border rounded px-3 py-2 w-full" placeholder="Company Role" value={projectForm.company_role} onChange={(e) => setProjectForm({ ...projectForm, company_role: e.target.value })} required />
              <input className="border rounded px-3 py-2 w-full" placeholder="Activity Sector" value={projectForm.activity_sector} onChange={(e) => setProjectForm({ ...projectForm, activity_sector: e.target.value })} required />
              <input className="border rounded px-3 py-2 w-full" placeholder="Product" value={projectForm.product} onChange={(e) => setProjectForm({ ...projectForm, product: e.target.value })} required />
              <select className="border rounded px-3 py-2 w-full" value={projectForm.market} onChange={(e) => setProjectForm({ ...projectForm, market: e.target.value })}>
                <option>CE</option><option>FDI</option><option>FDA</option><option>UKCA</option><option>Other</option>
              </select>
              <div className="flex flex-col">
                <label className="text-xs text-slate-500 mb-1">Progress: {projectForm.progress}%</label>
                <input type="range" min="0" max="100" className="w-full accent-brand-600" value={projectForm.progress} onChange={(e) => setProjectForm({ ...projectForm, progress: parseInt(e.target.value) || 0 })} />
              </div>
              <textarea className="border rounded px-3 py-2 w-full md:col-span-2" placeholder="Standards" rows={2} value={projectForm.standards} onChange={(e) => setProjectForm({ ...projectForm, standards: e.target.value })} />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setIsEditing(false)} className="px-4 py-2 border rounded">Cancel</button>
              <button className="bg-brand-600 text-white px-4 py-2 rounded">Save Changes</button>
            </div>
          </form>
        ) : (
          <>
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-semibold">{project.company_name}</h1>
                  <div className="flex items-center gap-2 bg-slate-50 px-2 py-1 rounded border">
                    <div className="w-16 bg-slate-200 rounded-full h-1.5">
                      <div className="bg-brand-500 h-1.5 rounded-full" style={{ width: `${project.progress}%` }}></div>
                    </div>
                    <span className="text-xs font-medium text-slate-600">{project.progress}%</span>
                  </div>
                </div>
                <div className="text-sm text-slate-500">{project.company_role}</div>
              </div>
              {user?.role === "consultant" && !project.is_validated && (
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowChat(true)}
                    className="text-sm bg-brand-50 text-brand-600 hover:bg-brand-100 px-3 py-1.5 rounded border border-brand-200 font-medium flex items-center gap-1">
                    <span className="text-lg leading-none">🤖</span> IA
                  </button>
                  <button
                    onClick={startEditing}
                    className="text-sm bg-slate-50 text-slate-600 hover:bg-slate-100 px-3 py-1.5 rounded border">
                    ✎ Edit
                  </button>
                  <button
                    onClick={() => { if (confirm("Are you sure you want to delete this project? This action is irreversible.")) deleteProject.mutate(); }}
                    className="text-sm bg-red-50 text-red-600 hover:bg-red-100 px-3 py-1.5 rounded border border-red-200">
                    🗑 Delete
                  </button>
                  <button
                    onClick={() => { if (confirm("Validate this project? It will become read-only and invisible to non-consultants.")) validate.mutate(); }}
                    className="text-sm bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-1.5 rounded">
                    ✓ Validate project
                  </button>
                </div>
              )}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 text-sm border-t pt-4">
              <Field label="Sector" value={project.activity_sector} />
              <Field label="Product" value={project.product} />
              <Field label="Market" value={project.market} />
              <Field label="Standards" value={project.standards || "—"} />
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2 mt-4 text-[11px] text-slate-400 border-t pt-2">
              <span>Created: {new Date(project.created_at).toLocaleString()}</span>
              <span>Last modified: {new Date(project.updated_at).toLocaleString()}</span>
              {project.validated_at && <span className="text-emerald-600 font-medium">Validated: {new Date(project.validated_at).toLocaleString()}</span>}
            </div>
          </>
        )}
      </div>

      {user?.role === "consultant" && (
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="px-5 py-3 border-b font-medium flex items-center gap-2">
            <UserSearch size={16} className="text-brand-600" />
            Équipe du projet
          </div>
          <div className="p-5 space-y-4">
            {/* Current members list — rendered from pre-loaded members query */}
            <div className="flex flex-wrap gap-2">
              {members.length === 0 && (
                <div className="text-sm text-slate-400 italic">Aucun membre assigné pour l'instant.</div>
              )}
              {members.map((m) => (
                <span key={m.id} className="inline-flex items-center gap-2 bg-brand-50 text-brand-700 text-sm rounded-full pl-3 pr-1 py-1">
                  <span className="font-medium">{m.full_name}</span>
                  <span className="text-xs opacity-60 capitalize">· {m.role}</span>
                  <button
                    onClick={() => removeMember.mutate(m.id)}
                    disabled={removeMember.isPending}
                    className="ml-1 w-5 h-5 rounded-full bg-white text-brand-600 hover:bg-red-100 hover:text-red-600 flex items-center justify-center font-bold text-xs"
                    title="Retirer ce membre"
                  >×</button>
                </span>
              ))}
            </div>

            {/* Email search to add member */}
            <div className="border-t pt-4 space-y-3">
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wide">Ajouter un membre par email</p>
              <div className="flex gap-2">
                <input
                  type="email"
                  className="border rounded-lg px-3 py-2 text-sm flex-1 focus:outline-none focus:ring-2 focus:ring-brand-400"
                  placeholder="nom@exemple.com"
                  value={memberEmail}
                  onChange={(e) => { setMemberEmail(e.target.value); setFoundUser(undefined); setSearchError(""); }}
                  onKeyDown={(e) => e.key === "Enter" && searchMember()}
                />
                <button
                  onClick={searchMember}
                  disabled={isSearching || !memberEmail.trim()}
                  className="flex items-center gap-1.5 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSearching ? <Loader2 size={14} className="animate-spin" /> : <UserSearch size={14} />}
                  Rechercher
                </button>
              </div>

              {/* Search result */}
              {foundUser && !project.member_ids.includes(foundUser.id) && foundUser.id !== project.owner_id && (
                <div className="flex items-center justify-between bg-brand-50 border border-brand-200 rounded-lg px-4 py-3">
                  <div>
                    <p className="text-sm font-semibold text-slate-800">{foundUser.full_name}</p>
                    <p className="text-xs text-slate-500">{foundUser.email} · <span className="capitalize">{foundUser.role}</span></p>
                  </div>
                  <button
                    onClick={handleAddFoundUser}
                    disabled={addMember.isPending}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-50"
                  >
                    {addMember.isPending ? <Loader2 size={13} className="animate-spin" /> : <UserPlus size={13} />}
                    Ajouter
                  </button>
                </div>
              )}
              {foundUser && (project.member_ids.includes(foundUser.id) || foundUser.id === project.owner_id) && (
                <div className="text-sm text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-4 py-2">
                  ⚠️ Cet utilisateur fait déjà partie de l'équipe.
                </div>
              )}
              {searchError && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
                  {searchError}
                </div>
              )}
            </div>
          </div>
        </div>
      )}


      <div className="bg-white rounded-lg shadow-sm border">
        <div className="px-5 py-3 border-b flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <h2 className="font-medium">Processes</h2>
          </div>
          <div className="flex gap-2">
            <input
              className="border rounded px-3 py-1.5 text-sm w-full md:w-64"
              placeholder="Search processes…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            {user?.role === "consultant" && (
              <button onClick={() => setShow(true)} className="text-sm bg-brand-600 hover:bg-brand-700 text-white px-3 py-1.5 rounded shrink-0">
                Add process
              </button>
            )}
          </div>
        </div>
        <div className="divide-y">
          {filtered.length === 0 && <div className="p-6 text-sm text-slate-500">{processes.length === 0 ? "No processes yet." : "No processes match your search."}</div>}
          {filtered.map((p) => (
            <Link key={p.id} to={`/processes/${p.id}`} className="block px-5 py-3 hover:bg-slate-50">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">{p.name} <span className="text-xs text-slate-500">v{p.version}</span></div>
                  <div className="text-sm text-slate-500">{p.description}</div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-16 bg-slate-200 rounded-full h-1.5">
                    <div className="bg-brand-500 h-1.5 rounded-full" style={{ width: `${p.progress}%` }}></div>
                  </div>
                  <span className="text-xs font-medium text-slate-600 w-8 text-right">{p.progress}%</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {show && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-20" onClick={() => setShow(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={onSubmit}
            className="bg-white p-6 rounded-lg shadow w-full max-w-md space-y-3">
            <h2 className="text-lg font-semibold">New process</h2>
            <input className="w-full border rounded px-3 py-2" placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            <textarea className="w-full border rounded px-3 py-2" placeholder="Description" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <input className="w-full border rounded px-3 py-2" placeholder="Version" value={form.version} onChange={(e) => setForm({ ...form, version: e.target.value })} />
            <div className="flex justify-end gap-2"><button type="button" onClick={() => setShow(false)} className="px-4 py-2">Cancel</button>
              <button className="bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded">Create</button></div>
          </form>
        </div>
      )}

      {showChat && (
        <StandardAnalysisChatbot 
          project={project} 
          onClose={() => setShowChat(false)}
          onConfirm={async (standards) => {
            await api.patch(`/projects/${project.id}`, { standards });
            qc.invalidateQueries({ queryKey: ["project", projectId] });
            setShowChat(false);
          }}
        />
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (<div><div className="text-xs uppercase text-slate-400">{label}</div><div className="text-sm font-medium">{value}</div></div>);
}
