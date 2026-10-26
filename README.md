# Blood Bank & Donation Management System (BBMS)

Find the Jira Dashboard here:
https://pes1ug24am351.atlassian.net/jira/software/projects/BLOOD/boards/70/backlog?epics=visible&atlOrigin=eyJpIjoiOWFmMGZlMDFhYzI0NGUyYWIzYmEwOTM1ODliNjMyNmQiLCJwIjoiaiJ9

Requirements, UML and the test plan are in the PDFs / DOCX at the repository root.

## Running the backend

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                  # then edit as needed

python -m src.backend.cli create-admin --email admin@example.com   # first admin account
uvicorn src.backend.main:app --reload
```

Interactive API docs: http://127.0.0.1:8000/docs

With the default settings the app uses a local SQLite file (`bbms.db`) and creates the
tables at startup. Signup OTPs and drive reminders are written to the server log by
`LoggingNotifier` until a real SMS/email provider is connected (development only).

Scheduled jobs (run from cron or similar):

```bash
python -m src.backend.cli expire-units --actor-id <staff or admin id>   # daily, BLOOD-14
python -m src.backend.cli send-reminders                                # hourly, BBS-F-042
```

## Running the frontend

A React + Vite dashboard in `src/frontend/`. Start the backend first, then:

```bash
cd src/frontend
pnpm install        # or: npm install
pnpm dev            # http://localhost:5173
```

The dev server forwards `/api` to the backend on port 8000 (`vite.config.js`), so no CORS
setup is needed. Set `VITE_API_TARGET` to point it somewhere else.

After login each role gets one read-only dashboard built from the existing endpoints:

| Role | Dashboard shows |
|---|---|
| Donor | blood group, whether they can donate (and why not), donation history, upcoming drives; a profile form until the profile exists |
| Blood bank staff | available units, stock by blood group and component, units expiring within 7 days, pending requests, drives |
| Hospital rep | the hospital's requests and their status |
| Admin | API status and drive bookings |

The theme is red and white (light) or red and black (dark). It follows the system setting,
and the header toggle overrides it. Colours are CSS variables at the top of `src/styles.css`.

```
src/frontend/src/
  main.jsx, App.jsx     entry point; picks the dashboard for the logged-in role
  api.js                fetch wrapper (bearer token, error messages, logout on 401)
  pages/Login.jsx       login + donor signup / OTP verification
  dashboards/           one component per role, plus shared pieces
  components/           stat cards, badges, blood group bars, theme toggle
```

## Running the tests

```bash
python -m pytest              # everything
python -m pytest tests/unit   # unit tests only
```

`pyproject.toml` puts the repository root on the import path, so tests always import the
backend as `src.backend.<module>`.

## Architecture

```
src/backend/
  main.py               app factory: builds the app and wires every module together
  cli.py                operator commands (create-admin, expire-units, send-reminders)
  config.py             settings from environment variables
  database.py           shared SQLAlchemy Base, engine and per-request sessions
  blood.py              blood groups, components and compatibility rules (shared)
  notifications.py      OTP / reminder delivery (development stand-in)
  auth/                 login, sessions, lockout, signup + OTP, roles, admin accounts
  donor/                profile, eligibility, donation history, recording donations
  inventory/            blood bags, expiry, CrossMatchInterface implementation
  hospital_requests/    submit, cross-match, approve / reject / dispatch
  drives/               drives, slot booking, reminders
```

Conventions used across modules:

- **Layers.** `routes.py` (HTTP only) -> `service.py` (business rules) -> models / repository
  (database). Services raise domain errors; routes turn them into HTTP status codes.
- **Dependency injection.** Each module exposes a `create_*_router(get_session, require_role, ...)`
  factory and never imports the app. `main.py` is the only place that knows every module,
  so modules can be tested with fakes (see `tests/unit/support.py`).
- **One schema.** All tables use `database.Base`, so foreign keys work across modules
  (`donor_profiles.donor_id -> auth_users.id`, ...). hospital_requests deliberately keeps
  no foreign keys into inventory and talks to it only through `CrossMatchInterface`.
- **Concurrency.** Unit allocation, slot booking and status changes use conditional
  `UPDATE ... WHERE <expected state>` statements, so of two simultaneous actions only one
  succeeds (BBS-NF-005).
- **Audit.** Request status changes and unit expiry record who did it and when (BBS-SR-004).

## Roles and main endpoints

| Role | Can |
|---|---|
| Donor | sign up, manage profile, check eligibility, view history, book drive slots |
| Hospital rep | submit and track blood requests for their hospital |
| Blood bank staff | log bags, run expiry, record donations, approve / reject / dispatch requests, run drives |
| Admin | create staff, hospital rep and admin accounts; run drives |

| Area | Endpoints |
|---|---|
| Auth | `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout`, `POST /api/auth/signup`, `/signup/verify`, `/signup/resend` |
| Admin | `POST /api/admin/accounts` |
| Donor | `POST/GET /api/donors/profile`, `GET /api/donors/me/eligibility`, `GET /api/donors/me/donations`, `GET/POST /api/donors/{donor_id}/donations` (staff) |
| Inventory | `POST/GET /api/inventory/bags`, `GET /api/inventory/bags/{unit_id}`, `POST /api/inventory/expire` |
| Requests | `POST/GET /api/requests`, `GET /api/requests/{id}`, `GET /api/requests/queue`, `GET .../matches`, `POST .../approve`, `.../reject`, `.../dispatch`, `GET .../units`, `.../history` |
| Drives | `POST/GET /api/drives`, `POST /api/drives/slots/{slot_id}/book`, `GET /api/drives/bookings/me`, `POST /api/drives/reminders/send` |

## End-to-end flow

1. A donor signs up, verifies the OTP and creates a profile.
2. The donor checks eligibility and books a slot at an upcoming drive (eligibility is checked
   for the drive date), and gets a reminder before the slot.
3. Staff record the donation: it is saved in the donor's history and a Whole Blood bag is
   added to inventory.
4. A hospital rep submits a request. Staff preview matches and approve it, which reserves
   compatible, unexpired bags. Dispatching marks those bags as sent. An expired bag can
   never be dispatched.

## Known gaps / next steps

- Database migrations: Alembic is in `requirements.txt` but not set up yet; tables are
  created with `create_all` at startup.
- A real SMS/email provider for OTPs and reminders.
- Recording a donation commits the history row and the inventory bag separately.
- An approved request whose allocated unit expires cannot be dispatched and has no
  re-allocation flow yet.
- Frontend actions (approve / dispatch requests, book slots, submit requests, log bags):
  the dashboards are read-only for now; the API already supports all of these.
