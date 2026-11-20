"""Run every test suite and write the test reports in docs/.

    python scripts/generate_test_reports.py

Runs the unit, integration and system tests, measures statement and branch coverage of
src/backend (unit + integration; the system tests run the server in another process),
and writes:

    docs/Unit_Test_Report.md
    docs/System_Validation_Report.md   (results section only; see SYSTEM_NOTES below)
    docs/Code_Coverage_Report.md
    docs/Branch_Coverage_Report.md
    docs/coverage_html/                browsable line-by-line coverage
    docs/raw/                          JUnit XML and coverage XML the reports are built from

The numbers in the reports come from the run, never typed in by hand. The script exits
with a non-zero status if any test fails.
"""
from __future__ import annotations

import ast
import json
import os
import platform
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RAW = DOCS / "raw"
SUITES = ("unit", "integration", "system")

# What each test file covers, shown in the Unit Test Report.
FILE_SCOPE = {
    "test_approve_dispatch": "Approve / reject / dispatch a request (BBS-F-032, BBS-SR-004)",
    "test_compatibility": "Blood group compatibility rules (BBS-F-031)",
    "test_cross_match": "Cross-match and allocation in the request service (BBS-F-031, BBS-NF-005)",
    "test_donation_history": "Donation history (BBS-F-012)",
    "test_drives": "Drives, slot booking, reminders (BBS-F-040, 041, 042)",
    "test_eligibility_check": "Donor eligibility rules (BBS-F-011)",
    "test_emergency_callout": "Emergency donor call-out (BLOOD-26)",
    "test_inventory_blood12": "Unique blood bag IDs (BBS-F-020)",
    "test_inventory_blood13": "Component type and expiry date (BBS-F-021)",
    "test_inventory_blood14": "Automatic expiry and audit (BBS-F-022, BBS-SR-004)",
    "test_inventory_cross_match": "Inventory side of cross-match (BBS-F-031, BBS-NF-005)",
    "test_low_stock": "Low-stock alerts (BLOOD-25)",
    "test_record_donation": "Recording a donation end to end (BBS-F-011, 012, 020)",
    "test_submit_blood_request": "Submitting a hospital request (BBS-F-030)",
    "test_account_lockout": "Account lockout after 5 wrong passwords (BBS-F-003)",
    "test_admin_accounts_api": "Admin creates staff / hospital / admin accounts (BBS-F-001)",
    "test_auth_api": "Login, identity, logout, role checks (BBS-F-001, BBS-SR-003)",
    "test_dashboard_actions_api": "Every write action the React dashboards make",
    "test_demo_seed": "Demo data loads every dashboard",
    "test_donor_profile_api": "Donor profile (BBS-F-010)",
    "test_emergency_callout_api": "Emergency donor call-out API (BLOOD-26)",
    "test_low_stock_api": "Low-stock alerts API (BLOOD-25)",
    "test_request_dispatch_flow": "Request -> cross-match -> dispatch across modules (BBS-F-030..032)",
    "test_signup_api": "Signup with OTP (BBS-F-002)",
    "test_signup_rules": "OTP expiry, attempt limit, delivery failure (BBS-F-002)",
}


def run(args: list[str], env: dict | None = None) -> int:
    print("$", " ".join(args), flush=True)
    return subprocess.run(args, cwd=ROOT, env={**os.environ, **(env or {})}).returncode


def run_suites() -> dict[str, dict]:
    """Run the three suites. Returns coverage JSON for 'unit' and 'combined'."""
    RAW.mkdir(parents=True, exist_ok=True)
    coverage_file = str(RAW / ".coverage")
    env = {"COVERAGE_FILE": coverage_file}
    pytest = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-W", "ignore"]
    cov = ["--cov=src/backend", "--cov-branch", "--cov-report="]
    coverage: dict[str, dict] = {}

    run([*pytest, "tests/unit", f"--junitxml={RAW / 'unit.xml'}", *cov], env)
    run([sys.executable, "-m", "coverage", "json", "-q", "-o", str(RAW / "coverage_unit.json")], env)
    coverage["unit"] = json.loads((RAW / "coverage_unit.json").read_text())

    run([*pytest, "tests/integration", f"--junitxml={RAW / 'integration.xml'}", *cov, "--cov-append"], env)
    run([sys.executable, "-m", "coverage", "json", "-q", "-o", str(RAW / "coverage_combined.json")], env)
    coverage["combined"] = json.loads((RAW / "coverage_combined.json").read_text())
    run([sys.executable, "-m", "coverage", "xml", "-q", "-o", str(RAW / "coverage_report.xml")], env)
    shutil.rmtree(DOCS / "coverage_html", ignore_errors=True)
    run([sys.executable, "-m", "coverage", "html", "-q", "-d", str(DOCS / "coverage_html")], env)
    (DOCS / "coverage_html" / ".gitignore").unlink(missing_ok=True)  # the HTML report is committed

    run([*pytest, "tests/system", f"--junitxml={RAW / 'system.xml'}"])

    for leftover in (".coverage", "coverage_unit.json", "coverage_combined.json"):
        (RAW / leftover).unlink(missing_ok=True)
    return coverage


