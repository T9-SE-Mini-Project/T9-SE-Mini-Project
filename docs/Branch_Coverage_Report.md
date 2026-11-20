# Branch Coverage Report

Blood Bank & Donation Management System (BBMS), Team T9.

Branch coverage of the backend, `src/backend`, measured with coverage.py (`--cov-branch`)
while the unit and integration tests run. Every `if`, loop and `try` has two or more exits
(branches); a branch is covered when a test takes it. A *partial* decision is one where a
test took one exit but no test took the other.

## 1. Test run

- Date of run: 20-11-2026 14:00
- Code under test: branch `feature/test-reports-docs`, commit `1841697` plus uncommitted changes
- Python 3.14.8 on Linux, pytest 8.4.2, coverage.py 7.16.2
- Database: SQLite, a new empty database for every test
- Produced by `python scripts/generate_test_reports.py`

## 2. Summary

| Tests run | Branches | Covered | Missed | Partial decisions | Branch coverage |
|---|---|---|---|---|---|
| Unit tests only | 292 | 144 | 148 | 14 | 49.3% |
| Unit + integration | 292 | 239 | 53 | 43 | **81.8%** |

Statement and branch coverage together: 92.5%.
The rest of this report uses the unit + integration figures.

## 3. Branch coverage by module

| Module | Branches | Covered | Branch coverage |
|---|---|---|---|
| `(app: main, cli, config, ...)` | 48 | 37 | 77.1% |
| `auth` | 82 | 62 | 75.6% |
| `donor` | 70 | 56 | 80.0% |
| `drives` | 16 | 14 | 87.5% |
| `hospital_requests` | 40 | 39 | 97.5% |
| `inventory` | 36 | 31 | 86.1% |

## 4. Branch coverage by file

Files without any branch are left out. A missed branch is written `from line -> to line`;
`exit` means leaving the function.

| File | Branches | Missed | Partial | Coverage | Branches not taken |
|---|---|---|---|---|---|
| `src/backend/auth/accounts.py` | 12 | 1 | 1 | 91.7% | 40 -> 41 |
| `src/backend/auth/dependencies.py` | 4 | 1 | 1 | 75.0% | 44 -> 45 |
| `src/backend/auth/models.py` | 8 | 3 | 3 | 62.5% | 20 -> 21, 22 -> 23, 25 -> 26 |
| `src/backend/auth/otp.py` | 4 | 2 | 2 | 50.0% | 15 -> 16, 22 -> 23 |
| `src/backend/auth/permissions.py` | 6 | 2 | 2 | 66.7% | 15 -> 16, 18 -> 19 |
| `src/backend/auth/security.py` | 2 | 1 | 1 | 50.0% | 12 -> 13 |
| `src/backend/auth/service.py` | 14 | 1 | 1 | 92.9% | 27 -> 28 |
| `src/backend/auth/sessions.py` | 12 | 5 | 5 | 58.3% | 20 -> 21, 27 -> 28, 40 -> 41, 50 -> 56, 71 -> exit |
| `src/backend/auth/signup.py` | 20 | 4 | 4 | 80.0% | 36 -> 37, 84 -> 85, 107 -> 108, 117 -> 121 |
| `src/backend/blood.py` | 10 | 0 | 0 | 100.0% |  |
| `src/backend/cli.py` | 16 | 8 | 6 | 50.0% | 45 -> 47, 50 -> 51, 52 -> 53, 52 -> 55, 61 -> 62, 64 -> 65, 67 -> 72, 75 -> 76 |
| `src/backend/config.py` | 2 | 0 | 0 | 100.0% |  |
| `src/backend/database.py` | 4 | 2 | 2 | 50.0% | 26 -> 33, 29 -> 31 |
| `src/backend/demo.py` | 14 | 0 | 0 | 100.0% |  |
| `src/backend/donor/donations.py` | 10 | 1 | 1 | 90.0% | 63 -> 64 |
| `src/backend/donor/eligibility.py` | 22 | 0 | 0 | 100.0% |  |
| `src/backend/donor/profile_routes.py` | 2 | 0 | 0 | 100.0% |  |
| `src/backend/donor/routes.py` | 2 | 2 | 0 | 0.0% | 137 -> 138, 137 -> 143 |
| `src/backend/donor/service.py` | 34 | 11 | 5 | 67.6% | 32 -> 33, 32 -> 34, 34 -> 35, 34 -> 36, 36 -> exit, 36 -> 37, 103 -> 104, 110 -> 111, 112 -> 117, 123 -> 124, 149 -> 150 |
| `src/backend/drives/schemas.py` | 6 | 0 | 0 | 100.0% |  |
| `src/backend/drives/service.py` | 10 | 2 | 2 | 80.0% | 116 -> 117, 125 -> 126 |
| `src/backend/hospital_requests/repository.py` | 4 | 0 | 0 | 100.0% |  |
| `src/backend/hospital_requests/routes.py` | 4 | 0 | 0 | 100.0% |  |
| `src/backend/hospital_requests/service.py` | 32 | 1 | 1 | 96.9% | 245 -> exit |
| `src/backend/inventory/cross_match.py` | 14 | 4 | 4 | 71.4% | 33 -> 34, 56 -> 57, 75 -> 76, 91 -> 92 |
| `src/backend/inventory/low_stock.py` | 8 | 0 | 0 | 100.0% |  |
| `src/backend/inventory/routes.py` | 2 | 1 | 1 | 50.0% | 66 -> 67 |
| `src/backend/inventory/service.py` | 12 | 0 | 0 | 100.0% |  |
| `src/backend/main.py` | 2 | 1 | 1 | 50.0% | 58 -> 60 |

10 of the 29 files that contain branches have every branch covered.

## 5. How to reproduce

```bash
python -m pytest tests/unit tests/integration --cov=src/backend --cov-branch --cov-report=term-missing
```

In `docs/coverage_html/index.html`, partially covered decisions are highlighted in yellow.
