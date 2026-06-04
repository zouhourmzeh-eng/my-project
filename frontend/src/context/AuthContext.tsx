import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api } from "../lib/api";

export type Role = "consultant" | "assistant" | "rmq";
export interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
  role: Role;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, full_name: string, password: string, role: Role, phone?: string) => Promise<void>;
  verifyEmail: (email: string, code: string) => Promise<void>;
  resendVerification: (email: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>(null!);

export function AuthProvider({ children }: { children: ReactNode }) {
  console.log("AUTH PROVIDER RENDERED");
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) { setLoading(false); return; }
    api.get<User>("/auth/me")
      .then((r) => setUser(r.data))
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      })
      .finally(() => setLoading(false));
  }, []);

  async function persist(data: any) {
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    setUser(data.user);
  }

  async function login(email: string, password: string) {
    const { data } = await api.post("/auth/login", { email, password });
    await persist(data);
  }
  async function register(email: string, full_name: string, password: string, role: Role, phone?: string) {
    await api.post("/auth/register", { email, full_name, password, role, phone });
  }
  async function verifyEmail(email: string, code: string) {
    const { data } = await api.post("/auth/verify-email", { email, code });
    await persist(data);
  }
  async function resendVerification(email: string) {
    await api.post("/auth/resend-verification", { email });
  }
  function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  }

  return <Ctx.Provider value={{ user, loading, login, register, verifyEmail, resendVerification, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
