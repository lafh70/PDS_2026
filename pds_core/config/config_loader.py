"""Carga unificada de configuracion del cliente (PROMPT 28)."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any

import yaml

_YAML_LIST_KEYS = (
    "procurement_types",
    "intervention_types",
)


def load_config(config_path: str) -> dict[str, Any]:
    """
    Carga client.yaml y todos los archivos config/ del cliente.

    Args:
        config_path: Ruta a client.yaml del cliente

    Returns:
        dict unificado con todas las configuraciones

    Raises:
        FileNotFoundError: Si config no existe
        ValueError: Si config invalido
    """
    path = Path(config_path)
    base = path.parent

    if not path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with open(path, encoding="utf-8") as f:
        config: dict[str, Any] = yaml.safe_load(f) or {}

    config["sources"] = _extract_section(_load_yaml(base / "sources.yaml"), "sources")
    config["portfolio_filters"] = _load_yaml(base / "portfolio_filters.yaml")
    config["procurement_types"] = _extract_section(
        _load_yaml(base / "procurement_types.yaml"), "procurement_types"
    )
    config["intervention_types"] = _extract_section(
        _load_yaml(base / "intervention_types.yaml"), "intervention_types"
    )
    config["traffic_lights"] = _load_yaml(base / "traffic_lights.yaml")
    config["forecast_rules"] = _load_yaml(base / "forecast_rules.yaml")
    config["risk_thresholds"] = _load_yaml(base / "risk_thresholds.yaml")
    config["mapeo_columnas"] = _load_csv(base / "mapeo_columnas.csv")
    config["pm_aliases"] = _load_csv(base / "pm_aliases.csv")

    _validate_config(config)
    return config


def load_config_for_client(client_name: str) -> dict[str, Any]:
    """Resuelve config/clients/{cliente}/client.yaml o fallback legacy."""
    root = Path(__file__).parent.parent.parent / "config" / "clients"
    folder_path = root / client_name / "client.yaml"
    if folder_path.exists():
        return load_config(str(folder_path))
    legacy_path = root / f"{client_name}.yaml"
    if legacy_path.exists():
        return _legacy_to_unified(legacy_path, client_name)
    raise FileNotFoundError(f"No config for client: {client_name}")


def _legacy_to_unified(legacy_path: Path, client_name: str) -> dict[str, Any]:
    """Adapta hackathon.yaml plano al dict unificado Parte 3."""
    with open(legacy_path, encoding="utf-8") as f:
        legacy = yaml.safe_load(f) or {}

    storage = legacy.get("storage", {})
    salidas = storage.get("salidas", {}).get("local_path", "out_/")
    return {
        "client": {
            "name": client_name.title(),
            "code": client_name.upper(),
            "version": legacy.get("version", "1.0"),
            "year": 2026,
        },
        "output": {
            "tracker_filename": f"{salidas.rstrip('/')}/PDS_TRACKER.xlsx",
            "pbi_filename": f"{salidas.rstrip('/')}/PDS_TRACKER_PBI.xlsx",
            "html_filename": f"{salidas.rstrip('/')}/PDS_TRACKER.html",
            "csv_filename": f"{salidas.rstrip('/')}/PDS_TRACKER.csv",
            "log_filename": "pipeline.log",
        },
        "storage": storage,
        "semaforos": legacy.get("semaforos", {}),
        "forecast": legacy.get("forecast", {}),
        "ingestion": legacy.get("ingestion", {}),
        "sources": {
            "portfolio_plan": {
                "enabled": True,
                "file": "entrada_canonica/PDS_GESTION.xlsx",
                "sheet": "DATOS",
                "header_row": 1,
            },
            "procurement": {
                "enabled": True,
                "file": "entrada_canonica/PDS_SOURCING.xlsx",
                "sheets_by_type": True,
            },
            "permits": {
                "enabled": True,
                "file": "entrada_canonica/PDS_PERMITS.xlsx",
                "sheet": "DATOS",
                "header_row": 1,
            },
            "finance": {
                "enabled": True,
                "file": "entrada_canonica/PDS_FINANCE.xlsx",
                "sheet": "DATOS",
                "header_row": 1,
            },
            "external_sources": {"enabled": False, "sources": []},
        },
        "portfolio_filters": {"exclude_stages": ["FINALIZADO", "CANCELADO"], "active_year": 2026},
        "procurement_types": [],
        "intervention_types": [],
        "traffic_lights": {},
        "forecast_rules": {"immutable_milestones": ["H6", "H11"]},
        "risk_thresholds": {},
        "mapeo_columnas": [],
        "pm_aliases": [],
    }


def _extract_section(data: dict[str, Any], key: str) -> Any:
    if key in data:
        return data[key]
    return data


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file missing: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Config file missing: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _validate_config(config: dict[str, Any]) -> None:
    required = ["client", "sources", "procurement_types", "traffic_lights"]
    for key in required:
        if key not in config:
            raise ValueError(f"Missing required config section: {key}")

    client = config.get("client", {})
    if not client.get("code"):
        raise ValueError("client.code is required in client.yaml")
    if not client.get("name"):
        raise ValueError("client.name is required in client.yaml")


def get_logger(name: str, config: dict[str, Any]) -> logging.Logger:
    """Logger estandar: consola + pipeline.log en directorio de salida."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    log_file = config.get("output", {}).get("log_filename", "pipeline.log")
    output_dir = Path(config.get("output", {}).get("tracker_filename", "out_/PDS_TRACKER.xlsx")).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    fh = logging.FileHandler(output_dir / log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
