from scenarios.base import ScenarioDefinition
from scenarios.wingstop import WINGSTOP_SCENARIO

SCENARIO_REGISTRY: dict[str, ScenarioDefinition] = {
    WINGSTOP_SCENARIO.id: WINGSTOP_SCENARIO,
}

DEFAULT_SCENARIO_ID = WINGSTOP_SCENARIO.id


def get_scenario_definition(scenario_id: str | None) -> ScenarioDefinition:
    if not scenario_id:
        return WINGSTOP_SCENARIO

    return SCENARIO_REGISTRY.get(scenario_id, WINGSTOP_SCENARIO)
