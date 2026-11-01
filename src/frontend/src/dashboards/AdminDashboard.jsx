import { StatCard } from "../components/ui.jsx";
import { DashboardHeading, LoadErrors, UpcomingDrives, drivesSummary, useDashboardData } from "./shared.jsx";

// Admin: system status and drive activity. Stock and requests are staff-only data.
export default function AdminDashboard() {
  const { loading, data, errors, reload } = useDashboardData({
    health: "/api/health",
    drives: "/api/drives",
  });
  const drives = drivesSummary(data.drives ?? []);
  const fill = drives.capacity ? Math.round((drives.booked / drives.capacity) * 100) : 0;

  return (
    <>
      <DashboardHeading title="Administration" subtitle="System status and donation drives" loading={loading} onRefresh={reload} />
      <LoadErrors errors={errors} />

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
