from __future__ import annotations

import os

from server.common import path as shared_paths

###############################################################################
CACHE_DIRECTORIES = {
    "uv": shared_paths.CACHE_PATH / "uv",
    "npm": shared_paths.CACHE_PATH / "npm",
    "pip": shared_paths.CACHE_PATH / "pip",
    "python": shared_paths.CACHE_PATH / "python",
    "pytest": shared_paths.CACHE_PATH / "pytest",
    "pytest-tmp": shared_paths.CACHE_PATH / "pytest-tmp",
    "ruff": shared_paths.CACHE_PATH / "ruff",
    "mypy": shared_paths.CACHE_PATH / "mypy",
    "coverage": shared_paths.CACHE_PATH / "coverage",
    "playwright-browsers": shared_paths.CACHE_PATH / "playwright-browsers",
    "vite": shared_paths.CACHE_PATH / "vite",
    "typescript": shared_paths.CACHE_PATH / "typescript",
    "keras": shared_paths.CACHE_PATH / "keras",
    "torch": shared_paths.CACHE_PATH / "torch",
    "torch-inductor": shared_paths.CACHE_PATH / "torch-inductor",
    "triton": shared_paths.CACHE_PATH / "triton",
    "matplotlib": shared_paths.CACHE_PATH / "matplotlib",
    "xdg": shared_paths.CACHE_PATH / "xdg",
    "cuda": shared_paths.CACHE_PATH / "cuda",
}

CACHE_ENVIRONMENT = {
    "FAIRS_CACHE_DIR": shared_paths.CACHE_PATH,
    "UV_CACHE_DIR": CACHE_DIRECTORIES["uv"],
    "NPM_CONFIG_CACHE": CACHE_DIRECTORIES["npm"],
    "PIP_CACHE_DIR": CACHE_DIRECTORIES["pip"],
    "PYTHONPYCACHEPREFIX": CACHE_DIRECTORIES["python"],
    "PYTEST_CACHE_DIR": CACHE_DIRECTORIES["pytest"],
    "PYTEST_BASETEMP_DIR": CACHE_DIRECTORIES["pytest-tmp"],
    "RUFF_CACHE_DIR": CACHE_DIRECTORIES["ruff"],
    "MYPY_CACHE_DIR": CACHE_DIRECTORIES["mypy"],
    "COVERAGE_FILE": CACHE_DIRECTORIES["coverage"] / ".coverage",
    "PLAYWRIGHT_BROWSERS_PATH": CACHE_DIRECTORIES["playwright-browsers"],
    "KERAS_HOME": CACHE_DIRECTORIES["keras"],
    "TORCH_HOME": CACHE_DIRECTORIES["torch"],
    "TORCHINDUCTOR_CACHE_DIR": CACHE_DIRECTORIES["torch-inductor"],
    "TRITON_CACHE_DIR": CACHE_DIRECTORIES["triton"],
    "MPLCONFIGDIR": CACHE_DIRECTORIES["matplotlib"],
    "XDG_CACHE_HOME": CACHE_DIRECTORIES["xdg"],
    "CUDA_CACHE_PATH": CACHE_DIRECTORIES["cuda"],
}

###############################################################################
def configure_cache_environment() -> None:
    """Create and export every disposable application cache below CACHE_PATH."""
    shared_paths.CACHE_PATH.mkdir(parents=True, exist_ok=True)
    for cache_path in CACHE_DIRECTORIES.values():
        cache_path.mkdir(parents=True, exist_ok=True)
    for variable_name, cache_path in CACHE_ENVIRONMENT.items():
        os.environ[variable_name] = str(cache_path)
