from __future__ import annotations

from functools import lru_cache

from server.common import path as shared_paths
from server.configurations.environment import load_environment
from server.configurations.management import ConfigurationManager
from server.domain.configuration import ServerSettings


###############################################################################
@lru_cache(maxsize=1)
def get_configuration_manager() -> ConfigurationManager:
    load_environment()
    return ConfigurationManager(config_path=shared_paths.CONFIGURATIONS_FILE)


###############################################################################
def get_server_settings() -> ServerSettings:
    return get_configuration_manager().get_all()


###############################################################################
def reload_settings_for_tests(config_path: str | None = None) -> ServerSettings:
    load_environment(force=True)
    return get_configuration_manager().reload(config_path=config_path)


###############################################################################
def get_poll_interval_seconds(minimum: float = 0.25) -> float:
    settings = get_server_settings()
    value = float(settings.jobs.polling_interval)
    return max(minimum, value)
