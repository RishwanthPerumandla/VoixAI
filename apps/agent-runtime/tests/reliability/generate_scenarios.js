const fs = require("fs");
const path = require("path");

const OUT_PATH = path.join(
  __dirname,
  "scenarios",
  "generated_wingstop_reliability.json",
);

function item(
  lineId,
  itemId,
  selectedFlavorIds = [],
  selectedModifierIds = [],
  quantity = 1,
  notes = "",
) {
  return {
    line_id: lineId,
    item_id: itemId,
    quantity,
    selected_flavor_ids: selectedFlavorIds,
    selected_modifier_ids: selectedModifierIds,
    notes,
  };
}

function scenario(name, description, tags, initial_state, turns, final_expected) {
  return { name, description, tags, initial_state, turns, final_expected };
}

const scenarios = [];
const customers = ["Cherry", "Rishi", "Sofia", "Mateo", "Ava", "Liam", "Nina", "Leo", "Maya", "Noah"];

function pushHappy(config) {
  scenarios.push(
    scenario(
      config.name,
      config.description,
      ["happy_paths"],
      config.initial_state,
      [
        { user: config.order_text, expected: { contains_items: config.expected_items } },
        {
          user: "What's my total?",
          expected: { telemetry_events: ["price_quoted"], total_present: true },
        },
        {
          user: "Review the order.",
          expected: {
            telemetry_events: ["confirmation_review_ready"],
            response_contains: ["Should I place it?"],
          },
        },
        {
          user: "Yes, place it.",
          expected: {
            telemetry_events: ["mock_order_created"],
            order_id_created: true,
            response_contains: ["order was placed"],
          },
        },
      ],
      {
        status: "completed",
        item_count: config.expected_items.length,
        completed_order: true,
      },
    ),
  );
}

[
  {
    name: "happy_classic_10_split",
    description: "Classic wings with split flavors and modifiers.",
    initial_state: { order_type: "pickup", customer_name: "Cherry" },
    order_text:
      "Add 10 classic wings with lemon pepper and mango habanero, all flats, well done, and ranch.",
    expected_items: ["classic_10"],
  },
  {
    name: "happy_boneless_8_ranch",
    description: "Boneless order prices and places cleanly.",
    initial_state: { order_type: "pickup", customer_name: "Rishi" },
    order_text: "Add 8 boneless wings with garlic parmesan and ranch.",
    expected_items: ["boneless_8"],
  },
  {
    name: "happy_classic_6_blue_cheese",
    description: "Single flavor classic wings with dip.",
    initial_state: { order_type: "pickup", customer_name: "Sofia" },
    order_text: "Add 6 bone in wings with original hot and blue cheese.",
    expected_items: ["classic_6"],
  },
  {
    name: "happy_tenders_3_hot_ranch",
    description: "Small tenders order succeeds.",
    initial_state: { order_type: "pickup", customer_name: "Mateo" },
    order_text: "Add 3 tenders with original hot and ranch.",
    expected_items: ["tenders_3"],
  },
  {
    name: "happy_sandwich_combo",
    description: "Combo order with side and drink succeeds.",
    initial_state: { order_type: "pickup", customer_name: "Ava" },
    order_text: "Add chicken sandwich combo with fries, coke, and plain.",
    expected_items: ["chicken_sandwich_combo"],
  },
  {
    name: "happy_large_fries",
    description: "Standalone fries order can be priced and placed.",
    initial_state: { order_type: "pickup", customer_name: "Liam" },
    order_text: "Add large fries extra crispy.",
    expected_items: ["large_fries"],
  },
  {
    name: "happy_family_pack",
    description: "Family pack with multiple flavors succeeds.",
    initial_state: { order_type: "pickup", customer_name: "Nina" },
    order_text: "Add family pack with lemon pepper, original hot, and garlic parmesan, all flats.",
    expected_items: ["family_pack_24pc"],
  },
  {
    name: "happy_combo_boneless_10",
    description: "Boneless combo with valid drink and side.",
    initial_state: { order_type: "pickup", customer_name: "Maya" },
    order_text: "Add 10 boneless combo with fries, sprite, lemon pepper, and ranch.",
    expected_items: ["combo_boneless_10"],
  },
  {
    name: "happy_meal_for_2",
    description: "Meal for two group pack succeeds.",
    initial_state: { order_type: "pickup", customer_name: "Noah" },
    order_text: "Add meal for 2 with lemon pepper and original hot, all drums, and fries.",
    expected_items: ["meal_for_2_15pc"],
  },
  {
    name: "happy_classic_20_three_flavors",
    description: "Twenty classic wings allow three flavors.",
    initial_state: { order_type: "pickup", customer_name: "Cherry" },
    order_text: "Add 20 bone in wings with lemon pepper, original hot, and garlic parmesan, ranch.",
    expected_items: ["classic_20"],
  },
  {
    name: "happy_boneless_50_four_flavors",
    description: "Fifty boneless wings allow four flavors.",
    initial_state: { order_type: "pickup", customer_name: "Rishi" },
    order_text:
      "Add 50 boneless wings with lemon pepper, original hot, garlic parmesan, and mango habanero, ranch.",
    expected_items: ["boneless_50"],
  },
  {
    name: "happy_party_pack_delivery",
    description: "Delivery order can still review and place.",
    initial_state: { order_type: "delivery", customer_name: "Sofia" },
    order_text:
      "Add party pack with lemon pepper, original hot, garlic parmesan, and mango habanero, all flats.",
    expected_items: ["party_pack_50pc"],
  },
  {
    name: "happy_classic_15_two_dips",
    description: "Included dip count can support multiple dips.",
    initial_state: { order_type: "pickup", customer_name: "Mateo" },
    order_text: "Add 15 bone in wings with lemon pepper and original hot, ranch, and blue cheese.",
    expected_items: ["classic_15"],
  },
  {
    name: "happy_chicken_sandwich",
    description: "Standalone sandwich succeeds.",
    initial_state: { order_type: "pickup", customer_name: "Ava" },
    order_text: "Add chicken sandwich with plain.",
    expected_items: ["chicken_sandwich"],
  },
  {
    name: "happy_32oz_drink",
    description: "Standalone drink succeeds.",
    initial_state: { order_type: "pickup", customer_name: "Liam" },
    order_text: "Add 32 oz drink.",
    expected_items: ["fountain_drink_32oz"],
  },
  {
    name: "happy_brownie",
    description: "Standalone dessert succeeds.",
    initial_state: { order_type: "pickup", customer_name: "Nina" },
    order_text: "Add brownie.",
    expected_items: ["brownie"],
  },
  {
    name: "happy_crew_pack",
    description: "Crew pack with valid flavors succeeds.",
    initial_state: { order_type: "pickup", customer_name: "Leo" },
    order_text: "Add crew pack with lemon pepper, original hot, and hickory smoked bbq, all drums.",
    expected_items: ["crew_pack_30pc"],
  },
  {
    name: "happy_combo_classic_8",
    description: "Classic combo with all flats succeeds.",
    initial_state: { order_type: "pickup", customer_name: "Maya" },
    order_text:
      "Add 8 classic combo with lemon pepper and original hot, fries, coke, all flats, and ranch.",
    expected_items: ["combo_classic_8"],
  },
].forEach(pushHappy);

