# System Validation Report

Blood Bank & Donation Management System (BBMS), Team T9.

## 1. Purpose and scope

This report shows whether the finished system does what the SRS (v1.0) asks for. Each system
test starts the real backend server, creates accounts the way a user would, and checks the
acceptance criterion of one or more SRS requirements over HTTP, exactly as the React frontend
calls it. Database checks are used where the SRS asks for one ("DB check confirms passwords
are hashed").

In scope: all 15 functional requirements (BBS-F-001 to BBS-F-042), the non-functional
requirements BBS-NF-001, 002, 003 and 005, the security requirements BBS-SR-002 to 005, the
security validation points in section 5.1 of the test plan, and the two Sprint 2 additions
(low-stock alerts, emergency donor call-out).

Not in scope of this run: see section 5.

## 2. Method

- Test cases: ST-01 to ST-18, described in `docs/Test_Cases.md`, automated in
  `tests/system/test_system_validation.py`.
- Each test gets a new server process (`uvicorn src.backend.main:app`) with an empty SQLite
  database, so tests cannot affect each other.
- The first admin is created the way the `create-admin` command does it. Staff and hospital
  accounts are then created by that admin through the API. Donors sign up through the API and
  verify with the OTP that the development notifier writes to the server log.
- Time-dependent behaviour is tested without waiting: a unit's expiry date is moved into the
  past in the database (ST-08) and the session timeout is set to 4 seconds for ST-15, as the
  test plan's risk table recommends.
- The section below is rewritten by `python scripts/generate_test_reports.py` on every run.

## 3. Results

<!-- results:begin -->
- Date of run: 20-11-2026 14:00
- Code under test: branch `feature/test-reports-docs`, commit `1841697` plus uncommitted changes
- Python 3.14.8 on Linux, pytest 8.4.2, coverage.py 7.16.2
- Database: SQLite, a new empty database for every test
- Produced by `python scripts/generate_test_reports.py`
- System under test: `uvicorn src.backend.main:app` started as its own process for each test,
  driven over HTTP

| Suite | Tests | Passed | Failed | Skipped | Time |
|---|---|---|---|---|---|
| System | 18 | 18 | 0 | 0 | 25.4 s |

| ID | Requirement | What is validated | Result |
|---|---|---|---|
| ST-01 | BBS-NF-002 | the running server answers health checks and serves its API docs. | PASS |
| ST-02 | BBS-F-001, AC-001 | Donor, Hospital Rep, Staff and Admin log in; each is told its own role. | PASS |
| ST-03 | BBS-F-002, AC-002 | an unverified donor cannot log in; a wrong code is refused. | PASS |
| ST-04 | BBS-F-003, AC-003 | after 5 wrong attempts even the right password is refused. | PASS |
| ST-05 | BBS-F-010, AC-010 | the profile is not saved while a required field is missing or empty. | PASS |
| ST-06 | BBS-F-011, BBS-F-012, AC-011, AC-012 | a donation 30 days ago makes the donor not yet eligible, shows in their history, and adds a Whole Blood bag to stock. | PASS |
| ST-07 | BBS-F-020, BBS-F-021, AC-020, AC-021 | every bag has a unique, searchable ID and its expiry date is filled in from the component type. | PASS |
| ST-08 | BBS-F-022, BBS-SR-004, AC-022 | an expired unit is not in available stock, and marking it expired is logged with user and timestamp. | PASS |
| ST-09 | BBS-F-030, BBS-F-031, BBS-F-032, BBS-SR-004, AC-030..032 | a submitted request shows in the staff queue, only compatible units are suggested (never B- for A+), and approving then dispatching moves it to 'Dispatched' with an audit trail. | PASS |
| ST-10 | BBS-F-040, BBS-F-041, AC-040, AC-041 | a drive without slots is refused; donors see upcoming drives and book; a full slot refuses the next donor. | PASS |
| ST-11 | BBS-F-042, AC-042 | a donor booked on a slot in the next 24 hours is reminded once; a booking further away is not reminded yet. | PASS |
| ST-12 | BLOOD-25, BLOOD-26 (Sprint 2 additions) | staff see low and out-of-stock groups and can call out compatible donors. | PASS |
| ST-13 | BBS-SR-003, test plan 5.1 RBAC | a donor is blocked from staff and admin actions, a hospital cannot change inventory or see another hospital's requests, and nothing works without logging in. | PASS |
| ST-14 | BBS-NF-003, BBS-SR-002 | database inspection finds Argon2 hashes, no plain-text passwords, signup codes or session tokens; the API never returns a password. | PASS |
| ST-15 | BBS-SR-005 | a token stops working after logout, and after the idle timeout (set to 4 seconds for this run) the user has to log in again. | PASS |
| ST-16 | test plan 5.1 input validation | SQL injection and script payloads never cause a server error, never bypass login and never damage data. | PASS |
| ST-17 | BBS-NF-001 | with 300 units in stock, the inventory list and a unit lookup each answer in under 2 seconds. | PASS |
| ST-18 | BBS-NF-005 | two staff members approve two requests for the last unit at the same moment; exactly one succeeds, in every one of 10 rounds. | PASS |

Response times measured in ST-17 (300 units in stock, 20 calls each, limit 2000 ms):

| Call | Median | Slowest |
|---|---|---|
| List available stock `GET /api/inventory/bags` | 2.2 ms | 5.5 ms |
| Look up one unit `GET /api/inventory/bags/{unit_id}` | 1.1 ms | 1.8 ms |

Failures:

None. Every test passed.
<!-- results:end -->

## 4. Requirement validation matrix

The status of a requirement is the result of the system tests listed for it in section 3.

| Requirement | Summary | Acceptance criterion | Validated by |
|---|---|---|---|
| BBS-F-001 | Login for four roles | AC-001: each role gets its own dashboard | ST-02 |
| BBS-F-002 | OTP at signup | AC-002: signup completes only after the correct OTP | ST-03 |
| BBS-F-003 | Lock after 5 wrong passwords | AC-003: 6th attempt is refused for 30 minutes | ST-04 (see O-1) |
| BBS-F-010 | Donor profile | AC-010: save fails if a required field is empty | ST-05 |
| BBS-F-011 | Eligibility rules | AC-011: donated 30 days ago means not yet eligible | ST-06 |
| BBS-F-012 | Donation history | AC-012: new donation appears in the history | ST-06 |
| BBS-F-020 | Unique bag ID | AC-020: each ID is searchable and shows its details | ST-07 |
| BBS-F-021 | Component and expiry date | AC-021: expiry is filled in from the component | ST-07 |
| BBS-F-022 | Expired units leave stock | AC-022: expired unit not in available stock | ST-08 |
| BBS-F-030 | Hospital submits a request | AC-030: request appears in the staff queue | ST-09 |
| BBS-F-031 | Compatible units suggested | AC-031: A+ request never suggests a B- unit | ST-09 |
| BBS-F-032 | Approve and dispatch | AC-032: status becomes Dispatched | ST-09 |
| BBS-F-040 | Create a drive | AC-040: no drive without at least one slot | ST-10 |
| BBS-F-041 | View drives, book a slot | AC-041: a full slot cannot be booked | ST-10 |
| BBS-F-042 | Reminder before the slot | AC-042: reminder sent before the slot time | ST-11 |
| BBS-NF-001 | Inventory search under 1-2 s | Measured response time | ST-17 |
| BBS-NF-002 | Availability | No unplanned downtime during testing | ST-01 (health check only) |
| BBS-NF-003 | Passwords and details stored securely | DB check: passwords hashed | ST-14 |
| BBS-NF-004 | Usable without training | A test user completes a task without help | Not validated (section 5) |
| BBS-NF-005 | No double allocation | Only one of two simultaneous allocations succeeds | ST-18 |
| BBS-SR-001 | Login over HTTPS | Site only reachable over HTTPS | Not validated (section 5) |
| BBS-SR-002 | Passwords hashed | DB inspection | ST-14 |
| BBS-SR-003 | Donor blocked from staff/admin actions | Donor login blocked from staff pages | ST-13 |
| BBS-SR-004 | Key actions logged with user and time | Log entry for approve and expire | ST-08, ST-09 |
| BBS-SR-005 | Session expires after inactivity | Session times out | ST-15 |
| Test plan 5.1 | Input validation, injection | No server error, no bypass | ST-16 |
| BLOOD-25 | Low-stock alerts (Sprint 2) | Low and out-of-stock groups listed | ST-12 |
| BLOOD-26 | Emergency donor call-out (Sprint 2) | Compatible donors selected | ST-12 (see D-01) |

## 5. Not validated in this run

| Item | Why | What is needed |
|---|---|---|
| BBS-SR-001 HTTPS | The project runs locally over plain HTTP; there is no deployed site with a certificate. | Deploy behind HTTPS and repeat ST-02 against it. |
| BBS-NF-004 Usability (TC-UX-01) | Needs a person who has not seen the system. Not something an automated test can show. | One donor and one hospital user complete signup and a request unaided; record the outcome. |
| Browser UI | The system tests call the API directly. The React dashboards were not driven through a browser (Selenium was planned, see `docs/Deviations.md`). The frontend production build succeeds, and the requests each dashboard form sends are covered by `tests/integration/test_dashboard_actions_api.py`. | Manual walkthrough of the four dashboards, or browser automation. |
| Real SMS / email | OTPs and reminders go to the server log (`LoggingNotifier`). No provider is connected. | Connect a provider and repeat ST-03 and ST-11. |
| PostgreSQL | All tests use SQLite. | Repeat the suites with `DATABASE_URL` pointing at PostgreSQL. |
| Load with many concurrent users | ST-17 measures one user with 300 units; ST-18 covers two simultaneous allocations. No JMeter load run was done. | Load test if the system is deployed for real use. |
| Availability over time (BBS-NF-002) | Only a health check; nobody measured uptime over the demo period. | Record uptime during the demo. |

## 6. Defects and observations

Found while preparing and running these tests.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| D-01 | Medium | Emergency call-out (BLOOD-26) | `POST /api/donors/emergency-callout` reports how many donors were notified, but no message is sent or logged. `send_notification` in `src/backend/donor/service.py` looks for a `send`, `notify` or `send_notification` method on `LoggingNotifier`, which has none, so it silently does nothing. The existing tests replace `send_notification` with a mock, so they pass. | Open |
| D-02 | Low | Emergency call-out (BLOOD-26) | The response field is named `eligible_donors_notified`, but the call-out selects every donor with a compatible blood group. It does not check eligibility (weight, age, 56-day gap). | Open |
| O-1 | Low | Login (BBS-F-003) | A locked account gets the same "Invalid email or password." reply as a wrong password, not the 'account locked' message in AC-003. This is deliberate (it does not reveal which emails exist) and is listed in `docs/Deviations.md`. | Accepted deviation |
| O-2 | Low | Drives (BBS-F-041) | Found by reading the code, not reproduced: the list of upcoming drives compares against the server's local date, while slot times are checked in UTC. On a server whose clock is not UTC, a drive can drop off the list a few hours early around midnight. Not visible in CI (UTC). | Open |

No defect was found in the 15 SRS functional requirements.

## 7. Conclusion

SRS section 6 sets the exit criteria: all High-priority functional requirements implemented
and verified, and no critical non-functional failure.

- All High-priority functional requirements (BBS-F-001, 002, 010, 011, 012, 020, 021, 022,
  030, 031) have a system test; the Medium and Low ones do too. Their results are in section 3.
- The High-priority non-functional requirements BBS-NF-001, 003 and 005 have a system test.
- BBS-SR-001 (HTTPS, High) is not validated, because the system is not deployed. This is the
  one High-priority item left open, together with the manual usability check.
- D-01 should be fixed before the emergency call-out is shown as working in a demo.
