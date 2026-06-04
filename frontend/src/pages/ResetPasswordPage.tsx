import { FormEvent, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { api } from "../lib/api";

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const [form, setForm] = useState({
    email: params.get("email") || "",
    phone: params.get("phone") || "",
    code: "",
    new_password: ""
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      await api.post("/auth/reset-password", form);
      alert("Password reset successfully! You can now sign in.");
      nav("/");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Invalid code or expired");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center p-4">
      <form onSubmit={onSubmit} className="bg-white p-8 rounded-lg shadow w-full max-w-sm space-y-4 border">
        <h1 className="text-2xl font-semibold text-brand-700">Reset Password</h1>
        <p className="text-sm text-slate-500">Enter the code sent to your {form.email ? "email" : "phone"} and your new password.</p>
        {form.email ? (
          <input className="w-full border rounded px-3 py-2 bg-slate-50" type="email" placeholder="Email" value={form.email} readOnly />
        ) : (
          <input className="w-full border rounded px-3 py-2 bg-slate-50" type="tel" placeholder="Phone" value={form.phone} readOnly />
        )}
        <input className="w-full border rounded px-3 py-2" type="text" placeholder="6-digit Code" value={form.code} onChange={(e) => setForm({...form, code: e.target.value})} required maxLength={6} />
        <input className="w-full border rounded px-3 py-2" type="password" placeholder="New Password" value={form.new_password} onChange={(e) => setForm({...form, new_password: e.target.value})} required minLength={8} />
        {error && <div className="text-sm text-red-600">{error}</div>}
        <button disabled={busy} className="w-full bg-brand-600 hover:bg-brand-700 text-white py-2 rounded font-medium disabled:opacity-50">
          {busy ? "Resetting…" : "Reset Password"}
        </button>
      </form>
    </div>
  );
}
