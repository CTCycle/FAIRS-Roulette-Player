from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path


OPENAPI_PATH = Path(__file__).resolve().parents[1] / "shared" / "openapi.json"


def render_openapi() -> str:
    """Render the runtime FastAPI contract as a stable JSON document."""
    from server.app import app

    return json.dumps(app.openapi(), indent=2) + "\n"


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export or check the shared OpenAPI schema.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the checked-in schema differs from the runtime contract",
    )
    options = parser.parse_args(arguments)
    rendered_schema = render_openapi()

    if options.check:
        if not OPENAPI_PATH.is_file():
            print(f"Missing OpenAPI schema: {OPENAPI_PATH}")
            return 1
        if OPENAPI_PATH.read_text(encoding="utf-8") != rendered_schema:
            print(f"OpenAPI schema is out of date: {OPENAPI_PATH}")
            return 1
        print(f"OpenAPI schema is current: {OPENAPI_PATH}")
        return 0

    OPENAPI_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPENAPI_PATH.write_text(rendered_schema, encoding="utf-8")
    print(f"Wrote OpenAPI schema: {OPENAPI_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
