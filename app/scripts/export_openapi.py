from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path


###############################################################################
def render_openapi() -> str:
    """Render the canonical runtime FastAPI contract as stable JSON."""
    from server.app import app
    from server.common.version import get_application_version

    app.version = get_application_version()
    return json.dumps(app.openapi(), indent=2) + "\n"


###############################################################################
def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export the canonical runtime OpenAPI schema."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="optional output path; without it the schema is written to stdout",
    )
    options = parser.parse_args(arguments)
    rendered_schema = render_openapi()

    if options.output is None:
        print(rendered_schema, end="")
        return 0

    output_path = options.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered_schema, encoding="utf-8")
    print(f"Wrote OpenAPI schema: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