# ----- JUnit XML -----

def read_junit(suite: str) -> dict:
    root = ET.parse(RAW / f"{suite}.xml").getroot()
    testsuite = root if root.tag == "testsuite" else root.find("testsuite")
    cases = []
    for case in testsuite.iter("testcase"):
        if case.find("failure") is not None or case.find("error") is not None:
            outcome = "FAIL"
        elif case.find("skipped") is not None:
            outcome = "SKIP"
        else:
            outcome = "PASS"
        problem = case.find("failure") if case.find("failure") is not None else case.find("error")
        cases.append({
            "file": case.get("classname", "").split(".")[-1],
            "name": case.get("name"),
            "time": float(case.get("time", 0)),
            "outcome": outcome,
            "message": (problem.get("message") or "").splitlines()[0][:200] if problem is not None else "",
            "properties": {p.get("name"): p.get("value") for p in case.iter("property")},
        })
    return {
        "cases": cases,
        "total": len(cases),
        "passed": sum(c["outcome"] == "PASS" for c in cases),
        "failed": sum(c["outcome"] == "FAIL" for c in cases),
        "skipped": sum(c["outcome"] == "SKIP" for c in cases),
        "time": float(testsuite.get("time", 0)),
    }


def environment() -> list[str]:
    def output(*args: str) -> str:
        return subprocess.run(args, cwd=ROOT, capture_output=True, text=True).stdout.strip()

    import coverage
    import pytest

    dirty = " plus uncommitted changes" if output("git", "status", "--porcelain", "--", "src", "tests") else ""
    return [
        f"- Date of run: {datetime.now().strftime('%d-%m-%Y %H:%M')}",
        f"- Code under test: branch `{output('git', 'rev-parse', '--abbrev-ref', 'HEAD')}`, "
        f"commit `{output('git', 'rev-parse', '--short', 'HEAD')}`{dirty}",
        f"- Python {platform.python_version()} on {platform.system()}, pytest {pytest.__version__}, "
        f"coverage.py {coverage.__version__}",
        "- Database: SQLite, a new empty database for every test",
        "- Produced by `python scripts/generate_test_reports.py`",
    ]


def summary_table(results: dict[str, dict], suites: tuple[str, ...]) -> list[str]:
    lines = ["| Suite | Tests | Passed | Failed | Skipped | Time |", "|---|---|---|---|---|---|"]
    for suite in suites:
        r = results[suite]
        lines.append(f"| {suite.capitalize()} | {r['total']} | {r['passed']} | {r['failed']} | {r['skipped']} | {r['time']:.1f} s |")
    if len(suites) > 1:
        total = {k: sum(results[s][k] for s in suites) for k in ("total", "passed", "failed", "skipped", "time")}
        lines.append(f"| **Total** | **{total['total']}** | **{total['passed']}** | **{total['failed']}** | **{total['skipped']}** | **{total['time']:.1f} s** |")
    return lines


def per_file_table(result: dict) -> list[str]:
    files: dict[str, list[dict]] = {}
    for case in result["cases"]:
        files.setdefault(case["file"], []).append(case)
    lines = ["| Test file | Covers | Tests | Passed | Failed |", "|---|---|---|---|---|"]
    for name in sorted(files):
        cases = files[name]
        lines.append(
            f"| `{name}.py` | {FILE_SCOPE.get(name, '')} | {len(cases)} | "
            f"{sum(c['outcome'] == 'PASS' for c in cases)} | {sum(c['outcome'] == 'FAIL' for c in cases)} |"
        )
    return lines


