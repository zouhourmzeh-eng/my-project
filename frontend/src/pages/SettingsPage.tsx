import { FormEvent, useState } from "react";
import { api } from "../lib/api";

export default function SettingsPage() {
  const [current, setCurrent] = useState("");
  const [newPass, setNewPass] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(""); setSuccess(false); setBusy(true);
    try {
      await api.post("/auth/change-password", { current_password: current, new_password: newPass });
      setSuccess(true);
      setCurrent(""); setNewPass("");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to change password");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-md mx-auto space-y-6">
      <h1 className="text-2xl font-semibold">Account Settings</h1>
      <div className="bg-white p-6 rounded-lg shadow-sm border space-y-4">
        <h2 className="text-lg font-medium border-b pb-2">Change Password</h2>
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-slate-600 mb-1">Current Password</label>
            <input className="w-full border rounded px-3 py-2" type="password" value={current} onChange={(e) => setCurrent(e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm text-slate-600 mb-1">New Password</label>
            <input className="w-full border rounded px-3 py-2" type="password" value={newPass} onChange={(e) => setNewPass(e.target.value)} required minLength={8} />
          </div>
          {error && <div className="text-sm text-red-600">{error}</div>}
          {success && <div className="text-sm text-emerald-600 font-medium">Password changed successfully!</div>}
          <button disabled={busy} className="bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded disabled:opacity-50 transition-colors">
            {busy ? "Updating…" : "Update Password"}
          </button>
        </form>
      </div>
    </div>
  );
}
