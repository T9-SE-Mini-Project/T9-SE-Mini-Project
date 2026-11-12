import { useCallback, useEffect, useState } from "react";
import { api, loadAll } from "../api.js";
import { Card, Empty, formatDate, formatTime } from "../components/ui.jsx";

// Dashboards re-fetch in the background this often, so a change made from another
// login (a new request, an approval, a booking) shows up without pressing Refresh.
const POLL_MS = 10_000;

// Loads a set of endpoints for a dashboard and exposes a reload function.
export function useDashboardData(requests) {
  const [state, setState] = useState({ loading: true, data: {}, errors: {} });
  const key = JSON.stringify(requests);

  const reload = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) setState((s) => ({ ...s, loading: true }));
    const result = await loadAll(JSON.parse(key));
    setState({ loading: false, ...result });
  }, [key]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    const timer = setInterval(() => {
      if (!document.hidden) reload({ quiet: true });
    }, POLL_MS);
    return () => clearInterval(timer);
  }, [reload]);

  return { ...state, reload };
}

// Runs a write action and keeps its busy / error / success state for the UI.
// `fn` returns the success message to show; `onDone` usually reloads the dashboard.
export function useAction(onDone) {
  const [state, setState] = useState({ busy: false, error: "", message: "" });

  async function run(fn) {
    setState({ busy: true, error: "", message: "" });
    try {
      const message = await fn();
      setState({ busy: false, error: "", message: message ?? "" });
      onDone?.();
      return true;
    } catch (err) {
      setState({ busy: false, error: err.message, message: "" });
      return false;
    }
  }

  return { ...state, run };
}

export function ActionStatus({ error, message }) {
  if (error) return <div className="alert error" role="alert">{error}</div>;
  if (message) return <div className="alert info" role="status">{message}</div>;
  return null;
}

export function DashboardHeading({ title, subtitle, loading, onRefresh, children }) {
  return (
    <div className="page-title">
      <div>
        <h1>{title}</h1>
        {subtitle && <div className="muted">{subtitle}</div>}
      </div>
      <div className="toolbar">
        {children}
        <button onClick={() => onRefresh()} disabled={loading}>{loading ? "Loading…" : "Refresh"}</button>
      </div>
    </div>
  );
}

// A form opened from a toolbar button, shown full width above the dashboard.
export function Panel({ title, onClose, children }) {
  return (
    <Card title={title} className="panel" action={<button onClick={onClose} aria-label="Close">Close</button>}>
      {children}
    </Card>
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

// ---------- schedule a drive (staff and admin, BBS-F-040) ----------

export function isoDay(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

function pad(n) {
  return String(n).padStart(2, "0");
}

// Back-to-back slots of `lengthMin` minutes from `firstStart` ("HH:MM") on `date`.
// Times are sent without a timezone, the same way the seed data stores them.
export function buildSlots(date, firstStart, count, lengthMin, capacity) {
  const [h, m] = firstStart.split(":").map(Number);
  const first = h * 60 + m;
  if (first + count * lengthMin > 24 * 60) throw new Error("The last slot must finish by midnight.");
  const at = (minutes) => `${date}T${pad(Math.floor(minutes / 60))}:${pad(minutes % 60)}:00`;
  return Array.from({ length: count }, (_, i) => ({
    start_time: at(first + i * lengthMin),
    end_time: at(first + (i + 1) * lengthMin),
    capacity,
  }));
}

export function DriveForm({ onCreated }) {
  const [form, setForm] = useState({
    name: "",
    location: "",
    date: isoDay(21),
    start: "09:00",
    slots: "4",
    length: "60",
    capacity: "10",
  });
  const action = useAction(onCreated);
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  function submit(e) {
    e.preventDefault();
    action.run(async () => {
      const slots = buildSlots(form.date, form.start, Number(form.slots), Number(form.length), Number(form.capacity));
      const drive = await api("/api/drives", {
        method: "POST",
        body: { name: form.name, location: form.location, date: form.date, slots },
      });
      setForm({ ...form, name: "", location: "" });
      const places = slots.length * Number(form.capacity);
      return `Scheduled “${drive.name}” on ${formatDate(drive.date)} with ${places} places. Donors can book it now.`;
    });
  }

  return (
    <form onSubmit={submit} className="form-grid">
      <label>Drive name<input value={form.name} onChange={set("name")} minLength={3} maxLength={100} placeholder="City Hospital blood drive" required /></label>
      <label>Location<input value={form.location} onChange={set("location")} minLength={3} maxLength={200} placeholder="Main hall, 2nd floor" required /></label>
      <label>Date<input type="date" value={form.date} min={isoDay(0)} onChange={set("date")} required /></label>
      <label>First slot starts<input type="time" value={form.start} onChange={set("start")} required /></label>
      <label>Number of slots<input type="number" min="1" max="12" value={form.slots} onChange={set("slots")} required /></label>
      <label>
        Slot length
        <select value={form.length} onChange={set("length")}>
          <option value="30">30 min</option>
          <option value="60">1 hour</option>
          <option value="90">1.5 hours</option>
          <option value="120">2 hours</option>
        </select>
      </label>
      <label>Donors per slot<input type="number" min="1" max="500" value={form.capacity} onChange={set("capacity")} required /></label>
      <div className="form-submit"><button className="primary" disabled={action.busy}>{action.busy ? "Saving…" : "Schedule drive"}</button></div>
      <div className="form-status"><ActionStatus {...action} /></div>
    </form>
  );
}
