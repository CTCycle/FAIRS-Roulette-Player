from __future__ import annotations

from functools import lru_cache

from server.common import path as shared_paths
from server.configurations.environment import load_environment
from server.configurations.management import ConfigurationManager
from server.contracts.configuration import ServerSettings

###############################################################################
@lru_cache(maxsize=1)
def get_configuration_manager() -> ConfigurationManager:
    return ConfigurationManager(config_path=shared_paths.CONFIGURATIONS_FILE)

###############################################################################
def get_server_settings() -> ServerSettings:
    return get_configuration_manager().get_all()

###############################################################################
def reload_settings_for_tests(config_path: str | None = None) -> ServerSettings:
    load_environment(force=True)
    return get_configuration_manager().reload(config_path=config_path)
