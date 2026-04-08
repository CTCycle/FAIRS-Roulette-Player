from __future__ import annotations

from pathlib import Path

from FAIRS.server.common.utils import variables as variables_module


def test_runtime_env_values_are_loaded_from_dotenv(
    tmp_path: Path, monkeypatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "FASTAPI_HOST=0.0.0.0",
                "FASTAPI_PORT=5111",
                "UI_HOST=127.0.0.1",
                "UI_PORT=8111",
                "MPLBACKEND=Agg",
                "KERAS_BACKEND=torch",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(variables_module, "ENV_FILE_PATH", str(env_file))
    env = variables_module.EnvironmentVariables()

    assert env.get("FASTAPI_HOST") == "0.0.0.0"
    assert env.get("FASTAPI_PORT") == "5111"
    assert env.get("UI_HOST") == "127.0.0.1"
    assert env.get("UI_PORT") == "8111"
    assert env.get("MPLBACKEND") == "Agg"
    assert env.get("KERAS_BACKEND") == "torch"
