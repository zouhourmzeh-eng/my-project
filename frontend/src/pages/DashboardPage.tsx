import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../context/AuthContext";

interface Stats {
  total_projects: number;
  total_processes: number;
  total_documents: number;
  documents_to_validate: number;
  unread_notifications: number;
}

interface Project {
  id: number; company_name: string; product: string; market: string; created_at: string;
  progress: number;
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { data: stats } = useQuery<Stats>({
    queryKey: ["dashboard"],
    queryFn: async () => (await api.get("/dashboard/stats")).data,
  });
  const { data: projects = [] } = useQuery<Project[]>({
    queryKey: ["projects"],
    queryFn: async () => (await api.get("/projects?limit=6")).data,
  });

  const { data: impacts = [] } = useQuery<any[]>({
    queryKey: ["regulatory-impacts"],
    queryFn: async () => (await api.get("/regulatory-watch/impacts?limit=3")).data,
    enabled: user?.role === "consultant",
  });

  const cards = [
    { label: "Projects", value: stats?.total_projects ?? "—" },
    { label: "Processes", value: stats?.total_processes ?? "—" },
    { label: "Documents", value: stats?.total_documents ?? "—" },
    { label: user?.role === "consultant" ? "To validate" : "Drafts", value: stats?.documents_to_validate ?? "—" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Welcome, {user?.full_name.split(" ")[0]}</h1>
        <p className="text-slate-500 text-sm">Overview of your quality management activity.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cards.map((c) => (
          <div key={c.label} className="bg-white p-4 rounded-lg shadow-sm border">
            <div className="text-xs text-slate-500 uppercase tracking-wide">{c.label}</div>
            <div className="text-3xl font-semibold mt-1 text-brand-700">{c.value}</div>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-lg shadow-sm border">
        <div className="px-5 py-3 border-b flex items-center justify-between">
          <h2 className="font-medium">Recent projects</h2>
          <Link to="/projects" className="text-sm text-brand-600 hover:underline">View all</Link>
        </div>
        <div className="divide-y">
          {projects.length === 0 && <div className="p-6 text-sm text-slate-500">No projects yet.</div>}
          {projects.map((p) => (
            <Link key={p.id} to={`/projects/${p.id}`} className="block px-5 py-3 hover:bg-slate-50 transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">{p.company_name}</div>
                  <div className="text-xs text-slate-500">{p.product} · {p.market}</div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-24 bg-slate-200 rounded-full h-2">
                    <div className="bg-brand-500 h-2 rounded-full" style={{ width: `${p.progress}%` }}></div>
                  </div>
                  <div className="text-xs font-medium w-8 text-right text-slate-600">{p.progress}%</div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {user?.role === "consultant" && (
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="px-5 py-3 border-b flex items-center justify-between bg-slate-50">
            <h2 className="font-medium flex items-center gap-2">
              <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
              Regulatory Watch Alerts
            </h2>
            <Link to="/regulatory-watch" className="text-sm text-brand-600 hover:underline">View history</Link>
          </div>
          <div className="divide-y">
            {impacts.length === 0 && <div className="p-6 text-sm text-slate-500">No regulatory alerts found.</div>}
            {impacts.map((imp: any) => (
              <Link key={imp.id} to="/regulatory-watch" className="block px-5 py-4 hover:bg-slate-50 transition-colors">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-[10px] font-black uppercase px-1.5 py-0.5 rounded ${
                        imp.update?.severity === 'critical' ? 'bg-red-600 text-white' :
                        imp.update?.severity === 'high' ? 'bg-orange-500 text-white' :
                        'bg-blue-500 text-white'
                      }`}>
                        {imp.update?.severity}
                      </span>
                      <span className="text-xs text-slate-400 font-medium">
                        {new Date(imp.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="font-semibold text-slate-800 leading-snug">{imp.update?.title}</div>
                  </div>
                  <div className="text-brand-600">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
