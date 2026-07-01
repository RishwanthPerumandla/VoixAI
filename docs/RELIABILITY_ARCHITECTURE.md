# Reliability Architecture

VoixAI now treats conversation and order truth as separate concerns.

## What Owns What

- The LLM owns the conversation flow, tone, and when to call tools.
- `packages/ordering` owns order truth.
- The reducer owns state mutation.
- Validation runs after every mutation.
- The state machine owns lifecycle status and submit authorization.
- The catalog at `apps/api/data/wingstop_demo_catalog.json` owns menu truth.

## Catalog-Driven Validation

The menu catalog replaces ad-hoc menu logic with structured validation:

- **Item templates** define required slots, optional slots, max flavors, and modifier group associations. The LLM no longer needs to "know" what an item allows — it reads slot definitions from the catalog.
- **Combo templates** encode the main component, included side/drink/dip counts, and rules (e.g., whether all-flats is allowed). Combo requirements like "must include a side and drink" are enforced by the validation engine, not prompt engineering.
- **Modifier groups** declare which item types they apply to, whether they are required, and max selection counts. The validation engine checks modifier validity against the group definitions, eliminating item-modifier mismatch bugs.
- **Flavors** carry an `allowed_for_item_types` list so the same flavor database serves wings, tenders, sandwiches, and fries — each with its own permitted set.
- **Synonyms** normalize customer input ("bone in" → "classic_wings") at the catalog level so item lookups are consistent across the codebase.

The validation engine in `packages/ordering/src/voix_ordering/validation.py` reads the catalog directly rather than duplicating rules in Python code. This means a menu change (new combo, new modifier, new flavor restriction) is a JSON edit — no Python changes required.

## Lifecycle

The explicit order statuses are:

- `idle`
- `greeting`
- `collecting_order`
- `validating_order`
- `pricing_order`
- `awaiting_confirmation`
- `submitting_order`
- `completed`
- `cancelled`
- `handoff_required`
- `failed`

The runtime can still sound natural, but submission is no longer a prompt-only sequence. `create_mock_order` re-validates and re-checks confirmation every time before placement.

## Intent Schema

The shared ordering package now exposes a structured intent model for:

- `add_item`
- `remove_item`
- `replace_item`
- `modify_item`
- `change_quantity`
- `change_flavor`
- `change_cook_preference`
- `change_piece_preference`
- `ask_total`
- `ask_menu`
- `confirm_order`
- `cancel_order`
- `restart_order`
- `handoff_request`
- `complaint`
- `unknown`

Each intent can carry target item details, replacement values, confidence, and clarification metadata.

## Reducer Rules

- Valid fields are preserved when an item type changes.
- Invalid modifiers are removed automatically when they no longer apply.
- Validation runs after every reducer mutation.
- Completed orders are immutable unless the customer starts a new order.
- `cancel_order` clears active items and marks the order `cancelled`.
- `restart_order` archives the old state and creates a fresh active order.
- Ambiguous targets trigger clarification instead of guessing.

Example:

- `10 classic wings + lemon pepper + all flats`
- Customer says: `make it boneless`
- Reducer output:
  - item becomes `boneless_10`
  - flavor remains
  - `all_flats` is removed
  - an `invalid_modifier_removed` event is recorded

## Telemetry

Telemetry now includes:

- reliability metrics
- recent reducer events
- last clarification question
- archived order count

The developer panel shows correction count, cancellations, validation failures, clarifications, unknown-item count, duplicate-submit prevention, final status, and the most recent reducer event.

## Replay And Regressions

Saved intent sequences can be replayed against the reducer with `replay_order_intents(...)`. This turns failed live sessions into deterministic regression fixtures.
