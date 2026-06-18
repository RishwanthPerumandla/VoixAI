# Mock Menu

This repository now uses a realistic wing-restaurant demo menu for the VoixAI Wingstop scenario.

Important:

- This is not an official Wingstop menu.
- The in-call restaurant name is `Voix Wings Demo`.
- Prices are demo prices only.
- Real production menus should come from a POS or menu source such as Square, Clover, Toast, or another restaurant menu API.

## What the demo menu includes

- Wing Combos
- Wings By The Piece
- Boneless Wings
- Crispy Tenders
- Chicken Sandwich
- Group Packs
- Fries
- Sides
- Dips
- Drinks
- Desserts

## Reliability model

The voice agent now relies on:

- a structured in-memory order state
- menu-backed item validation
- flavor validation and flavor-count limits
- modifier-group validation
- priced line-item breakdowns
- a confirmation gate before mock order creation

The structured order state tracks:

```json
{
  "items": [],
  "modifiers": [],
  "quantity": 1,
  "order_type": "pickup",
  "customer_name": "",
  "phone": "",
  "notes": "",
  "status": "collecting"
}
```

In practice, each order item is stored as a structured line item with:

- menu item id
- quantity
- selected flavors
- selected modifiers
- notes

## Validation rules

The current demo validation enforces:

- item must exist
- item must be available
- flavor must exist and be available
- flavor count cannot exceed the item limit
- classic bone-in wings can use `All Flats` or `All Drums`
- boneless wings cannot use `All Flats` or `All Drums`
- combos require drink and side selections
- order creation is blocked until the order is reviewed, priced, confirmed, and validated

## Pricing rules

The current demo quote logic supports:

- base item price
- quantity
- all-flats and all-drums upcharges
- priced modifier add-ons
- subtotal
- tax
- total
- ETA based on the slowest item in the order

## Known limitation

Assistant response auditing is deterministic, but it currently runs immediately after each assistant turn is generated and logged. It detects pricing or order-placement mismatches and surfaces them in telemetry, but it is not yet a full pre-speech rewrite or hard block layer inside the current LiveKit runtime flow.
