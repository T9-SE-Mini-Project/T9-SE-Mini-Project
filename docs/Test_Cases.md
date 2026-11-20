# Test Case Document

Blood Bank & Donation Management System (BBMS), Team T9.
Version 2.0, 20-11-2026. Updates the test cases named in Test Plan v1.0 (section 13) after
Sprint 1 and Sprint 2.

## 1. What changed since Test Plan v1.0

| Change | Reason |
|---|---|
| Test case IDs now follow the SRS: `TC-Donor-xx` and `TC-Hosp-xx`. The test plan wrote `TC-Don-xx` and `TC-HR-xx` for the same cases. | The SRS and the test plan used different IDs for the same test case. The SRS IDs are kept because every requirement row refers to them. |
| Every SRS requirement now has a written test case. The test plan listed seven example IDs only. | Part 1 and Part 3 of the deliverables ask for the full set. |
| `TC-Sec-01` was used twice in the SRS (BBS-NF-003 and BBS-SR-001). BBS-NF-003 is now covered by `TC-Sec-02` together with BBS-SR-002, which asks for the same check. | Duplicate ID. |
| The SRS traceability matrix names `BBS-F-023` and `BBS-NF-006`, which are not defined anywhere in the SRS. They are read as BBS-F-022 (expired units) and BBS-NF-005 (no double allocation). | Numbering slip in the SRS matrix. |
| New: `TC-Inv-04` (low-stock alerts, BLOOD-25), `TC-Donor-04` (emergency call-out, BLOOD-26), `TC-Auth-04` (admin creates accounts), `TC-Sec-06` (input validation), `TC-Avail-01`. | Features added in Sprint 2, and test plan section 5.1. |
| Test cases are automated with pytest and httpx. The test plan named Selenium, Postman and JMeter. | See `docs/Deviations.md`. |
| The response-time limit is 2 seconds (SRS BBS-NF-001). The test plan said 5 seconds. | The SRS is the stricter, authoritative figure. |

## 2. Summary and traceability

Type: F = functional, NF = non-functional, S = security. "System test" is the ST case in
`tests/system/test_system_validation.py`; results of every run are in
`docs/System_Validation_Report.md` and `docs/Unit_Test_Report.md`.

| Test case | Requirement | Type | Title | System test | Result (20-11-2026) |
|---|---|---|---|---|---|
| TC-Auth-01 | BBS-F-001 | F | Four roles log in | ST-02 | Pass |
| TC-Auth-02 | BBS-F-002 | F | Signup needs the correct OTP | ST-03 | Pass |
| TC-Auth-03 | BBS-F-003 | F | Lock after five wrong passwords | ST-04 | Pass |
| TC-Auth-04 | BBS-F-001 | F | Admin creates staff and hospital accounts | ST-02 | Pass |
| TC-Donor-01 | BBS-F-010 | F | Profile needs every required field | ST-05 | Pass |
| TC-Donor-02 | BBS-F-011 | F | Eligibility rules | ST-06 | Pass |
| TC-Donor-03 | BBS-F-012 | F | Donation appears in history | ST-06 | Pass |
| TC-Donor-04 | BLOOD-26 | F | Emergency donor call-out | ST-12 | Pass, with defect D-01 |
| TC-Inv-01 | BBS-F-020 | F | Unique, searchable bag ID | ST-07 | Pass |
| TC-Inv-02 | BBS-F-021 | F | Expiry date from component type | ST-07 | Pass |
| TC-Inv-03 | BBS-F-022 | F | Expired unit leaves available stock | ST-08 | Pass |
| TC-Inv-04 | BLOOD-25 | F | Low-stock alerts | ST-12 | Pass |
| TC-Hosp-01 | BBS-F-030 | F | Request reaches the staff queue | ST-09 | Pass |
| TC-Hosp-02 | BBS-F-031 | F | Only compatible units are suggested | ST-09 | Pass |
| TC-Hosp-03 | BBS-F-032 | F | Approve and dispatch | ST-09 | Pass |
| TC-Drive-01 | BBS-F-040 | F | Drive needs at least one slot | ST-10 | Pass |
| TC-Drive-02 | BBS-F-041 | F | Full slot cannot be booked | ST-10 | Pass |
| TC-Drive-03 | BBS-F-042 | F | Reminder before the slot | ST-11 | Pass |
| TC-Perf-01 | BBS-NF-001 | NF | Inventory search under 2 seconds | ST-17 | Pass |
| TC-Avail-01 | BBS-NF-002 | NF | Server is up and healthy | ST-01 | Pass |
| TC-UX-01 | BBS-NF-004 | NF | Usable without training | none (manual) | Not executed |
| TC-Conc-01 | BBS-NF-005 | NF | No double allocation | ST-18 | Pass |
| TC-Sec-01 | BBS-SR-001 | S | Login only over HTTPS | none | Not executed |
| TC-Sec-02 | BBS-SR-002, BBS-NF-003 | S | Passwords stored hashed | ST-14 | Pass |
| TC-Sec-03 | BBS-SR-003 | S | Role-based access is enforced | ST-13 | Pass |
| TC-Sec-04 | BBS-SR-004 | S | Key actions are logged | ST-08, ST-09 | Pass |
| TC-Sec-05 | BBS-SR-005 | S | Session ends after inactivity | ST-15 | Pass |
| TC-Sec-06 | Test plan 5.1 | S | Malicious input is rejected | ST-16 | Pass |

