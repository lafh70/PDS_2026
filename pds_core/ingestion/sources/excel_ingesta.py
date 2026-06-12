"""Excel template ingestor for canonical PDS sources."""

import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd

from pds_core.config.loader_columnas_simple import CargadorColumnasSimple
from pds_core.ingestion.base import IngestadorBase

PROJECT_ID_PATTERN = re.compile(r"^[A-Z]{2}-\d{4}-\d{4}-\d{2}$")

COLUMNAS_FECHA = {
    "GESTION": ["H1", "H6", "H7", "H11"],
    "SOURCING": ["Fecha_Adj_DDO", "Fecha_Adj_GC"],
    "PERMITS": ["H8", "H9", "H10"],
    "FINANCE": [],
}

COLUMNAS_MONTO = {
    "GESTION": [],
    "SOURCING": ["Monto_GC"],
    "PERMITS": [],
    "FINANCE": ["BC_Preaprobado", "Monto_BC_Final", "Total_Contabilizado", "Total_Comprometido"],
}


class IngestadorExcelIngesta(IngestadorBase):
    """Ingests data from the multi-sheet Excel ingestion template."""

    def __init__(self, tabla_canonica: str = "GESTION", logger=None):
        super().__init__("excel", tabla_canonica, logger)
        self._columnas_schema: List[str] = []

    def _columnas_requeridas(self, client_name: str = "hackathon") -> List[str]:
        columnas = CargadorColumnasSimple.load(client_name).get(self.tabla_canonica, [])
        return [col.nombre_canónico for col in columnas if col.obligatorio]

    def _resolver_columna(self, df: pd.DataFrame, nombre: str) -> bool:
        if nombre in df.columns:
            return True
        lower_map = {str(c).lower(): c for c in df.columns}
        return nombre.lower() in lower_map

    def _extraer(self, config: Dict[str, Any]) -> pd.DataFrame:
        self._client_name = config.get("client_name", "hackathon")
        ruta = config.get("ruta")
        sheet = config.get("sheet", self.tabla_canonica)
        bytes_data = config.get("bytes")

        if bytes_data is not None:
            df = pd.read_excel(BytesIO(bytes_data), sheet_name=sheet, engine="openpyxl")
        elif isinstance(ruta, (str, Path)):
            ruta_str = str(ruta)
            if ruta_str.startswith("http"):
                df = pd.read_excel(ruta_str, sheet_name=sheet, engine="openpyxl")
            else:
                df = pd.read_excel(ruta_str, sheet_name=sheet, engine="openpyxl")
        else:
            raise ValueError("config debe incluir 'ruta' o 'bytes'")

        df.columns = df.columns.astype(str).str.strip().str.lstrip("*").str.strip()
        self._log(f"Extraídas {len(df)} filas desde {sheet}")
        return df

    def _validar(self, df: pd.DataFrame) -> Tuple[bool, List[str]]:
        client_name = getattr(self, "_client_name", "hackathon")
        requeridas = self._columnas_requeridas(client_name)
        faltantes = [col for col in requeridas if not self._resolver_columna(df, col)]

        if faltantes:
            return False, [f"Columnas obligatorias faltantes: {faltantes}"]

        return True, []

    def _normalizar(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = df.columns.astype(str).str.strip().str.lstrip("*").str.strip()

        if "Project_ID" in df.columns:
            pid = df["Project_ID"].astype(str).str.strip()
            df = df[pid.str.match(r"^[A-Z]{2}-\d{4}-\d{4}-\d{2}$", na=False)].copy()

        for col in COLUMNAS_FECHA.get(self.tabla_canonica, []):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        for col in COLUMNAS_MONTO.get(self.tabla_canonica, []):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "Project_ID" in df.columns:
            df["Project_ID"] = (
                df["Project_ID"]
                .astype(str)
                .str.strip()
                .str.upper()
                .replace({"NAN": pd.NA, "NONE": pd.NA})
            )

        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].apply(
                lambda v: v.strip() if isinstance(v, str) else v
            )

        self._log(f"Normalizadas {len(df)} filas")
        return df

    def _validar_fila(self, row: pd.Series, idx: int) -> Tuple[bool, str]:
        project_id = str(row.get("Project_ID", "")).strip()
        if project_id and not PROJECT_ID_PATTERN.match(project_id):
            return False, f"Fila {idx}: Project_ID formato inválido: {project_id}"

        fechas_gestion = [("H6", "H11"), ("H1", "H6")]
        for inicio, fin in fechas_gestion:
            if inicio in row.index and fin in row.index:
                d_ini, d_fin = row.get(inicio), row.get(fin)
                if pd.notna(d_ini) and pd.notna(d_fin) and d_ini > d_fin:
                    return False, (
                        f"Fila {idx}: {inicio} ({d_ini}) posterior a {fin} ({d_fin})"
                    )

        return True, ""
