"""Seed realistic call + order telemetry for the dashboard.

This populates the SAME SQLite store the API/runtime use, so the dashboard has
data to render before (or alongside) real calls. It is safe to re-run: every
seeded row uses a stable ``seed-*`` id, so a second run replaces the demo set
rather than duplicating it.

Usage (from repo root, using the API venv so `storage` imports cleanly):

    apps/api/.venv/Scripts/python.exe scripts/seed_dashboard.py
    # optionally:  --calls 60  --days 3
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

# Import the API's storage module (single source of truth for the schema).
API_SRC = Path(__file__).resolve().parent.parent / "apps" / "api"
sys.path.insert(0, str(API_SRC))

from storage import CallRecord, OrderRecord, build_storage  # noqa: E402

random.seed(7)

MENU = [
    ("6 pc Boneless Wings", "12.49"),
    ("10 pc Classic Wings", "15.99"),
    ("Wing Combo for 2", "27.99"),
    ("Large Cajun Fries", "5.49"),
    ("Veggie Sticks & Ranch", "4.29"),
    ("20 pc Family Bundle", "34.99"),
]
FLAVORS = ["Lemon Pepper", "Garlic Parmesan", "Original Hot", "Mango Habanero", "Cajun"]
NAMES = ["Maya", "Jordan", "Priya", "Carlos", "Aisha", "Liam", "Sofia", "Wei", "Noah", "Imani"]
MODELS = ["openai/gpt-5.3-chat-latest", "openai/gpt-5.3-chat-latest", "gpt-realtime"]
PROVIDERS = ["classic", "classic", "openai_realtime", "gemini_live"]


def _order_placed_transcript(name: str, item: str, flavor: str, number: str, total: str) -> list[dict]:
    return [
        {"role": "assistant", "text": "Thanks for calling Voix Wings! What can I get started for you?"},
        {"role": "user", "text": f"Hi, can I get a {item}?"},
        {"role": "assistant", "text": "Absolutely. What flavor would you like on those?"},
        {"role": "user", "text": f"{flavor}, please."},
        {"role": "assistant", "text": "Great choice. Anything else — fries or a drink?"},
        {"role": "user", "text": "No that's it, thank you."},
        {"role": "assistant", "text": f"Perfect. That's a {item}, {flavor}. Your total is {total}. Can I get a name for the order?"},
        {"role": "user", "text": f"It's {name}."},
        {"role": "assistant", "text": f"You're all set, {name}! Order {number} will be ready in about 18 minutes. See you soon!"},
    ]


def _info_transcript() -> list[dict]:
    return [
        {"role": "assistant", "text": "Thanks for calling Voix Wings! How can I help?"},
        {"role": "user", "text": "What are your hours today?"},
        {"role": "assistant", "text": "We're open until 11 PM tonight. Anything else I can help with?"},
        {"role": "user", "text": "No, that's all. Thanks!"},
        {"role": "assistant", "text": "You bet — have a great day!"},
    ]


def _transfer_transcript() -> list[dict]:
    return [
        {"role": "assistant", "text": "Thanks for calling Voix Wings! How can I help?"},
        {"role": "user", "text": "I have a problem with a catering invoice from last week."},
        {"role": "assistant", "text": "I'm sorry about that. Let me connect you with a team member who handles catering billing."},
    ]


def seed(num_calls: int, days: int) -> None:
    store = build_storage()
    now = time.time()
    window = days * 24 * 3600

    placed = info = transfer = abandoned = 0
    order_seq = 50000

    for i in range(num_calls):
        started = now - random.random() * window
        name = random.choice(NAMES)
        provider = random.choice(PROVIDERS)
        model = random.choice(MODELS)
        roll = random.random()

        order_number = None
        guardrails = 0

        if roll < 0.62:  # order placed
            item, price = random.choice(MENU)
            flavor = random.choice(FLAVORS)
            order_seq += 1
            order_number = f"MOCK-{order_seq}"
            subtotal = float(price)
            tax = round(subtotal * 0.0825, 2)
            total = round(subtotal + tax, 2)
            transcript = _order_placed_transcript(name, item, flavor, order_number, f"${total:.2f}")
            outcome, status = "order_placed", "completed"
            sentiment = round(random.uniform(0.7, 0.98), 3)
            duration = random.uniform(75, 150)
            placed += 1
            # Persist a matching order so revenue + Orders page line up.
            order_payload = {
                "items": [{"item_id": "boneless_6", "quantity": 1, "selected_flavor_ids": [flavor.lower()]}],
                "customer_name": name,
                "order_type": "pickup",
                "status": "submitted",
            }
            try:
                store.insert_order(
                    OrderRecord(
                        order_number=order_number,
                        idempotency_key=f"seed-{order_number}",
                        room_name=f"voixai-seed-{i}",
                        status="submitted",
                        subtotal=f"${subtotal:.2f}",
                        tax=f"${tax:.2f}",
                        total=f"${total:.2f}",
                        eta_minutes=random.choice([15, 18, 20, 22]),
                        order_json=json.dumps(order_payload),
                        kitchen_ticket=f"TICKET {order_number}\n1x {item} ({flavor})",
                        created_at=started + duration,
                    )
                )
            except Exception:
                pass  # already seeded
        elif roll < 0.80:  # info only
            transcript = _info_transcript()
            outcome, status = "info_only", "completed"
            sentiment = round(random.uniform(0.55, 0.85), 3)
            duration = random.uniform(25, 70)
            info += 1
        elif roll < 0.92:  # transfer
            transcript = _transfer_transcript()
            outcome, status = "transfer", "completed"
            sentiment = round(random.uniform(0.35, 0.6), 3)
            duration = random.uniform(30, 60)
            transfer += 1
        else:  # abandoned
            transcript = [{"role": "assistant", "text": "Thanks for calling Voix Wings! How can I help?"}]
            outcome, status = "abandoned", "completed"
            sentiment = round(random.uniform(0.3, 0.5), 3)
            duration = random.uniform(5, 18)
            abandoned += 1

        turn_count = sum(1 for t in transcript if t["role"] == "user")
        ended = started + duration

        record = CallRecord(
            call_id=f"seed-call-{i:04d}",
            room_name=f"voixai-seed-{i}",
            scenario="wingstop_inbound_ordering",
            channel=random.choice(["web", "phone", "phone"]),
            voice_provider=provider,
            llm_model=model,
            status=status,
            outcome=outcome,
            started_at=started,
            ended_at=ended,
            duration_seconds=round(duration, 1),
            turn_count=turn_count,
            sentiment=sentiment,
            language="english",
            order_number=order_number,
            transcript_json=json.dumps(transcript),
            guardrail_violations=guardrails,
            error=None,
            created_at=started,
        )
        # Replace on re-run.
        if store.get_call_by_id(record.call_id) is not None:
            store.update_call(
                record.call_id,
                status=status,
                outcome=outcome,
                ended_at=ended,
                duration_seconds=record.duration_seconds,
                turn_count=turn_count,
                sentiment=sentiment,
                order_number=order_number,
                transcript_json=record.transcript_json,
            )
        else:
            store.insert_call(record)

    print(f"Seeded {num_calls} calls across {days} day(s):")
    print(f"  order_placed={placed}  info_only={info}  transfer={transfer}  abandoned={abandoned}")
    print("Open the dashboard at /dashboard to view them.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed dashboard demo telemetry.")
    parser.add_argument("--calls", type=int, default=48, help="Number of calls to seed")
    parser.add_argument("--days", type=int, default=2, help="Spread calls across N days")
    args = parser.parse_args()
    seed(args.calls, args.days)
