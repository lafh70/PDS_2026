"""End-to-end pipeline integration tests."""

from pathlib import Path

import pytest

from pds_core.config.loader import CargadorConfiguracion
from pds_core.integration.storage import StorageManager
from pds_core.pipeline.executor import PipelineExecutor
from pds_core.utils.excel_io import read_workbook


def test_pipeline_generates_all_outputs():
    config = CargadorConfiguracion.load("hackathon")
    storage = StorageManager(config.storage)

    if not storage.entrada_canonica.exists("PDS_GESTION.xlsx"):
        pytest.skip("Run scripts/seed_demo.py first")

    result = PipelineExecutor(config=config, storage_manager=storage).run()
    assert result["exitosos"] >= 1
    assert result["errores"] == 0

    wb = read_workbook("out_/PDS_TRACKER.xlsx")
    for sheet in ("MASTER", "MASTER_PORTFOLIO", "SEMAFOROS", "HITOS", "FORECAST", "KPI_PORTFOLIO"):
        assert sheet in wb, f"Missing sheet {sheet}"

    pbi = read_workbook("out_/PDS_TRACKER_PBI.xlsx")
    assert "tblPROJECTS" in pbi
    assert pbi["tblPROJECTS"]["Project_ID"].duplicated().sum() == 0


def test_src_pipeline_via_config(test_config_path):
    """Pipeline Parte 3: src/run_pipeline.py con config unificado."""
    from pds_core.config.config_loader import load_config
    from pds_core.pipeline.config_pipeline import run_all

    if not Path("entrada_canonica/PDS_GESTION.xlsx").exists():
        pytest.skip("Run scripts/seed_demo.py first")

    config = load_config(test_config_path)
    run_all(config)

    tracker = Path(config["output"]["tracker_filename"])
    assert tracker.exists()
    wb = read_workbook(tracker)
    assert "MASTER" in wb
    assert "SEMAFOROS" in wb

