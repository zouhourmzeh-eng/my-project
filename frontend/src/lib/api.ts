import axios from "axios";

export const API_URL = import.meta.env.VITE_API_URL || "/api";
// WS_URL must use the /ws proxy path (configured in vite.config.ts to forward to ws://localhost:8000)
// If a custom WS URL is set (e.g. in production), use that; otherwise build from window location
export const WS_URL = import.meta.env.VITE_WS_URL
  ? import.meta.env.VITE_WS_URL
  : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;

export const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string> | null = null;

async function doRefresh(): Promise<string> {
  const refresh = localStorage.getItem("refresh_token");
  if (!refresh) throw new Error("No refresh token");
  const { data } = await axios.post(`${API_URL}/auth/refresh`, { refresh_token: refresh });
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  return data.access_token;
}

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        refreshing = refreshing || doRefresh();
        const token = await refreshing;
        refreshing = null;
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      } catch {
        refreshing = null;
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        if (location.pathname !== "/") location.href = "/";
      }
    }
    return Promise.reject(error);
  }
);
