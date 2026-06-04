import { FormEvent, useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login, logout, user, loading } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Automatically logout when visiting the login page as requested by user
  useEffect(() => {
    if (user) {
      logout();
    }
  }, []); // Empty dependency array ensures this only runs once on mount

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
      nav("/dashboard");
    } catch (err: any) {
      setError(err.response?.data?.detail || "Login failed");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-10 h-10 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin"></div>
      </div>
    );
  }

  if (user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
        <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-sm border border-slate-100 text-center space-y-6">
          <div className="w-20 h-20 bg-brand-100 text-brand-600 rounded-full flex items-center justify-center mx-auto text-3xl font-bold">
            {user.full_name.charAt(0)}
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-800">Welcome back!</h1>
            <p className="text-slate-500 text-sm mt-1">You are signed in as <span className="font-semibold">{user.email}</span></p>
          </div>
          <div className="space-y-3">
            <button 
              onClick={() => nav("/dashboard")}
              className="w-full bg-brand-600 hover:bg-brand-700 text-white py-3 rounded-xl font-bold shadow-lg shadow-brand-100 transition-all active:scale-[0.98]"
            >
              Go to Dashboard
            </button>
            <button 
              onClick={() => logout()}
              className="w-full bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 py-3 rounded-xl font-semibold transition-all"
            >
              Sign out / Switch account
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md animate-in fade-in slide-in-from-bottom-4 duration-700">
        <div className="text-center mb-8">
          <div className="inline-block bg-brand-600 text-white px-4 py-2 rounded-2xl font-black text-2xl shadow-xl mb-4 shadow-brand-200">QMS</div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Quality Management</h1>
          <p className="text-slate-500 mt-2 font-medium">Enterprise Document & Compliance Hub</p>
        </div>

        <form onSubmit={onSubmit} className="bg-white p-8 rounded-3xl shadow-2xl shadow-slate-200 space-y-6 border border-slate-100">
          <div className="space-y-5">
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
              <div className="flex justify-between mb-2 px-1">
                <label className="block text-sm font-bold text-slate-700">Password</label>
                <Link to="/forgot-password" virtual-link="true" className="text-sm font-bold text-brand-600 hover:text-brand-700">Forgot?</Link>
              </div>
              <input 
                className="w-full border-2 border-slate-100 bg-slate-50 rounded-2xl px-5 py-3.5 focus:bg-white focus:border-brand-500 outline-none transition-all font-medium" 
                type="password" 
                placeholder="••••••••" 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                required 
              />
            </div>
          </div>

          {error && (
            <div className="bg-red-50 border-2 border-red-100 text-red-600 text-sm px-4 py-3 rounded-2xl flex flex-col gap-2 font-medium animate-in shake-in duration-300">
              <div className="flex items-center gap-3">
                <span className="text-lg">⚠️</span>
                <span>{error}</span>
              </div>
              {error === "Email not verified" && (
                <div className="pl-8 text-xs">
                  Votre e-mail n'est pas vérifié.{" "}
                  <Link 
                    to={`/verify-email?email=${encodeURIComponent(email)}`} 
                    className="text-brand-600 hover:text-brand-700 underline font-bold"
                  >
                    Confirmer maintenant →
                  </Link>
                </div>
              )}
            </div>
          )}

          <button 
            disabled={busy} 
            className="w-full bg-brand-600 hover:bg-brand-700 active:scale-[0.98] text-white py-4 rounded-2xl font-bold text-lg shadow-xl shadow-brand-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
          >
            <span className="flex items-center justify-center gap-2">
              {busy ? "Securing connection..." : "Sign in to Platform"}
              {!busy && <span className="group-hover:translate-x-1 transition-transform">→</span>}
            </span>
          </button>

          <div className="text-center pt-2">
            <p className="text-slate-500 font-medium">
              New here? <Link to="/register" className="text-brand-600 hover:text-brand-700 font-bold ml-1">Create an account</Link>
            </p>
          </div>
        </form>

      </div>
    </div>
  );
}
