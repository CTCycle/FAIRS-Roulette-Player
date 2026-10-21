# Copyright © 2026 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from server.contracts.configuration import JsonServerSettings
from server.repositories.database.backend import FAIRSDatabase
from server.repositories.schemas.models import ApplicationSettings


###############################################################################
class ApplicationSettingsRepository:
    """Read and update the one Settings-page row in the active database."""

    SETTINGS_ID = 1

    # -------------------------------------------------------------------------
    @staticmethod
    def _from_row(row: ApplicationSettings) -> JsonServerSettings:
        try:
            return JsonServerSettings.model_validate(
                {"jobs": row.jobs, "device": row.device, "roulette": row.roulette}
            )
        except ValidationError as exc:
            raise RuntimeError("Application settings stored in this database are invalid.") from exc

    # -------------------------------------------------------------------------
    @staticmethod
    def _read_legacy(path: Path) -> JsonServerSettings:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return JsonServerSettings.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            raise RuntimeError("Legacy application settings could not be imported safely.") from exc

    # -------------------------------------------------------------------------
    def ensure_row(
        self,
        database: FAIRSDatabase,
        *,
        legacy_path: str | Path | None = None,
        allow_legacy_import: bool = False,
        remove_legacy_after: bool = True,
    ) -> JsonServerSettings:
        path = Path(legacy_path) if legacy_path is not None else None
        with database.Session.begin() as session:
            row = session.get(ApplicationSettings, self.SETTINGS_ID)
            if row is None:
                settings = (
                    self._read_legacy(path)
                    if allow_legacy_import and path is not None and path.is_file()
                    else JsonServerSettings()
                )
                row = ApplicationSettings(
                    settings_id=self.SETTINGS_ID,
                    jobs=settings.jobs.model_dump(mode="json"),
                    device=settings.device.model_dump(mode="json"),
                    roulette=settings.roulette.model_dump(mode="json"),
                )
                session.add(row)
            else:
                settings = self._from_row(row)
        if remove_legacy_after and path is not None and path.is_file():
            try:
                path.unlink()
            except OSError:
                # A committed database row is authoritative. Retaining an old
                # file cannot overwrite it on later starts.
                pass
        return settings

    # -------------------------------------------------------------------------
    def get(self, database: FAIRSDatabase) -> JsonServerSettings:
        with database.Session() as session:
            row = session.get(ApplicationSettings, self.SETTINGS_ID)
            if row is None:
                raise RuntimeError("Application settings have not been initialized.")
            return self._from_row(row)

    # -------------------------------------------------------------------------
    def replace(
        self, database: FAIRSDatabase, settings: JsonServerSettings
    ) -> JsonServerSettings:
        candidate = JsonServerSettings.model_validate(settings)
        with database.Session.begin() as session:
            row = session.get(ApplicationSettings, self.SETTINGS_ID)
            if row is None:
                row = ApplicationSettings(settings_id=self.SETTINGS_ID)
                session.add(row)
            row.jobs = candidate.jobs.model_dump(mode="json")
            row.device = candidate.device.model_dump(mode="json")
            row.roulette = candidate.roulette.model_dump(mode="json")
        return candidate


__all__ = ["ApplicationSettingsRepository"]