28 test cases: 18 functional, 4 non-functional, 6 security (TC-Sec-02 also covers the
non-functional BBS-NF-003). 26 executed and passed, 2 not executed.

## 3. Test cases

Common precondition: the backend is running with an empty database and one admin account.
"Staff" means a Blood Bank Staff account, "hospital" a Hospital Rep account.

### Authentication and roles

**TC-Auth-01: Four roles log in** (BBS-F-001, AC-001)
- Precondition: one account for each role exists.
- Steps: 1. Log in as each role. 2. Ask the system who is logged in (`GET /api/auth/me`). 3. Log in as admin with a wrong password.
- Expected: each login succeeds and reports its own role (and hospital for the hospital rep), which is what the frontend uses to pick the dashboard. The wrong password is refused with 401.
- Also covered by: `tests/integration/test_auth_api.py`.

**TC-Auth-02: Signup needs the correct OTP** (BBS-F-002, AC-002)
- Steps: 1. Sign up as a new donor. 2. Try to log in before verifying. 3. Verify with a wrong code. 4. Verify with the code that was sent. 5. Log in. 6. Sign up again with the same email.
- Expected: login is refused in step 2 and still refused after step 3. The correct code is accepted and login works. The second signup is refused with 409.
- Also covered by: `tests/integration/test_signup_api.py`, `test_signup_rules.py` (code expiry, five wrong codes, delivery failure).

**TC-Auth-03: Lock after five wrong passwords** (BBS-F-003, AC-003)
- Steps: 1. Log in to one account with a wrong password five times. 2. Log in with the correct password. 3. Check the lock time in the database. 4. Log in to a different account.
- Expected: the sixth attempt is refused even with the correct password. The account is locked for 30 minutes. Other accounts are not affected.
- Note: the reply is the general "Invalid email or password." message, not 'account locked' (see `docs/Deviations.md`).
- Also covered by: `tests/integration/test_account_lockout.py` (lock expiry, counter reset after a successful login).

**TC-Auth-04: Admin creates staff and hospital accounts** (BBS-F-001)
- Steps: 1. As admin, create a staff account, a hospital account with a hospital ID, and another admin. 2. Log in as each. 3. Try to create a donor, a hospital rep without a hospital, and a duplicate email. 4. Try the same call as staff.
- Expected: the three accounts can log in with their role. The invalid ones are refused with 400 or 422. Staff get 403.
- Covered by: `tests/integration/test_admin_accounts_api.py`; ST-02 uses it to set up accounts.

### Donor

**TC-Donor-01: Profile needs every required field** (BBS-F-010, AC-010)
- Precondition: a verified donor without a profile.
- Steps: 1. Save the profile five times, each time leaving out one of name, blood group, date of birth, weight, phone. 2. Save it with an empty name. 3. Save a complete profile. 4. Read it back.
- Expected: steps 1 and 2 are refused with 422 and nothing is saved. Step 3 succeeds and step 4 returns the same data.
- Also covered by: `tests/integration/test_donor_profile_api.py`.

**TC-Donor-02: Eligibility rules** (BBS-F-011, AC-011)
- Precondition: a donor aged 18 to 65, weight 68 kg, no donations.
- Steps: 1. Check eligibility. 2. Staff record a completed donation dated 30 days ago. 3. Check eligibility again. 4. Staff try to record another donation today. 5. Check a donor weighing 44 kg and a donor aged 17.
- Expected: eligible in step 1. Not eligible in step 3, with the next eligible date 56 days after the donation. Step 4 is refused with 409. Both donors in step 5 are not eligible.
- Also covered by: `tests/unit/test_eligibility_check.py` (boundaries: exactly 45 kg, ages 18 and 65, day 55 and day 56).

