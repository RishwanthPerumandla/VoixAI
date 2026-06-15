import json
import importlib.util
import os
import re
import sys
import types
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from livekit.api import AccessToken, VideoGrants
from livekit.protocol.agent_dispatch import RoomAgentDispatch
from livekit.protocol.room import RoomConfiguration


API_DIR = Path(__file__).resolve().parent
ROOT_DIR = API_DIR.parent.parent
SESSION_CONFIG_DIR = ROOT_DIR / ".voixai" / "session-configs"
AGENT_RUNTIME_SRC_DIR = ROOT_DIR / "apps" / "agent-runtime" / "src"

load_dotenv(ROOT_DIR / ".env")
load_dotenv(ROOT_DIR / "apps" / "agent-runtime" / ".env")
load_dotenv(API_DIR / ".env", override=True)

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")
AGENT_NAME = os.getenv("AGENT_NAME", "my-agent")
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
).split(",")


def _load_wingstop_backend_module():
    if "livekit.agents" not in sys.modules:
        livekit_module = sys.modules.setdefault("livekit", types.ModuleType("livekit"))
        agents_module = types.ModuleType("livekit.agents")

        class Agent:  # noqa: D401
            """API stub."""

        class RunContext:  # noqa: D401
            """API stub."""

        def function_tool(fn):
            return fn

        agents_module.Agent = Agent
        agents_module.RunContext = RunContext
        agents_module.function_tool = function_tool
        sys.modules["livekit.agents"] = agents_module
        setattr(livekit_module, "agents", agents_module)

    if "channels" not in sys.modules:
        channels_module = types.ModuleType("channels")

        class ChannelDefinition:  # noqa: D401
            """API stub."""

        channels_module.ChannelDefinition = ChannelDefinition
        sys.modules["channels"] = channels_module

    scenarios_package = sys.modules.setdefault("scenarios", types.ModuleType("scenarios"))
    if "scenarios.base" not in sys.modules:
        scenarios_base_module = types.ModuleType("scenarios.base")

        class ScenarioDefinition:  # noqa: D401
            """API stub."""

            def __init__(self, **kwargs) -> None:
                self.__dict__.update(kwargs)

        scenarios_base_module.ScenarioDefinition = ScenarioDefinition
        sys.modules["scenarios.base"] = scenarios_base_module
        setattr(scenarios_package, "base", scenarios_base_module)

    module_path = AGENT_RUNTIME_SRC_DIR / "scenarios" / "wingstop.py"
    spec = importlib.util.spec_from_file_location("voixai_wingstop_backend", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load wingstop backend module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_wingstop_backend = _load_wingstop_backend_module()
MENU_ITEMS = _wingstop_backend.MENU_ITEMS
MODIFIER_OPTIONS = _wingstop_backend.MODIFIER_OPTIONS
FLAVOR_OPTIONS = _wingstop_backend.FLAVOR_OPTIONS
OrderLineItem = _wingstop_backend.OrderLineItem
OrderState = _wingstop_backend.OrderState
_resolve_flavor_id = _wingstop_backend._resolve_flavor_id
_resolve_item_id = _wingstop_backend._resolve_item_id
_resolve_modifier_id = _wingstop_backend._resolve_modifier_id
_validation_errors_for_line = _wingstop_backend._validation_errors_for_line
build_price_quote = _wingstop_backend.build_price_quote
validate_order = _wingstop_backend.validate_order


class TokenRequest(BaseModel):
    room_name: str = Field(min_length=1)
    participant_name: str = Field(min_length=1)
    runtime_config: dict[str, object] | None = None


class TokenResponse(BaseModel):
    livekit_url: str
    token: str
    room_name: str


class MenuResolveRequest(BaseModel):
    item_name: str = Field(min_length=1)
    quantity: int = Field(default=1, ge=1)
    flavors: list[str] = Field(default_factory=list)
    modifiers: list[str] = Field(default_factory=list)
    special_instructions: str | None = None
    validate_line: bool = True


class OrderLinePayload(BaseModel):
    line_id: str
    item_id: str
    quantity: int = Field(ge=1)
    selected_flavor_ids: list[str] = Field(default_factory=list)
    selected_modifier_ids: list[str] = Field(default_factory=list)
    notes: str = ""


class OrderPayload(BaseModel):
    items: list[OrderLinePayload] = Field(default_factory=list)
    modifiers: list[str] = Field(default_factory=list)
    quantity: int = 1
    order_type: str | None = None
    customer_name: str = ""
    phone: str = ""
    notes: str = ""
    status: str = "collecting"
    confirmed: bool = False
    pickup_time: str | None = None
    language: str = "english"
    total_shown: bool = False
    recap_readback: bool = False
    pos_validation_passed: bool = False
    last_validation_errors: list[str] = Field(default_factory=list)


class MenuResolveResponse(BaseModel):
    item_id: str | None = None
    item_name: str | None = None
    flavor_ids: list[str] = Field(default_factory=list)
    flavor_names: list[str] = Field(default_factory=list)
    modifier_ids: list[str] = Field(default_factory=list)
    modifier_names: list[str] = Field(default_factory=list)
    line_errors: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class MenuSummaryResponse(BaseModel):
    summary: str


class OrderValidationResponse(BaseModel):
    errors: list[str] = Field(default_factory=list)


class PriceLineItemResponse(BaseModel):
    line_id: str
    name: str
    quantity: int
    unit_price: str
    line_subtotal: str
    breakdown: list[str] = Field(default_factory=list)


class PriceQuoteResponse(BaseModel):
    subtotal: str
    tax: str
    total: str
    line_items: list[PriceLineItemResponse] = Field(default_factory=list)
    eta_minutes: int
    pricing_source: str


class OrderPricingResponse(BaseModel):
    errors: list[str] = Field(default_factory=list)
    price_quote: PriceQuoteResponse | None = None


def _session_config_path(room_name: str) -> Path:
    safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in room_name).strip("-")
    return SESSION_CONFIG_DIR / f"{safe_name or 'default-room'}.json"


