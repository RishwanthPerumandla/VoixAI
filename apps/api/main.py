import asyncio
import hashlib
import json
import logging
import os
import re
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

from services import (
    ConversationSessionService,
    CustomerService,
    MenuSeedService,
    OrderService,
    StoreService,
    format_money,
    line_inputs_from_quote,
    make_public_code,
    normalize_phone,
)
from storage import CallRecord, OrderRecord, build_storage

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
ALLOWED_ORIGIN_REGEX = os.getenv("ALLOWED_ORIGIN_REGEX")
DEFAULT_LOCAL_ORIGIN_REGEX = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"


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
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", room_name).strip("-") or "default-room"
    return SESSION_CONFIG_DIR / f"{safe_name}.json"


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


def _api_validation_messages(errors: list[str]) -> list[str]:
    messages: list[str] = []
    for error in errors:
        if error.startswith("combo_side_selection is required"):
            messages.append("This combo requires a side selection.")
        elif error.startswith("combo_drink_selection is required"):
            messages.append("This combo requires a drink selection.")
        else:
            messages.append(error)
    return messages


def _derive_idempotency_key(room_name: str, payload: OrderPayload) -> str:
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True)
    digest = hashlib.sha256(f"{room_name}\n{canonical}".encode("utf-8")).hexdigest()
    return f"{room_name}:{digest[:32]}"


def _new_order_number() -> str:
    return f"MOCK-{uuid4().hex[:12].upper()}"


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


# ---------------------------------------------------------------------------
# Call telemetry + analytics (dashboard)
# ---------------------------------------------------------------------------


class TranscriptTurn(BaseModel):
    role: str
    text: str
    ts: float | None = None


class CallStartRequest(BaseModel):
    call_id: str = Field(min_length=1)
    room_name: str = Field(min_length=1)
    scenario: str = ""
    channel: str = ""
    voice_provider: str = ""
    llm_model: str = ""
    language: str = "english"
    started_at: float | None = None


class CallUpdateRequest(BaseModel):
    status: str | None = None
    outcome: str | None = None
    ended_at: float | None = None
    duration_seconds: float | None = None
    turn_count: int | None = None
    sentiment: float | None = None
    language: str | None = None
    order_number: str | None = None
    guardrail_violations: int | None = None
    error: str | None = None
    transcript: list[TranscriptTurn] | None = None


class CallSummary(BaseModel):
    call_id: str
    room_name: str
    scenario: str
    channel: str
    voice_provider: str
    llm_model: str
    status: str
    outcome: str
    started_at: float
    ended_at: float | None
    duration_seconds: float | None
    turn_count: int
    sentiment: float | None
    language: str
    order_number: str | None
    guardrail_violations: int


class CallDetail(CallSummary):
    transcript: list[TranscriptTurn] = Field(default_factory=list)
    error: str | None = None


class ConversationSessionResponse(BaseModel):
    call_id: str
    room_name: str
    current_node: str | None = None
    outcome: str | None = None


class ConversationNodeUpdateRequest(BaseModel):
    room_name: str = Field(min_length=1)
    current_node: str = Field(min_length=1)


class ConversationIdentifyRequest(BaseModel):
    call_id: str = Field(min_length=1)
    room_name: str = Field(min_length=1)
    caller_id: str | None = None
    phone: str | None = None


class ConversationIdentifyResponse(BaseModel):
    call_id: str
    room_name: str
    current_node: str | None = None
    customer_id: str | None = None
    phone: str | None = None
    name: str | None = None
    is_returning: bool = False
    last_order_code: str | None = None
    last_order_summary: str | None = None


class ConversationNameRequest(BaseModel):
    call_id: str = Field(min_length=1)
    room_name: str = Field(min_length=1)
    customer_id: str | None = None
    phone: str | None = None
    name: str = Field(min_length=1)


class CallListResponse(BaseModel):
    calls: list[CallSummary] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0


class OrderListItem(BaseModel):
    order_number: str
    room_name: str
    status: str
    customer_name: str
    item_count: int
    item_summary: list[str] = Field(default_factory=list)
    subtotal: str
    tax: str
    total: str
    eta_minutes: int
    order_type: str | None = None
    created_at: float


class OrderListResponse(BaseModel):
    orders: list[OrderListItem] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0


class TimeBucket(BaseModel):
    label: str
    start: float
    calls: int
    orders: int
    completed: int


