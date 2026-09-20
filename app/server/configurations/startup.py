from __future__ import annotations

from server.common import path as shared_paths
from server.configurations.environment import load_environment
from server.configurations.management import ConfigurationManager
from server.contracts.configuration import ServerSettings

_configuration_manager: ConfigurationManager | None = None

###############################################################################
def get_configuration_manager() -> ConfigurationManager:
    global _configuration_manager
    if _configuration_manager is None:
        _configuration_manager = ConfigurationManager(
            runtime_path=shared_paths.RUNTIME_SETTINGS_FILE,
        )
    return _configuration_manager

###############################################################################
def _clear_configuration_manager_cache() -> None:
    global _configuration_manager
    _configuration_manager = None


# Preserve the existing test seam used throughout the repository.
get_configuration_manager.cache_clear = _clear_configuration_manager_cache  # type: ignore[attr-defined]

###############################################################################
def get_server_settings() -> ServerSettings:
    return get_configuration_manager().get_all()

###############################################################################
def reload_settings_for_tests(
    runtime_path: str | None = None,
) -> ServerSettings:
    global _configuration_manager
    load_environment(force=True)
    get_configuration_manager.cache_clear()  # type: ignore[attr-defined]
    if runtime_path is not None:
        _configuration_manager = ConfigurationManager(runtime_path=runtime_path)
    else:
        _configuration_manager = get_configuration_manager()
    return _configuration_manager.get_all()
