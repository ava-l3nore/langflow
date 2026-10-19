from collections.abc import Callable

from lfx.log.logger import logger
from lfx.services.settings.service import SettingsService
from typing_extensions import override

from langflow.services.factory import ServiceFactory
from langflow.services.session.service import SessionService
from langflow.services.storage.service import StorageService

DEFAULT_STORAGE_TYPE = "local"


def _load_local() -> type[StorageService]:
    from .local import LocalStorageService

    return LocalStorageService


def _load_s3() -> type[StorageService]:
    from .s3 import S3StorageService

    return S3StorageService


# Maps a storage_type setting to a loader for its StorageService class.
# Loaders keep backend imports lazy so optional dependencies (e.g. boto for S3)
# are only imported when that backend is selected.
_STORAGE_BACKENDS: dict[str, Callable[[], type[StorageService]]] = {
    "local": _load_local,
    "s3": _load_s3,
}


def register_storage_backend(storage_type: str, loader: Callable[[], type[StorageService]]) -> None:
    """Register a storage backend so StorageServiceFactory can create it without being edited."""
    _STORAGE_BACKENDS[storage_type.lower()] = loader


class StorageServiceFactory(ServiceFactory):
    def __init__(self) -> None:
        super().__init__(
            StorageService,
        )

    @override
    def create(self, session_service: SessionService, settings_service: SettingsService):
        storage_type = settings_service.settings.storage_type.lower()
        loader = _STORAGE_BACKENDS.get(storage_type)
        if loader is None:
            logger.warning(f"Storage type {storage_type} not supported. Using local storage.")
            loader = _STORAGE_BACKENDS[DEFAULT_STORAGE_TYPE]
        storage_class = loader()
        return storage_class(session_service, settings_service)