class AnalyticsOverview(BaseModel):
    window_hours: int
    total_calls: int
    completed_calls: int
    in_progress_calls: int
    failed_calls: int
    success_rate: float
    containment_rate: float
    orders_placed: int
    revenue_total: str
    avg_duration_seconds: float
    avg_turns: float
    avg_sentiment: float | None
    transfers: int
    abandoned: int
    outcomes: dict[str, int]
    sentiment_breakdown: dict[str, int]
    series: list[TimeBucket]


class HealthComponent(BaseModel):
    name: str
    status: str  # operational | degraded | down
    detail: str


class ObservabilitySnapshot(BaseModel):
    status: str
    uptime_seconds: float
    components: list[HealthComponent]
    total_calls: int
    failed_calls: int
    error_rate: float
    orders_total: int
    avg_duration_seconds: float
    p95_duration_seconds: float
    guardrail_violations: int


def _call_to_summary(record: CallRecord) -> CallSummary:
    return CallSummary(
        call_id=record.call_id,
        room_name=record.room_name,
        scenario=record.scenario,
        channel=record.channel,
        voice_provider=record.voice_provider,
        llm_model=record.llm_model,
        status=record.status,
        outcome=record.outcome,
        started_at=record.started_at,
        ended_at=record.ended_at,
        duration_seconds=record.duration_seconds,
        turn_count=record.turn_count,
        sentiment=record.sentiment,
        language=record.language,
        order_number=record.order_number,
        guardrail_violations=record.guardrail_violations,
    )


def _call_to_detail(record: CallRecord) -> CallDetail:
    try:
        turns = json.loads(record.transcript_json) if record.transcript_json else []
    except (ValueError, TypeError):
        turns = []
    return CallDetail(
        **_call_to_summary(record).model_dump(),
        transcript=[TranscriptTurn(**t) for t in turns if isinstance(t, dict)],
        error=record.error,
    )


def _conversation_session_to_response(row) -> ConversationSessionResponse:
    return ConversationSessionResponse(
        call_id=row.call_id,
        room_name=row.room_name,
        current_node=row.current_node,
        outcome=row.outcome,
    )


def _latest_order_summary(order) -> str | None:
    if order is None:
        return None
    return f"{order.public_code} ({order.status}, total {format_money(order.total)}, ETA {order.eta_minutes} minutes)"


_SERVER_STARTED_AT = time.time()


app = FastAPI(title="VoixAI MVP API", version="0.2.0")
allow_origins = [origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()]
allow_origin_regex = ALLOWED_ORIGIN_REGEX

