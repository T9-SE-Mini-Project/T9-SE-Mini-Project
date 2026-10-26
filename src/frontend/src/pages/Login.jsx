import { useState } from "react";
import { api } from "../api.js";
import ThemeToggle from "../components/ThemeToggle.jsx";
import { Logo } from "../components/ui.jsx";

// Login for every role, plus donor self-signup with OTP verification (BLOOD-6, BLOOD-7).
// Staff, hospital and admin accounts are created by an admin, so they only log in.
export default function Login({ onLogin }) {
  const [mode, setMode] = useState("login"); // login | signup | verify
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(action) {
    setBusy(true);
    setError("");
    setInfo("");
    try {
      await action();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const login = (e) => {
    e.preventDefault();
    run(async () => {
      const result = await api("/api/auth/login", { method: "POST", body: { email, password } });
      onLogin({ token: result.access_token, user: { ...result.user, email } });
    });
  };

  const signup = (e) => {
    e.preventDefault();
    run(async () => {
      await api("/api/auth/signup", { method: "POST", body: { email, password } });
      setMode("verify");
      setInfo("We sent a 6-digit code to your email.");
    });
  };

  const verify = (e) => {
    e.preventDefault();
    run(async () => {
      await api("/api/auth/signup/verify", { method: "POST", body: { email, code } });
      setMode("login");
      setCode("");
      setInfo("Account verified. You can log in now.");
    });
  };

  const resend = () =>
    run(async () => {
      await api("/api/auth/signup/resend", { method: "POST", body: { email } });
      setInfo("A new code is on its way.");
    });

  return (
    <main className="auth-page">
      <div className="auth-theme"><ThemeToggle /></div>
      <div className="card auth-card">
        <div className="brand"><Logo size={32} /> Blood Bank Management</div>

        {mode !== "verify" && (
          <div className="tabs" role="tablist">
            <button role="tab" aria-selected={mode === "login"} className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>
              Log in
            </button>
            <button role="tab" aria-selected={mode === "signup"} className={mode === "signup" ? "active" : ""} onClick={() => setMode("signup")}>
              Become a donor
            </button>
          </div>
        )}

        {error && <div className="alert error" role="alert">{error}</div>}
        {info && <div className="alert info" role="status">{info}</div>}

        {mode === "verify" ? (
          <form onSubmit={verify}>
            <label>
              Verification code
              <input value={code} onChange={(e) => setCode(e.target.value)} inputMode="numeric" pattern="[0-9]{6}" maxLength={6} required autoFocus />
            </label>
            <button className="primary" disabled={busy}>Verify</button>
            <button type="button" onClick={resend} disabled={busy}>Send a new code</button>
          </form>
        ) : (
          <form onSubmit={mode === "login" ? login : signup}>
            <label>
              Email
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" required />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                minLength={mode === "signup" ? 8 : 1}
                required
              />
            </label>
            <button className="primary" disabled={busy}>
              {mode === "login" ? "Log in" : "Create donor account"}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
