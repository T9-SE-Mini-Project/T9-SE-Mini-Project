import { useState } from "react";
import { api } from "../api.js";
import { BLOOD_GROUPS, Badge, Card, Empty, StatCard, formatDate, formatTime } from "../components/ui.jsx";
import { DashboardHeading, LoadErrors, UpcomingDrives, useDashboardData } from "./shared.jsx";

// Donor: eligibility (BBS-F-011), donation history (BBS-F-012), bookings and drives.
export default function DonorDashboard() {
  const { loading, data, errors, reload } = useDashboardData({
    profile: "/api/donors/profile",
    eligibility: "/api/donors/me/eligibility",
    donations: "/api/donors/me/donations",
    bookings: "/api/drives/bookings/me",
    drives: "/api/drives",
  });

  const noProfile = errors.profile?.status === 404;
  const eligibility = data.eligibility;
  const donations = data.donations ?? [];
  const completed = donations.filter((d) => d.status === "COMPLETED");
  const nextBooking = (data.bookings ?? [])
    .filter((b) => new Date(b.slot.start_time) > new Date())
    .sort((a, b) => a.slot.start_time.localeCompare(b.slot.start_time))[0];

  return (
    <>
      <DashboardHeading
        title={data.profile ? `Hello, ${data.profile.full_name.split(" ")[0]}` : "Your donor dashboard"}
        subtitle="Thank you for giving blood"
        loading={loading}
        onRefresh={reload}
      />
      <LoadErrors errors={errors} />

      {noProfile ? (
        <ProfileForm onSaved={reload} />
      ) : (
        <>
          <div className="stats">
            <StatCard label="Blood group" value={data.profile?.blood_group} hint={data.profile && `${data.profile.age} yrs · ${Number(data.profile.weight_kg)} kg`} />
            <StatCard
              label="Can donate"
              value={eligibility ? (eligibility.eligible ? "Yes" : "Not yet") : null}
              hint={eligibility?.next_eligible_date ? `from ${formatDate(eligibility.next_eligible_date)}` : eligibility?.eligible ? "you're eligible today" : ""}
            />
            <StatCard label="Donations" value={data.donations ? completed.length : null} hint={completed[0] ? `last on ${formatDate(completed[0].donation_date)}` : "none yet"} />
            <StatCard
              label="Next appointment"
              value={nextBooking ? formatDate(nextBooking.slot.start_time) : "None"}
              hint={nextBooking ? `at ${formatTime(nextBooking.slot.start_time)}` : "book a drive slot"}
            />
          </div>

          <div className="grid">
            {eligibility && !eligibility.eligible && (
              <Card title="Why you can't donate yet" className="wide">
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  {eligibility.reasons.map((r) => <li key={r}>{r}</li>)}
                </ul>
              </Card>
            )}

            <Card title="Donation history">
              {!donations.length ? (
                <Empty>Your donations will appear here.</Empty>
              ) : (
                <div className="table-wrap">
                  <table>
                    <thead><tr><th>Date</th><th>Quantity</th><th>Status</th></tr></thead>
                    <tbody>
                      {donations.map((d) => (
                        <tr key={d.donation_id}>
                          <td>{formatDate(d.donation_date)}</td>
                          <td>{d.quantity_ml} ml</td>
                          <td><Badge>{d.status}</Badge></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            <UpcomingDrives drives={data.drives} />
          </div>
        </>
      )}
    </>
  );
}

// Shown until the donor saves a profile (BBS-F-010): eligibility needs it.
function ProfileForm({ onSaved }) {
  const [form, setForm] = useState({ full_name: "", blood_group: "O+", date_of_birth: "", weight_kg: "", phone: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/api/donors/profile", { method: "POST", body: form });
      onSaved();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <Card title="Complete your donor profile">
      <p className="muted" style={{ marginTop: 0 }}>We need a few details to check whether you can donate.</p>
      {error && <div className="alert error" role="alert" style={{ marginBottom: 12 }}>{error}</div>}
      <form onSubmit={submit} style={{ display: "grid", gap: 12, gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))" }}>
        <label>Full name<input value={form.full_name} onChange={set("full_name")} maxLength={100} required /></label>
        <label>
          Blood group
          <select value={form.blood_group} onChange={set("blood_group")}>
            {BLOOD_GROUPS.map((g) => <option key={g}>{g}</option>)}
          </select>
        </label>
        <label>Date of birth<input type="date" value={form.date_of_birth} onChange={set("date_of_birth")} required /></label>
        <label>Weight (kg)<input type="number" step="0.1" min="1" value={form.weight_kg} onChange={set("weight_kg")} required /></label>
        <label>Phone<input type="tel" value={form.phone} onChange={set("phone")} maxLength={20} required /></label>
        <div style={{ alignSelf: "end" }}><button className="primary" disabled={busy}>Save profile</button></div>
      </form>
    </Card>
  );
}
