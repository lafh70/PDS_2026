"""Schema de configuracion por cliente (dataclasses)."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StorageLocation:
    """Define una ubicacion de almacenamiento (entrada, salida, logs)."""

    nombre: str
    provider: str
    local_path: Optional[str] = None
    sharepoint_folder: Optional[str] = None
    read_from: str = "local"
    write_to: str = "both"
    sync_direction: Optional[str] = None


@dataclass
class StorageConfig:
    """Configuracion de almacenamiento del cliente."""

    entrada_canonica: StorageLocation
    entrada_materializada: StorageLocation
    salidas: StorageLocation
    logs: StorageLocation
    backups: Optional[StorageLocation] = None
    sharepoint_site: Optional[str] = None
    sharepoint_auth_method: str = "device_code"


@dataclass
class SemaforosConfig:
    """Configuracion de reglas de semaforos (DDO, GC, permisos, finanzas)."""

    ddo_negro_keywords: List[str] = field(
        default_factory=lambda: ["CANCELADO", "NO REQUIERE"]
    )
    ddo_verde_keywords: List[str] = field(
        default_factory=lambda: ["ADJUDICADO", "ADJUDICADA"]
    )
    ddo_amarillo_keywords: List[str] = field(
        default_factory=lambda: ["EN PROCESO"]
    )
    ddo_alerta_ventana_dias: int = 14

    gc_negro_keywords: List[str] = field(
        default_factory=lambda: ["CANCELADO", "NO REQUIERE"]
    )
    gc_verde_keywords: List[str] = field(
        default_factory=lambda: ["ADJUDICADO", "ADJUDICADA"]
    )
    gc_amarillo_keywords: List[str] = field(
        default_factory=lambda: ["EN PROCESO"]
    )
    gc_alerta_ventana_dias: int = 14

    permits_negro_keywords: List[str] = field(
        default_factory=lambda: ["NO REQUIERE", "CANCELADO"]
    )
    permits_verde_keywords: List[str] = field(
        default_factory=lambda: ["Obtenido"]
    )
    permits_amarillo_keywords: List[str] = field(
        default_factory=lambda: ["Tramitando", "Derivado Gestor"]
    )
    permits_alerta_ventana_dias: int = 14

    finance_alerta_porcentaje: int = 85


@dataclass
class ForecastConfig:
    """Configuracion de forecast (duraciones, intervalos, tramites)."""

    duraciones_obras: Dict[str, int] = field(
        default_factory=lambda: {
            "INTEGRAL": 120,
            "MEDIA": 90,
            "BAJA": 30,
            "CORPORATIVO": 120,
            "RELOCALIZACION": 180,
        }
    )
    intervalo_h1_h2: int = 21
    intervalo_h2_h3: int = 30
    intervalo_h3_h4: int = 21
    intervalo_h4_h5: int = 30
    intervalo_h5_h6: int = 7
    tramite_dias: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: {
            "PERMISO_OBRA": {"GRANDE": 150, "MEDIANA": 90, "PEQUENA": 45},
            "AVISO": {"GRANDE": 45, "MEDIANA": 45, "PEQUENA": 45},
            "MICROBRA": {"GRANDE": 30, "MEDIANA": 30, "PEQUENA": 30},
        }
    )
    fecha_minima_h1: str = "2026-01-05"


@dataclass
class ClienteConfig:
    """Configuracion completa del cliente."""

    client_name: str
    version: str
    storage: StorageConfig
    semaforos: SemaforosConfig
    forecast: ForecastConfig
    ingestion: Dict[str, Any] = field(default_factory=dict)
    columnas_override: Optional[Dict[str, Any]] = None
    log_level: str = "INFO"
