"""Valida inyeccion dinamica de reglas (SemaforosRules, ForecastRules)."""

from datetime import datetime, timedelta

import pytest

from pds_core.config.schema.clients_schema import (
    ClienteConfig,
    ForecastConfig,
    SemaforosConfig,
    StorageConfig,
    StorageLocation,
)
from pds_core.rules.manager import ForecastRules, RulesManager, SemaforosRules


@pytest.fixture
def client_config():
    storage = StorageConfig(
        entrada_canonica=StorageLocation(nombre="e", provider="local", local_path="e/"),
        entrada_materializada=StorageLocation(nombre="m", provider="local", local_path="m/"),
        salidas=StorageLocation(nombre="s", provider="local", local_path="s/"),
        logs=StorageLocation(nombre="l", provider="local", local_path="l/"),
    )
    return ClienteConfig(
        client_name="test",
        version="1.0",
        storage=storage,
        semaforos=SemaforosConfig(
            ddo_negro_keywords=["CANCELADO"],
            ddo_verde_keywords=["ADJUDICADO"],
            ddo_amarillo_keywords=["EN PROCESO"],
        ),
        forecast=ForecastConfig(duraciones_obras={"INTEGRAL": 120, "MEDIA": 90}),
    )


def test_semaforos_ddo_estados(client_config):
    rules = SemaforosRules(client_config.semaforos)
    assert rules.calcular_ddo("ADJUDICADO") == "GREEN"
    assert rules.calcular_ddo("CANCELADO") == "BLACK"
    assert rules.calcular_ddo("EN PROCESO") == "YELLOW"
    assert rules.calcular_ddo("") == "WHITE"


def test_semaforos_finance_umbrales(client_config):
    rules = SemaforosRules(client_config.semaforos)
    assert rules.calcular_finance(50) == "GREEN"
    assert rules.calcular_finance(80) == "YELLOW"
    assert rules.calcular_finance(90) == "RED"


def test_forecast_h7_por_tipo(client_config):
    rules = ForecastRules(client_config.forecast)
    h6 = datetime(2026, 3, 1)
    assert rules.calcular_h7(h6, "INTEGRAL") == h6.date() + timedelta(days=120)
    assert rules.calcular_h7(h6, "MEDIA") == h6.date() + timedelta(days=90)


def test_rules_manager_inyecta_reglas(client_config):
    mgr = RulesManager(client_config)
    assert mgr.get_semaforos_rules().calcular_gc("ADJUDICADO") == "GREEN"
    assert mgr.get_forecast_rules().calcular_h7(datetime(2026, 1, 1), "INTEGRAL") is not None