scenarios.push(
  scenario(
    "happy_voodoo_fries_and_drink",
    "Two-item order across separate turns.",
    ["happy_paths"],
    { order_type: "pickup", customer_name: "Leo" },
    [
      { user: "Add voodoo fries.", expected: { contains_items: ["voodoo_fries"] } },
      {
        user: "Add 20 oz drink.",
        expected: { contains_items: ["voodoo_fries", "fountain_drink_20oz"] },
      },
      {
        user: "What's my total?",
        expected: { telemetry_events: ["price_quoted"], total_present: true },
      },
      {
        user: "Review the order.",
        expected: { telemetry_events: ["confirmation_review_ready"] },
      },
      {
        user: "Yes, place it.",
        expected: { telemetry_events: ["mock_order_created"], order_id_created: true },
      },
    ],
    { status: "completed", item_count: 2, completed_order: true },
  ),
);

scenarios.push(
  scenario(
    "happy_multi_item_order",
    "Multiple items can be placed together.",
    ["happy_paths"],
    { order_type: "pickup", customer_name: "Noah" },
    [
      {
        user: "Add 10 classic wings with lemon pepper, ranch, and well done.",
        expected: { contains_items: ["classic_10"] },
      },
      {
        user: "Add large fries extra crispy.",
        expected: { contains_items: ["classic_10", "large_fries"] },
      },
      {
        user: "What's my total?",
        expected: { telemetry_events: ["price_quoted"], total_present: true },
      },
      {
        user: "Review the order.",
        expected: { telemetry_events: ["confirmation_review_ready"] },
      },
      {
        user: "Yes, place it.",
        expected: { telemetry_events: ["mock_order_created"], order_id_created: true },
      },
    ],
    { status: "completed", item_count: 2, completed_order: true },
  ),
);

pushHappy({
  name: "happy_water_order",
  description: "Bottled water order succeeds.",
  initial_state: { order_type: "pickup", customer_name: "Maya" },
  order_text: "Add water.",
  expected_items: ["drink_water_item"],
});
pushHappy({
  name: "happy_cheese_fries_order",
  description: "Cheese fries order succeeds.",
  initial_state: { order_type: "pickup", customer_name: "Noah" },
  order_text: "Add cheese fries extra crispy.",
  expected_items: ["cheese_fries"],
});

const correctionConfigs = [
  ["correction_classic_to_boneless", item("line-1", "classic_10", ["lemon_pepper"], ["all_flats", "well_done"]), "Actually make that 10 boneless wings.", ["boneless_10"]],
  ["correction_boneless_to_classic", item("line-1", "boneless_10", ["lemon_pepper"], ["well_done"]), "Actually make that 10 classic wings.", ["classic_10"]],
  ["correction_change_flavor_to_garlic", item("line-1", "classic_10", ["lemon_pepper"], ["ranch"]), "Actually change it to garlic parmesan.", ["classic_10"]],
  ["correction_add_second_flavor", item("line-1", "classic_10", ["lemon_pepper"], []), "Actually make that lemon pepper and mango habanero.", ["classic_10"]],
  ["correction_classic_10_to_20", item("line-1", "classic_10", ["lemon_pepper"], []), "Actually make that 20 classic wings.", ["classic_20"]],
  ["correction_boneless_10_to_20", item("line-1", "boneless_10", ["lemon_pepper"], []), "Actually make that 20 boneless wings.", ["boneless_20"]],
  ["correction_add_ranch_later", item("line-1", "classic_10", ["lemon_pepper"], []), "Actually add ranch.", ["classic_10"]],
  ["correction_add_well_done_later", item("line-1", "classic_10", ["lemon_pepper"], []), "Actually make that well done.", ["classic_10"]],
  ["correction_sandwich_to_combo", item("line-1", "chicken_sandwich", ["plain"], []), "Actually make that chicken sandwich combo.", ["chicken_sandwich_combo"]],
  ["correction_combo_to_classic", item("line-1", "chicken_sandwich_combo", ["plain"], ["regular_seasoned_fries", "coke"]), "Actually make that 10 classic wings.", ["classic_10"]],
  ["correction_tenders_to_boneless", item("line-1", "tenders_6", ["original_hot"], ["ranch"]), "Actually make that 10 boneless wings.", ["boneless_10"]],
  ["correction_classic_6_to_10", item("line-1", "classic_6", ["lemon_pepper"], ["ranch"]), "Actually make that 10 classic wings.", ["classic_10"]],
  ["correction_classic_10_to_15", item("line-1", "classic_10", ["lemon_pepper"], ["ranch"]), "Actually make that 15 classic wings.", ["classic_15"]],
  ["correction_family_to_party", item("line-1", "family_pack_24pc", ["lemon_pepper", "original_hot"], ["all_flats"]), "Actually make that party pack.", ["party_pack_50pc"]],
  ["correction_party_to_crew", item("line-1", "party_pack_50pc", ["lemon_pepper", "original_hot", "garlic_parmesan"], ["all_drums"]), "Actually make that crew pack.", ["crew_pack_30pc"]],
  ["correction_hot_to_lemon", item("line-1", "classic_10", ["original_hot"], ["ranch"]), "Actually change it to lemon pepper.", ["classic_10"]],
  ["correction_lemon_to_garlic_and_ranch", item("line-1", "classic_10", ["lemon_pepper"], []), "Actually make that garlic parmesan and ranch.", ["classic_10"]],
  ["correction_mixed_language_boneless", item("line-1", "classic_10", ["lemon_pepper"], ["all_flats"]), "Mejor hazlas 10 boneless wings.", ["boneless_10"]],
];

correctionConfigs.forEach(([name, seededItem, turn, expectedItems]) => {
  scenarios.push(
    scenario(
      name,
      "Single correction path.",
      ["corrections"],
      { order_type: "pickup", customer_name: "Cherry", items: [seededItem] },
      [{ user: turn, expected: { contains_items: expectedItems, telemetry_events: ["validation_passed"] } }],
      { status: "collecting_order", line_item_ids: expectedItems, correction_count: 1 },
    ),
  );
});

[
  ["correction_remove_fries", [item("line-1", "classic_10", ["lemon_pepper"], ["ranch"]), item("line-2", "large_fries", [], ["extra_crispy"])], "Remove the fries.", ["classic_10"]],
  ["correction_remove_drink", [item("line-1", "classic_10", ["lemon_pepper"], ["ranch"]), item("line-2", "fountain_drink_20oz", [], [])], "Remove the drink.", ["classic_10"]],
  ["correction_remove_dip", [item("line-1", "classic_10", ["lemon_pepper"], []), item("line-2", "side_ranch")], "Remove the ranch dip.", ["classic_10"]],
  ["correction_remove_brownie", [item("line-1", "classic_10", ["lemon_pepper"], []), item("line-2", "brownie")], "Remove the brownie.", ["classic_10"]],
  ["correction_remove_sandwich", [item("line-1", "chicken_sandwich", ["plain"], []), item("line-2", "large_fries", [], [])], "Remove the sandwich.", ["large_fries"]],
].forEach(([name, items, turn, expectedItems]) => {
  scenarios.push(
    scenario(
      name,
      "Removal correction path.",
      ["corrections"],
      { order_type: "pickup", customer_name: "Rishi", items },
      [{ user: turn, expected: { items: expectedItems, telemetry_events: ["item_removed"] } }],
      { status: "collecting_order", line_item_ids: expectedItems, cancellation_count: 1 },
    ),
  );
});

scenarios.push(
  scenario(
    "correction_after_price",
    "Changing item after pricing clears checkout state.",
    ["corrections"],
    { order_type: "pickup", customer_name: "Sofia", items: [item("line-1", "classic_10", ["lemon_pepper"], ["ranch"])] },
    [
      { user: "What's my total?", expected: { telemetry_events: ["price_quoted"], total_present: true } },
      { user: "Actually make that 20 classic wings.", expected: { contains_items: ["classic_20"] } },
      { user: "What's my total?", expected: { telemetry_events: ["price_quoted", "subtotal_changed"], total_present: true } },
    ],
    { status: "pricing_order", line_item_ids: ["classic_20"], correction_count: 1 },
  ),
);