# Local Next.js dev commonly shifts from :3000 to :3001+ when the default port
# is busy. When no explicit allowlist is configured, accept loopback origins so
# browser preflight requests keep working across local port changes.
if not os.getenv("ALLOWED_ORIGINS") and not allow_origin_regex:
    allow_origin_regex = DEFAULT_LOCAL_ORIGIN_REGEX

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_origin_regex=allow_origin_regex,
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
        line_errors = _api_validation_messages(_validation_errors_for_line(line))

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

    # Check for existing idempotent replay before building the record.
    existing = await asyncio.to_thread(ORDER_STORAGE.get_order_by_idempotency_key, key)
    if existing is not None:
        return _order_record_to_response(existing, idempotent_replay=True)

    quote = build_price_quote(order)
    order_json = json.dumps(payload.order.model_dump(mode="json"))
    order_payload = payload.order.model_dump(mode="json")

    if hasattr(ORDER_STORAGE, "_Session"):
        for _ in range(5):
            try:
                with ORDER_STORAGE._lock, ORDER_STORAGE._Session() as session:  # type: ignore[attr-defined]
                    existing_order = OrderService(session)._by_idempotency_key(key)
                    if existing_order is not None:
                        record = OrderRecord(
                            order_number=existing_order.public_code,
                            idempotency_key=existing_order.idempotency_key or key,
                            room_name=existing_order.room_name or payload.room_name,
                            status=existing_order.status,
                            subtotal=f"${existing_order.subtotal:,.2f}",
                            tax=f"${existing_order.tax:,.2f}",
                            total=f"${existing_order.total:,.2f}",
                            eta_minutes=existing_order.eta_minutes,
                            order_json=existing_order.order_json,
                            kitchen_ticket=existing_order.kitchen_ticket,
                            created_at=(existing_order.placed_at or existing_order.updated_at).timestamp(),
                        )
                        return _order_record_to_response(record, idempotent_replay=True)

                    MenuSeedService(session).seed_menu()
                    store = StoreService(session).get_default_store()
                    customer = None
                    if payload.order.phone.strip():
                        customer = CustomerService(session).upsert_by_phone(
                            payload.order.phone,
                            name=payload.order.customer_name,
                            preferred_language=payload.order.language,
                        )
                    order_number = make_public_code(session)
                    kitchen_ticket = _build_kitchen_ticket(order, quote, order_number)
                    draft = OrderService(session).create_draft(
                        public_code=order_number,
                        customer=customer,
                        store=store,
                        room_name=payload.room_name,
                        idempotency_key=key,
                    )
                    OrderService(session).mutate_lines(
                        draft,
                        line_inputs_from_quote(order_payload, quote.line_items),
                        subtotal=quote.subtotal,
                        tax=quote.tax,
                        total=quote.total,
                        eta_minutes=quote.eta_minutes,
                        order_json=order_json,
                        kitchen_ticket=kitchen_ticket,
                    )
                    confirmed = OrderService(session).confirm(draft, idempotency_key=key)
                    session.commit()
                    logger.info("Persisted order %s for room %s", confirmed.public_code, payload.room_name)
                    record = OrderRecord(
                        order_number=confirmed.public_code,
                        idempotency_key=confirmed.idempotency_key or key,
                        room_name=confirmed.room_name or payload.room_name,
                        status=confirmed.status,
                        subtotal=f"${confirmed.subtotal:,.2f}",
                        tax=f"${confirmed.tax:,.2f}",
                        total=f"${confirmed.total:,.2f}",
                        eta_minutes=confirmed.eta_minutes,
                        order_json=confirmed.order_json,
                        kitchen_ticket=confirmed.kitchen_ticket,
                        created_at=(confirmed.placed_at or confirmed.updated_at).timestamp(),
                    )
                    return _order_record_to_response(record, idempotent_replay=False)
            except Exception:
                logger.exception("SQLAlchemy order persist failed; retrying if possible")
        raise HTTPException(status_code=500, detail="Could not persist the order. Please retry.")

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
        result = await asyncio.to_thread(ORDER_STORAGE.insert_order, candidate)
        if result is not None:
            logger.info("Persisted order %s for room %s", candidate.order_number, candidate.room_name)
            return _order_record_to_response(candidate, idempotent_replay=False)
        # INSERT OR IGNORE returned rowcount 0 — either a concurrent idempotent
        # replay beat us, or an astronomically unlikely UUID collision.
        replay = await asyncio.to_thread(ORDER_STORAGE.get_order_by_idempotency_key, key)
        if replay is not None:
            return _order_record_to_response(replay, idempotent_replay=True)

    raise HTTPException(status_code=500, detail="Could not persist the order. Please retry.")


def _summarize_order_json(order_json: str) -> tuple[str, int, list[str], str | None]:
    """Extract (customer_name, item_count, item_summary, order_type) from a stored
    order payload for the dashboard list view."""
    try:
        data = json.loads(order_json)
    except (ValueError, TypeError):
        return "", 0, [], None
    items = data.get("items", []) if isinstance(data, dict) else []
    summary: list[str] = []
    count = 0
    for line in items:
        if not isinstance(line, dict):
            continue
        qty = int(line.get("quantity", 1) or 1)
        count += qty
        item_id = line.get("item_id", "")
        name = MENU_ITEMS[item_id].display_name if item_id in MENU_ITEMS else item_id
        summary.append(f"{qty}× {name}")
    return (
        str(data.get("customer_name", "") or ""),
        count,
        summary,
        data.get("order_type"),
    )


@app.get("/api/orders", response_model=OrderListResponse)
async def list_orders(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    room_name: str | None = Query(default=None),
) -> OrderListResponse:
    records, total = await asyncio.to_thread(
        ORDER_STORAGE.list_orders, limit=limit, offset=offset, room_name=room_name
    )
    orders: list[OrderListItem] = []
    for r in records:
        customer, count, summary, order_type = _summarize_order_json(r.order_json)
        orders.append(
            OrderListItem(
                order_number=r.order_number,
                room_name=r.room_name,
                status=r.status,
                customer_name=customer,
                item_count=count,
                item_summary=summary,
                subtotal=r.subtotal,
                tax=r.tax,
                total=r.total,
                eta_minutes=r.eta_minutes,
                order_type=order_type,
                created_at=r.created_at,
            )
        )
    return OrderListResponse(orders=orders, total=total, limit=limit, offset=offset)


