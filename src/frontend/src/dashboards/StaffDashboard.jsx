import { Badge, BloodGroupBars, Card, Empty, StatCard, daysUntil, formatDate } from "../components/ui.jsx";
import { DashboardHeading, LoadErrors, UpcomingDrives, drivesSummary, useDashboardData } from "./shared.jsx";

const EXPIRING_WITHIN_DAYS = 7;
const COMPONENTS = ["Whole Blood", "RBC", "Platelets", "Plasma"];

// Blood bank staff: stock levels, units about to expire, the request queue and drives.
export default function StaffDashboard() {
  const { loading, data, errors, reload } = useDashboardData({
    bags: "/api/inventory/bags",
    pending: "/api/requests/queue?status=PENDING",
    approved: "/api/requests/queue?status=APPROVED",
    drives: "/api/drives",
  });

  const bags = data.bags ?? [];
  const pending = data.pending ?? [];
  const byGroup = countBy(bags, (b) => b.blood_group);
  const byComponent = countBy(bags, (b) => b.component);
  const expiring = bags
    .filter((b) => daysUntil(b.expiry_date) <= EXPIRING_WITHIN_DAYS)
    .sort((a, b) => a.expiry_date.localeCompare(b.expiry_date));
  const emergencies = pending.filter((r) => r.urgency === "emergency").length;
  const drives = drivesSummary(data.drives ?? []);

  return (
    <>
      <DashboardHeading title="Blood bank overview" subtitle="Available stock and work waiting for staff" loading={loading} onRefresh={reload} />
      <LoadErrors errors={errors} />

      <div className="stats">
        <StatCard label="Units available" value={data.bags ? bags.length : null} hint="unexpired, not allocated" />
        <StatCard label="Pending requests" value={data.pending ? pending.length : null} hint={emergencies ? `${emergencies} emergency` : "none urgent"} />
        <StatCard label={`Expiring in ${EXPIRING_WITHIN_DAYS} days`} value={data.bags ? expiring.length : null} hint="use these first" />
        <StatCard label="Awaiting dispatch" value={data.approved?.length} hint="approved requests" />
      </div>

      <div className="grid">
        <Card title="Stock by blood group">
          <BloodGroupBars counts={byGroup} />
          <div className="muted small" style={{ marginTop: 10 }}>Amber bars: fewer than 3 units.</div>
        </Card>

        <Card title="Stock by component">
          <table>
            <tbody>
              {COMPONENTS.map((c) => (
                <tr key={c}>
                  <td>{c}</td>
                  <td style={{ textAlign: "right", fontWeight: 700 }}>{byComponent[c] ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card title="Pending hospital requests" className="wide">
          {!pending.length ? (
            <Empty>No requests waiting.</Empty>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr><th>#</th><th>Hospital</th><th>Group</th><th>Component</th><th>Units</th><th>Urgency</th><th>Needed by</th><th>Received</th></tr>
                </thead>
                <tbody>
                  {pending.map((r) => (
                    <tr key={r.id}>
                      <td>{r.id}</td>
                      <td>{r.hospital_id}</td>
                      <td><strong>{r.blood_group}</strong></td>
                      <td>{r.component}</td>
                      <td>{r.quantity}</td>
                      <td><Badge>{r.urgency}</Badge></td>
                      <td>{formatDate(r.required_by)}</td>
                      <td>{formatDate(r.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title="Expiring soon">
          {!expiring.length ? (
            <Empty>Nothing expires in the next {EXPIRING_WITHIN_DAYS} days.</Empty>
          ) : (
            <div className="table-wrap">
              <table>
                <thead><tr><th>Unit</th><th>Group</th><th>Component</th><th>Expires</th></tr></thead>
                <tbody>
                  {expiring.slice(0, 8).map((b) => (
                    <tr key={b.unit_id}>
                      <td title={b.unit_id}>{b.unit_id.slice(0, 12)}…</td>
                      <td><strong>{b.blood_group}</strong></td>
                      <td>{b.component}</td>
                      <td><ExpiryBadge date={b.expiry_date} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <UpcomingDrives drives={data.drives} />
      </div>
      <p className="muted small" style={{ marginTop: 16 }}>
        Drives: {drives.booked} of {drives.capacity} places booked across {drives.count} upcoming drive{drives.count === 1 ? "" : "s"}.
      </p>
    </>
  );
}

function ExpiryBadge({ date }) {
  const days = daysUntil(date);
  return (
    <span title={formatDate(date)}>
      <Badge tone={days <= 2 ? "red" : "amber"}>{days === 1 ? "1 day" : `${days} days`}</Badge>
    </span>
  );
}

function countBy(items, keyOf) {
  return items.reduce((acc, item) => {
    const key = keyOf(item);
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});
}
