# Copyright © 2026 Thomas Virdis
# Licensed under the MIT License.

from __future__ import annotations

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
            raise RuntimeError(
                "Application settings stored in this database are invalid."
            ) from exc

    # -------------------------------------------------------------------------
    def ensure_row(
        self,
        database: FAIRSDatabase,
    ) -> JsonServerSettings:
        with database.Session.begin() as session:
            row = session.get(ApplicationSettings, self.SETTINGS_ID)
            if row is None:
                settings = JsonServerSettings()
                row = ApplicationSettings(
                    settings_id=self.SETTINGS_ID,
                    jobs=settings.jobs.model_dump(mode="json"),
                    device=settings.device.model_dump(mode="json"),
                    roulette=settings.roulette.model_dump(mode="json"),
                )
                session.add(row)
            else:
                settings = self._from_row(row)
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
