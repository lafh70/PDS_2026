"""Test unified config loader (PROMPT 28)."""

from pathlib import Path

from pds_core.config.config_loader import load_config


def test_load_hackathon_unified_config():
    path = Path("config/clients/hackathon/client.yaml")
    config = load_config(str(path))
    assert config["client"]["code"] == "HACKATHON"
    assert "sources" in config
    assert "traffic_lights" in config
    assert "mapeo_columnas" in config
    assert isinstance(config["procurement_types"], list)