@app.get("/api/orders/{order_number}", response_model=OrderSubmitResponse)
async def get_order(order_number: str) -> OrderSubmitResponse:
    record = await asyncio.to_thread(ORDER_STORAGE.get_order_by_number, order_number)
    if record is None:
        raise HTTPException(status_code=404, detail="Order not found.")
    return _order_record_to_response(record, idempotent_replay=False)


@app.get("/api/conversation/sessions/{call_id}", response_model=ConversationSessionResponse)
async def get_conversation_session(call_id: str) -> ConversationSessionResponse:
    def _get():
        with ORDER_STORAGE._lock, ORDER_STORAGE._Session() as session:  # type: ignore[attr-defined]
            from models import CallSession
            from sqlalchemy import select

            row = session.scalar(select(CallSession).where(CallSession.call_id == call_id))
            return _conversation_session_to_response(row) if row else None

    record = await asyncio.to_thread(_get)
    if record is None:
        raise HTTPException(status_code=404, detail="Conversation session not found.")
    return record


@app.patch("/api/conversation/sessions/{call_id}/node", response_model=ConversationSessionResponse)
async def update_conversation_node(
    call_id: str,
    payload: ConversationNodeUpdateRequest,
) -> ConversationSessionResponse:
    def _update():
        with ORDER_STORAGE._lock, ORDER_STORAGE._Session() as session:  # type: ignore[attr-defined]
            row = ConversationSessionService(session).set_current_node(
                call_id=call_id,
                room_name=payload.room_name,
                current_node=payload.current_node,
            )
            session.commit()
            return _conversation_session_to_response(row)

    return await asyncio.to_thread(_update)


@app.post("/api/conversation/identify", response_model=ConversationIdentifyResponse)
async def identify_conversation_caller(
    payload: ConversationIdentifyRequest,
) -> ConversationIdentifyResponse:
    def _identify():
        with ORDER_STORAGE._lock, ORDER_STORAGE._Session() as session:  # type: ignore[attr-defined]
            call_session, customer, is_returning, latest_order = ConversationSessionService(session).identify(
                call_id=payload.call_id,
                room_name=payload.room_name,
                caller_id=payload.caller_id,
                phone=payload.phone,
            )
            call_session.current_node = "IDENTIFY"
            session.commit()
            return ConversationIdentifyResponse(
                call_id=call_session.call_id,
                room_name=call_session.room_name,
                current_node=call_session.current_node,
                customer_id=customer.id if customer else None,
                phone=customer.phone if customer else normalize_phone(payload.phone or payload.caller_id),
                name=customer.name if customer else None,
                is_returning=is_returning,
                last_order_code=latest_order.public_code if latest_order else None,
                last_order_summary=_latest_order_summary(latest_order),
            )

    return await asyncio.to_thread(_identify)


@app.post("/api/conversation/name", response_model=ConversationIdentifyResponse)
async def persist_conversation_name(
    payload: ConversationNameRequest,
) -> ConversationIdentifyResponse:
    def _persist_name():
        with ORDER_STORAGE._lock, ORDER_STORAGE._Session() as session:  # type: ignore[attr-defined]
            conversation = ConversationSessionService(session).start_or_resume(
                call_id=payload.call_id,
                room_name=payload.room_name,
                current_node="IDENTIFY",
            )
            customer = None
            if payload.customer_id:
                from models import Customer

                customer = session.get(Customer, payload.customer_id)
            if customer is None:
                phone = normalize_phone(payload.phone)
                if not phone:
                    raise HTTPException(status_code=422, detail="A phone number is required to persist the caller name.")
                customer = CustomerService(session).upsert_by_phone(phone)
            customer = CustomerService(session).attach_name(customer.id, payload.name)
            latest_order = OrderService(session).get_latest_by_phone(customer.phone)
            session.commit()
            return ConversationIdentifyResponse(
                call_id=conversation.call_id,
                room_name=conversation.room_name,
                current_node=conversation.current_node,
                customer_id=customer.id,
                phone=customer.phone,
                name=customer.name,
                is_returning=True,
                last_order_code=latest_order.public_code if latest_order else None,
                last_order_summary=_latest_order_summary(latest_order),
            )

    return await asyncio.to_thread(_persist_name)


