## Components And Patterns

Last updated: 2026-09-04

## Navigation And Structure

- Top-level navigation exposes two tabs:
  - `Training`
  - `Inference`
- The sticky header includes the FAIRS logo, the `Training and inference workspace` subtitle, and icon-backed active navigation links.
- Navigation remains a desktop header; no mobile menu or collapsed navigation is provided.

## Desktop support

- The shared shell requires a browser viewport at least `1100px` wide and preserves the desktop layout below that width.
- Below the minimum, a non-dismissible notice tells the user to enlarge the browser window.
- Keep controls sized and ordered for mouse and keyboard use; do not add touch-first interaction variants.

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
- Guidance uses a small shared set of patterns: contextual `FeatureTip` callouts, click-to-open `HelpPopover` explanations, the optional `GuidedTour`, and the `Tips & Tricks` dialog available from the header Help button.
- Guidance is progressive and dismissible. Walkthroughs start only when the user chooses them from Help, while contextual tips appear in empty or application-specific states where a next action is useful.
- The shared guidance layer renders dialogs and tours through portals so they are not clipped by cards or scroll containers. It restores focus on close, traps keyboard focus while open, supports Escape dismissal, and respects `prefers-reduced-motion` for the demonstration animation.

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
- Help copy should be short and action-oriented; do not add a tip to a standard control unless its behavior is application-specific.

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
  - wide right-hand session history table with observed-value, remove, modify, and next-prediction actions
  - bounded table body that scrolls independently as the session history grows
- Guidance content:
  - Training explains the dataset, configuration, and monitor regions through a three-step optional walkthrough, with short help popovers inside the multi-step configuration wizard.
  - Inference explains setup, Play, and the observation loop through an optional three-step walkthrough and adds empty-state guidance when no checkpoint or history exists.
  - Tips & Tricks contains concise workflow advice and an inline launch entry for the current walkthrough.

## Guidance State

- The browser stores guidance state under the `fairs.guidance` local-storage key.
- Each entry stores a version and one of `seen`, `dismissed`, or `completed`. A changed definition version can show that guidance again without resetting unrelated entries.
- No server-side account state is required for this local-first application.

## Related Files

- Read `design_tokens.md` for the styling primitives these patterns rely on.
- Read `experience.md` for page-level behavior and accessibility expectations.
