# Deviations from the Submitted Documents

Blood Bank & Donation Management System (BBMS), Team T9. 20-11-2026.

The deliverables ask that anything built differently from the submitted SRS, architecture
document and test plan is written down and explained at the final demo. This is that list.

## 1. Requirements (SRS v1.0)

| # | SRS says | What was built | Why |
|---|---|---|---|
| R1 | AC-003: the 6th wrong attempt shows an 'account locked' message. | The account is locked for 30 minutes, but the reply is the same "Invalid email or password." as for a wrong password. | A separate message tells an attacker which emails have accounts. The lock itself works as specified (TC-Auth-03). |
| R2 | A Drive Coordinator role schedules drives (2.3, BBS-F-040). | There is no separate coordinator login. Blood bank staff and admins schedule drives. | BBS-F-001 defines exactly four login roles; a fifth was not worth adding for one screen. |
| R3 | A notification API sends OTPs and reminders by SMS or email (3.3). | `LoggingNotifier` writes them to the server log. The modules depend on a small interface, so a real provider can replace it without changing them. | No SMS or email provider account for a mini project. |
| R4 | HTTPS between frontend and backend (3.4, BBS-SR-001). | Runs over plain HTTP on localhost. | Not deployed, so there is no domain or certificate. HTTPS is a deployment setting, not a code change. |
| R5 | BBS-F-022: expiry "runs as a check on save/query, no scheduler needed". | Both: every stock query ignores units past their expiry date, and an expiry run (dashboard button, API, or `cli expire-units`) marks them EXPIRED and writes the audit entry. | BBS-SR-004 needs a logged action with a user and a time, which a query-time filter alone cannot give. |
| R6 | Section 2.2 lists barcode/QR tagging, test-result entry and administrative reporting. | Not built. Each bag gets a unique text ID (BBS-F-020). | These are in the product overview only; none of the 15 numbered requirements asks for them. |
| R7 | Not in the SRS. | Low-stock alerts (BLOOD-25) and emergency donor call-out (BLOOD-26) were added in Sprint 2. | Backlog items added during sprint planning. Test cases TC-Inv-04 and TC-Donor-04 were added for them. |
| R8 | The traceability matrix names BBS-F-023 and BBS-NF-006. | Treated as BBS-F-022 and BBS-NF-005. | Those two IDs are not defined in the SRS; a numbering slip. |

## 2. Architecture and design

| # | Design says | What was built | Why |
|---|---|---|---|
| A1 | One Database Component; the SRS allows MySQL, PostgreSQL or SQLite. | SQLite by default; PostgreSQL through `DATABASE_URL` (driver included, not tested). Tables are created at startup; Alembic migrations are not set up. | SQLite needs no installation for the demo and for CI. |
| A2 | The Notification Service is used by Authentication and Drive Management. | Donor Management also uses it, for the emergency call-out. | Follows from R7. |
| A3 | Layered architecture with five business components. | As designed: `auth`, `donor`, `inventory`, `hospital_requests`, `drives`, each split into routes, service and models. Hospital Request reaches Inventory only through `CrossMatchInterface`, as in the component diagram. | No deviation. Listed to confirm it. |

## 3. Test plan (v1.0)

| # | Test plan says | What was done | Why |
|---|---|---|---|
| T1 | Tools: Selenium (UI), Postman (API), JMeter (performance). | pytest with FastAPI TestClient and httpx for unit, integration and system tests; timing and concurrency checks written in pytest. | One tool that runs in GitHub Actions on every pull request. Postman and JMeter runs would be manual and not repeatable in CI. |
| T2 | UI automation and usability testing. | The React dashboards are checked by the production build in CI and by integration tests that send the same requests the forms send. No browser automation; the usability test TC-UX-01 has not been run. | Time. Listed as not validated in the System Validation Report. |
| T3 | Response-time target of 5 seconds. | Tested against 2 seconds. | The SRS (BBS-NF-001) says 1-2 seconds, and the SRS is authoritative. |
| T4 | Test case IDs `TC-Don-xx`, `TC-HR-xx`. | `TC-Donor-xx`, `TC-Hosp-xx`, as in the SRS. | The two documents disagreed; see `docs/Test_Cases.md`. |
| T5 | Test execution 08 to 17 October, UAT 19 to 22 October, summary report 23 October. | Tests were written with each story during the sprints (19 October to 2 November). System validation and the reports are dated 20 November. | The test plan schedule was written before the sprint dates were fixed. |
| T6 | Penetration testing of authentication, TLS 1.2+ verification. | Injection and input validation, RBAC, lockout, session and password-storage tests (TC-Sec-02 to 06). No penetration test, no TLS check. | No deployed environment (R4). |
| T7 | Defect tracking in Jira; defect density and ageing metrics. | Defects found in system validation are listed in the System Validation Report (D-01, D-02). Density and ageing were not measured. | Few defects were logged, too few for the metrics to mean anything. |

## 4. Process (deliverables Part 2 and Part 3)

| # | Asked for | What was done | Why |
|---|---|---|---|
| P1 | Backlog as a GitHub Project linked to the repo. | The backlog, story points and sprints are in Jira (project BLOOD, link in the README). Branches, commits and pull requests carry the Jira key. | The team was already using Jira from the SRS stage. |
| P2 | Sprint 1: 19 to 23 October. Sprint 2: 26 to 30 October. | Sprint 1 stories were merged between 19 and 26 October. Sprint 2 stories (CI, wiring, frontend, low-stock alerts, emergency call-out) were merged between 30 October and 2 November. | Spill-over of a few days in each sprint. |
| P3 | Development frozen after Sprint 2. | One more pull request was merged on 12 November: actions on the role dashboards (approve, dispatch, book a slot and so on), with its own integration tests. Until then the dashboards were read-only. | Needed for a usable demo. No backend rule changed. |
| P4 | Testing and reports: 2 to 6 November. | Reports generated on 20 November. | Late. |
