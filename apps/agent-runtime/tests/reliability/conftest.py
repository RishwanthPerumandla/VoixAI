from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pytest

from .fixtures.expected_events import PRIMARY_CATEGORIES

ROOT = Path(__file__).resolve().parents[4]
SRC_DIR = ROOT / "apps" / "agent-runtime" / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

REPORT_PATH = Path(__file__).resolve().parent / "reports" / "reliability_report.json"


@dataclass
class ReliabilityReportCollector:
    records: list[dict[str, object]] = field(default_factory=list)

    def record(
        self,
        *,
        name: str,
        tags: list[str],
        passed: bool,
        expected_validation_failure: bool,
        details: str | None = None,
    ) -> None:
        self.records.append(
            {
                "name": name,
                "tags": list(tags),
                "passed": passed,
                "expected_validation_failure": expected_validation_failure,
                "details": details,
            }
        )

    def write_report(self) -> None:
        total = len(self.records)
        passed = sum(1 for record in self.records if bool(record["passed"]))
        failed = total - passed
        failures_by_category = {category: 0 for category in PRIMARY_CATEGORIES}
        for record in self.records:
            if bool(record["passed"]):
                continue
            tags = [str(tag) for tag in record.get("tags", [])]
            category = next((tag for tag in tags if tag in failures_by_category), "unknown")
            failures_by_category.setdefault(category, 0)
            failures_by_category[category] += 1

        report = {
            "total_scenarios": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round((passed / total) * 100, 1) if total else 0.0,
            "failures_by_category": failures_by_category,
            "validation_failures_expected": sum(
                1 for record in self.records if bool(record["expected_validation_failure"])
            ),
            "correction_cases_passed": sum(
                1 for record in self.records if "corrections" in record["tags"] and bool(record["passed"])
            ),
            "cancellation_cases_passed": sum(
                1
                for record in self.records
                if "cancellations" in record["tags"] and bool(record["passed"])
            ),
            "confirmation_gate_cases_passed": sum(
                1
                for record in self.records
                if "confirmation_gate" in record["tags"] and bool(record["passed"])
            ),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("VoixAI Wingstop Reliability Suite")
        print(f"Total scenarios: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Pass rate: {report['pass_rate']}%")


@pytest.fixture(scope="session")
def reliability_reporter() -> ReliabilityReportCollector:
    reporter = ReliabilityReportCollector()
    yield reporter
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    reporter.write_report()