scenarios.push(
  scenario(
    "correction_during_confirmation",
    "Changing the order after recap requires repricing and re-review.",
    ["corrections"],
    { order_type: "pickup", customer_name: "Mateo", items: [item("line-1", "classic_10", ["lemon_pepper"], ["ranch"])] },
    [
      { user: "What's my total?", expected: { telemetry_events: ["price_quoted"], total_present: true } },
      { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } },
      { user: "Actually make that 10 boneless wings.", expected: { contains_items: ["boneless_10"] } },
      { user: "What's my total?", expected: { telemetry_events: ["price_quoted", "subtotal_changed"], total_present: true } },
      { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } },
      { user: "Yes, place it.", expected: { telemetry_events: ["mock_order_created"], order_id_created: true } },
    ],
    { status: "completed", line_item_ids: ["boneless_10"], completed_order: true, correction_count: 1 },
  ),
);

[
  scenario(
    "correction_repeated_two_steps",
    "Multiple corrections accumulate metrics.",
    ["corrections"],
    { order_type: "pickup", customer_name: "Ava", items: [item("line-1", "classic_10", ["lemon_pepper"], ["all_flats"])] },
    [
      { user: "Actually make that 10 boneless wings.", expected: { contains_items: ["boneless_10"], telemetry_events: ["invalid_modifier_removed"] } },
      { user: "Actually make that 20 boneless wings.", expected: { contains_items: ["boneless_20"] } },
    ],
    { status: "collecting_order", line_item_ids: ["boneless_20"], correction_count: 2 },
  ),
  scenario(
    "correction_repeated_three_steps",
    "Three corrections remain stable.",
    ["corrections"],
    { order_type: "pickup", customer_name: "Liam", items: [item("line-1", "classic_10", ["lemon_pepper"], ["well_done"])] },
    [
      { user: "Actually make that garlic parmesan.", expected: { contains_items: ["classic_10"] } },
      { user: "Actually add ranch.", expected: { contains_items: ["classic_10"] } },
      { user: "Actually make that 20 classic wings.", expected: { contains_items: ["classic_20"] } },
    ],
    { status: "collecting_order", line_item_ids: ["classic_20"], correction_count: 3 },
  ),
  scenario(
    "correction_remove_after_price",
    "Removing an item after a quote supports repricing.",
    ["corrections"],
    {
      order_type: "pickup",
      customer_name: "Nina",
      items: [item("line-1", "classic_10", ["lemon_pepper"], ["ranch"]), item("line-2", "large_fries", [], ["extra_crispy"])],
    },
    [
      { user: "What's my total?", expected: { telemetry_events: ["price_quoted"], total_present: true } },
      { user: "Remove the fries.", expected: { items: ["classic_10"], telemetry_events: ["item_removed"] } },
      { user: "What's my total?", expected: { telemetry_events: ["price_quoted", "subtotal_changed"], total_present: true } },
    ],
    { status: "pricing_order", line_item_ids: ["classic_10"], cancellation_count: 1 },
  ),
  scenario(
    "correction_add_extra_dip_after_price",
    "Adding a second dip changes the quote.",
    ["corrections"],
    { order_type: "pickup", customer_name: "Leo", items: [item("line-1", "classic_10", ["lemon_pepper"], ["ranch"])] },
    [
      { user: "What's my total?", expected: { telemetry_events: ["price_quoted"], total_present: true } },
      { user: "Actually add blue cheese.", expected: { contains_items: ["classic_10"] } },
      { user: "What's my total?", expected: { telemetry_events: ["price_quoted", "subtotal_changed"], total_present: true } },
    ],
    { status: "pricing_order", line_item_ids: ["classic_10"], correction_count: 1 },
  ),
  scenario(
    "correction_finish_after_changes",
    "Order can still finish after repeated changes.",
    ["corrections"],
    { order_type: "pickup", customer_name: "Maya", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] },
    [
      { user: "Actually add ranch.", expected: { contains_items: ["classic_10"] } },
      { user: "Actually make that 20 classic wings.", expected: { contains_items: ["classic_20"] } },
      { user: "What's my total?", expected: { telemetry_events: ["price_quoted"], total_present: true } },
      { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } },
      { user: "Yes, place it.", expected: { telemetry_events: ["mock_order_created"], order_id_created: true } },
    ],
    { status: "completed", line_item_ids: ["classic_20"], completed_order: true, correction_count: 2 },
  ),
  scenario(
    "correction_turns_to_new_item",
    "Correction can replace a single-item order with a dessert.",
    ["corrections"],
    { order_type: "pickup", customer_name: "Noah", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] },
    [{ user: "Actually make that brownie.", expected: { contains_items: ["brownie"] } }],
    { status: "collecting_order", line_item_ids: ["brownie"], correction_count: 1 },
  ),
].forEach((entry) => scenarios.push(entry));

for (const scenarioEntry of scenarios) {
  if (scenarioEntry.name === "correction_add_ranch_later") {
    scenarioEntry.final_expected.correction_count = 0;
  }
  if (scenarioEntry.name === "correction_add_well_done_later") {
    scenarioEntry.final_expected.correction_count = 0;
  }
  if (scenarioEntry.name === "correction_sandwich_to_combo") {
    scenarioEntry.turns[0].expected.telemetry_events = ["validation_failed"];
    scenarioEntry.final_expected.validation_failure_count = 1;
  }
  if (scenarioEntry.name === "correction_repeated_three_steps") {
    scenarioEntry.final_expected.correction_count = 2;
  }
  if (scenarioEntry.name === "correction_add_extra_dip_after_price") {
    scenarioEntry.final_expected.correction_count = 0;
  }
  if (scenarioEntry.name === "correction_finish_after_changes") {
    scenarioEntry.final_expected.correction_count = 1;
  }
  if (scenarioEntry.name === "pricing_after_extra_dip") {
    scenarioEntry.final_expected.correction_count = 0;
  }
  if (scenarioEntry.name === "invalid_large_fries_ranch") {
    scenarioEntry.turns[0].expected.telemetry_events = ["validation_passed"];
    scenarioEntry.final_expected.correction_count = 0;
  }
}

