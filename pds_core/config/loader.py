"""Carga configuracion de cliente desde YAML."""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from pds_core.config.schema.clients_schema import (
    ClienteConfig,
    ForecastConfig,
    SemaforosConfig,
    StorageConfig,
    StorageLocation,
)
from pds_core.config.validator import ValidadorConfiguracion


class CargadorConfiguracion:
    """Carga configuracion desde YAML y retorna ClienteConfig."""

    @staticmethod
    def _config_path(client_name: str) -> Path:
        root = Path(__file__).parent.parent.parent / "config" / "clients"
        folder = root / client_name / "client.yaml"
        if folder.exists():
            return folder
        flat = root / f"{client_name}.yaml"
        if flat.exists():
            return flat
        return folder

    @staticmethod
    def load(client_name: str = "hackathon") -> ClienteConfig:
        """
        Carga configuracion del cliente.

        Args:
            client_name: Nombre del cliente (archivo en config/clients/)

        Returns:
            ClienteConfig validado

        Raises:
            FileNotFoundError: Si no existe el YAML del cliente
            ValueError: Si la configuracion es invalida
        """
        config_path = CargadorConfiguracion._config_path(client_name)
        if not config_path.exists():
            raise FileNotFoundError(f"Config no existe: {config_path}")

        config_dict = CargadorConfiguracion._load_yaml(config_path)
        client_config = CargadorConfiguracion._dict_to_client_config(
            client_name, config_dict
        )
        ValidadorConfiguracion.validar(client_config)
        return client_config

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        """Carga YAML y retorna dict."""
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def _storage_location(data: Dict[str, Any], default_nombre: str) -> StorageLocation:
        """Construye StorageLocation desde dict YAML con defaults seguros."""
        if not data:
            raise ValueError(f"Storage location '{default_nombre}' no configurada")
        return StorageLocation(
            nombre=data.get("nombre", default_nombre),
            provider=data.get("provider", "local"),
            local_path=data.get("local_path"),
            sharepoint_folder=data.get("sharepoint_folder"),
            read_from=data.get("read_from", "local"),
            write_to=data.get("write_to", "both"),
            sync_direction=data.get("sync_direction"),
        )

    @staticmethod
    def _dict_to_client_config(
        client_name: str, config_dict: Dict[str, Any]
    ) -> ClienteConfig:
        """Convierte dict YAML a ClienteConfig."""
        storage_dict = config_dict.get("storage", {})
        backups_data = storage_dict.get("backups")
        backups: Optional[StorageLocation] = None
        if backups_data:
            backups = CargadorConfiguracion._storage_location(backups_data, "backups")

        storage = StorageConfig(
            entrada_canonica=CargadorConfiguracion._storage_location(
                storage_dict.get("entrada_canonica", {}), "entrada_canonica"
            ),
            entrada_materializada=CargadorConfiguracion._storage_location(
                storage_dict.get("entrada_materializada", {}), "entrada_materializada"
            ),
            salidas=CargadorConfiguracion._storage_location(
                storage_dict.get("salidas", {}), "salidas"
            ),
            logs=CargadorConfiguracion._storage_location(
                storage_dict.get("logs", {}), "logs"
            ),
            backups=backups,
            sharepoint_site=storage_dict.get("sharepoint_site"),
            sharepoint_auth_method=storage_dict.get(
                "sharepoint_auth_method", "device_code"
            ),
        )

        semaforos = SemaforosConfig(**config_dict.get("semaforos", {}))
        forecast = ForecastConfig(**config_dict.get("forecast", {}))

        client_block = config_dict.get("client", {})
        resolved_name = config_dict.get("client_name") or client_block.get("code", client_name)
        if isinstance(resolved_name, str):
            resolved_name = resolved_name.lower()

        version = config_dict.get("version") or client_block.get("version", "0.1")

        return ClienteConfig(
            client_name=resolved_name,
            version=version,
            storage=storage,
            semaforos=semaforos,
            forecast=forecast,
            ingestion=config_dict.get("ingestion", {}),
            columnas_override=config_dict.get("columnas_override"),
            log_level=config_dict.get("log_level", "INFO"),
        )
