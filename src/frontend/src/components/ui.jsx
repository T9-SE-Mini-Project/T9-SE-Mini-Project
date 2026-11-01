// Small presentational building blocks shared by every dashboard.

export function Logo({ size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path fill="currentColor" d="M12 2s7 7.6 7 12.5A7 7 0 0 1 5 14.5C5 9.6 12 2 12 2z" />
      <path fill="var(--surface)" d="M11 10h2v2.5h2.5v2H13V17h-2v-2.5H8.5v-2H11z" />
    </svg>
  );
}

export function StatCard({ label, value, hint }) {
  return (
    <div className="card stat">
      <div className="label">{label}</div>
      <div className="value">{value ?? "–"}</div>
      {hint && <div className="hint">{hint}</div>}
    </div>
  );
}

export function Card({ title, action, className = "", children }) {
  return (
    <section className={`card ${className}`}>
      {(title || action) && (
        <div className="page-title" style={{ marginBottom: 14 }}>
          {title && <h2 style={{ margin: 0 }}>{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

const STATUS_TONE = {
  AVAILABLE: "green",
  APPROVED: "green",
  COMPLETED: "green",
  DISPATCHED: "green",
  PENDING: "amber",
  ALLOCATED: "amber",
  DEFERRED: "amber",
  REJECTED: "red",
  EXPIRED: "red",
  CANCELLED: "red",
  emergency: "red",
  urgent: "amber",
};

// The colour comes from the status text, unless `tone` (red / amber / green) is given.
export function Badge({ children, tone }) {
  return <span className={`badge ${tone ?? STATUS_TONE[children] ?? ""}`}>{children}</span>;
}

export function Empty({ children }) {
  return <div className="empty">{children}</div>;
}

export const BLOOD_GROUPS = ["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"];

// Horizontal bars, one per blood group. Groups below `lowAt` units are shown in amber.
export function BloodGroupBars({ counts, lowAt = 3 }) {
  const max = Math.max(1, ...BLOOD_GROUPS.map((g) => counts[g] ?? 0));
  return (
    <div className="bars" role="list">
      {BLOOD_GROUPS.map((group) => {
        const n = counts[group] ?? 0;
        return (
          <div className="bar-row" role="listitem" key={group} aria-label={`${group}: ${n} units`}>
            <span className="group">{group}</span>
            <div className="bar-track">
              <div className={`bar-fill ${n < lowAt ? "low" : ""}`} style={{ width: `${(n / max) * 100}%` }} />
            </div>
            <span className="count">{n}</span>
          </div>
        );
      })}
    </div>
  );
}

export function formatDate(value) {
  if (!value) return "–";
  const date = value.length === 10 ? new Date(`${value}T00:00:00`) : new Date(value);
  return date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function formatTime(value) {
  if (!value) return "–";
  return new Date(value).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

export function daysUntil(isoDate) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((new Date(`${isoDate}T00:00:00`) - today) / 86_400_000);
}
