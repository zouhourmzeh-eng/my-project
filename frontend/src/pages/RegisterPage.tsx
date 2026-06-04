import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Role, useAuth } from "../context/AuthContext";

export default function RegisterPage() {
  const { register, user } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("assistant");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) { nav("/"); return null; }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      await register(email, name, password, role, phone);
      nav(`/verify-email?email=${encodeURIComponent(email)}`);
    }
    catch (err: any) {
      setError(err.response?.data?.detail || "Registration failed");
    }
    finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md animate-in fade-in slide-in-from-bottom-4 duration-700">
        <div className="text-center mb-8">
          <div className="inline-block bg-brand-600 text-white px-4 py-2 rounded-2xl font-black text-2xl shadow-xl mb-4 shadow-brand-200">QMS</div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Create an account</h1>
          <p className="text-slate-500 mt-2 font-medium">Join the Enterprise Document & Compliance Hub</p>
        </div>

        <form onSubmit={onSubmit} className="bg-white p-8 rounded-3xl shadow-2xl shadow-slate-200 space-y-5 border border-slate-100">
          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2 px-1">Full name</label>
            <input 
              className="w-full border-2 border-slate-100 bg-slate-50 rounded-2xl px-5 py-3.5 focus:bg-white focus:border-brand-500 outline-none transition-all font-medium" 
              placeholder="John Doe" 
              value={name} 
              onChange={(e) => setName(e.target.value)} 
              required 
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2 px-1">Email address</label>
            <input 
              className="w-full border-2 border-slate-100 bg-slate-50 rounded-2xl px-5 py-3.5 focus:bg-white focus:border-brand-500 outline-none transition-all font-medium" 
              type="email" 
              placeholder="name@company.com" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              required 
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2 px-1">Phone number (optional)</label>
            <input 
              className="w-full border-2 border-slate-100 bg-slate-50 rounded-2xl px-5 py-3.5 focus:bg-white focus:border-brand-500 outline-none transition-all font-medium" 
              type="tel" 
              placeholder="+33 6 12 34 56 78" 
              value={phone} 
              onChange={(e) => setPhone(e.target.value)} 
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2 px-1">Password</label>
            <input 
              className="w-full border-2 border-slate-100 bg-slate-50 rounded-2xl px-5 py-3.5 focus:bg-white focus:border-brand-500 outline-none transition-all font-medium" 
              type="password" 
              placeholder="•••••••• (min 8 chars)" 
              minLength={8} 
              value={password} 
              onChange={(e) => setPassword(e.target.value)} 
              required 
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2 px-1">Your role</label>
            <select 
              className="w-full border-2 border-slate-100 bg-slate-50 rounded-2xl px-5 py-3.5 focus:bg-white focus:border-brand-500 outline-none transition-all font-semibold" 
              value={role} 
              onChange={(e) => setRole(e.target.value as Role)}
            >
              <option value="consultant">Consultant</option>
              <option value="assistant">Assistant</option>
              <option value="rmq">RMQ (Quality Manager)</option>
            </select>
          </div>

          {error && (
            <div className="bg-red-50 border-2 border-red-100 text-red-600 text-sm px-4 py-3 rounded-2xl flex items-center gap-3 font-medium animate-in shake-in duration-300">
              <span className="text-lg">⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <button 
            disabled={busy} 
            className="w-full bg-brand-600 hover:bg-brand-700 active:scale-[0.98] text-white py-4 rounded-2xl font-bold text-lg shadow-xl shadow-brand-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed group mt-2"
          >
            <span className="flex items-center justify-center gap-2">
              {busy ? "Creating account..." : "Register & Verify"}
              {!busy && <span className="group-hover:translate-x-1 transition-transform">→</span>}
            </span>
          </button>

          <div className="text-center pt-2">
            <p className="text-slate-500 font-medium">
              Already have one? <Link to="/" className="text-brand-600 hover:text-brand-700 font-bold ml-1">Sign in</Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}
