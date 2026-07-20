## Components And Patterns

Last updated: 2026-07-20

## Navigation And Structure

- Top-level navigation exposes two tabs:
  - `Training`
  - `Inference`
- Header and navigation are sticky and visually separated from page content.

## Core Reusable Patterns

- Cards using `.card` are the default information container.
- Form controls such as `.form-input`, `.form-select`, `.input`, and `.select` should preserve the shared border and focus token behavior.
- Button variants include:
  - primary action
  - secondary action
  - ghost, destructive, and utility actions
- Table-based interaction is used for inference session history.
- Modal overlays are used for training wizard and metadata preview flows.

## Interaction States

Required states:

- default
- hover
- focus-visible
- disabled

Additional rules:

- Disabled actions must show non-interactive cursor and disabled styling.
- Inline errors should preserve alert semantics where implemented.
- Empty states should be explicit rather than implied by blank surfaces.

## Feature-Specific Patterns

- Training page patterns:
  - dataset upload
  - dataset preview
  - checkpoint preview and management
  - multi-step training configuration wizard with summary confirmation
  - training dashboard with metrics and charts
- Inference page patterns:
  - setup controls
  - AI suggestion panel
  - session controls
  - session history table

## Related Files

- Read `design_tokens.md` for the styling primitives these patterns rely on.
- Read `experience.md` for page-level behavior and accessibility expectations.
