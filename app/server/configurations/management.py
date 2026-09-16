from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from threading import RLock
from typing import Any

from server.common import path as shared_paths
from server.contracts.configuration import JsonServerSettings, ServerSettings

###############################################################################
class ConfigurationManager:

    # -------------------------------------------------------------------------
    def __init__(
        self,
        runtime_path: str | Path | None = None,
        legacy_config_path: str | Path | None = None,
        *,
        config_path: str | Path | None = None,
    ) -> None:
        if config_path is not None:
            if runtime_path is not None or legacy_config_path is not None:
                raise ValueError(
                    "config_path cannot be combined with runtime or legacy paths."
                )
            runtime_path = config_path

        self._lock = RLock()
        self._require_explicit_runtime_path = config_path is not None
        self._runtime_path = (
            Path(runtime_path)
            if runtime_path is not None
            else shared_paths.RUNTIME_SETTINGS_FILE
        )
        self._legacy_config_path = (
            Path(legacy_config_path)
            if legacy_config_path is not None
            else (
                shared_paths.CONFIGURATIONS_FILE
                if runtime_path is None
                else None
            )
        )
        self._json_settings: JsonServerSettings | None = None
        self._server_settings: ServerSettings | None = None
        self.reload()

    # -------------------------------------------------------------------------
    @property
    def config_path(self) -> Path:
        """Return the active runtime path for older callers."""
        return self._runtime_path

    # -------------------------------------------------------------------------
    @property
    def runtime_path(self) -> Path:
        return self._runtime_path

    # -------------------------------------------------------------------------
    @property
    def legacy_config_path(self) -> Path | None:
        return self._legacy_config_path

    # -------------------------------------------------------------------------
    @staticmethod
    def _read_payload(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise RuntimeError(f"Configuration file not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Unable to load configuration from {path}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("Configuration must be a JSON object.")
        return payload

    # -------------------------------------------------------------------------
    @classmethod
    def _parse_settings(cls, path: Path) -> JsonServerSettings:
        payload = cls._read_payload(path)
        try:
            return JsonServerSettings.model_validate(payload)
        except ValueError as exc:
            raise RuntimeError(f"Invalid structured settings in {path}: {exc}") from exc

    # -------------------------------------------------------------------------
    @staticmethod
    def _serialize_settings(settings: JsonServerSettings) -> str:
        payload = settings.model_dump(mode="json")
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    # -------------------------------------------------------------------------
    def _persist_json_settings(self, settings: JsonServerSettings) -> None:
        target = self._runtime_path
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=target.parent,
                prefix=f".{target.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(self._serialize_settings(settings))
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, target)
            temporary_path = None
        except OSError as exc:
            raise RuntimeError(f"Unable to persist runtime settings to {target}") from exc
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass

    # -------------------------------------------------------------------------
    def _reload_locked(self) -> ServerSettings:
        if self._runtime_path.exists():
            json_settings = self._parse_settings(self._runtime_path)
        elif self._legacy_config_path is not None and self._legacy_config_path.exists():
            json_settings = self._parse_settings(self._legacy_config_path)
            self._persist_json_settings(json_settings)
        else:
            if self._require_explicit_runtime_path:
                raise RuntimeError(f"Configuration file not found: {self._runtime_path}")
            json_settings = JsonServerSettings()
            self._persist_json_settings(json_settings)

        server_settings = json_settings.to_server_settings()
        self._json_settings = json_settings
        self._server_settings = server_settings
        return server_settings

    # -------------------------------------------------------------------------
    def reload(
        self,
        config_path: str | Path | None = None,
        *,
        runtime_path: str | Path | None = None,
        legacy_config_path: str | Path | None = None,
    ) -> ServerSettings:
        with self._lock:
            if config_path is not None:
                self._runtime_path = Path(config_path)
                self._legacy_config_path = None
                self._require_explicit_runtime_path = True
            elif runtime_path is not None:
                self._runtime_path = Path(runtime_path)
                if legacy_config_path is not None:
                    self._legacy_config_path = Path(legacy_config_path)
            elif legacy_config_path is not None:
                self._legacy_config_path = Path(legacy_config_path)
            return self._reload_locked()

    # -------------------------------------------------------------------------
    def get_all(self) -> ServerSettings:
        with self._lock:
            if self._server_settings is None:
                return self._reload_locked()
            return self._server_settings

    # -------------------------------------------------------------------------
    def get_json_settings(self) -> JsonServerSettings:
        with self._lock:
            if self._json_settings is None:
                self._reload_locked()
            assert self._json_settings is not None
            return self._json_settings.model_copy(deep=True)

    # -------------------------------------------------------------------------
    def replace_json_settings(self, settings: JsonServerSettings) -> ServerSettings:
        with self._lock:
            candidate = JsonServerSettings.model_validate(settings)
            server_settings = candidate.to_server_settings()
            self._persist_json_settings(candidate)
            self._json_settings = candidate
            self._server_settings = server_settings
            return server_settings

    # -------------------------------------------------------------------------
    def reset_json_settings(self) -> ServerSettings:
        return self.replace_json_settings(JsonServerSettings())

    # -------------------------------------------------------------------------
    def get_block(self, name: str) -> dict[str, Any]:
        normalized = name.strip().lower()
        with self._lock:
            if self._json_settings is None:
                self._reload_locked()
            assert self._json_settings is not None
            blocks = self._json_settings.to_blocks()
            return dict(blocks.get(normalized, {}))

    # -------------------------------------------------------------------------
    def get_value(self, block: str, key: str, default: Any | None = None) -> Any:
        return self.get_block(block).get(key, default)
