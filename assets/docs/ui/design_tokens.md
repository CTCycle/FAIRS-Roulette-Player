## Design Tokens

Last updated: 2026-08-20

## Typography

- Base font family:
  - `var(--font-sans)` resolves to the current sans-serif stack defined in `app/client/src/styles/global.css`
- Core type scale tokens:
  - `--font-size-xs: 0.75rem`
  - `--font-size-sm: 0.875rem`
  - `--font-size-md: 1rem`
  - `--font-size-lg: 1.125rem`
  - `--font-size-xl: 1.25rem`
  - `--font-size-2xl: 1.75rem`
- Default line height:
  - `--line-height-default: 1.5`
- Page titles use the established desktop-scale type system; no mobile-specific type scaling is required.
- Control and icon sizing:
  - `--control-height: 2.25rem`
  - `--icon-button-size: 2rem`

## Layout And Spacing

- Main app shell is route-based with sticky header and navigation.
- The app shell uses a sticky branded header; content scrolls inside the main layout.
- Global page container is constrained through `.page-shell` to a maximum width of 1680px.
- The desktop shell minimum is `--desktop-min-width: 1100px`.
- Spacing tokens:
  - `--spacing-xs: 0.25rem`
  - `--spacing-sm: 0.5rem`
  - `--spacing-md: 1rem`
  - `--spacing-lg: 1.5rem`
  - `--spacing-xl: 2rem`
  - `--spacing-2xl: 3rem`
- Radius tokens:
  - `--radius-sm: 0.375rem`
  - `--radius-md: 0.5rem`
  - `--radius-lg: 0.875rem`
  - `--radius-xl: 1rem`

## Color System

The current UI uses a dark-first tokenized palette defined in `app/client/src/styles/global.css`.

- Background and surface:
  - `--bg-primary`
  - `--bg-secondary`
  - `--bg-tertiary`
  - `--bg-elevated`
  - `--surface-soft`
- Text:
  - `--text-primary`
  - `--text-secondary`
  - `--text-accent`
- Borders:
  - `--border-color`
- Brand and action:
  - `--primary-accent`
  - `--primary-accent-hover`
- Semantic:
  - `--success`
  - `--warning`
  - `--danger`
  - `--roulette-green`
  - `--roulette-red`
- Focus:
  - `--focus-ring`
- Shadows:
  - `--shadow-sm`
  - `--shadow-md`

## Token Rules

- Use token values instead of hard-coded ad-hoc colors and spacing.
- Keep primary text readable on dark surfaces.
- Preserve semantic feedback colors for success, warning, and error states.

## Related Files

- Read `components_and_patterns.md` for how these tokens are applied in components.
- Read `experience.md` for desktop layout and support expectations.
