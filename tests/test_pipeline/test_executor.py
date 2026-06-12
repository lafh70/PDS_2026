from unittest.mock import MagicMock

import pandas as pd
import pytest

from pds_core.config.schema.clients_schema import (
    ClienteConfig,
    ForecastConfig,
    SemaforosConfig,
    StorageConfig,
    StorageLocation,
)
from pds_core.pipeline.executor import PipelineExecutor
from pds_core.pipeline.steps import Step01MasterAppend as Step1MasterAppend


@pytest.fixture
def mock_storage():
    from datetime import datetime
    from io import BytesIO

    mock = MagicMock()
    df = pd.DataFrame(
        {
            "Project_ID": ["HK-9001-2026-01"],
            "H6": [datetime(2026, 2, 1)],
            "Tipo_Intervención": ["INTEGRAL"],
            "Licitación_DDO": ["ADJUDICADO"],
        }
    )
    excel_bytes = BytesIO()
    with pd.ExcelWriter(excel_bytes, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="DATOS", index=False)
    data = excel_bytes.getvalue()
    mock.entrada_canonica.read.return_value = data
    mock.entrada_canonica.exists.return_value = True
    return mock


@pytest.fixture
def mock_config():
    storage = StorageConfig(
        entrada_canonica=StorageLocation(nombre="entrada", provider="local", local_path="entrada_canonica/"),
        entrada_materializada=StorageLocation(nombre="entrada_mat", provider="local", local_path="entrada/"),
        salidas=StorageLocation(nombre="salidas", provider="local", local_path="out_/"),
        logs=StorageLocation(nombre="logs", provider="local", local_path="logs/"),
    )
    return ClienteConfig(
        client_name="test",
        version="1.0",
        storage=storage,
        semaforos=SemaforosConfig(ddo_verde_keywords=["ADJUDICADO"]),
        forecast=ForecastConfig(duraciones_obras={"INTEGRAL": 120}),
    )


def test_pipeline_executor_init(mock_storage, mock_config):
    executor = PipelineExecutor(config=mock_config, storage_manager=mock_storage)
    assert executor.client_name == "test"


def test_pipeline_step_execute():
    df = pd.DataFrame({"Project_ID": ["HK-9001-2026-01"], "col1": [1]})
    step = Step1MasterAppend()
    from pds_core.pipeline.state import PipelineState

    state = step.execute(PipelineState(master=df))
    assert len(state.master) == 1
    assert step.duracion >= 0

