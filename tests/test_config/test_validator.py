"""Valida ValidadorConfiguracion."""

import pytest

from pds_core.config.loader import CargadorConfiguracion
from pds_core.config.schema.clients_schema import (
    ClienteConfig,
    ForecastConfig,
    SemaforosConfig,
    StorageConfig,
    StorageLocation,
)
from pds_core.config.validator import ValidadorConfiguracion


def _base_config(**overrides) -> ClienteConfig:
    storage = StorageConfig(
        entrada_canonica=StorageLocation(nombre="e", provider="local", local_path="entrada_canonica/"),
        entrada_materializada=StorageLocation(nombre="m", provider="local", local_path="entrada/"),
        salidas=StorageLocation(nombre="s", provider="local", local_path="out_/"),
        logs=StorageLocation(nombre="l", provider="local", local_path="logs/"),
    )
    cfg = ClienteConfig(
        client_name="test",
        version="1.0",
        storage=storage,
        semaforos=SemaforosConfig(),
        forecast=ForecastConfig(),
    )
    for key, val in overrides.items():
        setattr(cfg, key, val)
    return cfg


def test_validador_acepta_hackathon():
    config = CargadorConfiguracion.load("hackathon")
    assert ValidadorConfiguracion.validar(config) is True


def test_validador_rechaza_duracion_invalida():
    config = _base_config()
    config.forecast.duraciones_obras["INTEGRAL"] = 0
    with pytest.raises(ValueError, match="Duracion"):
        ValidadorConfiguracion.validar(config)


def test_validador_rechaza_finance_pct_invalido():
    config = _base_config()
    config.semaforos.finance_alerta_porcentaje = 150
    with pytest.raises(ValueError, match="finance_alerta_porcentaje"):
        ValidadorConfiguracion.validar(config)


def test_validador_rechaza_regex_project_id():
    config = _base_config()
    config.ingestion = {"project_id_format": "[invalid"}
    with pytest.raises(ValueError, match="regex"):
        ValidadorConfiguracion.validar(config)
