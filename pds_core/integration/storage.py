"""Storage abstraction: local filesystem and hybrid (local + SharePoint stub)."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Union

from pds_core.config.schema.clients_schema import StorageConfig, StorageLocation


class StorageBackend(ABC):
    """Interface for storage providers."""

    @abstractmethod
    def read(self, path: str) -> bytes:
        """Read file and return raw bytes."""

    @abstractmethod
    def write(self, path: str, data: bytes) -> None:
        """Write bytes to file."""

    @abstractmethod
    def list(self, folder: str) -> List[str]:
        """List file names in a folder."""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check whether a file exists."""

    @abstractmethod
    def delete(self, path: str) -> None:
        """Delete a file."""


class LocalBackend(StorageBackend):
    """Local filesystem storage."""

    def __init__(self, base_path: Union[str, Path]):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _full_path(self, path: str) -> Path:
        return self.base_path / path

    def read(self, path: str) -> bytes:
        full_path = self._full_path(path)
        if not full_path.exists():
            raise FileNotFoundError(f"No existe: {full_path}")
        return full_path.read_bytes()

    def write(self, path: str, data: bytes) -> None:
        full_path = self._full_path(path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)

    def list(self, folder: str) -> List[str]:
        full_path = self._full_path(folder)
        if not full_path.exists():
            return []
        return [f.name for f in full_path.iterdir() if f.is_file()]

    def exists(self, path: str) -> bool:
        return self._full_path(path).exists()

    def delete(self, path: str) -> None:
        full_path = self._full_path(path)
        if full_path.exists():
            full_path.unlink()


class SharePointBackend(StorageBackend):
    """SharePoint storage stub — to be implemented with MS Graph."""

    def read(self, path: str) -> bytes:
        raise NotImplementedError("SharePointBackend.read no implementado aún")

    def write(self, path: str, data: bytes) -> None:
        raise NotImplementedError("SharePointBackend.write no implementado aún")

    def list(self, folder: str) -> List[str]:
        raise NotImplementedError("SharePointBackend.list no implementado aún")

    def exists(self, path: str) -> bool:
        raise NotImplementedError("SharePointBackend.exists no implementado aún")

    def delete(self, path: str) -> None:
        raise NotImplementedError("SharePointBackend.delete no implementado aún")


class HybridBackend(StorageBackend):
    """Hybrid storage: local cache with optional SharePoint sync."""

    def __init__(
        self,
        local_backend: LocalBackend,
        read_from: str = "local_first",
        write_to: str = "both",
        sharepoint_backend: Optional[SharePointBackend] = None,
    ):
        self.local = local_backend
        self.read_from = read_from
        self.write_to = write_to
        self.sharepoint = sharepoint_backend or SharePointBackend()

    def read(self, path: str) -> bytes:
        if self.read_from == "sp_first":
            try:
                return self.sharepoint.read(path)
            except (NotImplementedError, FileNotFoundError):
                return self.local.read(path)

        try:
            return self.local.read(path)
        except FileNotFoundError:
            try:
                return self.sharepoint.read(path)
            except NotImplementedError:
                raise

    def write(self, path: str, data: bytes) -> None:
        if self.write_to in ("local", "both"):
            self.local.write(path, data)
        if self.write_to in ("sharepoint", "both"):
            try:
                self.sharepoint.write(path, data)
            except NotImplementedError:
                pass

    def list(self, folder: str) -> List[str]:
        return self.local.list(folder)

    def exists(self, path: str) -> bool:
        return self.local.exists(path)

    def delete(self, path: str) -> None:
        self.local.delete(path)
        try:
            self.sharepoint.delete(path)
        except NotImplementedError:
            pass


class StorageManager:
    """
    Gestiona almacenamiento flexible (local, SharePoint, hybrid).

    Arquitectura:
    - LocalBackend: lectura/escritura en filesystem local
    - SharePointBackend: stub para integracion MS Graph (futuro)
    - HybridBackend: cache local con sincronizacion opcional a SharePoint

    Uso:
        config = CargadorConfiguracion.load("hackathon").storage
        storage = StorageManager(config)
        data = storage.read_entrada_canonica("PDS_GESTION.xlsx")

    Args:
        storage_config: StorageConfig con ubicaciones por rol (entrada, salidas, logs).

    Raises:
        ValueError: Si el provider no es soportado.
    """

    def __init__(self, storage_config: StorageConfig):
        self.config = storage_config
        self.entrada_canonica = self._create_backend(storage_config.entrada_canonica)
        self.entrada_materializada = self._create_backend(
            storage_config.entrada_materializada
        )
        self.salidas = self._create_backend(storage_config.salidas)
        self.logs = self._create_backend(storage_config.logs)
        if storage_config.backups:
            self.backups = self._create_backend(storage_config.backups)
        else:
            self.backups = None

    def _create_backend(self, location: StorageLocation) -> StorageBackend:
        base = location.local_path or "."
        if location.provider == "local":
            return LocalBackend(base)
        if location.provider == "hybrid":
            local = LocalBackend(base)
            return HybridBackend(local, location.read_from, location.write_to)
        if location.provider == "sharepoint":
            return SharePointBackend()
        raise ValueError(f"Provider no soportado: {location.provider}")

    def read_entrada_canonica(self, path: str) -> bytes:
        return self.entrada_canonica.read(path)

    def write_entrada_canonica(self, path: str, data: bytes) -> None:
        self.entrada_canonica.write(path, data)

    def read_salidas(self, path: str) -> bytes:
        return self.salidas.read(path)

    def write_salidas(self, path: str, data: bytes) -> None:
        self.salidas.write(path, data)

    def write_logs(self, path: str, data: bytes) -> None:
        self.logs.write(path, data)
