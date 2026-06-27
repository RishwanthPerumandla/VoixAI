from __future__ import annotations

import pytest

from .scenario_runner import ReliabilityScenarioRunner, assert_final_expectation, assert_turn_expectation


@pytest.mark.asyncio
async def test_runner_can_complete_simple_happy_path() -> None:
    scenario = {
        "name": "runner_smoke_happy_path",
        "initial_state": {},
        "turns": [
            {"user": "This is pickup for Cherry."},
            {"user": "Add 10 boneless wings with lemon pepper and ranch."},
            {"user": "What's my total?"},
            {"user": "Review the order."},
            {"user": "Yes, place it."},
        ],
        "final_expected": {
            "status": "completed",
            "item_count": 1,
            "completed_order": True,
        },
    }
    runner = ReliabilityScenarioRunner()

    result = await runner.run_scenario(scenario)

    assert_final_expectation(result, scenario["final_expected"])


@pytest.mark.asyncio
async def test_runner_reports_turn_level_expectations() -> None:
    runner = ReliabilityScenarioRunner()
    runner.reset({})

    turn_result = await runner.run_turn("Add 10 boneless wings all flats with lemon pepper.")

    assert_turn_expectation(
        turn_result,
        {
            "status": "collecting_order",
            "contains_items": ["boneless_10"],
            "telemetry_events": ["invalid_modifier_removed", "validation_passed"],
        },
    )