def case_list(result: dict) -> list[str]:
    lines = ["| Test file | Test | Result |", "|---|---|---|"]
    for case in sorted(result["cases"], key=lambda c: (c["file"], c["name"])):
        lines.append(f"| `{case['file']}` | `{case['name']}` | {case['outcome']} |")
    return lines


def failures(results: dict[str, dict], suites: tuple[str, ...]) -> list[str]:
    failed = [(s, c) for s in suites for c in results[s]["cases"] if c["outcome"] == "FAIL"]
    if not failed:
        return ["None. Every test passed."]
    return [f"- `{suite}/{case['file']}::{case['name']}`: {case['message']}" for suite, case in failed]


# ----- reports -----

def write_unit_report(results: dict[str, dict]) -> None:
    lines = [
        "# Unit Test Report",
        "",
        "Blood Bank & Donation Management System (BBMS), Team T9.",
        "",
        "This report covers the automated unit tests (`tests/unit`, one module at a time with",
        "fakes for its neighbours) and the integration tests (`tests/integration`, the fully wired",
        "FastAPI app on a temporary database). System tests are in the System Validation Report.",
        "",
        "## 1. Test run",
        "",
        *environment(),
        "",
        "## 2. Summary",
        "",
        *summary_table(results, ("unit", "integration")),
        "",
        "## 3. Unit tests by file",
        "",
        *per_file_table(results["unit"]),
        "",
        "## 4. Integration tests by file",
        "",
        *per_file_table(results["integration"]),
        "",
        "## 5. Failures",
        "",
        *failures(results, ("unit", "integration")),
        "",
        "## 6. How to reproduce",
        "",
        "```bash",
        "python -m pytest tests/unit -v",
        "python -m pytest tests/integration -v",
        "```",
        "",
        "The same two commands run in GitHub Actions (`.github/workflows/CI.yml`, job `test`) on",
        "every pull request into `main`. Raw results: `docs/raw/unit.xml`, `docs/raw/integration.xml`.",
        "",
        "## Appendix A. Every unit test",
        "",
        *case_list(results["unit"]),
        "",
        "## Appendix B. Every integration test",
        "",
        *case_list(results["integration"]),
        "",
    ]
    (DOCS / "Unit_Test_Report.md").write_text("\n".join(lines))


def _ranges(numbers: list[int]) -> str:
    """[1, 2, 3, 7] -> '1-3, 7'"""
    if not numbers:
        return ""
    numbers = sorted(numbers)
    out, start, prev = [], numbers[0], numbers[0]
    for n in numbers[1:]:
        if n != prev + 1:
            out.append(f"{start}-{prev}" if start != prev else str(start))
            start = n
        prev = n
    out.append(f"{start}-{prev}" if start != prev else str(start))
    return ", ".join(out)


def _pct(part: int, whole: int) -> str:
    return "100%" if whole == 0 else f"{100 * part / whole:.1f}%"


def _modules(data: dict) -> dict[str, dict]:
    """Totals per backend package (auth, donor, ...)."""
    modules: dict[str, dict] = {}
    for path, info in data["files"].items():
        parts = Path(path).parts
        module = parts[2] if len(parts) > 3 else "(app: main, cli, config, ...)"
        total = modules.setdefault(module, {"statements": 0, "covered": 0, "branches": 0, "covered_branches": 0})
        s = info["summary"]
        total["statements"] += s["num_statements"]
        total["covered"] += s["covered_lines"]
        total["branches"] += s["num_branches"]
        total["covered_branches"] += s["covered_branches"]
    return modules