@app.post("/api/calls", response_model=CallDetail)
async def start_call(payload: CallStartRequest) -> CallDetail:
    """Open a call record at session start. Idempotent on ``call_id`` — a retried
    start returns the existing record rather than erroring."""
    existing = await asyncio.to_thread(ORDER_STORAGE.get_call_by_id, payload.call_id)
    if existing is not None:
        return _call_to_detail(existing)

    now = time.time()
    record = CallRecord(
        call_id=payload.call_id,
        room_name=payload.room_name,
        scenario=payload.scenario,
        channel=payload.channel,
        voice_provider=payload.voice_provider,
        llm_model=payload.llm_model,
        status="in_progress",
        outcome="unknown",
        started_at=payload.started_at or now,
        ended_at=None,
        duration_seconds=None,
        turn_count=0,
        sentiment=None,
        language=payload.language,
        order_number=None,
        transcript_json="[]",
        guardrail_violations=0,
        error=None,
        created_at=now,
    )
    result = await asyncio.to_thread(ORDER_STORAGE.insert_call, record)
    if result is None:
        replay = await asyncio.to_thread(ORDER_STORAGE.get_call_by_id, payload.call_id)
        if replay is not None:
            return _call_to_detail(replay)
        raise HTTPException(status_code=409, detail="Call already exists.")
    logger.info("Opened call %s for room %s", record.call_id, record.room_name)
    return _call_to_detail(record)


@app.patch("/api/calls/{call_id}", response_model=CallDetail)
async def update_call(call_id: str, payload: CallUpdateRequest) -> CallDetail:
    """Finalize or amend a call record (end time, transcript, outcome, sentiment)."""
    fields = payload.model_dump(exclude_none=True)
    transcript = fields.pop("transcript", None)
    if transcript is not None:
        fields["transcript_json"] = json.dumps(transcript)
    record = await asyncio.to_thread(ORDER_STORAGE.update_call, call_id, **fields)
    if record is None:
        raise HTTPException(status_code=404, detail="Call not found.")
    return _call_to_detail(record)


