import { useCallback, useEffect, useState } from "react";
import { loadAll } from "../api.js";
import { Card, Empty, formatDate, formatTime } from "../components/ui.jsx";

// Loads a set of endpoints for a dashboard and exposes a reload function.
export function useDashboardData(requests) {
  const [state, setState] = useState({ loading: true, data: {}, errors: {} });
  const key = JSON.stringify(requests);

  const reload = useCallback(async () => {
    setState((s) => ({ ...s, loading: true }));
    const result = await loadAll(JSON.parse(key));
    setState({ loading: false, ...result });
  }, [key]);

  useEffect(() => {
    reload();
  }, [reload]);

  return { ...state, reload };
}

export function DashboardHeading({ title, subtitle, loading, onRefresh }) {
  return (
    <div className="page-title">
      <div>
        <h1>{title}</h1>
        {subtitle && <div className="muted">{subtitle}</div>}
      </div>
      <button onClick={onRefresh} disabled={loading}>{loading ? "Loading…" : "Refresh"}</button>
    </div>
  );
}

export function LoadErrors({ errors }) {
  const messages = Object.values(errors).filter((e) => e.status !== 404).map((e) => e.message);
  if (!messages.length) return null;
  return <div className="alert error" role="alert" style={{ marginBottom: 16 }}>{[...new Set(messages)].join(" · ")}</div>;
}

export function drivesSummary(drives = []) {
  const slots = drives.flatMap((d) => d.slots);
  const capacity = slots.reduce((sum, s) => sum + s.capacity, 0);
  const booked = slots.reduce((sum, s) => sum + s.booked_count, 0);
  return { count: drives.length, capacity, booked, open: capacity - booked };
}

export function UpcomingDrives({ drives, className = "" }) {
  return (
    <Card title="Upcoming donation drives" className={className}>
      {!drives?.length ? (
        <Empty>No drives scheduled.</Empty>
      ) : (
        <ul className="list">
          {drives.map((drive) => {
            const { capacity, booked } = drivesSummary([drive]);
            return (
              <li key={drive.id}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
                  <strong>{drive.name}</strong>
                  <span className="muted small">{formatDate(drive.date)}</span>
                </div>
                <div className="muted small">{drive.location}</div>
                <div className="small" style={{ marginTop: 4 }}>
                  {drive.slots.length} slot{drive.slots.length === 1 ? "" : "s"}, from {formatTime(drive.slots[0]?.start_time)} ·{" "}
                  <strong>{capacity - booked}</strong> of {capacity} places open
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
