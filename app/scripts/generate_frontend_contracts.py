from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from export_openapi import render_openapi
from server.contracts.training import TrainingConfig

OUTPUT_PATH = (
    Path(__file__).resolve().parents[1]
    / "client"
    / "src"
    / "generated"
    / "api.ts"
)


###############################################################################
def _reference_name(reference: str) -> str:
    return reference.rsplit("/", 1)[-1]


###############################################################################
def _literal(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return json.dumps(value, ensure_ascii=False)


###############################################################################
def _schema_to_typescript(schema: Mapping[str, Any]) -> str:
    reference = schema.get("$ref")
    if isinstance(reference, str):
        return _reference_name(reference)

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values:
        return " | ".join(_literal(value) for value in enum_values)

    for keyword, separator in (("anyOf", " | "), ("oneOf", " | "), ("allOf", " & ")):
        variants = schema.get(keyword)
        if isinstance(variants, list) and variants:
            rendered = [_schema_to_typescript(variant) for variant in variants]
            return separator.join(dict.fromkeys(rendered))

    schema_type = schema.get("type")
    if schema_type == "string":
        return "string"
    if schema_type in {"integer", "number"}:
        return "number"
    if schema_type == "boolean":
        return "boolean"
    if schema_type == "null":
        return "null"
    if schema_type == "array":
        items = schema.get("items")
        item_type = (
            _schema_to_typescript(items)
            if isinstance(items, Mapping)
            else "unknown"
        )
        return f"Array<{item_type}>"
    if schema_type == "object" or "properties" in schema:
        properties = schema.get("properties")
        if isinstance(properties, Mapping):
            required = set(schema.get("required", []))
            members: list[str] = []
            for name in sorted(properties):
                property_schema = properties[name]
                property_type = (
                    _schema_to_typescript(property_schema)
                    if isinstance(property_schema, Mapping)
                    else "unknown"
                )
                optional = "" if name in required else "?"
                members.append(f"    {json.dumps(name)}{optional}: {property_type};")
            if members:
                return "{\n" + "\n".join(members) + "\n}"

        additional = schema.get("additionalProperties")
        if isinstance(additional, Mapping):
            return f"Record<string, {_schema_to_typescript(additional)}>"
        if additional is True:
            return "Record<string, unknown>"
        return "Record<string, never>"

    return "unknown"


###############################################################################
def _render_training_defaults() -> list[str]:
    defaults = TrainingConfig(use_data_generator=True).model_dump()
    defaults["use_data_generator"] = TrainingConfig.model_fields[
        "use_data_generator"
    ].default
    defaults["dataset_id"] = TrainingConfig.model_fields["dataset_id"].default

    lines = ["export const TRAINING_CONFIG_DEFAULTS = {"]
    for name in sorted(defaults):
        lines.append(f"    {json.dumps(name)}: {_literal(defaults[name])},")
    lines.extend(
        [
            "} as const satisfies TrainingConfig;",
            "",
        ]
    )
    return lines


###############################################################################
def render_typescript() -> str:
    openapi = json.loads(render_openapi())
    schemas = openapi.get("components", {}).get("schemas", {})
    if not isinstance(schemas, Mapping):
        raise RuntimeError("OpenAPI schema components are missing.")

    lines = [
        "// Generated from the canonical FastAPI/Pydantic contract.",
        "// Do not edit manually. Run app/scripts/generate_frontend_contracts.py.",
        "",
    ]
    for name in sorted(schemas):
        schema = schemas[name]
        if not isinstance(schema, Mapping):
            raise RuntimeError(f"OpenAPI component {name} is not an object schema.")
        rendered = _schema_to_typescript(schema)
        lines.append(f"export type {name} = {rendered};")
        lines.append("")

    lines.extend(_render_training_defaults())
    return "\n".join(lines)


###############################################################################
def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate or check frontend transport contracts from FastAPI/Pydantic."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the checked-in generated TypeScript differs from the backend contract",
    )
    options = parser.parse_args(arguments)
    rendered = render_typescript()

    if options.check:
        if not OUTPUT_PATH.is_file():
            print(f"Missing generated frontend contract: {OUTPUT_PATH}")
            return 1
        if OUTPUT_PATH.read_text(encoding="utf-8") != rendered:
            print(f"Generated frontend contract is out of date: {OUTPUT_PATH}")
            return 1
        print(f"Generated frontend contract is current: {OUTPUT_PATH}")
        return 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(rendered, encoding="utf-8")
    print(f"Wrote generated frontend contract: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
