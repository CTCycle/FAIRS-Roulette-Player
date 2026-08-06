## Experience

Last updated: 2026-08-02

## Page Composition

- `/training`
  - dataset upload and preview
  - checkpoint preview and management
  - six-step training configuration with clickable breadcrumbs and summary confirmation
  - training monitor with live metrics, circular episode progress, Stop action, and loss/reward charts
- `/inference`
  - checkpoint and dataset setup, including inference upload
  - initial-capital and bet controls
  - AI suggestion panel
  - session history table with editable observed values and row actions

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
- Preserve the two-panel inference layout on wide screens and stack setup/history regions on narrow screens.

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
- Training upload/preview and checkpoint rows collapse to one column at 768px; training wizard grids collapse to one column at 720px.
- Tables should remain scrollable when width is constrained.
- Button groups should wrap instead of overflowing.

## Accessibility

- Preserve global `:focus-visible` outline and offset styling.
- Keep navigation regions explicitly labeled.
- Inputs and icon-only actions need explicit labels or `aria-label` values.
- Error alerts should preserve live-region behavior where implemented.
- Respect reduced motion preferences.
- Dialogs should retain `role="dialog"`, `aria-modal`, and an accessible title; wizard steps expose current-step state.

## Design Principles

- Consistency over novelty.
- Clarity over decoration.
- Predictable behavior across Training and Inference.
- No parallel styling system outside the established tokens and patterns without a deliberate architectural reason.

## Related Files

- Read `design_tokens.md` for token definitions.
- Read `components_and_patterns.md` for reusable component behaviors.
