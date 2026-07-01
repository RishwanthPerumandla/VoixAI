# Showcase Demo Script

Use this flow to show the reliability layer, not just the happy path.

## Demo Goal

Show that VoixAI can survive messy customer behavior without corrupting order state.

## Suggested Demo

1. Start a pickup order for `Rishi`.
2. Add `10 classic wings`, half `Lemon Pepper`, half `Mango Habanero`, `well done`, `all flats`.
3. Add `large seasoned fries`, `extra crispy`, and `ranch`.
4. Change the wings to `boneless`.
5. Point out that `all flats` is removed automatically.
6. Change the wings back to `classic bone in`.
7. Ask for the total.
8. Ask the agent to review the order.
9. Confirm and place the order.

## Messy-Flow Variants

Use one or two of these during the demo:

- `Cancel the fries.`
- `Start over.`
- `Make it two.`
  Expected: clarification if multiple wing lines exist.
- `Actually make that boneless.`
  Expected: invalid piece preference is removed safely.
- `Can I get sushi?`
  Expected: clarification, not hallucination.
- `Get me a manager.`
  Expected: handoff flow.

## Validation Rules Enforced During Demo

The catalog-driven validation engine enforces these rules during every interaction:

- **Combos strictly require a side and drink** — the agent cannot confirm a combo order without both selections.
- **All flats / all drums are only valid on classic wings** — the reducer automatically removes them if the item type changes to boneless (and the developer panel shows the `invalid_modifier_removed` event).
- **Flavor limits are validated** — max flavors are enforced per item template; exceeding them triggers a `flavor_limit_adjusted` event and the extra flavors are trimmed.

## What To Call Out

- The model is conversational, but the backend owns truth.
- Mutations go through a reducer instead of raw prompt logic.
- Validation runs after each mutation.
- Replacements and cancellations are first-class flows.
- Reducer events and reliability counters show up in the developer panel.
- Replay fixtures now cover messy transcripts, so live failures can become regression tests.
