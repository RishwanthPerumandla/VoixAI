# Menu Catalog Architecture

## Why flat menus break voice agents

Static flat menu dicts (e.g., `{"name": "10pc wings", "price": 13.99}`) have no concept of slots, modifiers, or item relationships. Voice agents hallucinate invalid combinations because there is no machine-readable structure to validate against.

Combo orders degrade into ad-hoc logic scattered across prompt strings and tool implementations. Replacing items corrupts state because there is no definition of which modifier is valid for which item type.

## POS-grade catalog

The catalog at `apps/api/data/wingstop_demo_catalog.json` is the single source of truth for all menu data. It defines:

### Item templates
Individual (non-combo) menu items with:
- `id`, `name`, `item_type`, `base_price`
- `required_slots` - slots that must be filled (e.g., `flavor_selection`)
- `optional_slots` - slots the customer may choose
- `max_flavors`, `included_dip_count`, `modifier_group_ids`

### Combo templates
Combo items with:
- `main_component` - the primary chicken item (type + piece count)
- `included_components` - side, drink, dip counts included in the base price
- `rules` - whether piece_preference, all_flats, all_drums are allowed
- `required_slots` - always includes `combo_side_selection` and `combo_drink_selection`

### Group pack templates
Multi-serving packs with:
- `main_component` - allows classic or boneless choice
- `serves`, `max_flavors`, `included_components`
- `rules.wing_type_required` - forces agent to ask classic vs boneless

### Modifier groups
Reusable groups like `piece_preference`, `dip_selection`, `combo_side_selection` with:
- `applies_to_item_types` - which item types can use each group
- `required`, `max_select`, options with price_deltas

### Flavors
Sauce/dry rub options with:
- `flavor_type` (sauce, dry_rub, none), `heat_level`
- `allowed_for_item_types` - which item types can use each flavor

### Synonyms
Input normalization mappings so the agent resolves "bone in" to "classic_wings".

## Required slots

- `flavor_selection` - wings/tenders/sandwich must have a flavor (or "plain")
- `combo_side_selection` - combos require a side
- `combo_drink_selection` - combos require a drink
- `piece_preference` - optional selection of mixed/all flats/all drums

## Optional slots

- `piece_preference` (classic wings only)
- `wing_cook_preference` (classic wings, boneless wings, crispy tenders)
- `dip_selection` (most chicken items)
- `fry_cook_preference` (fries)
- `fry_seasoning_level` (fries)
- `fry_add_ons` (fries)

## Validation rules (code, not just JSON)

The validation engine at `packages/ordering/src/voix_ordering/validation.py` enforces:

1. Item/template exists and is available
2. Required slots must be filled before pricing/confirmation
3. Flavors must exist, be available, and be allowed for the item type
4. Flavor count must not exceed max_flavors for the item/size
5. Modifiers must exist, be available, and be allowed for the item type
6. `all_flats`/`all_drums` only for `classic_wings`
7. Cook preference only for wings, tenders, and fries (not drinks/desserts)
8. Combo requires side AND drink
9. Group pack requires wing type (if template allows classic or boneless)

## Reducer behavior

The reducer at `packages/ordering/src/voix_ordering/reducer.py` handles deterministic order mutations:

### Safe item replacement
- classic_wings -> boneless_wings: preserves quantity, flavors, dips, cook preference; removes piece_preference; emits `invalid_modifier_removed` event
- boneless_wings -> classic_wings: preserves quantity, flavors, dips, cook preference; allows piece_preference
- Combo type change: preserves side/drink/dip when valid; removes invalid slots

### Flavor limit enforcement
- When quantity changes, max_flavors is recomputed
- If existing flavors exceed new max, they are trimmed with a `flavor_limit_adjusted` event
- Half-and-half is valid when max_flavors >= 2

### Cancel/restart
- Cancel order: clears all items, sets status to cancelled
- Cancel item: removes target item only; if ambiguous, asks for clarification
- Restart: archives previous state, creates fresh empty order

## How this supports reliable tool calls

- Backend tools (validate_order, price_order) return structured results
- Gemini receives validation errors/warnings as structured data
- Confirmation gating prevents invalid orders
- Repricing happens after every state change
- Duplicate confirmation prevention (once COMPLETED, cannot re-submit)

## Future POS integration

The catalog schema is designed to map to real POS systems:
- `item_templates` map to POS menu items
- `modifier_groups` map to POS modifier groups
- `combo_templates` map to POS combo/meal deal definitions
- Validation rules encode POS business logic
- Synonyms handle cross-system item name differences
