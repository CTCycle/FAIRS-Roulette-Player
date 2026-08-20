from __future__ import annotations

import ast
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[2] / "server"

BOUNDARY_RULES: dict[str, tuple[str, ...]] = {
    "server.contracts": (
        "server.api",
        "server.services",
        "server.repositories",
        "server.configurations",
        "server.learning",
    ),
    "server.api": ("server.repositories", "server.learning"),
    "server.repositories": ("server.api", "server.services"),
    "server.learning": ("server.api", "server.services"),
}


def _module_name(path: Path) -> str:
    relative = path.relative_to(SERVER_ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(("server", *parts))


def _imported_modules(tree: ast.AST) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return {name for name in imported if name.startswith("server.")}


def test_backend_module_boundaries_remain_explicit() -> None:
    violations: list[str] = []

    for path in SERVER_ROOT.rglob("*.py"):
        if any(part in {".venv", "__pycache__"} for part in path.parts):
            continue
        module = _module_name(path)
        for imported in _imported_modules(ast.parse(path.read_text(encoding="utf-8"))):
            forbidden = BOUNDARY_RULES.get(module)
            if forbidden is None:
                forbidden = tuple(
                    target
                    for owner, targets in BOUNDARY_RULES.items()
                    if module == owner or module.startswith(f"{owner}.")
                    for target in targets
                )
            if any(imported == target or imported.startswith(f"{target}.") for target in forbidden):
                violations.append(f"{module} imports {imported}")

    assert not violations, "Architectural boundary violations:\n" + "\n".join(sorted(violations))
