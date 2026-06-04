import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";

interface Project {
  id: number; 
  company_name: string; 
  company_role: string; 
  activity_sector: string;
  product: string; 
  market: string; 
  created_at: string;
  is_validated: boolean;
  progress: number;
}

export default function ArchivedProjectsPage() {
  const qc = useQueryClient();
  const { data = [] } = useQuery<Project[]>({
    queryKey: ["projects", "archived"],
    queryFn: async () => (await api.get("/projects?archived=true&limit=200")).data,
  });

  const unvalidate = useMutation({
    mutationFn: async (id: number) => (await api.post(`/projects/${id}/unvalidate`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const [search, setSearch] = useState("");

  const filtered = data.filter((p) =>
    [p.company_name, p.product, p.activity_sector, p.market].some(v => v.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Archived Projects</h1>
          <p className="text-sm text-slate-500">View your validated and archived projects.</p>
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          <input
            className="border rounded px-3 py-2 text-sm w-full md:w-64"
            placeholder="Search archived projects…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border overflow-hidden">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-50 text-slate-500 uppercase text-xs">
            <tr>
              <th className="p-3 font-medium">Company</th>
              <th className="p-3 font-medium">Product</th>
              <th className="p-3 font-medium">Sector</th>
              <th className="p-3 font-medium">Market</th>
              <th className="p-3 font-medium">Progress</th>
              <th className="p-3 font-medium text-right">Status / Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.length === 0 && (
              <tr>
                <td colSpan={5} className="p-6 text-center text-slate-500">
                  {data.length === 0 ? "No archived projects." : "No projects match your search."}
                </td>
              </tr>
            )}
            {filtered.map((p) => (
              <tr key={p.id} className="hover:bg-slate-50 transition-colors">
                <td className="p-3">
                  <Link to={`/projects/${p.id}`} className="text-brand-700 hover:underline font-medium">
                    {p.company_name}
                  </Link>
                  <div className="text-xs text-slate-500">{p.company_role}</div>
                </td>
                <td className="p-3 text-slate-600">{p.product}</td>
                <td className="p-3 text-slate-600">{p.activity_sector}</td>
                <td className="p-3">
                  <span className="px-2 py-0.5 rounded bg-brand-50 text-brand-700 text-xs font-medium">
                    {p.market}
                  </span>
                </td>
                <td className="p-3">
                  <div className="flex items-center gap-2">
                    <div className="w-16 bg-slate-200 rounded-full h-1.5">
                      <div className="bg-brand-500 h-1.5 rounded-full" style={{ width: `${p.progress}%` }}></div>
                    </div>
                    <span className="text-xs text-slate-500">{p.progress}%</span>
                  </div>
                </td>
                <td className="p-3 text-right">
                  <div className="flex items-center justify-end gap-3">
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-slate-100 text-slate-600 text-xs font-medium">
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      Validated
                    </span>
                    <button 
                      onClick={() => {
                        if (confirm("Unlock this project? It will become active again.")) {
                          unvalidate.mutate(p.id);
                        }
                      }}
                      disabled={unvalidate.isPending}
                      className="text-xs px-2 py-1 rounded bg-white border border-amber-200 text-amber-700 hover:bg-amber-50 disabled:opacity-50"
                    >
                      Unlock
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
