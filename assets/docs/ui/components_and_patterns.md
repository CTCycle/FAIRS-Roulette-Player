## Components And Patterns

Last updated: 2026-08-02

## Navigation And Structure

- Top-level navigation exposes two tabs:
  - `Training`
  - `Inference`
- The sticky header includes the FAIRS logo, the `Training and inference workspace` subtitle, and icon-backed active navigation links.

## Core Reusable Patterns

- Cards using `.card` are the default information container.
- Form controls such as `.form-input`, `.form-select`, `.input`, and `.select` should preserve the shared border and focus token behavior.
- Button variants include:
  - primary action
  - secondary action
  - ghost, destructive, and utility actions
- Table-based interaction is used for inference session history.
- Dataset and checkpoint previews use compact rows with refresh, start/evaluate/resume, metadata, and delete actions.
- Modal overlays are used for the training wizard, checkpoint metadata, and resume flows.
- The training wizard has six labeled breadcrumb buttons, a summary step, and explicit Back/Next/Submit actions.

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
  - training dashboard with a connection status, metric cards, episode progress wheel, Stop action, and loss/reward charts
- Inference page patterns:
  - checkpoint/dataset setup and upload controls
  - capital and bet controls
  - AI suggestion panel with suggested-bet application
  - Play, Stop, and Clear session controls
  - editable session history table with observed-value, remove, modify, and next-prediction actions

## Related Files

- Read `design_tokens.md` for the styling primitives these patterns rely on.
- Read `experience.md` for page-level behavior and accessibility expectations.