def write_code_coverage_report(coverage: dict[str, dict]) -> None:
    unit, combined = coverage["unit"]["totals"], coverage["combined"]["totals"]
    lines = [
        "# Code Coverage Report",
        "",
        "Blood Bank & Donation Management System (BBMS), Team T9.",
        "",
        "Statement (line) coverage of the backend, `src/backend`, measured with coverage.py while",
        "the unit and integration tests run. Branch coverage is in the Branch Coverage Report.",
        "",
        "## 1. Test run",
        "",
        *environment(),
        "",
        "## 2. Summary",
        "",
        "| Tests run | Statements | Covered | Missed | Statement coverage |",
        "|---|---|---|---|---|",
        f"| Unit tests only | {unit['num_statements']} | {unit['covered_lines']} | {unit['missing_lines']} | {_pct(unit['covered_lines'], unit['num_statements'])} |",
        f"| Unit + integration | {combined['num_statements']} | {combined['covered_lines']} | {combined['missing_lines']} | **{_pct(combined['covered_lines'], combined['num_statements'])}** |",
        "",
        "The rest of this report uses the unit + integration figures.",
        "",
        "## 3. Coverage by module",
        "",
        "| Module | Statements | Covered | Statement coverage |",
        "|---|---|---|---|",
    ]
    for module, t in sorted(_modules(coverage["combined"]).items()):
        lines.append(f"| `{module}` | {t['statements']} | {t['covered']} | {_pct(t['covered'], t['statements'])} |")
    lines += [
        "",
        "## 4. Coverage by file",
        "",
        "Files with nothing to execute (empty `__init__.py`) are left out.",
        "",
        "| File | Statements | Missed | Coverage | Lines not executed |",
        "|---|---|---|---|---|",
    ]
    for path, info in sorted(coverage["combined"]["files"].items()):
        s = info["summary"]
        if s["num_statements"] == 0:
            continue
        lines.append(
            f"| `{path}` | {s['num_statements']} | {s['missing_lines']} | "
            f"{_pct(s['covered_lines'], s['num_statements'])} | {_ranges(info['missing_lines'])} |"
        )
    lines += [
        "",
        "## 5. What is not covered",
        "",
        "- `cli.py`: the `create-admin` command reads a password from the terminal and the `__main__`",
        "  entry point; `expire-units`, `send-reminders` and `seed-demo` call services that are tested",
        "  directly.",
        "- `donor/service.py`, `donor/routes.py`: the body of the emergency call-out is replaced by a",
        "  mock in its tests, and some input-validation error paths are not exercised.",
        "- `auth/sessions.py`, `auth/models.py`, `auth/permissions.py`: defensive checks for values the",
        "  API layer already rejects (empty token, unknown role, invalid user ID).",
        "- The React frontend (`src/frontend`) is not measured. It is checked by the production build",
        "  in CI and by the dashboard-action integration tests that send the same requests.",
        "",
        "## 6. How to reproduce",
        "",
        "```bash",
        "python -m pytest tests/unit tests/integration --cov=src/backend --cov-branch --cov-report=term-missing",
        "```",
        "",
        "Line-by-line view: open `docs/coverage_html/index.html` in a browser. Raw data: `docs/raw/coverage_report.xml`.",
        "",
    ]
    (DOCS / "Code_Coverage_Report.md").write_text("\n".join(lines))


def write_branch_coverage_report(coverage: dict[str, dict]) -> None:
    unit, combined = coverage["unit"]["totals"], coverage["combined"]["totals"]
    lines = [
        "# Branch Coverage Report",
        "",
        "Blood Bank & Donation Management System (BBMS), Team T9.",
        "",
        "Branch coverage of the backend, `src/backend`, measured with coverage.py (`--cov-branch`)",
        "while the unit and integration tests run. Every `if`, loop and `try` has two or more exits",
        "(branches); a branch is covered when a test takes it. A *partial* decision is one where a",
        "test took one exit but no test took the other.",
        "",
        "## 1. Test run",
        "",
        *environment(),
        "",
        "## 2. Summary",
        "",
        "| Tests run | Branches | Covered | Missed | Partial decisions | Branch coverage |",
        "|---|---|---|---|---|---|",
        f"| Unit tests only | {unit['num_branches']} | {unit['covered_branches']} | {unit['missing_branches']} | {unit['num_partial_branches']} | {_pct(unit['covered_branches'], unit['num_branches'])} |",
        f"| Unit + integration | {combined['num_branches']} | {combined['covered_branches']} | {combined['missing_branches']} | {combined['num_partial_branches']} | **{_pct(combined['covered_branches'], combined['num_branches'])}** |",
        "",
        f"Statement and branch coverage together: {combined['percent_covered']:.1f}%.",
        "The rest of this report uses the unit + integration figures.",
        "",
        "## 3. Branch coverage by module",
        "",
        "| Module | Branches | Covered | Branch coverage |",
        "|---|---|---|---|",
    ]
    for module, t in sorted(_modules(coverage["combined"]).items()):
        lines.append(f"| `{module}` | {t['branches']} | {t['covered_branches']} | {_pct(t['covered_branches'], t['branches'])} |")
    lines += [
        "",
        "## 4. Branch coverage by file",
        "",
        "Files without any branch are left out. A missed branch is written `from line -> to line`;",
        "`exit` means leaving the function.",
        "",
        "| File | Branches | Missed | Partial | Coverage | Branches not taken |",
        "|---|---|---|---|---|---|",
    ]
    for path, info in sorted(coverage["combined"]["files"].items()):
        s = info["summary"]
        if s["num_branches"] == 0:
            continue
        missed = ", ".join(f"{a} -> {'exit' if b < 0 else b}" for a, b in info["missing_branches"])
        lines.append(
            f"| `{path}` | {s['num_branches']} | {s['missing_branches']} | {s['num_partial_branches']} | "
            f"{_pct(s['covered_branches'], s['num_branches'])} | {missed} |"
        )
    fully = sum(1 for i in coverage["combined"]["files"].values() if i["summary"]["num_branches"] and not i["summary"]["missing_branches"])
    with_branches = sum(1 for i in coverage["combined"]["files"].values() if i["summary"]["num_branches"])
    lines += [
        "",
        f"{fully} of the {with_branches} files that contain branches have every branch covered.",
        "",
        "## 5. How to reproduce",
        "",
        "```bash",
        "python -m pytest tests/unit tests/integration --cov=src/backend --cov-branch --cov-report=term-missing",
        "```",
        "",
        "In `docs/coverage_html/index.html`, partially covered decisions are highlighted in yellow.",
        "",
    ]
    (DOCS / "Branch_Coverage_Report.md").write_text("\n".join(lines))


