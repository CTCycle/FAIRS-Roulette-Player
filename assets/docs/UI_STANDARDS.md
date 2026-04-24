# UI_STANDARDS

Last updated: 2026-04-24

This standard is based on the implemented React UI in `FAIRS/client/src` and should be enforced for all new UI changes.

## Typography

- Base font family: `var(--font-sans)` = `'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`.
- Core type scale tokens:
  - `--font-size-xs: 0.75rem`
  - `--font-size-sm: 0.875rem`
  - `--font-size-md: 1rem`
  - `--font-size-lg: 1.125rem`
  - `--font-size-xl: 1.25rem`
  - `--font-size-2xl: 1.75rem`
- Default line height: `--line-height-default: 1.5`.
- Page title scale uses `clamp(...)` for responsive hierarchy (`.page-title`).

## Layout and Spacing

- Main app shell is route-based (`MainLayout`) with sticky top header/navigation and scrollable content area.
- Global page container: `.page-shell` width constrained to `min(1680px, 100%)`.
- Spacing token scale:
  - `--spacing-xs: 0.25rem`
  - `--spacing-sm: 0.5rem`
  - `--spacing-md: 1rem`
  - `--spacing-lg: 1.5rem`
  - `--spacing-xl: 2rem`
  - `--spacing-2xl: 3rem`
- Corner radius tokens:
  - `--radius-sm: 0.375rem`
  - `--radius-md: 0.5rem`
  - `--radius-lg: 0.875rem`
  - `--radius-xl: 1rem`
- Training and inference pages use card-based sections with dense control spacing and explicit separators.

## Color System

The UI uses a dark-first tokenized palette in `src/styles/global.css`.

- Background/surface:
  - `--bg-primary`, `--bg-secondary`, `--bg-tertiary`, `--bg-elevated`, `--surface-soft`
- Text:
  - `--text-primary`, `--text-secondary`, `--text-accent`
- Border:
  - `--border-color`
- Brand/action:
  - `--primary-accent`, `--primary-accent-hover`
- Semantic colors:
  - `--success`, `--warning`, `--danger`
  - roulette domain colors: `--roulette-green`, `--roulette-red`
- Focus token:
  - `--focus-ring` with explicit outline + offset behavior.

Contrast and readability:
- Primary text must remain on dark surfaces (`--text-primary` on `--bg-*`).
- Status messaging uses semantic backgrounds with border contrast (success/info/error blocks).

## Components and Patterns

### Navigation and structure

- Top-level navigation has two tabs (`Training`, `Inference`) using `NavLink` active state.
- Header and nav are sticky and visually separated with translucent surfaces/borders.

### Core reusable patterns

- Cards (`.card`) are the default information container.
- Form controls (`.form-input`, `.form-select`, `.input`, `.select`) must preserve tokenized border/focus behavior.
- Button variants:
  - Primary action (`.btn-primary`, `.primaryButton`)
  - Secondary action (`.btn-clear`, `.secondaryButton`)
  - Ghost/destructive/utility (`.ghostButton`, icon buttons)
- Table-based interaction for inference session history (`GameSession` history table).
- Modal overlays for training wizard and metadata previews.

### Interaction states

- Required states: default, hover, focus-visible, disabled.
- Buttons and icon buttons must have disabled styling and non-interactive cursor when disabled.
- Errors shown inline with `role="alert"` where implemented.
- Empty states must be explicit (for example history empty panel and preview empty blocks).

## Page Structure

- `/training`
  - Dataset upload + dataset preview
  - Checkpoint preview/manage
  - Training dashboard (status, metrics, charts)
- `/inference`
  - Checkpoint/dataset setup
  - Session controls (Play/Stop/Clear)
  - AI suggestion panel
  - Session history table with step actions

Composition rules:
- Keep each page inside `.page-shell` and use sectioned cards.
- Preserve separation between setup controls and live telemetry/history views.

## User Experience Rules

- Core flows must remain linear and predictable:
  - Upload/select dataset -> choose checkpoint -> start workflow.
- Prevent invalid actions with disabled controls and validation messages.
- Keep error feedback local to the failing action.
- Preserve explicit loading states (`Uploading...`, `isStarting`, `isStopping`, recompute flags).
- Keep outcome/profit feedback immediate and visually distinct (`.outcomeWin`, `.outcomeLoss`).

## Responsiveness

Implemented breakpoints include:
- `max-width: 1100px`: inference session grid collapses to one column.
- `max-width: 900px`: training shell/nav/control sections stack vertically.
- `max-width: 768px`, `720px`, `700px`, `520px`, `480px`: metric grids, wizard grids, and page paddings simplify for small screens.

Rules:
- Multi-column layouts must degrade to one column on narrow viewports.
- Tables must remain scrollable (`overflow: auto`) when width is constrained.
- Button clusters should wrap gracefully (`flex-wrap: wrap`) in header actions.

## Accessibility

- Global focus styling is enforced with `:focus-visible` outline and offset.
- Navigation region uses ARIA (`role="navigation"`, `aria-label="Primary"`).
- Inputs and actions include explicit labels/`aria-label` attributes where not self-describing.
- Error alerts use polite live regions where implemented (`role="alert"`, `aria-live="polite"`).
- Reduced motion is respected through `@media (prefers-reduced-motion: reduce)`.

## Design Principles

- Consistency over novelty: reuse existing tokens/components first.
- Clarity over decoration: prioritize task completion and readable status feedback.
- Predictability: keep control behavior stable across Training and Inference pages.
- Avoid unnecessary visual complexity and avoid introducing parallel styling systems outside existing global tokens.