**TC-Donor-03: Donation appears in history** (BBS-F-012, AC-012)
- Steps: 1. Staff record a 450 ml donation for a donor. 2. The donor opens their history. 3. Staff look up the bag ID returned in step 1.
- Expected: the history shows the donation with date, quantity and status. A Whole Blood bag with the donor's blood group is in inventory.
- Also covered by: `tests/unit/test_donation_history.py`, `test_record_donation.py`.

**TC-Donor-04: Emergency donor call-out** (BLOOD-26, added in Sprint 2)
- Precondition: one O- donor and one AB+ donor with profiles.
- Steps: 1. Staff trigger a call-out for 2 units of O- at "City Hospital". 2. Trigger one for blood type "Z+". 3. A donor tries to trigger one.
- Expected: only the O- donor is selected. "Z+" is refused with 400. The donor gets 403.
- Open defect D-01: the selected donors are counted but no message is sent (`docs/System_Validation_Report.md`, section 6).
- Also covered by: `tests/unit/test_emergency_callout.py`, `tests/integration/test_emergency_callout_api.py`.

### Inventory

**TC-Inv-01: Unique, searchable bag ID** (BBS-F-020, AC-020)
- Steps: 1. Staff log 12 bags. 2. Look up each by its ID. 3. Look up an ID that does not exist.
- Expected: all 12 IDs are different. Each lookup returns that bag's details. The unknown ID gives 404.
- Also covered by: `tests/unit/test_inventory_blood12.py`.

**TC-Inv-02: Expiry date from component type** (BBS-F-021, AC-021)
- Steps: 1. Log bags of Whole Blood, RBC, Platelets and Plasma collected yesterday.
- Expected: expiry is collection date plus 35, 42, 5 and 365 days respectively, without staff entering it.
- Also covered by: `tests/unit/test_inventory_blood13.py`.

**TC-Inv-03: Expired unit leaves available stock** (BBS-F-022, AC-022)
- Steps: 1. Log a fresh Platelets bag and one collected 10 days ago. 2. Move another bag's expiry date to yesterday in the database. 3. List available stock. 4. Run the expiry check.
- Expected: the 10-day-old bag is saved as EXPIRED. Available stock lists only the fresh bag. The expiry check marks the one remaining bag EXPIRED.
- Also covered by: `tests/unit/test_inventory_blood14.py`.

**TC-Inv-04: Low-stock alerts** (BLOOD-25, added in Sprint 2)
- Precondition: 3 O- RBC and 2 A+ RBC units in stock.
- Steps: 1. Staff request low-stock alerts with threshold 2. 2. A donor requests them.
- Expected: A+ RBC is LOW_STOCK with 2 units, empty groups are OUT_OF_STOCK, O- RBC is not listed. The donor gets 403.
- Also covered by: `tests/unit/test_low_stock.py`, `tests/integration/test_low_stock_api.py`.

### Hospital requests

**TC-Hosp-01: Request reaches the staff queue** (BBS-F-030, AC-030)
- Steps: 1. Hospital submits a request for 2 units of A+ RBC. 2. Staff open the pending queue.
- Expected: the request is in the queue with status PENDING.
- Also covered by: `tests/unit/test_submit_blood_request.py` (quantity limit, required-by date, unknown fields).

**TC-Hosp-02: Only compatible units are suggested** (BBS-F-031, AC-031)
- Precondition: one A+, one O- and one B- RBC unit in stock; a pending A+ request for 2 units.
- Steps: 1. Staff preview the matches for the request.
- Expected: the A+ and O- units are suggested. The B- unit is never suggested.
- Also covered by: `tests/unit/test_compatibility.py` (every blood group and component), `test_cross_match.py`.

**TC-Hosp-03: Approve and dispatch** (BBS-F-032, AC-032)
- Steps: 1. Staff approve the request. 2. Staff dispatch it. 3. Hospital opens the request. 4. Submit another request for 2 units when only 1 compatible unit is left and approve it.
- Expected: status goes APPROVED then DISPATCHED, the two units are DISPATCHED and no longer in available stock, the hospital sees DISPATCHED. Step 4 is refused with 409 and the request stays PENDING.
- Also covered by: `tests/unit/test_approve_dispatch.py`, `tests/integration/test_request_dispatch_flow.py`.

### Drives

**TC-Drive-01: Drive needs at least one slot** (BBS-F-040, AC-040)
- Steps: 1. Staff create a drive with location and date but no slots. 2. Create it with one slot.
- Expected: step 1 is refused with 422. Step 2 succeeds.
- Also covered by: `tests/unit/test_drives.py`.

