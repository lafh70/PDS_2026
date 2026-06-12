"""Base classes and types for the ingestion pipeline."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import time


class EstadoIngesta(Enum):
    """Lifecycle states for an ingestion run."""

    EXTRAYENDO = "extrayendo"
    VALIDANDO = "validando"
    NORMALIZANDO = "normalizando"
    COMPLETADO = "completado"
    ERROR = "error"


@dataclass
class ResultadoIngesta:
    """Outcome of a single source ingestion."""

    tipo_fuente: str
    tabla_canonica: str
    estado: EstadoIngesta
    filas_ingestion: int = 0
    filas_validas: int = 0
    filas_rechazadas: int = 0
    errores: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    dataframe: Optional[pd.DataFrame] = None
    timestamp: datetime = field(default_factory=datetime.now)
    duracion_segundos: float = 0.0


class IngestadorBase(ABC):
    """Abstract base for all data ingestors."""

    def __init__(self, tipo_fuente: str, tabla_canonica: str, logger=None):
        self.tipo_fuente = tipo_fuente
        self.tabla_canonica = tabla_canonica
        self.logger = logger

    def ingestar(self, configuracion: Dict[str, Any]) -> ResultadoIngesta:
        """Run the full ingestion pipeline: extract → validate → normalize → row checks."""
        inicio = time.time()
        resultado = ResultadoIngesta(
            tipo_fuente=self.tipo_fuente,
            tabla_canonica=self.tabla_canonica,
            estado=EstadoIngesta.EXTRAYENDO,
        )

        try:
            self._log(f"Extrayendo {self.tabla_canonica}")
            df = self._extraer(configuracion)
            resultado.filas_ingestion = len(df)

            resultado.estado = EstadoIngesta.VALIDANDO
            self._log(f"Validando schema {self.tabla_canonica}")
            valido, errores = self._validar(df)
            if not valido:
                resultado.estado = EstadoIngesta.ERROR
                resultado.errores = errores
                return resultado

            resultado.estado = EstadoIngesta.NORMALIZANDO
            self._log(f"Normalizando {self.tabla_canonica}")
            df = self._normalizar(df)

            self._log("Validando integridad de datos")
            df_valido, filas_validas, filas_rechazadas, warnings = self._validar_datos(df)
            resultado.filas_validas = filas_validas
            resultado.filas_rechazadas = filas_rechazadas
            resultado.warnings = warnings
            resultado.estado = EstadoIngesta.COMPLETADO
            resultado.dataframe = df_valido

        except Exception as exc:
            resultado.estado = EstadoIngesta.ERROR
            resultado.errores = [str(exc)]
            self._log(f"Error: {exc}")

        finally:
            resultado.duracion_segundos = time.time() - inicio

        return resultado

    def _validar_datos(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, int, int, List[str]]:
        """Validate row-level integrity and return only valid rows."""
        valid_indices: List[Any] = []
        filas_rechazadas = 0
        warnings: List[str] = []

        for idx, row in df.iterrows():
            project_id = row.get("Project_ID")
            if pd.isna(project_id) or str(project_id).strip() == "":
                filas_rechazadas += 1
                warnings.append(f"Fila {idx}: Project_ID vacío")
                continue

            is_valid, error = self._validar_fila(row, idx)
            if is_valid:
                valid_indices.append(idx)
            else:
                filas_rechazadas += 1
                warnings.append(error)

        df_valido = df.loc[valid_indices].copy() if valid_indices else df.iloc[0:0].copy()
        return df_valido, len(valid_indices), filas_rechazadas, warnings

    def _log(self, msg: str) -> None:
        if self.logger:
            self.logger.log("info", msg)
        else:
            print(msg)

    @abstractmethod
    def _extraer(self, configuracion: Dict[str, Any]) -> pd.DataFrame:
        """Extract raw data from the source."""

    @abstractmethod
    def _validar(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate schema / required columns."""

    @abstractmethod
    def _normalizar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize types and values."""

    @abstractmethod
    def _validar_fila(self, row: pd.Series, idx: int) -> Tuple[bool, str]:
        """Row-level validation."""
