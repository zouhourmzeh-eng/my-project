import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/api";

export default function ForgotPasswordPage() {
  const [method, setMethod] = useState<"email" | "phone">("email");
  const [value, setValue] = useState("");
  const [success, setSuccess] = useState(false);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = method === "email" ? { email: value } : { phone: value };
      await api.post("/auth/forgot-password", payload);
      setSuccess(true);
      const url = method === "email" 
        ? `/reset-password?email=${encodeURIComponent(value)}` 
        : `/reset-password?phone=${encodeURIComponent(value)}`;
      setTimeout(() => nav(url), 2000);
    } catch {
      setSuccess(true);
      const url = method === "email" 
        ? `/reset-password?email=${encodeURIComponent(value)}` 
        : `/reset-password?phone=${encodeURIComponent(value)}`;
      setTimeout(() => nav(url), 2000);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center p-4">
      <form onSubmit={onSubmit} className="bg-white p-8 rounded-lg shadow w-full max-w-sm space-y-4 border">
        <h1 className="text-2xl font-semibold text-brand-700">Recover Password</h1>
        
        <div className="flex bg-slate-100 p-1 rounded-md text-sm">
          <button type="button" onClick={() => { setMethod("email"); setValue(""); }}
            className={`flex-1 py-1 rounded ${method === "email" ? "bg-white shadow" : "text-slate-500"}`}>Email</button>
          <button type="button" onClick={() => { setMethod("phone"); setValue(""); }}
            className={`flex-1 py-1 rounded ${method === "phone" ? "bg-white shadow" : "text-slate-500"}`}>Phone</button>
        </div>

        <p className="text-sm text-slate-500">
          Enter your {method} and we'll send you a recovery code.
        </p>
        
        <input 
          className="w-full border rounded px-3 py-2" 
          type={method === "email" ? "email" : "tel"} 
          placeholder={method === "email" ? "Email address" : "Phone number"} 
          value={value} 
          onChange={(e) => setValue(e.target.value)} 
          required 
        />
        {success && (
          <div className="text-sm text-brand-600 bg-brand-50 p-2 rounded">
            If an account exists for {value}, you will receive a code shortly. Redirecting…
          </div>
        )}
        <button disabled={busy} className="w-full bg-brand-600 hover:bg-brand-700 text-white py-2 rounded font-medium disabled:opacity-50">
          {busy ? "Sending…" : "Send Recovery Code"}
        </button>
        <div className="text-center">
          <Link to="/" className="text-sm text-slate-500 hover:underline">Back to Login</Link>
        </div>
      </form>
    </div>
  );
}