**TC-Drive-02: Full slot cannot be booked** (BBS-F-041, AC-041)
- Precondition: a drive next week with one slot of capacity 1; two eligible donors.
- Steps: 1. The first donor lists upcoming drives. 2. Books the slot. 3. The second donor books the same slot.
- Expected: the drive is listed. The first booking succeeds. The second is refused with 409 "This slot is fully booked."
- Also covered by: `tests/unit/test_drives.py` (double booking, started slot, ineligible donor), `tests/integration/test_dashboard_actions_api.py`.

**TC-Drive-03: Reminder before the slot** (BBS-F-042, AC-042)
- Precondition: one donor booked on a slot 3 hours from now and on another 7 days from now.
- Steps: 1. Admin runs "send reminders". 2. Donor opens their bookings. 3. Admin runs it again.
- Expected: one reminder, for the slot in 3 hours. The later booking has no reminder yet. The second run sends nothing.

### Non-functional

**TC-Perf-01: Inventory search under 2 seconds** (BBS-NF-001)
- Precondition: 300 units in stock.
- Steps: 1. List available stock 20 times. 2. Look up 20 different units by ID. Time every call.
- Expected: the slowest call is under 2 seconds. Measured times are in the System Validation Report.

**TC-Avail-01: Server is up and healthy** (BBS-NF-002)
- Steps: 1. Call the health endpoint. 2. Open the API documentation page.
- Expected: `{"status": "ok"}`, and the documentation lists the auth, donor, inventory, request and drive endpoints.

**TC-UX-01: Usable without training** (BBS-NF-004). Manual, not executed.
- Steps: 1. A person who has not used the system registers as a donor, completes the profile and books a slot. 2. Another submits a hospital request.
- Expected: both finish without help.

**TC-Conc-01: No double allocation** (BBS-NF-005)
- Precondition: one AB- Whole Blood unit; two pending requests for one AB- Whole Blood unit each.
- Steps: 1. Two staff members approve one request each at the same moment. 2. Repeat 10 times with a new unit and new requests.
- Expected: in every round exactly one approval succeeds and gets the unit. The other is refused with 409 and its request stays PENDING.
- Also covered by: `tests/unit/test_inventory_cross_match.py`, `test_cross_match.py`.

### Security

**TC-Sec-01: Login only over HTTPS** (BBS-SR-001). Not executed: the project is not deployed with a certificate.
- Steps: 1. Open the deployed site over `http://`. 2. Open it over `https://`.
- Expected: HTTP is refused or redirected; login works over HTTPS only.

**TC-Sec-02: Passwords stored hashed** (BBS-SR-002, BBS-NF-003)
- Steps: 1. Create two accounts with the same password and start a signup. 2. Read the password and code columns in the database. 3. Search the whole database file for the password and for a session token.
- Expected: both passwords are Argon2 hashes and differ from each other. The signup code is hashed. The plain password and the session token do not appear anywhere in the file. No API reply contains a password.

**TC-Sec-03: Role-based access is enforced** (BBS-SR-003)
- Steps: 1. As a donor, call 11 staff, admin and hospital actions (log a bag, list stock, run expiry, see the queue, approve, dispatch, create an account, create a drive, send reminders, read another donor's history, submit a request). 2. Call them without logging in. 3. As hospital A, change inventory and approve a request. 4. As hospital B, open hospital A's request.
- Expected: 403 for every call in step 1, 401 in step 2, 403 in step 3. Hospital B gets 404 and an empty list.

**TC-Sec-04: Key actions are logged** (BBS-SR-004)
- Steps: 1. Staff approve and dispatch a request. 2. Read the request history. 3. Run the expiry check on an expired unit. 4. Read the inventory audit table.
- Expected: APPROVED and DISPATCHED entries with the staff member's ID and a timestamp. One EXPIRED entry for the unit with the staff member's ID and a timestamp.

**TC-Sec-05: Session ends after inactivity** (BBS-SR-005)
- Precondition: idle timeout set to 4 seconds for the test (15 minutes by default).
- Steps: 1. Log in, log out, use the old token. 2. Log in and make a call every 1.5 seconds. 3. Wait 5.5 seconds and call again. 4. Log in again.
- Expected: the token is refused after logout. It keeps working while in use. After the idle period it is refused with 401 and a new login is needed.

**TC-Sec-06: Malicious input is rejected** (test plan 5.1)
- Steps: 1. Log in with SQL injection text as email and as password. 2. Look up a bag and a request with injection text as the ID. 3. Save a profile whose name contains a `<script>` tag and a `DROP TABLE` statement. 4. Submit a request with an extra `status` field, and one with quantity -5.
- Expected: no login succeeds and no call returns a server error. The name is stored and returned as plain text in JSON and the table still exists. Step 4 is refused with 422.
