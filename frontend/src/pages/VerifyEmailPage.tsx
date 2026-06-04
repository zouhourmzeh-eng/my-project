import { FormEvent, useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function VerifyEmailPage() {
  const { verifyEmail, resendVerification, user } = useAuth();
  const nav = useNavigate();
  const [searchParams] = useSearchParams();
  const email = searchParams.get("email") || "";

  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  
  // Cooldown for resending code
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    if (user) {
      nav("/dashboard");
    }
  }, [user]);

  useEffect(() => {
    if (cooldown > 0) {
      const timer = setTimeout(() => setCooldown(cooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [cooldown]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");
    if (!email) {
      setError("Adresse e-mail manquante.");
      return;
    }
    if (code.length !== 6) {
      setError("Le code doit comporter 6 chiffres.");
      return;
    }
    setBusy(true);
    try {
      await verifyEmail(email, code);
      setSuccess("Compte confirmé avec succès ! Connexion en cours...");
      setTimeout(() => {
        nav("/dashboard");
      }, 1500);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Code de validation incorrect ou expiré.");
    } finally {
      setBusy(false);
    }
  }

  async function handleResend() {
    if (!email) return;
    setError("");
    setSuccess("");
    try {
      await resendVerification(email);
      setSuccess("Un nouveau code a été envoyé à votre e-mail.");
      setCooldown(60);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Impossible de renvoyer le code.");
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-md animate-in fade-in slide-in-from-bottom-4 duration-700">
        <div className="text-center mb-8">
          <div className="inline-block bg-brand-600 text-white px-4 py-2 rounded-2xl font-black text-2xl shadow-xl mb-4 shadow-brand-200">QMS</div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight">Vérifier votre e-mail</h1>
          <p className="text-slate-500 mt-2 font-medium">Un code de validation à 6 chiffres a été envoyé.</p>
        </div>

        <form onSubmit={onSubmit} className="bg-white p-8 rounded-3xl shadow-2xl shadow-slate-200 space-y-6 border border-slate-100">
          <div className="text-center">
            <p className="text-sm font-semibold text-slate-600">Code envoyé à :</p>
            <p className="text-base font-bold text-brand-600 mt-1 break-all">{email || "adresse e-mail inconnue"}</p>
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-700 mb-2 text-center">Saisir le code à 6 chiffres</label>
            <input 
              className="w-full border-2 border-slate-100 bg-slate-50 rounded-2xl px-5 py-4 focus:bg-white focus:border-brand-500 outline-none transition-all font-mono text-center text-3xl tracking-widest" 
              type="text" 
              maxLength={6}
              placeholder="000000" 
              value={code} 
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} 
              required 
            />
          </div>

          {error && (
            <div className="bg-red-50 border-2 border-red-100 text-red-600 text-sm px-4 py-3 rounded-2xl flex items-center gap-3 font-medium animate-in shake-in duration-300">
              <span className="text-lg">⚠️</span>
              <span>{error}</span>
            </div>
          )}

          {success && (
            <div className="bg-emerald-50 border-2 border-emerald-100 text-emerald-600 text-sm px-4 py-3 rounded-2xl flex items-center gap-3 font-medium animate-in fade-in duration-300">
              <span className="text-lg">✅</span>
              <span>{success}</span>
            </div>
          )}

          <button 
            disabled={busy || !email} 
            className="w-full bg-brand-600 hover:bg-brand-700 active:scale-[0.98] text-white py-4 rounded-2xl font-bold text-lg shadow-xl shadow-brand-200 transition-all disabled:opacity-50 disabled:cursor-not-allowed group"
          >
            <span className="flex items-center justify-center gap-2">
              {busy ? "Vérification en cours..." : "Confirmer mon compte"}
              {!busy && <span className="group-hover:translate-x-1 transition-transform">→</span>}
            </span>
          </button>

          <div className="flex flex-col items-center gap-3 pt-2">
            <button 
              type="button"
              onClick={handleResend}
              disabled={cooldown > 0 || !email}
              className="text-sm font-bold text-brand-600 hover:text-brand-700 disabled:text-slate-400 disabled:cursor-not-allowed transition-colors"
            >
              {cooldown > 0 ? `Renvoyer le code (${cooldown}s)` : "Renvoyer le code de validation"}
            </button>
            
            <p className="text-slate-500 font-medium text-sm mt-1">
              Retourner à la page de <Link to="/" className="text-brand-600 hover:text-brand-700 font-bold">Connexion</Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}
