import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, WS_URL } from "../lib/api";

interface Notification {
  id: number; title: string; body: string; link: string; read: boolean; created_at: string;
}

export function NotificationBell() {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);

  const { data = [] } = useQuery<Notification[]>({
    queryKey: ["notifications"],
    queryFn: async () => (await api.get("/notifications")).data,
    refetchInterval: 60_000,
  });

  const [toast, setToast] = useState<{ title: string; body: string; link: string } | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    const ws = new WebSocket(`${WS_URL}/ws/notifications?token=${token}`);
    ws.onmessage = (ev) => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
      try {
        const msg = JSON.parse(ev.data);
        if (msg.title) {
          setToast({ title: msg.title, body: msg.body || "", link: msg.link || "/" });
          setTimeout(() => setToast(null), 5000);
        }
      } catch { /* ignore */ }
    };
    return () => ws.close();
  }, [qc]);

  const unread = data.filter((n) => !n.read).length;

  async function markAll() {
    await api.post("/notifications/read-all");
    qc.invalidateQueries({ queryKey: ["notifications"] });
  }
  async function clearAll() {
    if (confirm("Clear all notifications?")) {
      await api.delete("/notifications/clear-all");
      qc.invalidateQueries({ queryKey: ["notifications"] });
    }
  }
  async function deleteOne(id: number) {
    await api.delete(`/notifications/${id}`);
    qc.invalidateQueries({ queryKey: ["notifications"] });
  }

  return (
    <div className="relative">
      {toast && (
        <Link to={toast.link} onClick={() => setToast(null)}
          className="fixed top-16 right-4 z-50 w-80 bg-white text-slate-800 border shadow-lg rounded-lg p-3 hover:bg-slate-50 animate-fade-in">
          <div className="text-sm font-medium">{toast.title}</div>
          <div className="text-xs text-slate-500 mt-0.5 line-clamp-2">{toast.body}</div>
        </Link>
      )}
      <button onClick={() => setOpen((o) => !o)} className="relative px-2 py-1">
        <span aria-hidden>🔔</span>
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] rounded-full px-1.5 leading-4">{unread}</span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 top-10 w-80 max-h-96 overflow-auto bg-white text-slate-800 rounded shadow-lg border z-30">
          <div className="flex items-center justify-between px-3 py-2 border-b">
            <strong className="text-sm">Notifications</strong>
            <div className="flex gap-2">
              <button onClick={markAll} className="text-xs text-brand-600 hover:underline">Mark read</button>
              <button onClick={clearAll} className="text-xs text-red-600 hover:underline">Clear all</button>
            </div>
          </div>
          {data.length === 0 && <div className="p-4 text-sm text-slate-500">No notifications</div>}
          {data.map((n) => (
            <div key={n.id} className={`group flex items-center border-b hover:bg-slate-50 ${n.read ? "opacity-70" : ""}`}>
              <Link to={n.link || "/"} onClick={() => setOpen(false)}
                className="flex-1 block px-3 py-2 text-sm">
                <div className="font-medium">{n.title}</div>
                <div className="text-xs text-slate-500 truncate">{n.body}</div>
                <div className="text-[10px] text-slate-400 mt-0.5">{new Date(n.created_at).toLocaleString()}</div>
              </Link>
              <button onClick={(e) => { e.preventDefault(); deleteOne(n.id); }}
                className="hidden group-hover:block px-2 py-1 text-slate-400 hover:text-red-500 text-sm" title="Delete">
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
