import { useState } from "react";
import { api } from "./api";
import Dashboard from "./Dashboard";

function LoginForm({ onSuccess }) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.login(login, password);   // POST /api/v1/auth/token, JWT сохраняется в api.js
      onSuccess();
    } catch (err) {
      setError(err.message);              // вывод экранируется React при рендере (NFR-SEC-03)
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit}
          style={{ maxWidth: 360, margin: "10vh auto", padding: 24,
                   border: "1px solid #ddd", borderRadius: 8 }}>
      <h2>Вход в систему анализа активности</h2>
      <label>
        Логин
        <input value={login} onChange={(e) => setLogin(e.target.value)}
               autoComplete="username" required />
      </label>
      <label>
        Пароль
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
               autoComplete="current-password" required />
      </label>
      {error && <p role="alert" style={{ color: "crimson" }}>{error}</p>}
      <button type="submit" disabled={busy}>{busy ? "Проверка…" : "Войти"}</button>
      <p style={{ color: "#888", fontSize: 12 }}>
        Демонстрационные учётные записи: analyst / analyst, admin / admin
      </p>
    </form>
  );
}

export default function App() {
  const [authed, setAuthed] = useState(() => Boolean(localStorage.getItem("token")));

  const logout = () => {
    localStorage.removeItem("token");     // сброс JWT (TTL 15 мин, NFR-SEC-01)
    setAuthed(false);
  };

  return authed ? (
    <>
      <header style={{ display: "flex", justifyContent: "flex-end", padding: "8px 16px" }}>
        <button onClick={logout}>Выйти</button>
      </header>
      <Dashboard />
    </>
  ) : (
    <LoginForm onSuccess={() => setAuthed(true)} />
  );
}