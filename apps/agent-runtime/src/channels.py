from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelDefinition:
    id: str
    label: str
    screenless: bool
    prompt_suffix: str


WEB_CHANNEL = ChannelDefinition(
    id="web",
    label="Web voice session",
    screenless=False,
    prompt_suffix=(
        "The user is in a web voice session with a live transcript and workflow panel available."
    ),
)

PHONE_CHANNEL = ChannelDefinition(
    id="phone",
    label="Inbound phone call",
    screenless=True,
    prompt_suffix=(
        "The user is on a phone call. Keep every response screenless-first, fully spoken, and self-contained."
    ),
)

CHANNEL_REGISTRY: dict[str, ChannelDefinition] = {
    WEB_CHANNEL.id: WEB_CHANNEL,
    PHONE_CHANNEL.id: PHONE_CHANNEL,
}

DEFAULT_CHANNEL_ID = WEB_CHANNEL.id


def get_channel_definition(channel_id: str | None) -> ChannelDefinition:
    if not channel_id:
        return WEB_CHANNEL

    return CHANNEL_REGISTRY.get(channel_id, WEB_CHANNEL)
