import { Badge, Card, Empty, StatCard, formatDate } from "../components/ui.jsx";
import { DashboardHeading, LoadErrors, useDashboardData } from "./shared.jsx";

// Hospital representative: track this hospital's blood requests (BLOOD-15).
export default function HospitalDashboard({ user }) {
  const { loading, data, errors, reload } = useDashboardData({ requests: "/api/requests" });
  const requests = data.requests ?? [];
  const count = (status) => (data.requests ? requests.filter((r) => r.status === status).length : null);
  const unitsOnTheWay = requests.filter((r) => r.status === "APPROVED").reduce((sum, r) => sum + r.quantity, 0);

  return (
    <>
      <DashboardHeading title="Blood requests" subtitle={`Hospital #${user.hospital_id}`} loading={loading} onRefresh={reload} />
      <LoadErrors errors={errors} />

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
