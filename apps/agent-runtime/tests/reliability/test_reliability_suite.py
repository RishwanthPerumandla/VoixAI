from __future__ import annotations

import pytest

from .fixtures.scenario_loader import load_scenarios
from .scenario_runner import (
    ReliabilityScenarioRunner,
    assert_final_expectation,
    assert_turn_expectation,
)

SCENARIOS = load_scenarios()


def _expects_validation_failure(scenario: dict[str, object]) -> bool:
    turns = scenario.get("turns", [])
    if isinstance(turns, list):
        for turn in turns:
            if isinstance(turn, dict) and turn.get("expected", {}).get("validation_errors"):
                return True
    final_expected = scenario.get("final_expected", {})
    if isinstance(final_expected, dict):
        return bool(final_expected.get("validation_failure_count"))
    return False


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda case: str(case["name"]))
async def test_reliability_suite(
    scenario: dict[str, object],
    reliability_reporter,
) -> None:
    runner = ReliabilityScenarioRunner()
    try:
        result = await runner.run_scenario(scenario)
        for turn_result, turn in zip(result.turns, scenario.get("turns", []), strict=False):
            expected = turn.get("expected")
            if expected:
                assert_turn_expectation(turn_result, expected)
        final_expected = scenario.get("final_expected")
        if final_expected:
            assert_final_expectation(result, final_expected)
        reliability_reporter.record(
            name=str(scenario["name"]),
            tags=list(scenario.get("tags", [])),
            passed=True,
            expected_validation_failure=_expects_validation_failure(scenario),
        )
    except Exception as exc:
        reliability_reporter.record(
            name=str(scenario["name"]),
            tags=list(scenario.get("tags", [])),
            passed=False,
            expected_validation_failure=_expects_validation_failure(scenario),
            details=str(exc),
        )
        raise
