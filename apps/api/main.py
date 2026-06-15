import asyncio
import hashlib
import json
import logging
import os
import random
import time
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from livekit.api import AccessToken, VideoGrants
from livekit.protocol.agent_dispatch import RoomAgentDispatch
from livekit.protocol.room import RoomConfiguration

# The ordering domain (menu, pricing, validation, order state) is the single
# source of truth, shared with the agent runtime via the `voix-ordering` package.
from voix_ordering import (
    FLAVOR_OPTIONS,
    MENU_ITEMS,
    MODIFIER_OPTIONS,
    OrderLineItem,
    OrderState,
    OrderStateMachine,
    build_price_quote,
    validate_order,
)
from voix_ordering.confirmation import _build_kitchen_ticket
from voix_ordering.menu import (
    _resolve_flavor_id,
    _resolve_item_id,
    _resolve_modifier_id,
    category_summary,
    menu_overview_summary,
    suggest_item_names,
)
from voix_ordering.validation import _validation_errors_for_line

from storage import DuplicateKeyError, OrderRecord, build_storage

logger = logging.getLogger("voixai.api")


API_DIR = Path(__file__).resolve().parent
ROOT_DIR = API_DIR.parent.parent
SESSION_CONFIG_DIR = ROOT_DIR / ".voixai" / "session-configs"

# Durable persistence (M3). Orders are idempotent and survive restarts.
ORDER_STORAGE = build_storage()

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


class OrderSubmitRequest(BaseModel):
    room_name: str = Field(min_length=1)
    order: OrderPayload
    # Optional client-supplied key; if omitted the server derives a stable one
    # from the room + canonical order so retries never double-submit.
    idempotency_key: str | None = None


class OrderSubmitResponse(BaseModel):
    order_number: str
    status: str
    subtotal: str
    tax: str
    total: str
    eta_minutes: int
    kitchen_ticket: str
    idempotent_replay: bool = False


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
    # Delegate to the domain's tokenized matcher (number-aware, alias-aware) so
    # suggestions match how items are actually resolved.
    return suggest_item_names(raw_name, limit=3)


def _derive_idempotency_key(room_name: str, payload: OrderPayload) -> str:
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True)
    digest = hashlib.sha256(f"{room_name}\n{canonical}".encode("utf-8")).hexdigest()
    return f"{room_name}:{digest[:32]}"


def _new_order_number() -> str:
    return f"MOCK-{random.randint(10001, 99999)}"


def _order_record_to_response(record: OrderRecord, *, idempotent_replay: bool) -> "OrderSubmitResponse":
    return OrderSubmitResponse(
        order_number=record.order_number,
        status=record.status,
        subtotal=record.subtotal,
        tax=record.tax,
        total=record.total,
        eta_minutes=record.eta_minutes,
        kitchen_ticket=record.kitchen_ticket,
        idempotent_replay=idempotent_replay,
    )


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
    # Category names are matched by tokens (so "combos" finds "Wing Combos") and
    # never fail hard: an unknown/ambiguous category falls back to the overview,
    # so the agent always gets real menu info instead of "not available".
    if category and category.strip():
        return MenuSummaryResponse(summary=category_summary(category))
    return MenuSummaryResponse(summary=menu_overview_summary())


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


@app.post("/api/orders", response_model=OrderSubmitResponse)
async def submit_order(payload: OrderSubmitRequest) -> OrderSubmitResponse:
    order = _order_state_from_payload(payload.order)

    # Defense in depth: the API re-runs the hard submit gate even though the
    # runtime already checked it. The backend is the authority on placement, so
    # an invalid or unconfirmed order can never be persisted.
    decision = OrderStateMachine(order).authorize_submit()
    if not decision.authorized:
        raise HTTPException(
            status_code=422,
            detail={
                "errors": decision.validation_errors,
                "reasons": decision.confirmation_reasons,
            },
        )

    key = payload.idempotency_key or _derive_idempotency_key(payload.room_name, payload.order)

    existing = await asyncio.to_thread(ORDER_STORAGE.get_order_by_idempotency_key, key)
    if existing is not None:
        return _order_record_to_response(existing, idempotent_replay=True)

    quote = build_price_quote(order)
    order_json = json.dumps(payload.order.model_dump(mode="json"))

    for _ in range(5):
        order_number = _new_order_number()
        candidate = OrderRecord(
            order_number=order_number,
            idempotency_key=key,
            room_name=payload.room_name,
            status="submitted",
            subtotal=quote.subtotal,
            tax=quote.tax,
            total=quote.total,
            eta_minutes=quote.eta_minutes,
            order_json=order_json,
            kitchen_ticket=_build_kitchen_ticket(order, quote, order_number),
            created_at=time.time(),
        )
        try:
            await asyncio.to_thread(ORDER_STORAGE.insert_order, candidate)
        except DuplicateKeyError:
            # Either the idempotency key was written concurrently (replay) or the
            # random order number collided (retry with a new one).
            replay = await asyncio.to_thread(ORDER_STORAGE.get_order_by_idempotency_key, key)
            if replay is not None:
                return _order_record_to_response(replay, idempotent_replay=True)
            continue
        logger.info("Persisted order %s for room %s", candidate.order_number, candidate.room_name)
        return _order_record_to_response(candidate, idempotent_replay=False)

    raise HTTPException(status_code=500, detail="Could not persist the order. Please retry.")


@app.get("/api/orders/{order_number}", response_model=OrderSubmitResponse)
async def get_order(order_number: str) -> OrderSubmitResponse:
    record = await asyncio.to_thread(ORDER_STORAGE.get_order_by_number, order_number)
    if record is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return _order_record_to_response(record, idempotent_replay=False)


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

    runtime_config_json = (
        json.dumps(payload.runtime_config) if payload.runtime_config is not None else ""
    )

    if payload.runtime_config is not None:
        # Fallback handoff for single-host/local dev. The primary handoff is the
        # dispatch metadata below, which travels with the agent job and works
        # across hosts (no shared filesystem required).
        SESSION_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        _session_config_path(payload.room_name).write_text(
            json.dumps(payload.runtime_config, indent=2),
            encoding="utf-8",
        )
        # Record the session (best-effort; never block token issuance on it).
        try:
            await asyncio.to_thread(
                ORDER_STORAGE.upsert_session,
                payload.room_name,
                runtime_config_json,
            )
        except Exception:
            logger.exception("Failed to record session for room %s", payload.room_name)

    identity = f"{payload.participant_name}-{uuid4().hex[:8]}"
    # Primary runtime-config handoff: attach it to the agent dispatch metadata so
    # the worker reads it from the job, not from a shared file.
    room_config = RoomConfiguration(
        agents=[RoomAgentDispatch(agent_name=AGENT_NAME, metadata=runtime_config_json)]
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
