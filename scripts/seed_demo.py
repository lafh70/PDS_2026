#!/usr/bin/env python
"""Genera datos demo y ejecuta las 3 fases del pipeline."""

import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _demo_rows() -> dict:
    gestion = pd.DataFrame(
        [
            {
                "Project_ID": "HK-9001-2026-01",
                "Nro_Sucursal": "9001",
                "Nombre": "Renovacion Sucursal Centro",
                "PM": "Juan Perez",
                "Etapa": "ETAPA 2",
                "Tipo_Intervención": "INTEGRAL",
                "Descripción": "Obra integral sucursal",
                "H1": date(2026, 1, 15),
                "H6": date(2026, 3, 1),
                "H7": date(2026, 7, 1),
                "H11": date(2026, 8, 1),
                "Observaciones": "Proyecto demo 1",
            },
            {
                "Project_ID": "HK-9002-2026-01",
                "Nro_Sucursal": "9002",
                "Nombre": "ATM Zona Norte",
                "PM": "Maria Lopez",
                "Etapa": "ETAPA 1",
                "Tipo_Intervención": "MEDIA",
                "Descripción": "Instalacion ATM",
                "H1": date(2026, 2, 1),
                "H6": date(2026, 4, 15),
                "H7": date(2026, 7, 15),
                "H11": date(2026, 8, 15),
                "Observaciones": "Proyecto demo 2",
            },
        ]
    )
    sourcing = pd.DataFrame(
        [
            {
                "Project_ID": "HK-9001-2026-01",
                "Licitación_DDO": "ADJUDICADO",
                "Estudio_DDO": "Completo",
                "Fecha_Adj_DDO": date(2026, 1, 20),
                "Licitación_GC": "EN PROCESO",
                "GC_Adjudicado": "",
                "Fecha_Adj_GC": None,
                "Monto_GC": 1500000,
            },
            {
                "Project_ID": "HK-9002-2026-01",
                "Licitación_DDO": "EN PROCESO",
                "Estudio_DDO": "Pendiente",
                "Fecha_Adj_DDO": None,
                "Licitación_GC": "PENDIENTE",
                "GC_Adjudicado": "",
                "Fecha_Adj_GC": None,
                "Monto_GC": 800000,
            },
        ]
    )
    permits = pd.DataFrame(
        [
            {
                "Project_ID": "HK-9001-2026-01",
                "Tipo_Permiso": "PERMISO_OBRA",
                "Gestor_Municipal": "Gestor A",
                "Status_Permiso": "Tramitando",
                "H8": date(2026, 2, 10),
                "H9": None,
                "H10": None,
                "Observaciones": "",
            },
            {
                "Project_ID": "HK-9002-2026-01",
                "Tipo_Permiso": "AVISO",
                "Gestor_Municipal": "Gestor B",
                "Status_Permiso": "Obtenido",
                "H8": date(2026, 3, 1),
                "H9": date(2026, 4, 1),
                "H10": date(2026, 10, 1),
                "Observaciones": "",
            },
        ]
    )
    finance = pd.DataFrame(
        [
            {
                "Project_ID": "HK-9001-2026-01",
                "Partida": "CAPEX",
                "AF": "AF-001",
                "BC_Nro": "BC-100",
                "BC_Preaprobado": 2000000,
                "Monto_BC_Final": 1800000,
                "Total_Contabilizado": 900000,
                "Total_Comprometido": 1200000,
            },
            {
                "Project_ID": "HK-9002-2026-01",
                "Partida": "CAPEX",
                "AF": "AF-002",
                "BC_Nro": "BC-101",
                "BC_Preaprobado": 1000000,
                "Monto_BC_Final": 950000,
                "Total_Contabilizado": 200000,
                "Total_Comprometido": 400000,
            },
        ]
    )
    return {"GESTION": gestion, "SOURCING": sourcing, "PERMITS": permits, "FINANCE": finance}


def main() -> None:
    from pds_core.config.loader import CargadorConfiguracion
    from pds_core.config.loader_columnas_simple import CargadorColumnasSimple
    from pds_core.ingestion.manager import OrquestadorIngesta
    from pds_core.integration.storage import StorageManager
    from pds_core.pipeline.executor import PipelineExecutor
    from pds_core.utils.excel_generator_simple import GeneradorExcelIngestaSimple

    client = "hackathon"
    demo_path = ROOT / "entrada_canonica" / "PDS_INGESTA_DEMO.xlsx"

    print("FASE 1: Generando plantilla...")
    columnas = CargadorColumnasSimple.load(client)
    GeneradorExcelIngestaSimple.generate(columnas, demo_path)

    print("FASE 1b: Rellenando datos demo...")
    with pd.ExcelWriter(demo_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        for sheet, df in _demo_rows().items():
            df.to_excel(writer, sheet_name=sheet, index=False)

    print("FASE 2: Ingestando...")
    config = CargadorConfiguracion.load(client)
    storage = StorageManager(config.storage)
    OrquestadorIngesta(config, storage).ingestar_todo(demo_path)

    print("FASE 3: Pipeline...")
    result = PipelineExecutor(client_name=client, storage_manager=storage, config=config).run()

    print(f"\n[OK] Demo completo: {result['exitosos']} proyectos -> out_/PDS_TRACKER.xlsx")


if __name__ == "__main__":
    main()