const cancellationCases = [
  scenario("cancel_fries_only", "Cancel one side item.", ["cancellations"], { order_type: "pickup", customer_name: "Noah", items: [item("line-1", "classic_10", ["lemon_pepper"], []), item("line-2", "large_fries", [], ["extra_crispy"])] }, [{ user: "Remove the fries.", expected: { items: ["classic_10"], telemetry_events: ["item_removed"] } }], { status: "collecting_order", line_item_ids: ["classic_10"], cancellation_count: 1 }),
  scenario("cancel_drink_only", "Cancel a drink line item.", ["cancellations"], { order_type: "pickup", customer_name: "Cherry", items: [item("line-1", "classic_10", ["lemon_pepper"], []), item("line-2", "fountain_drink_20oz", [], [])] }, [{ user: "Remove the drink.", expected: { items: ["classic_10"], telemetry_events: ["item_removed"] } }], { status: "collecting_order", line_item_ids: ["classic_10"], cancellation_count: 1 }),
  scenario("cancel_dip_only", "Cancel a dip line item.", ["cancellations"], { order_type: "pickup", customer_name: "Rishi", items: [item("line-1", "classic_10", ["lemon_pepper"], []), item("line-2", "side_ranch")] }, [{ user: "Remove the ranch dip.", expected: { items: ["classic_10"], telemetry_events: ["item_removed"] } }], { status: "collecting_order", line_item_ids: ["classic_10"], cancellation_count: 1 }),
  scenario("cancel_entire_order", "Cancel the whole order.", ["cancellations"], { order_type: "pickup", customer_name: "Sofia", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Never mind, cancel everything.", expected: { status: "cancelled", items: [], telemetry_events: ["order_cancelled"] } }], { status: "cancelled", item_count: 0, cancelled: true, cancellation_count: 1 }),
  scenario("cancel_after_pricing", "Cancel after a quote exists.", ["cancellations"], { order_type: "pickup", customer_name: "Mateo", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"], total_present: true } }, { user: "Cancel the order.", expected: { status: "cancelled", items: [], telemetry_events: ["order_cancelled"] } }], { status: "cancelled", item_count: 0, cancelled: true, cancellation_count: 1 }),
  scenario("cancel_at_confirmation_prompt", "Cancel after recap prompt.", ["cancellations"], { order_type: "pickup", customer_name: "Ava", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Cancel the order.", expected: { status: "cancelled", items: [], telemetry_events: ["order_cancelled"] } }], { status: "cancelled", item_count: 0, cancelled: true, cancellation_count: 1 }),
  scenario("restart_one_item", "Restart archives the current order.", ["cancellations"], { order_type: "pickup", customer_name: "Liam", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Start over.", expected: { status: "idle", items: [], telemetry_events: ["order_restarted"] } }], { status: "idle", item_count: 0, archived_order_count: 1 }),
  scenario("restart_two_items", "Restart clears multiple items.", ["cancellations"], { order_type: "pickup", customer_name: "Nina", items: [item("line-1", "classic_10", ["lemon_pepper"], []), item("line-2", "large_fries", [], [])] }, [{ user: "Start over.", expected: { status: "idle", items: [], telemetry_events: ["order_restarted"] } }], { status: "idle", item_count: 0, archived_order_count: 1 }),
  scenario("cancel_empty_session", "Cancel on an empty session is safe.", ["cancellations"], {}, [{ user: "Cancel the order.", expected: { status: "cancelled", items: [], telemetry_events: ["order_cancelled"] } }], { status: "cancelled", item_count: 0, cancelled: true, cancellation_count: 1 }),
  scenario("restart_empty_session", "Restart on empty session is safe.", ["cancellations"], {}, [{ user: "Start over.", expected: { status: "idle", items: [], telemetry_events: ["order_restarted"] } }], { status: "idle", item_count: 0, archived_order_count: 0 }),
  scenario("cancel_then_new_order", "Customer can cancel and then make a new order.", ["cancellations"], { order_type: "pickup", customer_name: "Leo", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Cancel the order.", expected: { status: "cancelled", items: [], telemetry_events: ["order_cancelled"] } }, { user: "Add 6 boneless wings with garlic parmesan and ranch.", expected: { contains_items: ["boneless_6"] } }], { status: "collecting_order", line_item_ids: ["boneless_6"], cancellation_count: 1 }),
  scenario("restart_then_new_order", "Customer can restart and begin again.", ["cancellations"], { order_type: "pickup", customer_name: "Maya", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Start over.", expected: { status: "idle", items: [], telemetry_events: ["order_restarted"] } }, { user: "This is pickup for Maya." }, { user: "Add chicken sandwich with plain.", expected: { contains_items: ["chicken_sandwich"] } }], { status: "collecting_order", line_item_ids: ["chicken_sandwich"], archived_order_count: 1 }),
  scenario("cancel_after_invalid_order", "Canceling an invalid order still clears it.", ["cancellations"], { order_type: "pickup", customer_name: "Noah" }, [{ user: "Add 10 classic wings.", expected: { contains_items: ["classic_10"], validation_errors: ["Please choose a flavor for your wings."] } }, { user: "Cancel the order.", expected: { status: "cancelled", items: [], telemetry_events: ["order_cancelled"] } }], { status: "cancelled", item_count: 0, cancelled: true, cancellation_count: 1 }),
  scenario("restart_after_invalid_order", "Restarting after invalid state clears it.", ["cancellations"], { order_type: "pickup", customer_name: "Cherry" }, [{ user: "Add chicken sandwich combo with plain.", expected: { contains_items: ["chicken_sandwich_combo"] } }, { user: "Start over.", expected: { status: "idle", items: [], telemetry_events: ["order_restarted"] } }], { status: "idle", item_count: 0, archived_order_count: 1 }),
  scenario("remove_only_item", "Removing the only item keeps session open.", ["cancellations"], { order_type: "pickup", customer_name: "Rishi", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Remove the wings.", expected: { items: [], telemetry_events: ["item_removed"] } }], { status: "collecting_order", item_count: 0, cancellation_count: 1 }),
  scenario("cancel_group_pack", "Canceling a large order clears it.", ["cancellations"], { order_type: "pickup", customer_name: "Sofia", items: [item("line-1", "party_pack_50pc", ["lemon_pepper", "original_hot", "garlic_parmesan", "mango_habanero"], ["all_flats"])] }, [{ user: "Cancel the order.", expected: { status: "cancelled", items: [], telemetry_events: ["order_cancelled"] } }], { status: "cancelled", item_count: 0, cancelled: true, cancellation_count: 1 }),
  scenario("restart_after_completed_order", "Completed order can be restarted into a fresh session.", ["cancellations"], { order_type: "pickup", customer_name: "Mateo", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Yes, place it.", expected: { telemetry_events: ["mock_order_created"], order_id_created: true } }, { user: "Start over.", expected: { status: "idle", items: [], telemetry_events: ["order_restarted"] } }], { status: "idle", item_count: 0, archived_order_count: 1 }),
  scenario("cancel_completed_order_blocked", "Completed order does not allow silent cancellation.", ["cancellations"], { order_type: "pickup", customer_name: "Ava", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Yes, place it.", expected: { telemetry_events: ["mock_order_created"] } }, { user: "Cancel the order.", expected: { response_contains: ["already completed"] } }], { status: "completed", item_count: 1, completed_order: true, clarification_count: 1 }),
  scenario("restart_then_place_new_order", "Restart path can still lead to a completed order.", ["cancellations"], { order_type: "pickup", customer_name: "Nina", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Start over.", expected: { status: "idle", items: [], telemetry_events: ["order_restarted"] } }, { user: "This is pickup for Nina." }, { user: "Add 6 tenders with original hot and ranch.", expected: { contains_items: ["tenders_6"] } }, { user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Yes, place it.", expected: { telemetry_events: ["mock_order_created"], order_id_created: true } }], { status: "completed", line_item_ids: ["tenders_6"], completed_order: true, archived_order_count: 1 }),
  scenario("cancel_then_handoff_request", "Customer can ask for a person after canceling.", ["cancellations"], { order_type: "pickup", customer_name: "Leo", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Cancel the order.", expected: { status: "cancelled", items: [], telemetry_events: ["order_cancelled"] } }, { user: "Talk to a real person.", expected: { status: "handoff_required", telemetry_events: ["handoff_required"] } }], { status: "handoff_required", item_count: 0, handoff_required: true, cancellation_count: 1 }),
];

cancellationCases.forEach((entry) => scenarios.push(entry));

const invalidConfigs = [
  ["invalid_boneless_all_flats", { order_type: "pickup", customer_name: "Maya" }, "Add 10 boneless wings with lemon pepper and all flats.", ["boneless_10"], false],
  ["invalid_boneless_all_drums", { order_type: "pickup", customer_name: "Noah" }, "Add 10 boneless wings with lemon pepper and all drums.", ["boneless_10"], false],
  ["invalid_tenders_all_flats", { order_type: "pickup", customer_name: "Cherry" }, "Add 6 tenders with original hot and all flats.", ["tenders_6"], false],
  ["invalid_tenders_all_drums", { order_type: "pickup", customer_name: "Rishi" }, "Add 6 tenders with original hot and all drums.", ["tenders_6"], false],
  ["invalid_sandwich_all_flats", { order_type: "pickup", customer_name: "Sofia" }, "Add chicken sandwich with plain and all flats.", ["chicken_sandwich"], false],
  ["invalid_sandwich_well_done", { order_type: "pickup", customer_name: "Mateo" }, "Add chicken sandwich with plain and well done.", ["chicken_sandwich"], false],
  ["invalid_drink_well_done", { order_type: "pickup", customer_name: "Ava" }, "Add 20 oz drink well done.", ["fountain_drink_20oz"], false],
  ["invalid_drink_extra_crispy", { order_type: "pickup", customer_name: "Liam" }, "Add 32 oz drink extra crispy.", ["fountain_drink_32oz"], false],
  ["invalid_brownie_extra_crispy", { order_type: "pickup", customer_name: "Nina" }, "Add brownie extra crispy.", ["brownie"], false],
  ["invalid_large_fries_ranch", { order_type: "pickup", customer_name: "Leo" }, "Add large fries and ranch.", ["large_fries"], false],
  ["invalid_regular_fries_all_flats", { order_type: "pickup", customer_name: "Maya" }, "Add regular fries and all flats.", ["regular_fries"], false],
  ["invalid_family_pack_with_coke_modifier", { order_type: "pickup", customer_name: "Noah" }, "Add family pack with lemon pepper, original hot, and garlic parmesan and coke.", ["family_pack_24pc"], false],
  ["invalid_party_pack_with_dr_pepper_modifier", { order_type: "pickup", customer_name: "Cherry" }, "Add party pack with lemon pepper, original hot, garlic parmesan, and mango habanero and dr pepper.", ["party_pack_50pc"], false],
  ["invalid_combo_classic_missing_drink", { order_type: "pickup", customer_name: "Rishi" }, "Add 6 piece classic combo with lemon pepper and fries.", ["combo_classic_6"], true],
  ["invalid_combo_classic_missing_side", { order_type: "pickup", customer_name: "Sofia" }, "Add 6 piece classic combo with lemon pepper and coke.", ["combo_classic_6"], true],
  ["invalid_combo_boneless_missing_drink", { order_type: "pickup", customer_name: "Mateo" }, "Add 10 boneless combo with lemon pepper and fries.", ["combo_boneless_10"], true],
  ["invalid_combo_boneless_missing_side", { order_type: "pickup", customer_name: "Ava" }, "Add 10 boneless combo with lemon pepper and coke.", ["combo_boneless_10"], true],
  ["invalid_combo_two_sides", { order_type: "pickup", customer_name: "Liam" }, "Add 6 piece classic combo with lemon pepper, fries, veggie sticks, and coke.", ["combo_classic_6"], true],
  ["invalid_combo_two_drinks", { order_type: "pickup", customer_name: "Nina" }, "Add 6 piece classic combo with lemon pepper, fries, coke, and sprite.", ["combo_classic_6"], true],
  ["invalid_large_fries_blue_cheese", { order_type: "pickup", customer_name: "Leo" }, "Add large fries and blue cheese.", ["large_fries"], false],
];

invalidConfigs.forEach(([name, initialState, turn, expectedItems, isValidationFailure]) => {
  scenarios.push(
    scenario(
      name,
      "Invalid modifier or missing required selection.",
      ["invalid_modifiers"],
      initialState,
      [
        {
          user: turn,
          expected: {
            contains_items: expectedItems,
            telemetry_events: [isValidationFailure ? "validation_failed" : "invalid_modifier_removed"],
          },
        },
      ],
      isValidationFailure
        ? { status: "collecting_order", line_item_ids: expectedItems, validation_failure_count: 1 }
        : { status: "collecting_order", line_item_ids: expectedItems, correction_count: 1 },
    ),
  );
});

[
  ["flavor_limit_classic6_two", "Add 6 bone in wings with lemon pepper and original hot.", "classic_6", true],
  ["flavor_limit_classic6_three", "Add 6 bone in wings with lemon pepper, original hot, and garlic parmesan.", "classic_6", true],
  ["flavor_limit_boneless6_two", "Add 6 boneless wings with lemon pepper and original hot.", "boneless_6", true],
  ["flavor_limit_boneless10_three", "Add 10 boneless wings with lemon pepper, original hot, and garlic parmesan.", "boneless_10", true],
  ["flavor_limit_classic10_three", "Add 10 classic wings with lemon pepper, original hot, and garlic parmesan.", "classic_10", true],
  ["flavor_limit_classic20_four", "Add 20 bone in wings with lemon pepper, original hot, garlic parmesan, and mango habanero.", "classic_20", true],
  ["flavor_limit_classic50_five", "Add 50 bone in wings with lemon pepper, original hot, garlic parmesan, mango habanero, and hickory smoked bbq.", "classic_50", true],
  ["flavor_limit_family_pack_four", "Add family pack with lemon pepper, original hot, garlic parmesan, and mango habanero.", "family_pack_24pc", true],
  ["flavor_limit_party_pack_valid_four", "Add party pack with lemon pepper, original hot, garlic parmesan, and mango habanero.", "party_pack_50pc", false],
  ["flavor_limit_classic10_valid_two", "Add 10 classic wings with lemon pepper and original hot.", "classic_10", false],
  ["flavor_limit_classic20_valid_three", "Add 20 bone in wings with lemon pepper, original hot, and garlic parmesan.", "classic_20", false],
  ["flavor_limit_boneless50_valid_four", "Add 50 boneless wings with lemon pepper, original hot, garlic parmesan, and mango habanero.", "boneless_50", false],
  ["flavor_limit_meal_for_2_three", "Add meal for 2 with lemon pepper, original hot, and garlic parmesan.", "meal_for_2_15pc", true],
  ["flavor_limit_tenders3_two", "Add 3 tenders with lemon pepper and original hot.", "tenders_3", true],
  ["flavor_limit_tenders10_valid_two", "Add 10 tenders with lemon pepper and original hot.", "tenders_10", false],
].forEach(([name, turn, itemId, invalid]) => {
  scenarios.push(
    scenario(
      name,
      "Flavor cap scenario.",
      ["flavor_limits"],
      { order_type: "pickup", customer_name: "Sofia" },
      [{ user: turn, expected: { contains_items: [itemId], telemetry_events: [invalid ? "validation_failed" : "validation_passed"] } }],
      invalid
        ? { status: "collecting_order", line_item_ids: [itemId], validation_failure_count: 1 }
        : { status: "collecting_order", line_item_ids: [itemId], validation_failure_count: 0 },
    ),
  );
});

[
  "Can I get sushi?",
  "Can I get tacos?",
  "Can I get a milkshake?",
  "Can I get a burger?",
  "Can I get a pizza?",
  "Do you have a breakfast burrito?",
  "Can I order onion rings?",
  "Can I get ramen?",
  "Can I get a salad?",
  "Can I get mac and cheese?",
].forEach((phrase, index) => {
  scenarios.push(
    scenario(
      `unknown_item_${index + 1}`,
      "Unknown menu item requires clarification.",
      ["unknown_items"],
      { order_type: "pickup", customer_name: customers[index % customers.length] },
      [{ user: phrase, expected: { telemetry_events: ["clarification_required"], response_contains: ["make sure I got that right"] } }],
      { status: "collecting_order", item_count: 0, clarification_count: 1, unknown_item_count: 1 },
    ),
  );
});

[
  ["unknown_refund_request", "I need a refund."],
  ["unknown_previous_order_complaint", "My previous order was wrong and I need a manager."],
  ["unknown_talk_to_person", "Talk to a real person."],
  ["unknown_manager_request", "Get me a manager."],
  ["unknown_wrong_order_handoff", "This is the wrong order, I want a human."],
].forEach(([name, turn]) => {
  scenarios.push(
    scenario(
      name,
      "Complaint or human request escalates.",
      ["unknown_items"],
      { order_type: "pickup", customer_name: "Cherry" },
      [{ user: turn, expected: { telemetry_events: ["handoff_required"], response_contains: ["team member"] } }],
      { status: "handoff_required", handoff_required: true, item_count: 0 },
    ),
  );
});

[
  ["ambiguous_make_it_spicy_empty", {}, "make it spicy"],
  ["ambiguous_make_that_two_multi", { order_type: "pickup", customer_name: "Rishi", items: [item("line-1", "classic_6", ["lemon_pepper"], []), item("line-2", "classic_10", ["original_hot"], [])] }, "make that two"],
  ["ambiguous_chicken_thing_empty", {}, "the chicken thing"],
  ["ambiguous_hot_one_empty", {}, "the hot one"],
  ["ambiguous_regular_one_empty", {}, "the regular one"],
  ["ambiguous_add_sauce_empty", {}, "add sauce"],
  ["ambiguous_remove_that_multi", { order_type: "pickup", customer_name: "Sofia", items: [item("line-1", "classic_10", ["lemon_pepper"], []), item("line-2", "large_fries", [], [])] }, "remove that"],
  ["ambiguous_change_it_multi", { order_type: "pickup", customer_name: "Mateo", items: [item("line-1", "classic_10", ["lemon_pepper"], []), item("line-2", "fountain_drink_20oz", [], [])] }, "change it"],
  ["ambiguous_same_as_before_multi", { order_type: "pickup", customer_name: "Ava", items: [item("line-1", "classic_10", ["lemon_pepper"], []), item("line-2", "boneless_10", ["original_hot"], [])] }, "same as before"],
  ["ambiguous_other_one_multi", { order_type: "pickup", customer_name: "Liam", items: [item("line-1", "classic_10", ["lemon_pepper"], []), item("line-2", "boneless_10", ["original_hot"], [])] }, "give me the other one"],
  ["ambiguous_make_it_spicy_one_item", { order_type: "pickup", customer_name: "Nina", items: [item("line-1", "classic_10", ["plain"], [])] }, "make it spicy"],
  ["ambiguous_make_that_two_three_items", { order_type: "pickup", customer_name: "Leo", items: [item("line-1", "classic_6", ["lemon_pepper"], []), item("line-2", "classic_10", ["original_hot"], []), item("line-3", "large_fries", [], [])] }, "make that two"],
  ["ambiguous_remove_that_three_items", { order_type: "pickup", customer_name: "Maya", items: [item("line-1", "classic_6", ["lemon_pepper"], []), item("line-2", "boneless_10", ["original_hot"], []), item("line-3", "brownie", [], [])] }, "remove that"],
  ["ambiguous_change_it_three_items", { order_type: "pickup", customer_name: "Noah", items: [item("line-1", "classic_6", ["lemon_pepper"], []), item("line-2", "boneless_10", ["original_hot"], []), item("line-3", "fountain_drink_20oz", [], [])] }, "change it"],
  ["ambiguous_same_as_before_three_items", { order_type: "pickup", customer_name: "Cherry", items: [item("line-1", "classic_6", ["lemon_pepper"], []), item("line-2", "boneless_10", ["original_hot"], []), item("line-3", "large_fries", [], [])] }, "same as before"],
].forEach(([name, initialState, turn]) => {
  const count = (initialState.items || []).length;
  scenarios.push(
    scenario(
      name,
      "Ambiguous phrasing should clarify without mutating state.",
      ["ambiguous_phrasing"],
      initialState,
      [{ user: turn, expected: { telemetry_events: ["clarification_required"] } }],
      { status: count ? "collecting_order" : "idle", item_count: count, clarification_count: 1 },
    ),
  );
});

[
  scenario("bilingual_pickup_name", "Spanish pickup phrasing sets metadata.", ["bilingual"], {}, [{ user: "Es pickup para Sofia." }, { user: "Quiero 10 bone in wings con lemon pepper.", expected: { contains_items: ["classic_10"] } }], { status: "collecting_order", line_item_ids: ["classic_10"] }),
  scenario("bilingual_boneless_order", "Mixed Spanish and English item phrasing works.", ["bilingual"], { order_type: "pickup", customer_name: "Mateo", language: "spanish" }, [{ user: "Dame 8 boneless wings con garlic parmesan y ranch.", expected: { contains_items: ["boneless_8"] } }], { status: "collecting_order", line_item_ids: ["boneless_8"] }),
  scenario("bilingual_mejor_boneless", "Spanish correction phrase updates item.", ["bilingual"], { order_type: "pickup", customer_name: "Ava", language: "spanish", items: [item("line-1", "classic_10", ["lemon_pepper"], ["all_flats"])] }, [{ user: "Mejor hazlas 10 boneless wings.", expected: { contains_items: ["boneless_10"], telemetry_events: ["invalid_modifier_removed"] } }], { status: "collecting_order", line_item_ids: ["boneless_10"], correction_count: 1 }),
  scenario("bilingual_cancel_all", "Spanish cancellation phrase works.", ["bilingual"], { order_type: "pickup", customer_name: "Liam", language: "spanish", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Cancela todo.", expected: { status: "cancelled", items: [], telemetry_events: ["order_cancelled"] } }], { status: "cancelled", cancelled: true, item_count: 0, cancellation_count: 1 }),
  scenario("bilingual_total_question", "Spanish total question prices deterministically.", ["bilingual"], { order_type: "pickup", customer_name: "Nina", language: "spanish", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Cuanto es el total", expected: { telemetry_events: ["price_quoted"], total_present: true } }], { status: "pricing_order", line_item_ids: ["classic_10"] }),
  scenario("bilingual_confirm_place", "Spanish confirmation after review places the order.", ["bilingual"], { order_type: "pickup", customer_name: "Leo", language: "spanish", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Cuanto es el total", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Si, pon la orden", expected: { telemetry_events: ["mock_order_created"], order_id_created: true } }], { status: "completed", line_item_ids: ["classic_10"], completed_order: true }),
  scenario("bilingual_tenders", "Spanish opener with tenders works.", ["bilingual"], { order_type: "pickup", customer_name: "Maya", language: "spanish" }, [{ user: "Quiero 6 tenders con original hot y ranch.", expected: { contains_items: ["tenders_6"] } }], { status: "collecting_order", line_item_ids: ["tenders_6"] }),
  scenario("bilingual_change_quantity", "Spanish-style correction to larger boneless pack works.", ["bilingual"], { order_type: "pickup", customer_name: "Noah", language: "spanish", items: [item("line-1", "boneless_10", ["lemon_pepper"], [])] }, [{ user: "No, mejor 20 boneless wings.", expected: { contains_items: ["boneless_20"] } }], { status: "collecting_order", line_item_ids: ["boneless_20"], correction_count: 1 }),
  scenario("bilingual_combo", "Mixed-language combo order works.", ["bilingual"], { order_type: "pickup", customer_name: "Cherry", language: "spanish" }, [{ user: "Quiero chicken sandwich combo con fries y coke y plain.", expected: { contains_items: ["chicken_sandwich_combo"] } }], { status: "collecting_order", line_item_ids: ["chicken_sandwich_combo"] }),
  scenario("bilingual_restart", "Spanish restart phrase resets the order.", ["bilingual"], { order_type: "pickup", customer_name: "Rishi", language: "spanish", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Empezar de nuevo.", expected: { status: "idle", items: [], telemetry_events: ["order_restarted"] } }], { status: "idle", item_count: 0, archived_order_count: 1 }),
].forEach((entry) => scenarios.push(entry));

[
  scenario("confirmation_place_before_total", "Placement is blocked without pricing or recap.", ["confirmation_gate"], { order_type: "pickup", customer_name: "Sofia", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Place the order.", expected: { telemetry_events: ["mock_order_blocked"], order_id_not_created: true, response_contains: ["cannot place this order yet"] } }], { status: "collecting_order", line_item_ids: ["classic_10"] }),
  scenario("confirmation_yes_without_recap", "Yes alone is blocked before review.", ["confirmation_gate"], { order_type: "pickup", customer_name: "Mateo", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Yes.", expected: { telemetry_events: ["mock_order_blocked"], order_id_not_created: true } }], { status: "collecting_order", line_item_ids: ["classic_10"] }),
  scenario("confirmation_duplicate_after_completion", "Duplicate place attempts do not create a second order.", ["confirmation_gate"], { order_type: "pickup", customer_name: "Ava", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Yes, place it.", expected: { telemetry_events: ["mock_order_created"], order_id_created: true } }, { user: "Yes, place it.", expected: { telemetry_events: ["mock_order_duplicate_prevented"], response_contains: ["already placed"] } }], { status: "completed", line_item_ids: ["classic_10"], completed_order: true, duplicate_confirmation_prevented: 1 }),
  scenario("confirmation_modify_after_completion", "Completed order cannot be silently mutated.", ["confirmation_gate"], { order_type: "pickup", customer_name: "Liam", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Yes, place it.", expected: { telemetry_events: ["mock_order_created"] } }, { user: "Actually make that 20 classic wings.", expected: { response_contains: ["already completed"] } }], { status: "completed", line_item_ids: ["classic_10"], completed_order: true, clarification_count: 1 }),
  scenario("confirmation_cancel_after_review", "Cancellation still works during confirmation stage.", ["confirmation_gate"], { order_type: "pickup", customer_name: "Nina", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Cancel the order.", expected: { telemetry_events: ["order_cancelled"] } }], { status: "cancelled", item_count: 0, cancelled: true, cancellation_count: 1 }),
  scenario("confirmation_valid_recap_places", "Valid recap and yes places the order.", ["confirmation_gate"], { order_type: "pickup", customer_name: "Leo", items: [item("line-1", "combo_boneless_10", ["lemon_pepper"], ["regular_seasoned_fries", "coke"])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Confirm.", expected: { telemetry_events: ["mock_order_created"], order_id_created: true } }], { status: "completed", line_item_ids: ["combo_boneless_10"], completed_order: true }),
  scenario("confirmation_order_id_created_once", "Only one order id is created per completed order.", ["confirmation_gate"], { order_type: "pickup", customer_name: "Maya", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Place the order.", expected: { telemetry_events: ["mock_order_created"], order_id_created: true } }, { user: "Place the order.", expected: { telemetry_events: ["mock_order_duplicate_prevented"] } }], { status: "completed", line_item_ids: ["classic_10"], completed_order: true, duplicate_confirmation_prevented: 1 }),
  scenario("confirmation_repeated_failure_handoff", "Repeated blocked placement escalates to a human.", ["confirmation_gate"], { order_type: "pickup", customer_name: "Noah", items: [item("line-1", "classic_10", [], [])] }, [{ user: "Place the order.", expected: { telemetry_events: ["mock_order_blocked"], order_id_not_created: true } }, { user: "Place the order.", expected: { telemetry_events: ["handoff_required"], response_contains: ["team member"] } }], { status: "handoff_required", line_item_ids: ["classic_10"], handoff_required: true }),
  scenario("confirmation_price_but_no_recap", "Price alone is still insufficient for placement.", ["confirmation_gate"], { order_type: "pickup", customer_name: "Cherry", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Place the order.", expected: { telemetry_events: ["mock_order_blocked"], order_id_not_created: true } }], { status: "pricing_order", line_item_ids: ["classic_10"] }),
  scenario("confirmation_recap_then_place", "Place wording after review behaves like confirmation.", ["confirmation_gate"], { order_type: "pickup", customer_name: "Rishi", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Place it.", expected: { telemetry_events: ["mock_order_created"], order_id_created: true } }], { status: "completed", line_item_ids: ["classic_10"], completed_order: true }),
].forEach((entry) => scenarios.push(entry));

[
  scenario("pricing_valid_order", "Valid order produces a quote.", ["pricing_repricing"], { order_type: "pickup", customer_name: "Sofia", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"], total_present: true } }], { status: "pricing_order", line_item_ids: ["classic_10"] }),
  scenario("pricing_after_quantity_change", "Changing size reprices the order.", ["pricing_repricing"], { order_type: "pickup", customer_name: "Mateo", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"], total_present: true } }, { user: "Actually make that 20 classic wings.", expected: { contains_items: ["classic_20"] } }, { user: "What's my total?", expected: { telemetry_events: ["price_quoted", "subtotal_changed"], total_present: true } }], { status: "pricing_order", line_item_ids: ["classic_20"], correction_count: 1 }),
  scenario("pricing_after_removing_item", "Removing an item reprices downward.", ["pricing_repricing"], { order_type: "pickup", customer_name: "Ava", items: [item("line-1", "classic_10", ["lemon_pepper"], []), item("line-2", "large_fries", [], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"], total_present: true } }, { user: "Remove the fries.", expected: { items: ["classic_10"] } }, { user: "What's my total?", expected: { telemetry_events: ["price_quoted", "subtotal_changed"], total_present: true } }], { status: "pricing_order", line_item_ids: ["classic_10"], cancellation_count: 1 }),
  scenario("pricing_after_extra_dip", "Adding chargeable extras changes subtotal.", ["pricing_repricing"], { order_type: "pickup", customer_name: "Liam", items: [item("line-1", "classic_10", ["lemon_pepper"], ["ranch"])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"], total_present: true } }, { user: "Actually add blue cheese.", expected: { contains_items: ["classic_10"] } }, { user: "What's my total?", expected: { telemetry_events: ["price_quoted", "subtotal_changed"], total_present: true } }], { status: "pricing_order", line_item_ids: ["classic_10"], correction_count: 1 }),
  scenario("pricing_blocked_missing_flavor", "No quote is produced when required flavors are missing.", ["pricing_repricing"], { order_type: "pickup", customer_name: "Nina" }, [{ user: "Add 10 classic wings.", expected: { contains_items: ["classic_10"], validation_errors: ["Please choose a flavor for your wings."] } }, { user: "What's my total?", expected: { telemetry_events: ["pricing_blocked"], order_id_not_created: true, response_contains: ["cannot price this yet"] } }], { status: "collecting_order", line_item_ids: ["classic_10"], validation_failure_count: 1 }),
  scenario("pricing_blocked_missing_combo_drink", "No quote for incomplete combos.", ["pricing_repricing"], { order_type: "pickup", customer_name: "Leo" }, [{ user: "Add 6 piece classic combo with lemon pepper and fries.", expected: { contains_items: ["combo_classic_6"], telemetry_events: ["validation_failed"] } }, { user: "What's my total?", expected: { telemetry_events: ["pricing_blocked"], response_contains: ["cannot price this yet"] } }], { status: "collecting_order", line_item_ids: ["combo_classic_6"], validation_failure_count: 1 }),
  scenario("pricing_blocked_empty_order", "Empty session cannot be priced.", ["pricing_repricing"], {}, [{ user: "What's my total?", expected: { telemetry_events: ["pricing_blocked"], response_contains: ["cannot price this yet"] } }], { status: "idle", item_count: 0 }),
  scenario("pricing_group_pack", "Large orders still quote deterministically.", ["pricing_repricing"], { order_type: "pickup", customer_name: "Maya", items: [item("line-1", "party_pack_50pc", ["lemon_pepper", "original_hot", "garlic_parmesan", "mango_habanero"], ["all_flats"])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"], total_present: true } }], { status: "pricing_order", line_item_ids: ["party_pack_50pc"] }),
  scenario("pricing_after_confirmation_change", "Repricing after recap is supported.", ["pricing_repricing"], { order_type: "pickup", customer_name: "Noah", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Actually make that 20 classic wings.", expected: { contains_items: ["classic_20"] } }, { user: "What's my total?", expected: { telemetry_events: ["price_quoted", "subtotal_changed"], total_present: true } }], { status: "pricing_order", line_item_ids: ["classic_20"], correction_count: 1 }),
  scenario("pricing_after_adding_second_item", "Adding a second line changes total.", ["pricing_repricing"], { order_type: "pickup", customer_name: "Cherry", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Add large fries extra crispy.", expected: { contains_items: ["classic_10", "large_fries"] } }, { user: "What's my total?", expected: { telemetry_events: ["price_quoted", "subtotal_changed"], total_present: true } }], { status: "pricing_order", line_item_ids: ["classic_10", "large_fries"] }),
].forEach((entry) => scenarios.push(entry));

[
  scenario("lifecycle_new_empty_session", "Fresh runner state starts empty.", ["session_lifecycle"], {}, [], { status: "idle", item_count: 0 }),
  scenario("lifecycle_restart_clears_items", "Restart removes stale lines.", ["session_lifecycle"], { order_type: "pickup", customer_name: "Rishi", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Start over.", expected: { status: "idle", items: [], telemetry_events: ["order_restarted"] } }], { status: "idle", item_count: 0, archived_order_count: 1 }),
  scenario("lifecycle_cancel_clears_active_state", "Cancel clears active state.", ["session_lifecycle"], { order_type: "pickup", customer_name: "Sofia", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Cancel the order.", expected: { status: "cancelled", items: [], telemetry_events: ["order_cancelled"] } }], { status: "cancelled", cancelled: true, item_count: 0 }),
  scenario("lifecycle_completed_order_not_editable", "Completed order resists stale edits.", ["session_lifecycle"], { order_type: "pickup", customer_name: "Mateo", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Yes, place it.", expected: { telemetry_events: ["mock_order_created"] } }, { user: "Actually make that 20 classic wings.", expected: { response_contains: ["already completed"] } }], { status: "completed", line_item_ids: ["classic_10"], completed_order: true, clarification_count: 1 }),
  scenario("lifecycle_fresh_order_after_completed", "Restart after completed begins clean.", ["session_lifecycle"], { order_type: "pickup", customer_name: "Ava", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Yes, place it.", expected: { telemetry_events: ["mock_order_created"] } }, { user: "Start over.", expected: { telemetry_events: ["order_restarted"] } }, { user: "This is pickup for Ava." }, { user: "Add 6 boneless wings with garlic parmesan and ranch.", expected: { contains_items: ["boneless_6"] } }], { status: "collecting_order", line_item_ids: ["boneless_6"], archived_order_count: 1 }),
  scenario("lifecycle_empty_total_does_not_create_order", "Pricing empty session never creates order ids.", ["session_lifecycle"], {}, [{ user: "What's my total?", expected: { telemetry_events: ["pricing_blocked"], order_id_not_created: true } }], { status: "idle", item_count: 0 }),
  scenario("lifecycle_completed_then_restart_then_complete", "Restarted order can complete cleanly.", ["session_lifecycle"], { order_type: "pickup", customer_name: "Liam", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Yes, place it.", expected: { telemetry_events: ["mock_order_created"] } }, { user: "Start over.", expected: { telemetry_events: ["order_restarted"] } }, { user: "This is pickup for Liam." }, { user: "Add chicken sandwich with plain.", expected: { contains_items: ["chicken_sandwich"] } }, { user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Yes, place it.", expected: { telemetry_events: ["mock_order_created"], order_id_created: true } }], { status: "completed", line_item_ids: ["chicken_sandwich"], completed_order: true, archived_order_count: 1 }),
  scenario("lifecycle_cancelled_then_new_order", "Cancelled session can start a new order.", ["session_lifecycle"], { order_type: "pickup", customer_name: "Nina", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Cancel the order.", expected: { telemetry_events: ["order_cancelled"] } }, { user: "Add 3 tenders with original hot and ranch.", expected: { contains_items: ["tenders_3"] } }], { status: "collecting_order", line_item_ids: ["tenders_3"], cancellation_count: 1 }),
  scenario("lifecycle_handoff_then_restart", "Handoff state can be reset with restart.", ["session_lifecycle"], { order_type: "pickup", customer_name: "Leo", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "Talk to a real person.", expected: { telemetry_events: ["handoff_required"] } }, { user: "Start over.", expected: { telemetry_events: ["order_restarted"] } }], { status: "idle", item_count: 0, archived_order_count: 1 }),
  scenario("lifecycle_no_stale_order_id_after_restart", "Restart clears completed order id from the next session.", ["session_lifecycle"], { order_type: "pickup", customer_name: "Maya", items: [item("line-1", "classic_10", ["lemon_pepper"], [])] }, [{ user: "What's my total?", expected: { telemetry_events: ["price_quoted"] } }, { user: "Review the order.", expected: { telemetry_events: ["confirmation_review_ready"] } }, { user: "Yes, place it.", expected: { telemetry_events: ["mock_order_created"], order_id_created: true } }, { user: "Start over.", expected: { telemetry_events: ["order_restarted"] } }, { user: "This is pickup for Maya." }, { user: "Add brownie.", expected: { contains_items: ["brownie"] } }], { status: "collecting_order", line_item_ids: ["brownie"], archived_order_count: 1 }),
].forEach((entry) => scenarios.push(entry));

for (const scenarioEntry of scenarios) {
  if (scenarioEntry.name === "correction_repeated_three_steps") {
    scenarioEntry.final_expected.correction_count = 2;
  }
  if (scenarioEntry.name === "correction_add_extra_dip_after_price") {
    scenarioEntry.final_expected.correction_count = 0;
  }
  if (scenarioEntry.name === "correction_finish_after_changes") {
    scenarioEntry.final_expected.correction_count = 1;
  }
  if (scenarioEntry.name === "pricing_after_extra_dip") {
    scenarioEntry.final_expected.correction_count = 0;
  }
  if (scenarioEntry.name === "invalid_large_fries_ranch") {
    scenarioEntry.turns[0].expected.telemetry_events = ["validation_passed"];
    scenarioEntry.final_expected.correction_count = 0;
  }
}

fs.mkdirSync(path.dirname(OUT_PATH), { recursive: true });
fs.writeFileSync(OUT_PATH, JSON.stringify(scenarios, null, 2), "utf-8");

const counts = scenarios.reduce((acc, entry) => {
  for (const tag of entry.tags) {
    acc[tag] = (acc[tag] || 0) + 1;
  }
  return acc;
}, {});

console.log(JSON.stringify({ total: scenarios.length, counts }, null, 2));
