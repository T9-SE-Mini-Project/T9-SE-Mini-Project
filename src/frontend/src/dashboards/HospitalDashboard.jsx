import { useState } from "react";
import { api } from "../api.js";
import { BLOOD_GROUPS, Badge, Card, Empty, StatCard, formatDate } from "../components/ui.jsx";
import { ActionStatus, DashboardHeading, LoadErrors, Panel, useAction, useDashboardData } from "./shared.jsx";

const COMPONENTS = ["Whole Blood", "RBC", "Platelets", "Plasma"];
const MAX_UNITS = 10; // MAX_UNITS_PER_REQUEST on the backend

// Hospital representative: submit blood requests and track them (BLOOD-15).
export default function HospitalDashboard({ user }) {
  const { loading, data, errors, reload } = useDashboardData({ requests: "/api/requests" });
  const [formOpen, setFormOpen] = useState(false);
  const requests = data.requests ?? [];
  const count = (status) => (data.requests ? requests.filter((r) => r.status === status).length : null);
  const unitsOnTheWay = requests.filter((r) => r.status === "APPROVED").reduce((sum, r) => sum + r.quantity, 0);

  return (
    <>
      <DashboardHeading title="Blood requests" subtitle={`Hospital #${user.hospital_id}`} loading={loading} onRefresh={reload}>
        <button className="primary" onClick={() => setFormOpen(true)}>New request</button>
      </DashboardHeading>
      <LoadErrors errors={errors} />

      {formOpen && (
        <Panel title="Request blood" onClose={() => setFormOpen(false)}>
          <RequestForm onSubmitted={() => reload({ quiet: true })} />
        </Panel>
      )}

      <div className="stats">
        <StatCard label="Waiting for approval" value={count("PENDING")} />
        <StatCard label="Approved" value={count("APPROVED")} hint={unitsOnTheWay ? `${unitsOnTheWay} units being prepared` : "nothing being prepared"} />
        <StatCard label="Dispatched" value={count("DISPATCHED")} />
        <StatCard label="Rejected" value={count("REJECTED")} />
      </div>

      <Card title="All requests">
        {!requests.length ? (
          <Empty>No requests submitted yet.</Empty>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>#</th><th>Group</th><th>Component</th><th>Units</th><th>Urgency</th><th>Patient ref.</th><th>Needed by</th><th>Submitted</th><th>Status</th></tr>
              </thead>
              <tbody>
                {requests.map((r) => (
                  <tr key={r.id}>
                    <td>{r.id}</td>
                    <td><strong>{r.blood_group}</strong></td>
                    <td>{r.component}</td>
                    <td>{r.quantity}</td>
                    <td><Badge>{r.urgency}</Badge></td>
                    <td>{r.patient_reference ?? "–"}</td>
                    <td>{formatDate(r.required_by)}</td>
                    <td>{formatDate(r.created_at)}</td>
                    <td><Badge>{r.status}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  );
}

const EMPTY_REQUEST = {
  blood_group: "O+",
  component: "RBC",
  quantity: "1",
  urgency: "routine",
  required_by: "",
  patient_reference: "",
  notes: "",
};

function RequestForm({ onSubmitted }) {
  const [form, setForm] = useState(EMPTY_REQUEST);
  const action = useAction(onSubmitted);
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  function submit(e) {
    e.preventDefault();
    action.run(async () => {
      const created = await api("/api/requests", {
        method: "POST",
        body: {
          ...form,
          quantity: Number(form.quantity),
          // datetime-local is local time; the API wants a full timestamp.
          required_by: form.required_by ? new Date(form.required_by).toISOString() : null,
        },
      });
      setForm(EMPTY_REQUEST);
      return `Request #${created.id} sent to the blood bank (${created.quantity} × ${created.blood_group} ${created.component}).`;
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
      <label>Units<input type="number" min="1" max={MAX_UNITS} value={form.quantity} onChange={set("quantity")} required /></label>
      <label>
        Urgency
        <select value={form.urgency} onChange={set("urgency")}>
          <option value="routine">Routine</option>
          <option value="urgent">Urgent</option>
          <option value="emergency">Emergency</option>
        </select>
      </label>
      <label>Needed by (optional)<input type="datetime-local" value={form.required_by} onChange={set("required_by")} /></label>
      <label>Patient reference (optional)<input value={form.patient_reference} onChange={set("patient_reference")} maxLength={50} /></label>
      <label className="span-2">Notes (optional)<input value={form.notes} onChange={set("notes")} maxLength={500} /></label>
      <div className="form-submit"><button className="primary" disabled={action.busy}>{action.busy ? "Sending…" : "Submit request"}</button></div>
      <div className="form-status"><ActionStatus {...action} /></div>
    </form>
  );
}
