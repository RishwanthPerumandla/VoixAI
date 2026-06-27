"""Concurrent ordering load test against the deterministic core.

Simulates N concurrent ordering sessions using the same scenario runner that
powers the reliability suite.  No LiveKit, audio, or API keys needed.

Usage:
    .venv\Scripts\python.exe -m tests.load_test_concurrent_orders [--concurrency N] [--sessions N]
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
import time
from dataclasses import dataclass, field


QUIET_SCENARIOS = [
    {
        "name": "load_test_basic",
        "turns": [
            {"user": "Pickup for {name}.", "expected": {}},
            {"user": "10 classic wings with lemon pepper.", "expected": {}},
            {"user": "What's my total?", "expected": {"total_present": True}},
            {"user": "Review the order.", "expected": {}},
            {"user": "Yes, place it.", "expected": {}},
        ],
        "final_expected": {"status": "completed", "completed_order": True},
    },
    {
        "name": "load_test_boneless",
        "turns": [
            {"user": "Pickup for {name}.", "expected": {}},
            {"user": "Add 10 boneless wings with hot.", "expected": {}},
            {"user": "What's my total?", "expected": {"total_present": True}},
            {"user": "Review the order.", "expected": {}},
            {"user": "Yes, place the order.", "expected": {}},
        ],
        "final_expected": {"status": "completed", "completed_order": True},
    },
    {
        "name": "load_test_with_correction",
        "turns": [
            {"user": "Pickup for {name}.", "expected": {}},
            {"user": "20 classic wings with barbecue.", "expected": {}},
            {"user": "Change that to hot instead.", "expected": {}},
            {"user": "What's my total?", "expected": {"total_present": True}},
            {"user": "Review the order.", "expected": {}},
            {"user": "Yes.", "expected": {}},
        ],
        "final_expected": {"status": "completed", "completed_order": True},
    },
]

NAMES = [
    "Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank",
    "Ivy", "Jack", "Ken", "Luna", "Mia", "Noah", "Owen", "Paul",
    "Quinn", "Rosa", "Sam", "Tina", "Uma", "Vince", "Wade", "Xena",
    "Yara", "Zack",
]


@dataclass
class SessionResult:
    scenario_name: str
    duration_seconds: float
    passed: bool
    error: str | None = None
    events: list[str] = field(default_factory=list)


async def run_session(
    runner: "ReliabilityScenarioRunner",
    scenario_template: dict,
    name: str,
) -> SessionResult:
    scenario = _fill_template(scenario_template, name)
    start = time.monotonic()
    try:
        result = await runner.run_scenario(scenario)
        duration = time.monotonic() - start
        if result.mock_order_id is not None:
            return SessionResult(
                scenario_name=scenario["name"],
                duration_seconds=duration,
                passed=True,
                events=[e for t in result.turns for e in t.telemetry_events],
            )
        else:
            return SessionResult(
                scenario_name=scenario["name"],
                duration_seconds=duration,
                passed=False,
                error=f"Order not placed (status={result.order_status})",
            )
    except Exception as exc:
        duration = time.monotonic() - start
        return SessionResult(
            scenario_name=scenario["name"],
            duration_seconds=duration,
            passed=False,
            error=str(exc),
        )


def _fill_template(scenario: dict, name: str) -> dict:
    import copy
    s = copy.deepcopy(scenario)
    s["name"] = f"{scenario['name']}_{name.lower()}"
    new_turns = []
    for turn in s["turns"]:
        t = dict(turn)
        t["user"] = turn["user"].format(name=name)
        new_turns.append(t)
    s["turns"] = new_turns
    return s


async def main(concurrency: int = 10, total_sessions: int = 50) -> None:
    from tests.reliability.scenario_runner import ReliabilityScenarioRunner

    print(f"Concurrent ordering load test: {total_sessions} sessions, concurrency={concurrency}")
    print()

    semaphore = asyncio.Semaphore(concurrency)
    results: list[SessionResult] = []
    runner_refs: list[ReliabilityScenarioRunner] = []

    async def throttled_run(name: str, template: dict) -> SessionResult:
        async with semaphore:
            runner = ReliabilityScenarioRunner()
            runner_refs.append(runner)
            return await run_session(runner, template, name)

    tasks = []
    for i in range(total_sessions):
        name = NAMES[i % len(NAMES)]
        template = QUIET_SCENARIOS[i % len(QUIET_SCENARIOS)]
        tasks.append(throttled_run(name, template))

    start_wall = time.monotonic()

    if sys.version_info >= (3, 11):
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            _print_progress(len(results), total_sessions)
    else:
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)

    wall_elapsed = time.monotonic() - start_wall

    print()
    print("=" * 60)
    print("LOAD TEST RESULTS")
    print("=" * 60)

    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]
    durations = [r.duration_seconds for r in results]

    print(f"Total sessions:     {total_sessions}")
    print(f"Concurrency:        {concurrency}")
    print(f"Passed:             {len(passed)}")
    print(f"Failed:             {len(failed)}")
    print(f"Wall-clock time:    {wall_elapsed:.2f}s")
    print(f"Throughput:         {total_sessions / wall_elapsed:.1f} sessions/s")
    if durations:
        print(f"Avg session time:   {sum(durations) / len(durations):.3f}s")
        print(f"Min session time:   {min(durations):.3f}s")
        print(f"Max session time:   {max(durations):.3f}s")
        print(f"P50:                {sorted(durations)[len(durations)//2]:.3f}s")
        print(f"P95:                {sorted(durations)[int(len(durations)*0.95)]:.3f}s")
        print(f"P99:                {sorted(durations)[int(len(durations)*0.99)]:.3f}s")
    print()

    if failed:
        print("FAILURES:")
        for f in failed[:10]:
            print(f"  - [{f.scenario_name}] {f.error}")
        if len(failed) > 10:
            print(f"  ... and {len(failed) - 10} more")

    return 0 if not failed else 1


def _print_progress(done: int, total: int) -> None:
    if total == 0:
        return
    pct = done * 100 // total
    bar_len = 40
    filled = bar_len * done // total
    bar = "=" * filled + "." * (bar_len - filled)
    print(f"\r  [{bar}] {done}/{total} ({pct}%)", end="", flush=True)
    if done == total:
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Concurrent ordering load test")
    parser.add_argument("--concurrency", type=int, default=10, help="Max concurrent sessions")
    parser.add_argument("--sessions", type=int, default=50, help="Total number of sessions")
    args = parser.parse_args()
    exit(asyncio.run(main(concurrency=args.concurrency, total_sessions=args.sessions)))
