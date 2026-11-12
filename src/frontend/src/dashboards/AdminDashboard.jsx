import { useState } from "react";
import { api } from "../api.js";
import { StatCard } from "../components/ui.jsx";
import {
  ActionStatus,
  DashboardHeading,
  DriveForm,
  LoadErrors,
  Panel,
  UpcomingDrives,
  drivesSummary,
  useAction,
  useDashboardData,
} from "./shared.jsx";

// Admin: system status and drive activity. Stock and requests are staff-only data.
// Admins coordinate drives too, so they can schedule one and send slot reminders.
export default function AdminDashboard() {
  const { loading, data, errors, reload } = useDashboardData({
    health: "/api/health",
    drives: "/api/drives",
  });
  const [formOpen, setFormOpen] = useState(false);
  const refresh = () => reload({ quiet: true });
  const reminders = useAction(refresh);
  const drives = drivesSummary(data.drives ?? []);
  const fill = drives.capacity ? Math.round((drives.booked / drives.capacity) * 100) : 0;

  function sendReminders() {
    reminders.run(async () => (await api("/api/drives/reminders/send", { method: "POST" })).message);
  }

  return (
    <>
      <DashboardHeading title="Administration" subtitle="System status and donation drives" loading={loading} onRefresh={reload}>
        <button className="primary" onClick={() => setFormOpen(true)}>Schedule drive</button>
        <button onClick={sendReminders} disabled={reminders.busy}>{reminders.busy ? "Sending…" : "Send reminders"}</button>
      </DashboardHeading>
      <LoadErrors errors={errors} />
      {(reminders.error || reminders.message) && <div style={{ marginBottom: 16 }}><ActionStatus {...reminders} /></div>}

      {formOpen && (
        <Panel title="Schedule a donation drive" onClose={() => setFormOpen(false)}>
          <DriveForm onCreated={refresh} />
        </Panel>
      )}

      <div className="stats">
        <StatCard label="API status" value={data.health?.status === "ok" ? "Online" : loading ? null : "Down"} />
        <StatCard label="Upcoming drives" value={data.drives ? drives.count : null} />
        <StatCard label="Places booked" value={data.drives ? `${drives.booked}/${drives.capacity}` : null} hint={`${fill}% full`} />
        <StatCard label="Places open" value={data.drives ? drives.open : null} />
      </div>

      <UpcomingDrives drives={data.drives} />
      <p className="muted small" style={{ marginTop: 16 }}>
        Create staff, hospital and admin accounts through <code>POST /api/admin/accounts</code> (see the API docs at /docs).
      </p>
    </>
  );
}