def _order_state_from_payload(payload: OrderPayload) -> OrderState:
    return OrderState(
        items=[
            OrderLineItem(
                line_id=line.line_id,
                item_id=line.item_id,
                quantity=line.quantity,
                selected_flavor_ids=list(line.selected_flavor_ids),
                selected_modifier_ids=list(line.selected_modifier_ids),
                notes=line.notes,
            )
            for line in payload.items
        ],
        modifiers=list(payload.modifiers),
        quantity=payload.quantity,
        order_type=payload.order_type,
        customer_name=payload.customer_name,
        phone=payload.phone,
        notes=payload.notes,
        status=payload.status,
        confirmed=payload.confirmed,
        pickup_time=payload.pickup_time,
        language=payload.language,
        total_shown=payload.total_shown,
        recap_readback=payload.recap_readback,
        pos_validation_passed=payload.pos_validation_passed,
        last_validation_errors=list(payload.last_validation_errors),
    )


def _closest_menu_suggestions(raw_name: str) -> list[str]:
    tokens = {token for token in re.split(r"[^a-z0-9]+", raw_name.lower()) if token}
    if not tokens:
        return []

    scored: list[tuple[int, str]] = []
    for item in MENU_ITEMS.values():
        haystack = item.display_name.lower()
        score = sum(1 for token in tokens if token in haystack)
        if score:
            scored.append((score, item.display_name))

    scored.sort(key=lambda entry: (-entry[0], entry[1]))
    return [name for _, name in scored[:3]]


