## Experience

Last updated: 2026-09-04

## Page Composition

- `/training`
  - dataset upload and preview
  - checkpoint preview and management
  - side-by-side comparison of stored checkpoint configuration and training summaries
  - six-step training configuration with clickable breadcrumbs and summary confirmation
  - training monitor with live DQN metrics, replay-buffer warm-up state, circular episode/step progress, Stop action, and loss/reward charts
- `/inference`
  - checkpoint and dataset setup, including inference upload
  - initial-capital and bet controls
  - agent suggestion panel
  - large session history table on the right with editable observed values and row actions
- Walkthroughs do not open automatically. From Help, users can choose a three-step walkthrough for Training or Inference, covering data/setup, configuration/play, and monitoring/observation.

Composition rules:

- Keep each page inside `.page-shell`.
- Preserve clear separation between setup controls and live telemetry or history views.
- Keep the desktop Inference workspace balanced: stack setup, metrics, and the agent suggestion on the left, and give the session history the wider right-hand column.
- Constrain the history surface to the workspace height and let `.tableBody` scroll when the session grows instead of extending the page indefinitely.
- Keep research diagnostics compact and subordinate to the primary Training or Inference workflow. Do not create a third analytics workspace for information that naturally belongs to those workflows.

## Workflow Behavior

- Core flows should remain linear:
  - upload or select data
  - choose checkpoint or configuration
  - start the workflow
- Prevent invalid actions with disabled controls and local validation messages.
- Training configuration validates relationships between exploration settings, replay memory, batch size, and dynamic-betting options before submission; the backend remains authoritative for the same constraints.
- Keep error feedback local to the action that failed.
- Preserve explicit loading states for long-running or multi-step actions.
- Keep outcome and profit feedback immediate and visually distinct.
- The training monitor calls the pre-learning replay-memory phase `Replay warm-up`; epsilon remains visible separately because epsilon-greedy exploration continues after learning begins.
- Validation metrics are shown only when a fresh validation measurement exists rather than being visually carried forward across unsampled steps.
- Checkpoint `Open in Inference` preserves dataset provenance. If the checkpoint's training dataset is unavailable or incompatible, the UI asks the user to choose a dataset explicitly instead of silently substituting one.
- Preserve the two-panel inference layout at every supported viewport width. Below the desktop minimum, retain the desktop geometry and show the minimum-window notice instead of stacking setup and history regions.
- Keep guidance adjacent to the feature it explains, short enough to scan, and dismissible without blocking the workflow. Do not repeat a dismissed tip during the same guidance version.

## Desktop support

- The supported browser viewport is at least `1100px` wide.
- The interface is optimized for desktop computers, laptops, and Windows tablets that behave like normal desktop browser environments.
- Phones, mobile navigation, touch-first interactions, and small-screen responsive layouts are not supported targets.
- Below `1100px`, the application keeps its desktop minimum width and displays a clear request to enlarge the browser window.
- Multi-column layouts remain intact at supported widths. Dense tables may scroll within their own surface when their intrinsic desktop width is needed.

Desktop layouts should favor information density, horizontal space, and efficient mouse and keyboard interaction over compact viewport adaptation.

## Accessibility

- Preserve global `:focus-visible` outline and offset styling.
- Keep navigation regions explicitly labeled.
- Inputs and icon-only actions need explicit labels or `aria-label` values.
- Error alerts should preserve live-region behavior where implemented.
- Respect reduced motion preferences.
- Dialogs should retain `role="dialog"`, `aria-modal`, and an accessible title; wizard steps expose current-step state.
- Guidance dialogs and tours move focus to their first action, keep Tab navigation within the open surface, close with Escape, and restore focus to the invoking control. Tour targets are highlighted without replacing the underlying controls, and the animated demonstration becomes static when reduced motion is requested.

## Design Principles

- Consistency over novelty.
- Clarity over decoration.
- Predictable behavior across Training and Inference.
- Research terminology must match the underlying DQN semantics.
- No parallel styling system outside the established tokens and patterns without a deliberate architectural reason.

## Related Files

- Read `design_tokens.md` for token definitions.
- Read `components_and_patterns.md` for reusable component behaviors.
