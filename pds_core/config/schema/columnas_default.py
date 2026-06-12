"""Default column definitions for canonical Excel templates."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ColumnaDef:
    """Defines a column in the Excel ingestion template."""

    nombre_canónico: str
    tipo: str
    obligatorio: bool = False
    nombre_display: str = ""
    descripción: str = ""
    validación_tipo: Optional[str] = None
    valores_desde: Optional[List[str]] = None
    tabla: str = "GESTION"
    orden_default: int = 0

    def __post_init__(self) -> None:
        if not self.nombre_display:
            self.nombre_display = self.nombre_canónico


COLUMNAS_DEFAULT_GESTION = [
    ColumnaDef("Project_ID", "text", True, tabla="GESTION", orden_default=1,
               descripción="Identificador único (HK-9001-2026-01)"),
    ColumnaDef("Nro_Sucursal", "text", True, tabla="GESTION", orden_default=2),
    ColumnaDef("Nombre", "text", True, tabla="GESTION", orden_default=3),
    ColumnaDef("PM", "text", tabla="GESTION", orden_default=4),
    ColumnaDef("Etapa", "text", tabla="GESTION", orden_default=5),
    ColumnaDef("Tipo_Intervención", "text", tabla="GESTION", orden_default=6),
    ColumnaDef("Descripción", "text", tabla="GESTION", orden_default=7),
    ColumnaDef("H1", "date", tabla="GESTION", orden_default=8),
    ColumnaDef("H6", "date", True, tabla="GESTION", orden_default=9),
    ColumnaDef("H7", "date", tabla="GESTION", orden_default=10),
    ColumnaDef("H11", "date", True, tabla="GESTION", orden_default=11),
    ColumnaDef("Observaciones", "text", tabla="GESTION", orden_default=12),
]

COLUMNAS_DEFAULT_SOURCING = [
    ColumnaDef("Project_ID", "text", True, tabla="SOURCING", orden_default=1),
    ColumnaDef("Licitación_DDO", "text", tabla="SOURCING", orden_default=2),
    ColumnaDef("Estudio_DDO", "text", tabla="SOURCING", orden_default=3),
    ColumnaDef("Fecha_Adj_DDO", "date", tabla="SOURCING", orden_default=4),
    ColumnaDef("Licitación_GC", "text", tabla="SOURCING", orden_default=5),
    ColumnaDef("GC_Adjudicado", "text", tabla="SOURCING", orden_default=6),
    ColumnaDef("Fecha_Adj_GC", "date", tabla="SOURCING", orden_default=7),
    ColumnaDef("Licitación_Transportista", "text", tabla="SOURCING", orden_default=8),
    ColumnaDef("Empresa_Transportista", "text", tabla="SOURCING", orden_default=9),
    ColumnaDef("Monto_GC", "number", tabla="SOURCING", orden_default=10),
]

COLUMNAS_DEFAULT_PERMITS = [
    ColumnaDef("Project_ID", "text", True, tabla="PERMITS", orden_default=1),
    ColumnaDef("Tipo_Permiso", "text", tabla="PERMITS", orden_default=2),
    ColumnaDef("Gestor_Municipal", "text", tabla="PERMITS", orden_default=3),
    ColumnaDef("Status_Permiso", "text", tabla="PERMITS", orden_default=4),
    ColumnaDef("H8", "date", tabla="PERMITS", orden_default=5),
    ColumnaDef("H9", "date", tabla="PERMITS", orden_default=6),
    ColumnaDef("H10", "date", tabla="PERMITS", orden_default=7),
    ColumnaDef("Observaciones", "text", tabla="PERMITS", orden_default=8),
]

COLUMNAS_DEFAULT_FINANCE = [
    ColumnaDef("Project_ID", "text", True, tabla="FINANCE", orden_default=1),
    ColumnaDef("Partida", "text", tabla="FINANCE", orden_default=2),
    ColumnaDef("AF", "text", tabla="FINANCE", orden_default=3),
    ColumnaDef("BC_Nro", "text", tabla="FINANCE", orden_default=4),
    ColumnaDef("BC_Preaprobado", "number", tabla="FINANCE", orden_default=5),
    ColumnaDef("Monto_BC_Final", "number", tabla="FINANCE", orden_default=6),
    ColumnaDef("Total_Contabilizado", "number", tabla="FINANCE", orden_default=7),
    ColumnaDef("Total_Comprometido", "number", tabla="FINANCE", orden_default=8),
]

COLUMNAS_DEFAULT = {
    "GESTION": COLUMNAS_DEFAULT_GESTION,
    "SOURCING": COLUMNAS_DEFAULT_SOURCING,
    "PERMITS": COLUMNAS_DEFAULT_PERMITS,
    "FINANCE": COLUMNAS_DEFAULT_FINANCE,
}
