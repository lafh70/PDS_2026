"""Main pipeline executor: load → merge → 21 modules → multi-format export."""

import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

from pds_core.config.loader import CargadorConfiguracion
from pds_core.config.schema.clients_schema import ClienteConfig
from pds_core.integration.storage import StorageManager
from pds_core.pipeline.exports import (
    export_csv,
    export_html,
    export_pbi,
    run_backup,
    run_data_quality,
    run_verification,
)
from pds_core.pipeline.state import PipelineState
from pds_core.pipeline.steps import build_all_steps
from pds_core.rules.manager import RulesManager
from pds_core.utils.excel_io import write_sheet

CANONICAL_FILES = {
    "GESTION": "PDS_GESTION.xlsx",
    "SOURCING": "PDS_SOURCING.xlsx",
    "PERMITS": "PDS_PERMITS.xlsx",
    "FINANCE": "PDS_FINANCE.xlsx",
}


class PipelineExecutor:
    """
    Orquestador del pipeline ETL completo (modulos M01-M21).

    Flujo:
    1. Carga y merge de fuentes canonicas (GESTION, SOURCING, PERMITS, FINANCE)
    2. Ejecuta pasos de procesamiento (portfolio, semaforos, forecast, riesgos, KPI...)
    3. Exporta Tracker multi-formato (xlsx, CSV, HTML, PBI) + backup + verificacion

    Uso:
        executor = PipelineExecutor(client_name="hackathon")
        resultado = executor.run()

    Args:
        client_name: Identificador de cliente o ClienteConfig ya cargado.
        storage_manager: StorageManager opcional (inyeccion para tests).
        rules_manager: RulesManager opcional (reglas de negocio por cliente).
        config: ClienteConfig explicito (alternativa a client_name).

    Returns:
        dict con metricas: proyectos, pasos, duracion, rutas de salida.
    """

    def __init__(
        self,
        client_name: str | ClienteConfig | None = None,
        storage_manager: StorageManager | None = None,
        rules_manager: RulesManager | None = None,
        config: ClienteConfig | None = None,
    ):
        if config is not None:
            self.config = config
        elif isinstance(client_name, ClienteConfig):
            self.config = client_name
        else:
            self.config = CargadorConfiguracion.load(client_name or "hackathon")

        self.client_name = self.config.client_name
        self.storage = storage_manager or StorageManager(self.config.storage)
        self.rules = rules_manager or RulesManager(self.config, self._load_yaml_bundle(self.client_name))

    @staticmethod
    def _load_yaml_bundle(client_name: str) -> dict:
        try:
            from pds_core.config.config_loader import load_config_for_client
            return load_config_for_client(client_name)
        except (FileNotFoundError, ValueError):
            return {}

    def run(self, dry_run: bool = False) -> dict[str, Any]:
        inicio = datetime.now()
        resultado: dict[str, Any] = {
            "client": self.client_name,
            "total_proyectos": 0,
            "exitosos": 0,
            "errores": 0,
            "duracion_segundos": 0.0,
            "timestamp": datetime.now().isoformat(),
            "pasos": [],
            "salidas": [],
        }

        try:
            print(f"Cargando entrada_canonica/ para {self.client_name}...")
            master = self._load_and_merge()
            state = PipelineState(master=master)
            resultado["total_proyectos"] = len(master)

            steps = build_all_steps(self.rules)
            print(f"Ejecutando pipeline ({len(steps)} modulos)...")
            for step in steps:
                state = step.execute(state)
                resultado["pasos"].append(
                    {"nombre": step.nombre, "duracion_segundos": round(step.duracion, 3)}
                )

            resultado["exitosos"] = len(state.portfolio)

            if not dry_run:
                print("Guardando salidas...")
                out_dir = self._output_dir()
                paths = self._save_all_outputs(state, out_dir)
                resultado["salidas"] = [str(p) for p in paths]

        except Exception as exc:
            print(f"Error pipeline: {exc}")
            resultado["errores"] = 1
            resultado["error_detalle"] = str(exc)
            raise

        finally:
            resultado["duracion_segundos"] = (datetime.now() - inicio).total_seconds()

        return resultado

    def _output_dir(self) -> Path:
        loc = self.config.storage.salidas
        return Path(loc.local_path or "out_")

    def _read_sheet(self, filename: str) -> pd.DataFrame:
        raw = self.storage.entrada_canonica.read(filename)
        return pd.read_excel(BytesIO(raw), sheet_name="DATOS", engine="openpyxl")

    def _load_and_merge(self) -> pd.DataFrame:
        df = self._read_sheet(CANONICAL_FILES["GESTION"]).copy()
        for label, filename in {
            "SOURCING": CANONICAL_FILES["SOURCING"],
            "PERMITS": CANONICAL_FILES["PERMITS"],
            "FINANCE": CANONICAL_FILES["FINANCE"],
        }.items():
            if not self.storage.entrada_canonica.exists(filename):
                print(f"  Aviso: {filename} no encontrado; se omite {label}")
                continue
            df_src = self._read_sheet(filename)
            overlap = set(df.columns) & set(df_src.columns) - {"Project_ID"}
            df_src = df_src.drop(columns=list(overlap), errors="ignore")
            df = df.merge(df_src, on="Project_ID", how="left")
        return df

    def _save_all_outputs(self, state: PipelineState, out_dir: Path) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        tracker_path = out_dir / "PDS_TRACKER.xlsx"

        if tracker_path.exists():
            tracker_path.unlink()

        sheet_order = [
            "MASTER",
            "MASTER_PORTFOLIO_ALL",
            "MASTER_PORTFOLIO",
            "SEMAFOROS",
            "HITOS",
            "FORECAST",
            "FORECAST_VALIDATION",
            "RIESGOS",
            "ALERTAS_TODAS",
            "ALERTAS_CRITICAS",
            "ALERTAS_ALTAS",
            "KPI_PORTFOLIO",
            "SCORECARD_COMITE",
            "DASHBOARD",
            "DATOS_GRAFICOS",
            "GANTT_HITOS",
            "GANTT_FORECAST",
            "TARJETA_PROYECTO",
        ]

        paths: list[Path] = [tracker_path]
        write_sheet(tracker_path, "MASTER", state.sheets.get("MASTER", state.master))
        for name in sheet_order:
            if name in state.sheets and not state.sheets[name].empty:
                write_sheet(tracker_path, name, state.sheets[name])

        write_sheet(tracker_path, "CONSOLIDADO", state.master)

        paths.append(export_pbi(state, out_dir))
        paths.append(export_csv(state, out_dir))
        paths.append(export_html(state, out_dir, self.client_name))

        dq = run_data_quality(state, out_dir)
        paths.append(out_dir / "DATA_QUALITY_REPORT.json")

        backup = run_backup(out_dir)
        if backup:
            paths.append(backup)

        run_verification(tracker_path, out_dir / "PDS_TRACKER_PBI.xlsx", out_dir / "DATA_QUALITY_REPORT.json")

        reporte = {
            "timestamp": datetime.now().isoformat(),
            "cliente": self.client_name,
            "proyectos": len(state.portfolio),
            "estado": "completado",
            "quality_score": dq.get("quality_score"),
            "hojas": list(state.sheets.keys()),
        }
        log_name = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.storage.logs.write(log_name, json.dumps(reporte, indent=2).encode("utf-8"))

        print("VERIFICATION PASSED - Pipeline complete")
        return paths
