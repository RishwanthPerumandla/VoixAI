# Demo Script

## Goal

Show the VoixAI MVP as a simple restaurant voice agent demo from greeting through mock order confirmation.

## Before You Start

Make sure these are running:

1. `apps/api`
2. `apps/agent-runtime`
3. `apps/web`

Open the web app and click `Start Conversation`.

## Recommended Walkthrough

### 1. Start the order

User:

```txt
Hi, I want ten lemon pepper wings for pickup.
```

Expected outcome:

- The agent greets the user naturally.
- The order starts in the current-session memory.

### 2. Add more order detail

User:

```txt
Make that classic, and add a soda.
```

Expected outcome:

- The agent keeps the order short and conversational.
- The order state now includes pickup, wings, flavor, style, and drink.

### 3. Ask for a recap

User:

```txt
Can you recap that for me?
```

Expected outcome:

- The agent gives a recap.
- The UI current-order summary panel updates if the recap includes the structured summary.
- The mock total is included before confirmation.

### 4. Make a correction

User:

```txt
Actually, make that boneless and add fries.
```

Expected outcome:

- The order state updates instead of resetting.
- The correction logs appear in the agent runtime.
- The current-order summary panel updates after the next recap.

### 5. Change the drink

User:

```txt
Change the soda to lemonade.
```

Expected outcome:

- The drink changes in memory.
- The updated mock total is used for the next recap.

### 6. Confirm the mock order

User:

```txt
Yes, go ahead.
```

Expected outcome:

- The agent confirms the mock order.
- The response includes a fake order number like `VX-1042`.
- The final mock order panel updates with the order number and total.

## Demo Notes

- If the order summary panel is empty, ask the agent for a recap again.
- If the final order panel is empty, make sure the agent actually confirmed the order and spoke the `VX-####` number.
- If interruption behavior looks rough, use the transcript, speaking/listening indicators, and agent logs to explain that this is still an MVP learning build.
