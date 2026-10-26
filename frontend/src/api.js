// src/api.js
const BASE = "/api/v1";
let token = localStorage.getItem("token");
const setToken = (t) => { token = t; localStorage.setItem("token", t); };
async function call(path, opts = {}) {
  const res = await fetch(BASE + path, { ...opts, headers: {
    ...(opts.headers || {}), ...(token ? { Authorization: `Bearer ${token}` } : {}) } });
  if (!res.ok) throw new Error(((await res.json().catch(() => ({}))).detail) || res.status);
  return res.headers.get("content-type")?.includes("json") ? res.json() : res.blob();
}
export const api = {
  login: async (login, password) => {
    const res = await fetch(BASE + "/auth/token", { method: "POST",
      body: new URLSearchParams({ username: login, password }) });
    if (!res.ok) throw new Error("Неверный логин или пароль");
    setToken((await res.json()).access_token);
  },
  history: () => call("/data/history"),
  metrics: () => call("/metrics"),
  forecast: (days = 14) => call(`/forecast/predict?days=${days}`),
  report: (fmt) => call(`/reports/export?format=${fmt}`),
  importLogs: (file) => { const fd = new FormData(); fd.append("file", file);
    return call("/data/import", { method: "POST", body: fd }); },
};