def system_cases() -> dict[str, tuple[str, str, str]]:
    """test function name -> (ST id, requirements, description), read from the docstrings."""
    tree = ast.parse((ROOT / "tests/system/test_system_validation.py").read_text())
    cases = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_st"):
            doc = " ".join((ast.get_docstring(node) or "").split())
            head, _, description = doc.partition(": ")
            st_id, _, requirements = head.partition(" / ")
            cases[node.name] = (st_id, requirements, description)
    return cases


def write_system_results(results: dict[str, dict]) -> None:
    """Fill the generated section of docs/System_Validation_Report.md (between the markers)."""
    result = results["system"]
    by_name = {case["name"]: case for case in result["cases"]}
    lines = [
        *environment(),
        "- System under test: `uvicorn src.backend.main:app` started as its own process for each test,",
        "  driven over HTTP",
        "",
        *summary_table(results, ("system",)),
        "",
        "| ID | Requirement | What is validated | Result |",
        "|---|---|---|---|",
    ]
    for name, (st_id, requirements, description) in system_cases().items():
        case = by_name.get(name)
        lines.append(f"| {st_id} | {requirements} | {description} | {case['outcome'] if case else 'NOT RUN'} |")
    perf = next((c["properties"] for c in result["cases"] if c["properties"]), None)
    if perf:
        lines += [
            "",
            "Response times measured in ST-17 (300 units in stock, 20 calls each, limit 2000 ms):",
            "",
            "| Call | Median | Slowest |",
            "|---|---|---|",
            f"| List available stock `GET /api/inventory/bags` | {perf['list_median_ms']} ms | {perf['list_max_ms']} ms |",
            f"| Look up one unit `GET /api/inventory/bags/{{unit_id}}` | {perf['lookup_median_ms']} ms | {perf['lookup_max_ms']} ms |",
        ]
    lines += ["", "Failures:", "", *failures(results, ("system",))]

    path = DOCS / "System_Validation_Report.md"
    begin, end = "<!-- results:begin -->", "<!-- results:end -->"
    text = path.read_text()
    if begin not in text or end not in text:
        raise SystemExit(f"{path} must contain the markers {begin} and {end}")
    head, rest = text.split(begin, 1)
    tail = rest.split(end, 1)[1]
    path.write_text(head + begin + "\n" + "\n".join(lines) + "\n" + end + tail)


def main() -> int:
    coverage = run_suites()
    results = {suite: read_junit(suite) for suite in SUITES}
    write_unit_report(results)
    write_code_coverage_report(coverage)
    write_branch_coverage_report(coverage)
    write_system_results(results)
    failed = sum(r["failed"] for r in results.values())
    print(f"Reports written to {DOCS.relative_to(ROOT)}/. Failed tests: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
