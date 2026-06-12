import tempfile
from datetime import datetime

import pandas as pd
import pytest

from pds_core.ingestion.base import EstadoIngesta
from pds_core.ingestion.sources.excel_ingesta import IngestadorExcelIngesta


@pytest.fixture
def sample_excel_path():
    df = pd.DataFrame(
        {
            "Project_ID": ["HK-9001-2026-01"],
            "Nro_Sucursal": ["9001"],
            "Nombre": ["Test Project"],
            "PM": ["Test PM"],
            "Etapa": ["ETAPA 1"],
            "Tipo_Intervención": ["INTEGRAL"],
            "H1": ["2026-01-15"],
            "H6": ["2026-02-01"],
            "H11": ["2026-08-01"],
        }
    )
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        with pd.ExcelWriter(tmp.name, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="GESTION", index=False)
        yield tmp.name


def test_ingestador_extrae_excel(sample_excel_path):
    ingestador = IngestadorExcelIngesta(tabla_canonica="GESTION")
    df = ingestador._extraer({"ruta": sample_excel_path, "sheet": "GESTION"})
    assert len(df) == 1
    assert "Project_ID" in df.columns


def test_ingestador_valida_schema(sample_excel_path):
    ingestador = IngestadorExcelIngesta(tabla_canonica="GESTION")
    df = ingestador._extraer({"ruta": sample_excel_path, "sheet": "GESTION", "client_name": "hackathon"})
    valido, errores = ingestador._validar(df)
    assert valido is True
    assert len(errores) == 0


def test_resultado_ingesta_exitoso(sample_excel_path):
    ingestador = IngestadorExcelIngesta(tabla_canonica="GESTION")
    resultado = ingestador.ingestar(
        {"ruta": sample_excel_path, "sheet": "GESTION", "client_name": "hackathon"}
    )
    assert resultado.estado == EstadoIngesta.COMPLETADO
    assert resultado.filas_validas > 0
