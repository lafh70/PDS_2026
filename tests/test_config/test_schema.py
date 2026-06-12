"""Valida dataclasses de schema (ColumnaDef, ClienteConfig, etc.)."""

from pds_core.config.schema.clients_schema import (
    ClienteConfig,
    ForecastConfig,
    SemaforosConfig,
    StorageConfig,
    StorageLocation,
)
from pds_core.config.schema.columnas_default import COLUMNAS_DEFAULT, ColumnaDef


def test_columna_def_defaults():
    col = ColumnaDef(
        nombre_canónico="Project_ID",
        tipo="text",
        obligatorio=True,
        tabla="GESTION",
        orden_default=1,
    )
    assert col.nombre_display == "Project_ID"
    assert col.obligatorio is True


def test_columnas_default_structure():
    for tabla in ("GESTION", "SOURCING", "PERMITS", "FINANCE"):
        assert tabla in COLUMNAS_DEFAULT
        assert len(COLUMNAS_DEFAULT[tabla]) >= 5

    gestion_ids = [c.nombre_canónico for c in COLUMNAS_DEFAULT["GESTION"]]
    assert "Project_ID" in gestion_ids
    assert "H6" in gestion_ids


def test_storage_location_dataclass():
    loc = StorageLocation(nombre="salidas", provider="local", local_path="out_/")
    assert loc.provider == "local"
    assert loc.read_from == "local"


def test_cliente_config_minimal():
    storage = StorageConfig(
        entrada_canonica=StorageLocation(nombre="e", provider="local", local_path="e/"),
        entrada_materializada=StorageLocation(nombre="m", provider="local", local_path="m/"),
        salidas=StorageLocation(nombre="s", provider="local", local_path="s/"),
        logs=StorageLocation(nombre="l", provider="local", local_path="l/"),
    )
    cfg = ClienteConfig(
        client_name="test",
        version="1.0",
        storage=storage,
        semaforos=SemaforosConfig(),
        forecast=ForecastConfig(),
    )
    assert cfg.client_name == "test"
    assert cfg.semaforos.finance_alerta_porcentaje == 85
