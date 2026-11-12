import { useState } from "react";
import { api } from "../api.js";
import { BLOOD_GROUPS, Badge, BloodGroupBars, Card, Empty, StatCard, daysUntil, formatDate } from "../components/ui.jsx";
import {
  ActionStatus,
  DashboardHeading,
  DriveForm,
  LoadErrors,
  Panel,
  UpcomingDrives,
  drivesSummary,
  isoDay,
  useAction,
  useDashboardData,
} from "./shared.jsx";

const EXPIRING_WITHIN_DAYS = 7;
const COMPONENTS = ["Whole Blood", "RBC", "Platelets", "Plasma"];

// Blood bank staff: stock levels, units about to expire, the request queue and drives.
// Staff can log new bags, approve / reject / dispatch requests, schedule drives and run
// the expiry check from here.
export default function StaffDashboard() {
  const { loading, data, errors, reload } = useDashboardData({
    bags: "/api/inventory/bags",
    pending: "/api/requests/queue?status=PENDING",
    approved: "/api/requests/queue?status=APPROVED",
    drives: "/api/drives",
  });
  const [panel, setPanel] = useState(null);
  const refresh = () => reload({ quiet: true });
  const expiry = useAction(refresh);

  const bags = data.bags ?? [];
  const pending = data.pending ?? [];
  const approved = data.approved ?? [];
  const byGroup = countBy(bags, (b) => b.blood_group);
  const byComponent = countBy(bags, (b) => b.component);
  const expiring = bags
    .filter((b) => daysUntil(b.expiry_date) <= EXPIRING_WITHIN_DAYS)
    .sort((a, b) => a.expiry_date.localeCompare(b.expiry_date));
  const emergencies = pending.filter((r) => r.urgency === "emergency").length;
  const drives = drivesSummary(data.drives ?? []);

  function runExpiry() {
    expiry.run(async () => {
      const { expired_count } = await api("/api/inventory/expire", { method: "POST" });
      return expired_count ? `Marked ${expired_count} expired unit(s); they are no longer in stock.` : "No units have expired.";
    });
  }

  return (
    <>
      <DashboardHeading title="Blood bank overview" subtitle="Available stock and work waiting for staff" loading={loading} onRefresh={reload}>
        <button className="primary" onClick={() => setPanel("bags")}>Log blood bags</button>
        <button onClick={() => setPanel("drive")}>Schedule drive</button>
        <button onClick={runExpiry} disabled={expiry.busy}>{expiry.busy ? "Checking…" : "Run expiry check"}</button>
      </DashboardHeading>
      <LoadErrors errors={errors} />
      {(expiry.error || expiry.message) && <div style={{ marginBottom: 16 }}><ActionStatus {...expiry} /></div>}

      {panel === "bags" && (
        <Panel title="Log blood bags" onClose={() => setPanel(null)}>
          <BagForm onAdded={refresh} />
        </Panel>
      )}
      {panel === "drive" && (
        <Panel title="Schedule a donation drive" onClose={() => setPanel(null)}>
          <DriveForm onCreated={refresh} />
        </Panel>
      )}

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

        <PendingRequests requests={pending} onChanged={refresh} />
        <ReadyToDispatch requests={approved} onChanged={refresh} />

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

// Log a batch of identical bags from one collection (BLOOD-12). Each bag gets its own
// unit ID and an expiry date from the component's shelf life (BLOOD-13).
function BagForm({ onAdded }) {
  const [form, setForm] = useState({ blood_group: "O+", component: "Whole Blood", collection_date: isoDay(0), count: "1" });
  const action = useAction(onAdded);
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  function submit(e) {
    e.preventDefault();
    action.run(async () => {
      const count = Number(form.count);
      let last;
      for (let i = 0; i < count; i++) {
        last = await api("/api/inventory/bags", {
          method: "POST",
          body: { blood_group: form.blood_group, component: form.component, collection_date: form.collection_date },
        });
      }
      return `Added ${count} unit${count === 1 ? "" : "s"} of ${form.blood_group} ${form.component}, expiring ${formatDate(last.expiry_date)}.`;
    });
  }

  return (
    <form onSubmit={submit} className="form-grid">
      <label>
        Blood group
        <select value={form.blood_group} onChange={set("blood_group")}>
          {BLOOD_GROUPS.map((g) => <option key={g}>{g}</option>)}
        </select>
      </label>
      <label>
        Component
        <select value={form.component} onChange={set("component")}>
          {COMPONENTS.map((c) => <option key={c}>{c}</option>)}
        </select>
      </label>
      <label>Collected on<input type="date" value={form.collection_date} max={isoDay(0)} onChange={set("collection_date")} required /></label>
      <label>Number of bags<input type="number" min="1" max="50" value={form.count} onChange={set("count")} required /></label>
      <div className="form-submit"><button className="primary" disabled={action.busy}>{action.busy ? "Adding…" : "Add to stock"}</button></div>
      <div className="form-status"><ActionStatus {...action} /></div>
    </form>
  );
}

// Approve allocates compatible units from stock (BLOOD-16/17); reject needs a reason.
function PendingRequests({ requests, onChanged }) {
  const action = useAction(onChanged);
  const [rejecting, setRejecting] = useState(null);
  const [reason, setReason] = useState("");

  function approve(r) {
    action.run(async () => {
      await api(`/api/requests/${r.id}/approve`, { method: "POST" });
      return `Request #${r.id} approved: ${r.quantity} unit(s) of ${r.blood_group} ${r.component} set aside for hospital #${r.hospital_id}.`;
    });
  }

  async function reject(e, r) {
    e.preventDefault();
    const ok = await action.run(async () => {
      await api(`/api/requests/${r.id}/reject`, { method: "POST", body: { reason } });
      return `Request #${r.id} rejected.`;
    });
    if (ok) {
      setRejecting(null);
      setReason("");
    }
  }

  return (
    <Card title="Pending hospital requests" className="wide">
      <ActionStatus {...action} />
      {!requests.length ? (
        <Empty>No requests waiting.</Empty>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>#</th><th>Hospital</th><th>Group</th><th>Component</th><th>Units</th><th>Urgency</th><th>Needed by</th><th>Received</th><th /></tr>
            </thead>
            <tbody>
              {requests.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>{r.hospital_id}</td>
                  <td><strong>{r.blood_group}</strong></td>
                  <td>{r.component}</td>
                  <td>{r.quantity}</td>
                  <td><Badge>{r.urgency}</Badge></td>
                  <td>{formatDate(r.required_by)}</td>
                  <td>{formatDate(r.created_at)}</td>
                  <td className="row-actions">
                    {rejecting === r.id ? (
                      <form onSubmit={(e) => reject(e, r)} className="inline-form">
                        <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason" maxLength={500} required autoFocus />
                        <button className="primary" disabled={action.busy}>Reject</button>
                        <button type="button" onClick={() => setRejecting(null)}>Cancel</button>
                      </form>
                    ) : (
                      <>
                        <button className="primary" onClick={() => approve(r)} disabled={action.busy}>Approve</button>
                        <button onClick={() => { setRejecting(r.id); setReason(""); }} disabled={action.busy}>Reject</button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

// Approved requests whose units are set aside; dispatching marks them as sent (BBS-F-032).
function ReadyToDispatch({ requests, onChanged }) {
  const action = useAction(onChanged);

  function dispatch(r) {
    action.run(async () => {
      await api(`/api/requests/${r.id}/dispatch`, { method: "POST" });
      return `Request #${r.id} dispatched to hospital #${r.hospital_id}.`;
    });
  }

  return (
    <Card title="Ready to dispatch" className="wide">
      <ActionStatus {...action} />
      {!requests.length ? (
        <Empty>Approved requests appear here until they are sent.</Empty>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>#</th><th>Hospital</th><th>Group</th><th>Component</th><th>Units</th><th>Urgency</th><th>Needed by</th><th /></tr>
            </thead>
            <tbody>
              {requests.map((r) => (
                <tr key={r.id}>
                  <td>{r.id}</td>
                  <td>{r.hospital_id}</td>
                  <td><strong>{r.blood_group}</strong></td>
                  <td>{r.component}</td>
                  <td>{r.quantity}</td>
                  <td><Badge>{r.urgency}</Badge></td>
                  <td>{formatDate(r.required_by)}</td>
                  <td className="row-actions">
                    <button className="primary" onClick={() => dispatch(r)} disabled={action.busy}>Dispatch</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
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
