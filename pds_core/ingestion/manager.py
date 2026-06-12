"""Orchestrates multi-source ingestion into canonical storage."""

import json
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, Union

import pandas as pd

from pds_core.ingestion.base import EstadoIngesta, ResultadoIngesta
from pds_core.ingestion.normalizers.column_mapper import ColumnMapper
from pds_core.ingestion.sources.excel_ingesta import IngestadorExcelIngesta


class OrquestadorIngesta:
    """
    Coordina ingesta multi-fuente hacia almacenamiento canonico.

    Responsabilidades:
    - Leer Excel por tabla (GESTION, SOURCING, PERMITS, FINANCE)
    - Validar schema y normalizar columnas (display → canonico)
    - Persistir en entrada_canonica/PDS_{TABLA}.xlsx
    - Generar reporte JSON en logs/

    Uso:
        config = CargadorConfiguracion.load("hackathon")
        storage = StorageManager(config.storage)
        orquestador = OrquestadorIngesta(config, storage)
        orquestador.ingestar_todo({"GESTION": {"tipo": "excel", "ruta": "...", "sheet": "GESTION"}})

    Args:
        cliente_config: ClienteConfig con rutas y reglas del cliente.
        storage_manager: StorageManager para escribir salida canonica.
        logger: Logger opcional.
    """

    TABLAS = ("GESTION", "SOURCING", "PERMITS", "FINANCE")

    def __init__(self, cliente_config, storage_manager, logger=None):
        self.config = cliente_config
        self.storage = storage_manager
        self.logger = logger

    def ingestar_todo(
        self, config_ingesta: Union[Dict[str, Dict[str, Any]], Any]
    ) -> Dict[str, ResultadoIngesta]:
        """
        Ingest all canonical tables.

        Args:
            config_ingesta: Per-table config, e.g.
                {"GESTION": {"tipo": "excel", "ruta": "...", "sheet": "GESTION"}, ...}
                Or a Path/str to a multi-sheet Excel workbook.

        Returns:
            Dict mapping table name to ResultadoIngesta.
        """
        if not isinstance(config_ingesta, dict):
            config_ingesta = self._config_desde_workbook(config_ingesta)

        resultados: Dict[str, ResultadoIngesta] = {}

        for tabla in self.TABLAS:
            config_fuente = config_ingesta.get(tabla)
            if not config_fuente:
                continue

            print(f"Ingesting {tabla}...")
            config_fuente = dict(config_fuente)
            config_fuente.setdefault("client_name", self.config.client_name)
            ingestador = IngestadorExcelIngesta(tabla_canonica=tabla, logger=self.logger)
            resultado = ingestador.ingestar(config_fuente)
            resultados[tabla] = resultado

            if resultado.estado == EstadoIngesta.COMPLETADO and resultado.dataframe is not None:
                df = ColumnMapper.map_display_to_canonical(
                    resultado.dataframe,
                    self.config.client_name,
                    tabla,
                )
                self._guardar_canonica(tabla, df)
                print(f"[OK] {tabla} guardado en entrada_canonica")
            else:
                print(f"[FAIL] {tabla} fallo: {resultado.errores}")

        self._generar_reporte(resultados)
        return resultados

    def _config_desde_workbook(self, ruta) -> Dict[str, Dict[str, Any]]:
        """Build per-table config from a single multi-sheet workbook path."""
        return {
            tabla: {"tipo": "excel", "ruta": str(ruta), "sheet": tabla}
            for tabla in self.TABLAS
        }

    def _guardar_canonica(self, tabla: str, df: pd.DataFrame) -> None:
        """Persist validated DataFrame to entrada_canonica as PDS_{TABLA}.xlsx."""
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="DATOS", index=False)

        archivo = f"PDS_{tabla}.xlsx"
        self.storage.entrada_canonica.write(archivo, output.getvalue())

    def _generar_reporte(self, resultados: Dict[str, ResultadoIngesta]) -> None:
        """Write JSON ingestion report to logs storage."""
        reporte = {
            "timestamp": datetime.now().isoformat(),
            "cliente": self.config.client_name,
            "resultados": {
                tabla: {
                    "estado": resultado.estado.value,
                    "filas_validas": resultado.filas_validas,
                    "filas_rechazadas": resultado.filas_rechazadas,
                    "duracion_segundos": resultado.duracion_segundos,
                    "errores": resultado.errores[:5],
                    "warnings": resultado.warnings[:10],
                }
                for tabla, resultado in resultados.items()
            },
        }

        nombre_archivo = f"ingesta_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.storage.logs.write(nombre_archivo, json.dumps(reporte, indent=2).encode("utf-8"))
