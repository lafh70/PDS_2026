"""Tests motor reglas YAML."""

import yaml
from pathlib import Path

import pandas as pd

from pds_core.rules.yaml_engine import build_semaforos_row, eval_risks, fill_forecast, worst_state
from tests.fixtures.acme_projects import ACME_PROJECTS

CFG = Path("config/clients/hackathon")


def _load(name):
    with open(CFG / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_worst_state_priority():
    assert worst_state(["GREEN", "RED", "YELLOW"]) == "RED"


def test_acme004_finance_red():
    tl = _load("traffic_lights.yaml")
    row = dict(ACME_PROJECTS[3])
    r = build_semaforos_row(row, tl)
    assert r["FINANCE_State"] == "RED"


def test_forecast_h6_h11_immutable():
    fr = _load("forecast_rules.yaml")
    row = {"Project_ID": "X", "Tipo_Intervención": "INTEGRAL", "H6": "2026-03-01", "H11": "2026-09-01"}
    out = fill_forecast(row, fr)
    assert str(out["H6"])[:10] == "2026-03-01"
    assert str(out["H11"])[:10] == "2026-09-01"
    assert out.get("H2") is not None


def test_risk_budget_from_yaml():
    rt = _load("risk_thresholds.yaml")
    row = ACME_PROJECTS[3]
    risks = eval_risks(row, rt)
    types = [r["Risk_Type"] for r in risks]
    assert "BUDGET_OVERRUN" in types


def test_transport_red_near_h11():
    from datetime import date, timedelta

    tl = _load("traffic_lights.yaml")
    h11 = (date.today() + timedelta(days=8)).isoformat()
    row = {
        "Project_ID": "ACME-T01",
        "Licitación_Transportista": "A COTIZAR",
        "H11": h11,
    }
    r = build_semaforos_row(row, tl)
    assert r["TRANSPORT_State"] == "RED"
    assert "TRANSPORT_Reason" in r


def test_transport_black_not_required():
    tl = _load("traffic_lights.yaml")
    row = {"Project_ID": "ACME-T02", "Licitación_Transportista": "NO REQUIERE", "H11": "2026-12-01"}
    r = build_semaforos_row(row, tl)
    assert r["TRANSPORT_State"] == "BLACK"
