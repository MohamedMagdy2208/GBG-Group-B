import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
});

export function setAuthTokens(accessToken: string, refreshToken?: string | null, expiresInSeconds?: number | null) {
  localStorage.setItem("token", accessToken);
  if (refreshToken) {
    localStorage.setItem("refresh_token", refreshToken);
  }
  if (expiresInSeconds) {
    localStorage.setItem("token_expires_at", String(Date.now() + expiresInSeconds * 1000));
  }
}

export function clearAuthTokens() {
  localStorage.removeItem("token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("token_expires_at");
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise: Promise<string | null> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as (typeof error.config & { _retry?: boolean }) | undefined;
    const status = error.response?.status;
    const url = String(original?.url ?? "");
    const refreshToken = localStorage.getItem("refresh_token");
    if (!original || status !== 401 || original._retry || !refreshToken || url.includes("/auth/refresh") || url.includes("/auth/login")) {
      return Promise.reject(error);
    }

    original._retry = true;
    refreshPromise ??= api
      .post("/auth/refresh", { refresh_token: refreshToken })
      .then((response) => {
        setAuthTokens(response.data.access_token, response.data.refresh_token, response.data.expires_in_seconds);
        return response.data.access_token as string;
      })
      .catch(() => {
        clearAuthTokens();
        window.dispatchEvent(new Event("auth:expired"));
        return null;
      })
      .finally(() => {
        refreshPromise = null;
      });

    const newToken = await refreshPromise;
    if (!newToken) {
      return Promise.reject(error);
    }
    original.headers = { ...(original.headers ?? {}), Authorization: `Bearer ${newToken}` };
    return api(original);
  },
);

export async function uploadFile(file: File, folder: string) {
  const data = new FormData();
  data.append("file", file);
  const response = await api.post(`/files/upload?folder=${folder}`, data, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data as { file_id: string; url: string; retention_expires_at?: string; malware_scan_status?: string };
}