app = FastAPI(title="VoixAI MVP API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "OK"}


@app.get("/api/menu/summary", response_model=MenuSummaryResponse)
async def get_menu_summary(category: str | None = Query(default=None)) -> MenuSummaryResponse:
    if category:
        normalized_category = category.strip().lower()
        matching_items = [
            item.display_name
            for item in MENU_ITEMS.values()
            if item.category.strip().lower() == normalized_category
        ]
        if not matching_items:
            raise HTTPException(status_code=404, detail="That category is not available in this demo menu.")
        return MenuSummaryResponse(summary=f"{category.title()} options: {', '.join(matching_items)}.")

    categories = sorted({item.category for item in MENU_ITEMS.values()})
    return MenuSummaryResponse(
        summary=(
            "Available categories are "
            + ", ".join(categories[:-1])
            + f", and {categories[-1]}."
        )
    )


@app.post("/api/menu/resolve-selection", response_model=MenuResolveResponse)
async def resolve_menu_selection(payload: MenuResolveRequest) -> MenuResolveResponse:
    item_id = _resolve_item_id(payload.item_name)
    if item_id is None:
        return MenuResolveResponse(
            line_errors=["That item is not available in this demo menu."],
            suggestions=_closest_menu_suggestions(payload.item_name),
        )

    flavor_ids: list[str] = []
    flavor_names: list[str] = []
    line_errors: list[str] = []
    for flavor_name in payload.flavors:
        flavor_id = _resolve_flavor_id(flavor_name)
        if flavor_id is None:
            line_errors.append(f"{flavor_name} is not available in this demo menu.")
            continue
        if flavor_id not in flavor_ids:
            flavor_ids.append(flavor_id)
            flavor_names.append(FLAVOR_OPTIONS[flavor_id].display_name)

    modifier_ids: list[str] = []
    modifier_names: list[str] = []
    for modifier_name in payload.modifiers:
        modifier_id = _resolve_modifier_id(modifier_name)
        if modifier_id is None:
            line_errors.append(f"{modifier_name} is not a valid option for this demo menu.")
            continue
        if modifier_id not in modifier_ids:
            modifier_ids.append(modifier_id)
            modifier_names.append(MODIFIER_OPTIONS[modifier_id].display_name)

    if not line_errors and payload.validate_line:
        line = OrderLineItem(
            line_id="line-preview",
            item_id=item_id,
            quantity=payload.quantity,
            selected_flavor_ids=flavor_ids,
            selected_modifier_ids=modifier_ids,
            notes=(payload.special_instructions or "").strip(),
        )
        line_errors = _validation_errors_for_line(line)

    return MenuResolveResponse(
        item_id=item_id,
        item_name=MENU_ITEMS[item_id].display_name,
        flavor_ids=flavor_ids,
        flavor_names=flavor_names,
        modifier_ids=modifier_ids,
        modifier_names=modifier_names,
        line_errors=line_errors,
    )


@app.post("/api/menu/validate-order", response_model=OrderValidationResponse)
async def validate_menu_order(payload: OrderPayload) -> OrderValidationResponse:
    order = _order_state_from_payload(payload)
    return OrderValidationResponse(errors=validate_order(order))


@app.post("/api/menu/price-order", response_model=OrderPricingResponse)
async def price_menu_order(payload: OrderPayload) -> OrderPricingResponse:
    order = _order_state_from_payload(payload)
    errors = validate_order(order)
    if errors:
        return OrderPricingResponse(errors=errors, price_quote=None)
    quote = build_price_quote(order)
    return OrderPricingResponse(
        errors=[],
        price_quote=PriceQuoteResponse(
            subtotal=quote.subtotal,
            tax=quote.tax,
            total=quote.total,
            line_items=[
                PriceLineItemResponse(
                    line_id=line.line_id,
                    name=line.name,
                    quantity=line.quantity,
                    unit_price=line.unit_price,
                    line_subtotal=line.line_subtotal,
                    breakdown=list(line.breakdown),
                )
                for line in quote.line_items
            ],
            eta_minutes=quote.eta_minutes,
            pricing_source=quote.pricing_source,
        ),
    )


@app.post("/api/livekit/token", response_model=TokenResponse)
async def create_livekit_token(payload: TokenRequest) -> TokenResponse:
    if not LIVEKIT_URL or not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
        raise HTTPException(
            status_code=500,
            detail=(
                "Realtime transport environment variables are missing. Set LIVEKIT_URL, "
                "LIVEKIT_API_KEY, and LIVEKIT_API_SECRET before requesting tokens."
            ),
        )

    if payload.runtime_config is not None:
        SESSION_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _session_config_path(payload.room_name).write_text(
            json.dumps(payload.runtime_config, indent=2),
            encoding="utf-8",
        )

    identity = f"{payload.participant_name}-{uuid4().hex[:8]}"
    room_config = RoomConfiguration(
        agents=[RoomAgentDispatch(agent_name=AGENT_NAME)]
    )

    token = (
        AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(identity)
        .with_name(payload.participant_name)
        .with_grants(
            VideoGrants(
                room_join=True,
                room=payload.room_name,
                can_publish=True,
                can_publish_data=True,
                can_subscribe=True,
            )
        )
        .with_room_config(room_config)
        .to_jwt()
    )

    return TokenResponse(
        livekit_url=LIVEKIT_URL,
        token=token,
        room_name=payload.room_name,
    )
