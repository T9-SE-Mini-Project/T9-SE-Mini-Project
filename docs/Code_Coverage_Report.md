# Code Coverage Report

Blood Bank & Donation Management System (BBMS), Team T9.

Statement (line) coverage of the backend, `src/backend`, measured with coverage.py while
the unit and integration tests run. Branch coverage is in the Branch Coverage Report.

## 1. Test run

- Date of run: 20-11-2026 14:00
- Code under test: branch `feature/test-reports-docs`, commit `1841697` plus uncommitted changes
- Python 3.14.8 on Linux, pytest 8.4.2, coverage.py 7.16.2
- Database: SQLite, a new empty database for every test
- Produced by `python scripts/generate_test_reports.py`

## 2. Summary

| Tests run | Statements | Covered | Missed | Statement coverage |
|---|---|---|---|---|
| Unit tests only | 1820 | 1035 | 785 | 56.9% |
| Unit + integration | 1820 | 1715 | 105 | **94.2%** |

The rest of this report uses the unit + integration figures.

## 3. Coverage by module

| Module | Statements | Covered | Statement coverage |
|---|---|---|---|
| `(app: main, cli, config, ...)` | 248 | 227 | 91.5% |
| `auth` | 391 | 361 | 92.3% |
| `donor` | 321 | 283 | 88.2% |
| `drives` | 214 | 208 | 97.2% |
| `hospital_requests` | 456 | 451 | 98.9% |
| `inventory` | 190 | 185 | 97.4% |

## 4. Coverage by file

Files with nothing to execute (empty `__init__.py`) are left out.

| File | Statements | Missed | Coverage | Lines not executed |
|---|---|---|---|---|
| `src/backend/auth/accounts.py` | 30 | 4 | 86.7% | 41, 58-60 |
| `src/backend/auth/admin_routes.py` | 20 | 0 | 100.0% |  |
| `src/backend/auth/dependencies.py` | 27 | 1 | 96.3% | 45 |
| `src/backend/auth/models.py` | 15 | 3 | 80.0% | 21, 23, 26 |
| `src/backend/auth/orm.py` | 26 | 0 | 100.0% |  |
| `src/backend/auth/otp.py` | 12 | 2 | 83.3% | 16, 23 |
| `src/backend/auth/permissions.py` | 10 | 2 | 80.0% | 16, 19 |
| `src/backend/auth/repository.py` | 13 | 1 | 92.3% | 25 |
| `src/backend/auth/routes.py` | 33 | 0 | 100.0% |  |
| `src/backend/auth/security.py` | 12 | 1 | 91.7% | 13 |
| `src/backend/auth/service.py` | 38 | 1 | 97.4% | 28 |
| `src/backend/auth/sessions.py` | 44 | 6 | 86.4% | 21, 28, 41, 56-58 |
| `src/backend/auth/signup.py` | 79 | 8 | 89.9% | 37, 70-71, 85, 108, 128-130 |
| `src/backend/auth/signup_routes.py` | 32 | 1 | 96.9% | 55 |
| `src/backend/blood.py` | 26 | 0 | 100.0% |  |
| `src/backend/cli.py` | 53 | 15 | 71.7% | 51-60, 62-63, 65-66, 76 |
| `src/backend/config.py` | 25 | 2 | 92.0% | 39-40 |
| `src/backend/database.py` | 31 | 2 | 93.5% | 31, 33 |
| `src/backend/demo.py` | 53 | 0 | 100.0% |  |
| `src/backend/donor/__init__.py` | 3 | 0 | 100.0% |  |
| `src/backend/donor/donations.py` | 37 | 3 | 91.9% | 64, 69, 71 |
| `src/backend/donor/eligibility.py` | 69 | 0 | 100.0% |  |
| `src/backend/donor/models.py` | 25 | 0 | 100.0% |  |
| `src/backend/donor/profile_routes.py` | 29 | 0 | 100.0% |  |
| `src/backend/donor/routes.py` | 73 | 19 | 74.0% | 72-73, 88-91, 104-105, 112-115, 119-121, 136-138, 143 |
| `src/backend/donor/service.py` | 85 | 16 | 81.2% | 32-37, 104, 111, 117, 121-122, 124, 141-143, 150 |
| `src/backend/drives/__init__.py` | 2 | 0 | 100.0% |  |
| `src/backend/drives/models.py` | 34 | 0 | 100.0% |  |
| `src/backend/drives/routes.py` | 31 | 0 | 100.0% |  |
| `src/backend/drives/schemas.py` | 54 | 0 | 100.0% |  |
| `src/backend/drives/service.py` | 93 | 6 | 93.5% | 35, 83-85, 117, 126 |
| `src/backend/hospital_requests/__init__.py` | 4 | 0 | 100.0% |  |
| `src/backend/hospital_requests/compatibility.py` | 3 | 0 | 100.0% |  |
| `src/backend/hospital_requests/config.py` | 8 | 0 | 100.0% |  |
| `src/backend/hospital_requests/cross_match.py` | 15 | 0 | 100.0% |  |
| `src/backend/hospital_requests/models.py` | 72 | 0 | 100.0% |  |
| `src/backend/hospital_requests/orm.py` | 40 | 0 | 100.0% |  |
| `src/backend/hospital_requests/repository.py` | 56 | 3 | 94.6% | 86-88 |
| `src/backend/hospital_requests/routes.py` | 79 | 2 | 97.5% | 126-127 |
| `src/backend/hospital_requests/schemas.py` | 58 | 0 | 100.0% |  |
| `src/backend/hospital_requests/service.py` | 121 | 0 | 100.0% |  |
| `src/backend/inventory/__init__.py` | 3 | 0 | 100.0% |  |
| `src/backend/inventory/cross_match.py` | 49 | 4 | 91.8% | 34, 57, 76, 92 |
| `src/backend/inventory/low_stock.py` | 18 | 0 | 100.0% |  |
| `src/backend/inventory/models.py` | 28 | 0 | 100.0% |  |
| `src/backend/inventory/routes.py` | 53 | 1 | 98.1% | 67 |
| `src/backend/inventory/service.py` | 39 | 0 | 100.0% |  |
| `src/backend/main.py` | 51 | 0 | 100.0% |  |
| `src/backend/notifications.py` | 9 | 2 | 77.8% | 23, 26 |

## 5. What is not covered

- `cli.py`: the `create-admin` command reads a password from the terminal and the `__main__`
  entry point; `expire-units`, `send-reminders` and `seed-demo` call services that are tested
  directly.
- `donor/service.py`, `donor/routes.py`: the body of the emergency call-out is replaced by a
  mock in its tests, and some input-validation error paths are not exercised.
- `auth/sessions.py`, `auth/models.py`, `auth/permissions.py`: defensive checks for values the
  API layer already rejects (empty token, unknown role, invalid user ID).
- The React frontend (`src/frontend`) is not measured. It is checked by the production build
  in CI and by the dashboard-action integration tests that send the same requests.

## 6. How to reproduce

```bash
python -m pytest tests/unit tests/integration --cov=src/backend --cov-branch --cov-report=term-missing
```

Line-by-line view: open `docs/coverage_html/index.html` in a browser. Raw data: `docs/raw/coverage_report.xml`.