@app.get("/api/calls", response_model=CallListResponse)
async def list_calls(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    outcome: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> CallListResponse:
    records, total = await asyncio.to_thread(
        ORDER_STORAGE.list_calls,
        limit=limit,
        offset=offset,
        status=status,
        outcome=outcome,
        search=search,
    )
    return CallListResponse(
        calls=[_call_to_summary(r) for r in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/api/calls/{call_id}", response_model=CallDetail)
async def get_call(call_id: str) -> CallDetail:
    record = await asyncio.to_thread(ORDER_STORAGE.get_call_by_id, call_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Call not found.")
    return _call_to_detail(record)


def _money_to_float(value: str) -> float:
    try:
        return float(str(value).replace("$", "").replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


@app.get("/api/analytics/overview", response_model=AnalyticsOverview)
async def analytics_overview(
    window_hours: int = Query(default=24, ge=1, le=24 * 90),
    buckets: int = Query(default=12, ge=1, le=96),
) -> AnalyticsOverview:
    now = time.time()
    since = now - window_hours * 3600
    records = await asyncio.to_thread(ORDER_STORAGE.list_calls_since, since)

    total = len(records)
    completed = sum(1 for r in records if r.status == "completed")
    in_progress = sum(1 for r in records if r.status == "in_progress")
    failed = sum(1 for r in records if r.status == "failed")
    finished = [r for r in records if r.status != "in_progress"]
    orders_placed = sum(1 for r in records if r.order_number)
    transfers = sum(1 for r in records if r.outcome == "transfer")
    abandoned = sum(1 for r in records if r.outcome == "abandoned")

    durations = [r.duration_seconds for r in records if r.duration_seconds is not None]
    avg_duration = sum(durations) / len(durations) if durations else 0.0
    turns = [r.turn_count for r in records if r.turn_count]
    avg_turns = sum(turns) / len(turns) if turns else 0.0
    sentiments = [r.sentiment for r in records if r.sentiment is not None]
    avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else None

    outcomes: dict[str, int] = {}
    for r in records:
        outcomes[r.outcome] = outcomes.get(r.outcome, 0) + 1

    sentiment_breakdown = {"positive": 0, "neutral": 0, "negative": 0}
    for s in sentiments:
        if s >= 0.66:
            sentiment_breakdown["positive"] += 1
        elif s >= 0.4:
            sentiment_breakdown["neutral"] += 1
        else:
            sentiment_breakdown["negative"] += 1

    # Revenue: look up each linked order's total.
    revenue = 0.0
    for r in records:
        if not r.order_number:
            continue
        order = await asyncio.to_thread(ORDER_STORAGE.get_order_by_number, r.order_number)
        if order is not None:
            revenue += _money_to_float(order.total)

    # Time series buckets across the window.
    bucket_span = (window_hours * 3600) / buckets
    series: list[TimeBucket] = []
    for i in range(buckets):
        b_start = since + i * bucket_span
        b_end = b_start + bucket_span
        in_bucket = [r for r in records if b_start <= r.started_at < b_end]
        label = time.strftime("%H:%M", time.localtime(b_start)) if window_hours <= 48 else time.strftime("%m/%d", time.localtime(b_start))
        series.append(
            TimeBucket(
                label=label,
                start=b_start,
                calls=len(in_bucket),
                orders=sum(1 for r in in_bucket if r.order_number),
                completed=sum(1 for r in in_bucket if r.status == "completed"),
            )
        )

    success_rate = (completed / len(finished)) if finished else 0.0
    containment_rate = (1 - (transfers / len(finished))) if finished else 0.0

    return AnalyticsOverview(
        window_hours=window_hours,
        total_calls=total,
        completed_calls=completed,
        in_progress_calls=in_progress,
        failed_calls=failed,
        success_rate=round(success_rate, 4),
        containment_rate=round(containment_rate, 4),
        orders_placed=orders_placed,
        revenue_total=f"${revenue:,.2f}",
        avg_duration_seconds=round(avg_duration, 1),
        avg_turns=round(avg_turns, 1),
        avg_sentiment=round(avg_sentiment, 3) if avg_sentiment is not None else None,
        transfers=transfers,
        abandoned=abandoned,
        outcomes=outcomes,
        sentiment_breakdown=sentiment_breakdown,
        series=series,
    )


@app.get("/api/observability/health", response_model=ObservabilitySnapshot)
async def observability_health() -> ObservabilitySnapshot:
    now = time.time()
    records = await asyncio.to_thread(ORDER_STORAGE.list_calls_since, now - 7 * 24 * 3600)
    total = len(records)
    failed = sum(1 for r in records if r.status == "failed")
    error_rate = (failed / total) if total else 0.0
    durations = sorted(r.duration_seconds for r in records if r.duration_seconds is not None)
    avg_duration = sum(durations) / len(durations) if durations else 0.0
    p95 = durations[int(len(durations) * 0.95) - 1] if durations else 0.0
    guardrails = sum(r.guardrail_violations for r in records)
    orders_total = await asyncio.to_thread(ORDER_STORAGE.count_orders)

    db_ok = True
    try:
        await asyncio.to_thread(ORDER_STORAGE.count_orders)
    except Exception:
        db_ok = False

    livekit_configured = bool(LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET)

    components = [
        HealthComponent(
            name="API service",
            status="operational",
            detail="FastAPI request handler responding",
        ),
        HealthComponent(
            name="Order datastore",
            status="operational" if db_ok else "down",
            detail=f"SQLite WAL · {orders_total} orders persisted" if db_ok else "Datastore unreachable",
        ),
        HealthComponent(
            name="Realtime transport",
            status="operational" if livekit_configured else "degraded",
            detail="LiveKit credentials configured" if livekit_configured else "LiveKit credentials missing",
        ),
        HealthComponent(
            name="Idempotency guard",
            status="operational",
            detail="Order submission deduplicated on idempotency key",
        ),
    ]
    statuses = {c.status for c in components}
    overall = "down" if "down" in statuses else ("degraded" if "degraded" in statuses else "operational")

    return ObservabilitySnapshot(
        status=overall,
        uptime_seconds=round(now - _SERVER_STARTED_AT, 1),
        components=components,
        total_calls=total,
        failed_calls=failed,
        error_rate=round(error_rate, 4),
        orders_total=orders_total,
        avg_duration_seconds=round(avg_duration, 1),
        p95_duration_seconds=round(p95, 1),
        guardrail_violations=guardrails,
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
