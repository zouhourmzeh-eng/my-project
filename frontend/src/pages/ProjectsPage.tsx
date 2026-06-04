import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";
import StandardAnalysisChatbot from "../components/StandardAnalysisChatbot";

interface Project {
  id: number; company_name: string; company_role: string; activity_sector: string;
  product: string; market: string; created_at: string; progress: number;
}

export default function ProjectsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const { data = [] } = useQuery<Project[]>({
    queryKey: ["projects", "active"],
    queryFn: async () => (await api.get("/projects?archived=false&limit=200")).data,
  });

  const [show, setShow] = useState(false);
  const [form, setForm] = useState({
    company_name: "", company_role: "", activity_sector: "", product: "",
    market: "", standards: "",
  });
  const [search, setSearch] = useState("");
  const [analyzingProject, setAnalyzingProject] = useState<Project | null>(null);

  const filtered = data.filter((p) =>
    [p.company_name, p.product, p.activity_sector, p.market].some(v => v.toLowerCase().includes(search.toLowerCase()))
  );

  const create = useMutation({
    mutationFn: async () => (await api.post("/projects", form)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      setShow(false);
      setForm({ company_name: "", company_role: "", activity_sector: "", product: "", market: "CE", standards: "" });
    },
  });

  const deleteProject = useMutation({
    mutationFn: async (id: number) => (await api.delete(`/projects/${id}`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  function onSubmit(e: FormEvent) { e.preventDefault(); create.mutate(); }

  return (
    <div className="space-y-5">
      <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <div className="flex gap-2 w-full md:w-auto">
          <input
            className="border rounded px-3 py-2 text-sm w-full md:w-64"
            placeholder="Search projects…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {user?.role === "consultant" && (
            <>
              <button onClick={() => setShow(true)} className="bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded shrink-0">
                New project
              </button>
            </>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 uppercase text-xs">
            <tr><th className="text-left p-3">Company</th><th className="text-left p-3">Product</th><th className="text-left p-3">Sector</th><th className="text-left p-3">Market</th><th className="text-left p-3">Progress</th><th className="p-3"></th></tr>
          </thead>
          <tbody>
            {filtered.length === 0 && <tr><td colSpan={5} className="p-6 text-center text-slate-500">{data.length === 0 ? "No projects." : "No projects match your search."}</td></tr>}
            {filtered.map((p) => (
              <tr key={p.id} className="border-t hover:bg-slate-50">
                <td className="p-3"><Link to={`/projects/${p.id}`} className="text-brand-700 hover:underline font-medium">{p.company_name}</Link><div className="text-xs text-slate-500">{p.company_role}</div></td>
                <td className="p-3">{p.product}</td>
                <td className="p-3">{p.activity_sector}</td>
                <td className="p-3"><span className="px-2 py-0.5 rounded bg-brand-50 text-brand-700 text-xs">{p.market}</span></td>
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-slate-200 rounded-full h-1.5">
                      <div className="bg-brand-500 h-1.5 rounded-full" style={{ width: `${p.progress}%` }}></div>
                    </div>
                    <span className="text-xs text-slate-500">{p.progress}%</span>
                  </div>
                </td>
                <td className="p-3 text-right">
                  {user?.role === "consultant" && (
                    <button
                      onClick={() => { if (confirm("Delete this project?")) deleteProject.mutate(p.id); }}
                      className="text-red-600 hover:text-red-800 text-xs font-medium">
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {show && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-20" onClick={() => setShow(false)}>
          <form onClick={(e) => e.stopPropagation()} onSubmit={onSubmit}
            className="bg-white p-6 rounded-lg shadow w-full max-w-lg space-y-3">
            <h2 className="text-lg font-semibold">New project</h2>
            {(["company_name","company_role","activity_sector","product"] as const).map((k) => (
              <input key={k} className="w-full border rounded px-3 py-2" placeholder={k.replace("_"," ")}
                value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} required />
            ))}
            <select className="w-full border rounded px-3 py-2" value={form.market}
              onChange={(e) => {
                const newMarket = e.target.value;
                setForm({ ...form, market: newMarket });
                // Automatically trigger analysis if enough data is present
                if (newMarket) {
                  setAnalyzingProject({ ...form, market: newMarket } as any);
                }
              }}>
              <option value="">Select Market</option>
              <option>CE</option><option>FDI</option><option>FDA</option><option>UKCA</option><option>Other</option>
            </select>
            <textarea className="w-full border rounded px-3 py-2" placeholder="Applicable standards / regulations"
              value={form.standards} onChange={(e) => setForm({ ...form, standards: e.target.value })} rows={2} />
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="px-4 py-2" onClick={() => setShow(false)}>Cancel</button>
              <button disabled={create.isPending} className="bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded disabled:opacity-50">
                {create.isPending ? "Creating…" : "Create"}
              </button>
            </div>
          </form>
        </div>
      )}

      {analyzingProject && (
        <StandardAnalysisChatbot 
          project={analyzingProject} 
          onClose={() => setAnalyzingProject(null)}
          onConfirm={async (standards) => {
            // If the project already has an ID, it was already created, so we update it via API
            if (analyzingProject.id) {
              await api.patch(`/projects/${analyzingProject.id}`, { standards });
              qc.invalidateQueries({ queryKey: ["projects"] });
            } else {
              // Otherwise, we are in "pre-creation" mode, so we update the form state
              setForm(prev => ({ ...prev, standards }));
            }
            setAnalyzingProject(null);
          }}
        />
      )}
    </div>
  );
}
