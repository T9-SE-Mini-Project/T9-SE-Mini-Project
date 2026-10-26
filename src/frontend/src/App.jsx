import { useEffect, useState } from "react";
import { api, loadSession, saveSession, setUnauthorizedHandler } from "./api.js";
import ThemeToggle from "./components/ThemeToggle.jsx";
import { Logo } from "./components/ui.jsx";
import AdminDashboard from "./dashboards/AdminDashboard.jsx";
import DonorDashboard from "./dashboards/DonorDashboard.jsx";
import HospitalDashboard from "./dashboards/HospitalDashboard.jsx";
import StaffDashboard from "./dashboards/StaffDashboard.jsx";
import Login from "./pages/Login.jsx";

const DASHBOARDS = {
  donor: DonorDashboard,
  hospital_rep: HospitalDashboard,
  blood_bank_staff: StaffDashboard,
  admin: AdminDashboard,
};

const ROLE_NAMES = {
  donor: "Donor",
  hospital_rep: "Hospital",
  blood_bank_staff: "Blood bank staff",
  admin: "Admin",
};

export default function App() {
  const [session, setSession] = useState(loadSession);

  function updateSession(next) {
    saveSession(next);
    setSession(next);
  }

  useEffect(() => {
    setUnauthorizedHandler(() => updateSession(null));
  }, []);

  async function logout() {
    try {
      await api("/api/auth/logout", { method: "POST" });
    } catch {
      // The session may already be gone; log out locally either way.
    }
    updateSession(null);
  }

  if (!session) return <Login onLogin={updateSession} />;

  const { user } = session;
  const Dashboard = DASHBOARDS[user.role];
  return (
    <>
      <header className="header">
        <div className="brand"><Logo /> <span>BBMS</span></div>
        <span className="role-chip">{ROLE_NAMES[user.role]}</span>
        <div className="spacer" />
        {user.email && <span className="who muted small">{user.email}</span>}
        <ThemeToggle />
        <button onClick={logout}>Log out</button>
      </header>
      <main className="page">
        <Dashboard user={user} />
      </main>
    </>
  );
}
