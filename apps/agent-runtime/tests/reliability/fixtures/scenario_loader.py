from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional when only JSON fixtures exist
    yaml = None

SCENARIOS_DIR = Path(__file__).resolve().parents[1] / "scenarios"


def _load_payload(path: Path) -> Any:
    suffix = path.suffix.lower()
    raw = path.read_text(encoding="utf-8")
    if suffix == ".json":
        return json.loads(raw)
    if suffix in {".yaml", ".yml"}:
        if yaml is None:
            raise ModuleNotFoundError("pyyaml is required to load YAML reliability scenarios.")
        return yaml.safe_load(raw)
    raise TypeError(f"Unsupported scenario file type: {path.name}")


def load_scenarios() -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    for path in sorted(SCENARIOS_DIR.glob("*")):
        if path.suffix.lower() not in {".json", ".yaml", ".yml"}:
            continue
        payload = _load_payload(path)
        if isinstance(payload, dict):
            payload = payload.get("scenarios", [])
        if not isinstance(payload, list):
            raise TypeError(f"Scenario file {path} must contain a list.")
        for scenario in payload:
            if not isinstance(scenario, dict):
                raise TypeError(f"Scenario in {path} must be an object.")
            scenario.setdefault("source_file", path.name)
            scenarios.append(scenario)
    return scenarios
