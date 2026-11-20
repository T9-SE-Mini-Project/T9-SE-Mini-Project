# BBMS documents

| Document | What it is |
|---|---|
| [Software_Architecture_and_Design.md](Software_Architecture_and_Design.md) | Architecture and design specification: components, traceability, security, sequence diagrams, API design, error handling |
| [Test_Cases.md](Test_Cases.md) | The 28 test cases, updated after the sprints, with the requirement each one traces to |
| [Unit_Test_Report.md](Unit_Test_Report.md) | Results of the unit and integration tests |
| [System_Validation_Report.md](System_Validation_Report.md) | End-to-end results against a running server, requirement by requirement, with open defects |
| [Code_Coverage_Report.md](Code_Coverage_Report.md) | Statement coverage of the backend |
| [Branch_Coverage_Report.md](Branch_Coverage_Report.md) | Branch coverage of the backend |
| [Deviations.md](Deviations.md) | Where the product differs from the SRS, design and test plan, and why |
| [coverage_html/index.html](coverage_html/index.html) | Line-by-line coverage; open it in a browser |
| [raw/](raw/) | JUnit XML and coverage XML the reports are built from |

The four reports are generated. To refresh them after a code change:

```bash
python scripts/generate_test_reports.py
```

`Software_Architecture_and_Design.md`, `Test_Cases.md` and `Deviations.md` are written by hand. So is `System_Validation_Report.md`,
except its results section (section 3), which the script rewrites.
