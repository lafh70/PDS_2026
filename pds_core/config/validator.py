"""Validacion de configuracion de cliente."""

import os
import re
from pathlib import Path

from pds_core.config.schema.clients_schema import ClienteConfig

PROJECT_ID_FORMAT_DEFAULT = r"^[A-Z]{2}-\d{4}-\d{4}-\d{2}$"


class ValidadorConfiguracion:
    """Valida configuracion de cliente."""

    @staticmethod
    def validar(config: ClienteConfig) -> bool:
        """
        Valida configuracion del cliente.

        Args:
            config: ClienteConfig

        Returns:
            True si OK

        Raises:
            ValueError: Si la configuracion es invalida
        """
        ValidadorConfiguracion._validar_storage(config)
        ValidadorConfiguracion._validar_reglas(config)
        print("[OK] Configuracion valida")
        return True

    @staticmethod
    def _validar_storage(config: ClienteConfig) -> None:
        """Valida configuracion de almacenamiento."""
        entrada = config.storage.entrada_canonica
        if not entrada.local_path and not entrada.sharepoint_folder:
            raise ValueError("entrada_canonica debe tener local_path o sharepoint_folder")

        locations = [
            config.storage.entrada_canonica,
            config.storage.entrada_materializada,
            config.storage.salidas,
            config.storage.logs,
        ]
        if config.storage.backups:
            locations.append(config.storage.backups)

        uses_remote = False
        for loc in locations:
            provider = (loc.provider or "").lower()
            if provider in ("sharepoint", "hybrid"):
                uses_remote = True
                if not config.storage.sharepoint_site and not loc.sharepoint_folder:
                    raise ValueError(
                        f"Ubicacion '{loc.nombre}' requiere sharepoint_site o sharepoint_folder"
                    )

            if provider in ("local", "hybrid") and loc.local_path:
                path = Path(loc.local_path)
                if not path.exists():
                    path.mkdir(parents=True, exist_ok=True)
                if not os.access(path, os.W_OK):
                    raise ValueError(f"Sin permisos escritura: {path}")

        if uses_remote:
            ValidadorConfiguracion._simular_conexion_sharepoint(config)

        print("[OK] Almacenamiento valido")

    @staticmethod
    def _simular_conexion_sharepoint(config: ClienteConfig) -> None:
        """Simula verificacion de conectividad SharePoint (sin llamada real)."""
        site = config.storage.sharepoint_site or ""
        if not site.startswith("http"):
            raise ValueError(
                f"sharepoint_site invalido (simulacion): {config.storage.sharepoint_site!r}"
            )
        print(f"[OK] SharePoint simulado: {site}")

    @staticmethod
    def _validar_reglas(config: ClienteConfig) -> None:
        """Valida reglas de negocio (duraciones, formatos, umbrales)."""
        for tipo, duracion in config.forecast.duraciones_obras.items():
            if duracion <= 0:
                raise ValueError(
                    f"Duracion {tipo} debe ser > 0, es {duracion}"
                )

        pct = config.semaforos.finance_alerta_porcentaje
        if not 0 < pct <= 100:
            raise ValueError(
                f"finance_alerta_porcentaje debe estar entre 1 y 100, es {pct}"
            )

        fmt = config.ingestion.get("project_id_format", PROJECT_ID_FORMAT_DEFAULT)
        try:
            re.compile(fmt)
        except re.error as exc:
            raise ValueError(f"project_id_format regex invalido: {fmt}") from exc

        if not re.match(fmt, "HK-9001-2026-01"):
            raise ValueError(
                f"project_id_format no acepta ejemplo canonico HK-9001-2026-01: {fmt}"
            )

        print("[OK] Reglas validas")
