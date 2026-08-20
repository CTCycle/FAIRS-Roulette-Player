## Testing And Quality

Last updated: 2026-08-20

## Quality Baseline

- Prefer small, well-scoped changes over broad rewrites.
- Keep docs synchronized with behavior changes in the same change set.
- Treat typing, linting, and relevant tests as part of the definition of done.

## Python Validation

- Lint and format with Ruff or the repository-equivalent configured tooling.
- Follow a Pylance-compatible type discipline.
- Prefer targeted `pytest` execution when changing narrow backend behavior.
- Expand to broader unit or e2e coverage when changes cross module boundaries.

## Frontend Validation

- Use the existing npm scripts for linting and build validation.
- Keep parser logic defensive where backend payloads can drift.
- Validate UI behavior visually when user-facing layout or interaction changes are involved.
- The current frontend package provides build and lint scripts but no standalone frontend test scripts.

## Test Layout

Primary automated test surfaces live under `app/tests`:

- `app/tests/unit`
  - unit and service-level validation
- `app/tests/e2e`
  - API and workflow coverage
- `app/tests/run_tests.bat`
  - repository-standard Windows test entry point
- `.github/workflows/ci.yml`
  - Linux CI runs Ruff, backend unit tests, Alembic history/model consistency checks, OpenAPI generation, and the PostgreSQL persistence contract.

## Migration Validation

- Keep the immutable baseline aligned with all four current SQLAlchemy tables, indexes, named checks/unique constraints, and foreign-key cascade semantics.
- Use test-only synthetic revisions for behind-version and rollback cases; do not add failure-only revisions to production history.
- Validate clean, current, legacy adoption, partial/drift rejection, unknown/ahead revision rejection, rollback, and concurrent SQLite initialization. Run PostgreSQL persistence migration coverage when the service is available.

## Change Expectations

- Run the smallest relevant test slice first.
- Use broader checks when shared infrastructure or startup flow changes.
- Keep QA artifacts in `assets/QA/` when persistent evidence is needed.
- Do not leave temporary logs, screenshots, or validation scraps scattered through the repository.

## Related Files

- Read `python.md` for backend implementation rules.
- Read `typescript.md` for frontend implementation rules.
- Read `../operations/troubleshooting.md` for common runtime and test recovery checks.
