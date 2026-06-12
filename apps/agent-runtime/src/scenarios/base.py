from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from livekit.agents import Agent

from channels import ChannelDefinition

@dataclass(frozen=True)
class ScenarioDefinition:
    id: str
    label: str
    agent_factory: Callable[[Any, ChannelDefinition], Agent]
    snapshot_builder: Callable[[Any], dict[str, object]]
