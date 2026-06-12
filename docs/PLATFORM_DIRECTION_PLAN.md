# Platform Direction Plan

Last updated: 2026-06-12

## Purpose

This document captures the intended product and UI direction for VoixAI as it evolves from a single demo use case into a reusable core voice AI system.

The current implementation is centered on a Wingstop-style ordering workflow, but the long-term product direction is broader:

- VoixAI should be the reusable voice AI system
- Wingstop inbound ordering should be one use case running on that system
- additional use cases should be added later without needing to redesign the whole product

## Core Product Positioning

VoixAI should be presented as:

- a core voice AI platform
- a reusable realtime voice workflow system
- a product that can support multiple business use cases

It should not be positioned as only:

- a Wingstop app
- a restaurant-only UI
- a one-off voice ordering demo

## Product Model

The recommended structure is:

1. `Core Voice AI System`
2. `Use Case Modules`
3. `Channel / Deployment Layer`

### 1. Core Voice AI System

This is the reusable foundation that should stay generic across use cases.

Responsibilities:

- session orchestration
- classic/realtime voice mode routing
- transcript handling
- voice activity visualization
- generic session controls
- tool execution framework
- telemetry and debugging
- text fallback
- session analytics hooks
- use-case loading and configuration

### 2. Use Case Modules

These are domain-specific workflows that run on top of the core system.

Initial use case:

- `Wingstop inbound ordering`

Future possible use cases:

- restaurant reservations
- support intake
- appointment scheduling
- lead qualification
- internal operations workflows

### 3. Channel / Deployment Layer

These are the environments where the same core system and use cases can run.

Examples:

- web demo
- inbound phone
- embedded widget
- mobile
- internal agent-assist console

## Current Use Case

The current primary use case should be explicitly described as:

- `Wingstop inbound ordering`

This means:

- the current ordering workflow is valid and important
- it should be treated as the first packaged use case
- it should not define the identity of the whole product

## UI Direction

The UI should feel like:

- `VoixAI` is the main product
- the active scenario is visible
- the current scenario happens to be Wingstop inbound ordering

### Recommended framing

Use:

- `VoixAI`
- `Voice AI System`
- `Scenario: Wingstop inbound ordering`

Avoid positioning the app as:

- just a Wingstop app
- just a restaurant demo
- a one-off ordering prototype

## Recommended UX Structure

### Landing Screen

The landing page should communicate:

- VoixAI is a reusable voice AI system
- Wingstop ordering is the current live scenario
- more scenarios can be supported later

Suggested layout:

- product heading: `VoixAI`
- subheading: `Voice AI System`
- scenario label: `Wingstop inbound ordering`
- supporting copy explaining that the system runs realtime voice workflows
- primary CTA: `Start demo`
- scenario section showing the current active use case
- small “coming next” area for future use cases

### Live Session Screen

The live screen should separate:

- reusable voice session UI
- scenario-specific workspace UI

Recommended composition:

- header:
  - `VoixAI`
  - `Scenario: Wingstop inbound ordering`
  - current session state
  - end session
- left/main:
  - reusable session experience
  - assistant stage
  - voice visualizer
  - transcript
  - text composer
- right:
  - scenario-specific panel

For Wingstop, the right panel contains:

- service type
- items
- modifiers
- drink
- pickup time
- confirmation state

For future use cases, the right panel would change without redesigning the left/core side.

## Design Principle

The product should be:

- platform-first
- use-case-aware
- reusable
- scenario-driven

The UI should make it obvious that:

- the voice engine is reusable
- the session shell is reusable
- the business workflow is modular

## Naming Model

Recommended naming hierarchy:

- `VoixAI` = platform
- `Scenario` = business workflow
- `Wingstop inbound ordering` = current scenario
- `Channel` = web, phone, widget, mobile

This should be reflected consistently in:

- UI copy
- code structure
- docs
- architecture planning

## Frontend Architecture Direction

The frontend should be split into:

### Reusable core session components

Examples:

- `SessionShell`
- `SessionHeader`
- `VoiceStage`
- `VoiceVisualizer`
- `ConversationTimeline`
- `TextComposer`
- `DeveloperDetails`

These should stay generic.

### Scenario-specific components

Examples for the current use case:

- `WingstopOrderPanel`
- `WingstopOrderSummary`
- `WingstopConfirmationView`

These should be specific to the Wingstop ordering scenario.

## Scenario Registry Direction

The project should move toward a scenario registry so that new workflows can be plugged in intentionally.

Suggested scenario shape:

- `scenarioId`
- `title`
- `description`
- `channelSupport`
- `agentInstructions`
- `toolset`
- `summaryPanelComponent`
- `confirmationComponent`
- `defaultRuntimeConfig`

Initial scenario:

- `wingstop_inbound_ordering`

## Runtime Direction

The current runtime is still heavily centered on the Wingstop ordering logic inside the Python runtime.

Longer term, the runtime should evolve toward:

- generic session lifecycle in core runtime
- scenario-specific instructions and tools loaded by scenario
- scenario-specific state schemas where appropriate

Recommended near-term approach:

- do not rewrite the whole runtime immediately
- keep the current Wingstop flow working
- begin wrapping Wingstop behavior as the first scenario boundary
- move toward scenario-driven runtime composition incrementally

## Inbound Phone Direction

One explicitly planned use case is:

- `Wingstop inbound phone orders`

That means the system should be built with channel-awareness in mind.

Future channel considerations:

- phone-specific greeting logic
- no-screen conversational behavior
- escalation/transfer handling
- phone-appropriate confirmation prompts
- channel-specific interruption tuning

## Recommended Phased Plan

### Phase 1: Reframe the product in UI and docs

Goal:

- make the system feel like VoixAI first
- make Wingstop clearly the current scenario

Work:

- update UI headers and product copy
- add scenario language to the interface
- align docs with platform-first framing

### Phase 2: Separate core session UI from scenario UI

Goal:

- isolate reusable session experience from business workflow panel

Work:

- keep the left/core session shell generic
- move the right-side workflow into a Wingstop-specific panel

### Phase 3: Add a frontend scenario config layer

Goal:

- make additional use cases structurally possible

Work:

- add scenario metadata/config
- route labels and panels through scenario config

### Phase 4: Introduce scenario-aware runtime boundaries

Goal:

- reduce coupling between the runtime core and Wingstop logic

Work:

- move toward scenario-driven instructions/tools/state composition

### Phase 5: Prepare for broader multi-channel use

Goal:

- support web, phone, and future delivery channels cleanly

Work:

- model channels explicitly
- prepare scenario behavior per channel

## Best Immediate Next Step

The best next implementation move is:

1. UI reframing
2. frontend scenario abstraction
3. Wingstop panel extraction

This gives the product the right platform posture immediately without forcing a risky full runtime rewrite.

## Bottom Line

VoixAI should become:

- a reusable voice AI system

And the current Wingstop workflow should be treated as:

- the first production-style scenario running on that system

That is the right balance between:

- preserving the current demo value
- building toward a broader product platform
