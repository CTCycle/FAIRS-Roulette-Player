## Experience

Last updated: 2026-07-20

## Page Composition

- `/training`
  - dataset upload and preview
  - checkpoint preview and management
  - multi-step training configuration and summary confirmation
  - training dashboard, metrics, and charts
- `/inference`
  - checkpoint and dataset setup
  - session controls
  - AI suggestion panel
  - session history table

Composition rules:

- Keep each page inside `.page-shell`.
- Preserve clear separation between setup controls and live telemetry or history views.

## Workflow Behavior

- Core flows should remain linear:
  - upload or select data
  - choose checkpoint or configuration
  - start the workflow
- Prevent invalid actions with disabled controls and local validation messages.
- Keep error feedback local to the action that failed.
- Preserve explicit loading states for long-running or multi-step actions.
- Keep outcome and profit feedback immediate and visually distinct.

## Responsiveness

Implemented breakpoints currently include:

- `1100px`
- `900px`
- `768px`
- `720px`
- `700px`
- `520px`
- `480px`

Rules:

- Multi-column layouts must collapse cleanly on narrow viewports.
- Tables should remain scrollable when width is constrained.
- Button groups should wrap instead of overflowing.

## Accessibility

- Preserve global `:focus-visible` outline and offset styling.
- Keep navigation regions explicitly labeled.
- Inputs and icon-only actions need explicit labels or `aria-label` values.
- Error alerts should preserve live-region behavior where implemented.
- Respect reduced motion preferences.

## Design Principles

- Consistency over novelty.
- Clarity over decoration.
- Predictable behavior across Training and Inference.
- No parallel styling system outside the established tokens and patterns without a deliberate architectural reason.

## Related Files

- Read `design_tokens.md` for token definitions.
- Read `components_and_patterns.md` for reusable component behaviors.
