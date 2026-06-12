"""Config-driven ETL runner (PROMPTS 34-41). Bridges unified config to pds_core steps."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from pds_core.config.config_loader import get_logger
from pds_core.config.loader import CargadorConfiguracion
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
from pds_core.pipeline.steps import (
    Step01MasterAppend,
    Step02EnrichFinance,
    Step06BuildPortfolio,
    Step07TrafficLights,
    Step08Milestones,
    Step09Forecast,
    Step10RiskEngine,
    Step11Alerts,
    Step12Kpi,
    Step13Dashboard,
    Step14Gantt,
    Step15ProjectCard,
)
from pds_core.rules.manager import RulesManager
from pds_core.utils.dates import parse_date
from pds_core.utils.excel_io import read_sheet, write_sheet

STATE_KEY = "_pipeline_state"
RULES_KEY = "_rules_manager"


def tracker_path(config: dict[str, Any]) -> Path:
    return Path(config.get("output", {}).get("tracker_filename", "out_/PDS_TRACKER.xlsx"))


def output_dir(config: dict[str, Any]) -> Path:
    return tracker_path(config).parent


def _get_state(config: dict[str, Any]) -> PipelineState:
    if STATE_KEY not in config:
        config[STATE_KEY] = PipelineState(master=pd.DataFrame())
    return config[STATE_KEY]


def _get_rules(config: dict[str, Any]) -> RulesManager:
    if RULES_KEY not in config:
        from pds_core.config.loader import CargadorConfiguracion
        client_code = config.get("client", {}).get("code", "HACKATHON").lower()
        try:
            client_cfg = CargadorConfiguracion.load(client_code)
        except FileNotFoundError:
            client_cfg = CargadorConfiguracion.load("hackathon")
        yaml = {k: config.get(k) for k in (
            "traffic_lights", "forecast_rules", "risk_thresholds", "portfolio_filters"
        ) if config.get(k)}
        config[RULES_KEY] = RulesManager(client_cfg, yaml)
    return config[RULES_KEY]


def _apply_column_mapping(df: pd.DataFrame, config: dict[str, Any], fuente: str) -> pd.DataFrame:
    mapeo = {
        row["col_cliente"]: row["col_canonica"]
        for row in config.get("mapeo_columnas", [])
        if row.get("fuente") == fuente
    }
    return df.rename(columns=mapeo, errors="ignore")


def _normalize_pm(df: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    if "PM" not in df.columns:
        return df
    aliases = {row["alias"]: row["canonical"] for row in config.get("pm_aliases", [])}
    df = df.copy()
    df["PM"] = df["PM"].map(lambda x: aliases.get(str(x).strip(), x) if pd.notna(x) else x)
    return df


def _merge_source(df: pd.DataFrame, filename: str, sheet: str = "DATOS") -> pd.DataFrame:
    path = Path(filename)
    if not path.exists():
        return df
    src = read_sheet(path, sheet)
    overlap = set(df.columns) & set(src.columns) - {"Project_ID"}
    src = src.drop(columns=list(overlap), errors="ignore")
    return df.merge(src, on="Project_ID", how="left")


def _write_master(config: dict[str, Any], df: pd.DataFrame) -> None:
    write_sheet(tracker_path(config), "MASTER", df)


def _persist_sheets(config: dict[str, Any], state: PipelineState) -> None:
    path = tracker_path(config)
    write_sheet(path, "MASTER", state.sheets.get("MASTER", state.master))
    for name, df in state.sheets.items():
        if name != "MASTER" and df is not None and not df.empty:
            write_sheet(path, name, df)


def run_step(step_id: str, config: dict[str, Any]) -> None:
    """Execute one ETL module by id (01-21)."""
    num = step_id.split("_")[0] if "_" in step_id else step_id
    num = num.zfill(2)[:2]
    handlers = {
        "01": _run_01,
        "02": _run_02,
        "03": _run_03,
        "04": _run_04,
        "05": _run_05,
        "06": _run_06,
        "07": _run_07,
        "08": _run_08,
        "09": _run_09,
        "10": _run_10,
        "11": _run_11,
        "12": _run_12,
        "13": _run_13,
        "14": _run_14,
        "15": _run_15,
        "16": _run_16,
        "17": _run_17,
        "18": _run_18,
        "19": _run_19,
        "20": _run_20,
        "21": _run_21,
    }
    if num not in handlers:
        raise ValueError(f"Unknown pipeline step: {step_id}")
    handlers[num](config)


def run_all(config: dict[str, Any]) -> None:
    """Run modules 01 through 21 in order."""
    for n in range(1, 22):
        run_step(f"{n:02d}", config)


def _run_01(config: dict[str, Any]) -> None:
    log = get_logger("01_append_master", config)
    log.info("START append_master")
    sources = config["sources"]
    portfolio = sources["portfolio_plan"]
    df = read_sheet(portfolio["file"], portfolio["sheet"], portfolio.get("header_row", 1))
    df = _apply_column_mapping(df, config, "portfolio_plan")
    df = _normalize_pm(df, config)
    for col in [f"H{i}" for i in range(1, 12)]:
        if col in df.columns:
            df[col] = df[col].apply(parse_date)
    state = _get_state(config)
    state.master = df
    state = Step01MasterAppend().execute(state)
    _write_master(config, state.master)
    log.info(f"MASTER written: {len(state.master)} rows")
    log.info("END append_master")


def _run_02(config: dict[str, Any]) -> None:
    log = get_logger("02_enrich_procurement", config)
    log.info("START enrich_procurement")
    path = tracker_path(config)
    df = read_sheet(path, "MASTER")
    proc_file = config["sources"]["procurement"]["file"]
    df = _merge_source(df, proc_file)
    df = _apply_column_mapping(df, config, "procurement")
    state = _get_state(config)
    state.master = df
    write_sheet(path, "MASTER", df)
    log.info("END enrich_procurement")


def _run_03(config: dict[str, Any]) -> None:
    log = get_logger("03_enrich_permits", config)
    log.info("START enrich_permits")
    path = tracker_path(config)
    df = read_sheet(path, "MASTER")
    permits = config["sources"]["permits"]
    df = _merge_source(df, permits["file"], permits.get("sheet", "DATOS"))
    df = _apply_column_mapping(df, config, "permits")
    state = _get_state(config)
    state.master = df
    write_sheet(path, "MASTER", df)
    log.info("END enrich_permits")


def _run_04(config: dict[str, Any]) -> None:
    log = get_logger("04_enrich_finance", config)
    log.info("START enrich_finance")
    path = tracker_path(config)
    df = read_sheet(path, "MASTER")
    finance = config["sources"]["finance"]
    df = _merge_source(df, finance["file"], finance.get("sheet", "DATOS"))
    df = _apply_column_mapping(df, config, "finance")
    state = _get_state(config)
    state.master = df
    state = Step02EnrichFinance().execute(state)
    write_sheet(path, "MASTER", state.master)
    log.info("END enrich_finance")


def _run_05(config: dict[str, Any]) -> None:
    log = get_logger("05_enrich_external_sources", config)
    log.info("START enrich_external_sources")
    ext = config["sources"].get("external_sources", {})
    if not ext.get("enabled", False):
        log.info("External sources disabled — skip")
        return
    path = tracker_path(config)
    df = read_sheet(path, "MASTER")
    for source in ext.get("sources", []):
        if not source.get("enabled", False):
            log.info(f"Skip external source {source.get('type')}")
            continue
        try:
            src = read_sheet(source["file"], source["sheet"])
            prefix = source.get("type", "EXT").upper()
            src = src.rename(columns={c: f"{prefix}_{c}" for c in src.columns if c != "Project_ID"})
            df = df.merge(src, on="Project_ID", how="left")
        except FileNotFoundError:
            log.warning(f"External source not found: {source.get('file')}")
    write_sheet(path, "MASTER", df)
    state = _get_state(config)
    state.master = df
    log.info("END enrich_external_sources")


def _run_06(config: dict[str, Any]) -> None:
    state = _get_state(config)
    state.master = read_sheet(tracker_path(config), "MASTER")
    state = Step06BuildPortfolio().execute(state)
    _persist_sheets(config, state)


def _run_07(config: dict[str, Any]) -> None:
    state = _get_state(config)
    state.master = read_sheet(tracker_path(config), "MASTER")
    state = Step07TrafficLights(rules_manager=_get_rules(config)).execute(state)
    _persist_sheets(config, state)


def _run_08(config: dict[str, Any]) -> None:
    state = _get_state(config)
    state.master = read_sheet(tracker_path(config), "MASTER_PORTFOLIO")
    state = Step08Milestones().execute(state)
    _persist_sheets(config, state)


def _run_09(config: dict[str, Any]) -> None:
    state = _get_state(config)
    state.master = read_sheet(tracker_path(config), "MASTER_PORTFOLIO")
    state.sheets["HITOS"] = read_sheet(tracker_path(config), "HITOS")
    state = Step09Forecast(rules_manager=_get_rules(config)).execute(state)
    _persist_sheets(config, state)


def _run_10(config: dict[str, Any]) -> None:
    state = _load_state_from_tracker(config)
    state = Step10RiskEngine(rules_manager=_get_rules(config)).execute(state)
    _persist_sheets(config, state)


def _run_11(config: dict[str, Any]) -> None:
    state = _load_state_from_tracker(config)
    state = Step11Alerts().execute(state)
    _persist_sheets(config, state)


def _run_12(config: dict[str, Any]) -> None:
    state = _load_state_from_tracker(config)
    state = Step12Kpi().execute(state)
    _persist_sheets(config, state)


def _run_13(config: dict[str, Any]) -> None:
    state = _load_state_from_tracker(config)
    state = Step13Dashboard().execute(state)
    _persist_sheets(config, state)


def _run_14(config: dict[str, Any]) -> None:
    state = _load_state_from_tracker(config)
    state = Step14Gantt().execute(state)
    _persist_sheets(config, state)


def _run_15(config: dict[str, Any]) -> None:
    state = _load_state_from_tracker(config)
    state = Step15ProjectCard().execute(state)
    _persist_sheets(config, state)


def _run_16(config: dict[str, Any]) -> None:
    state = _load_state_from_tracker(config)
    client = config.get("client", {}).get("name", "client")
    export_html(state, output_dir(config), client)


def _run_17(config: dict[str, Any]) -> None:
    state = _load_state_from_tracker(config)
    out = output_dir(config)
    export_csv(state, out)


def _run_18(config: dict[str, Any]) -> None:
    state = _load_state_from_tracker(config)
    out = output_dir(config)
    export_pbi(state, out)


def _run_19(config: dict[str, Any]) -> None:
    backup_cfg = config.get("backup", {"enabled": True, "retention_days": 30})
    run_backup(output_dir(config), retention_days=backup_cfg.get("retention_days", 30))


def _run_20(config: dict[str, Any]) -> None:
    state = _load_state_from_tracker(config)
    run_data_quality(state, output_dir(config))


def _run_21(config: dict[str, Any]) -> None:
    out = output_dir(config)
    pbi = Path(config.get("output", {}).get("pbi_filename", out / "PDS_TRACKER_PBI.xlsx"))
    dq = out / "DATA_QUALITY_REPORT.json"
    run_verification(tracker_path(config), pbi, dq)
    get_logger("21_verification", config).info("VERIFICATION PASSED - Pipeline complete")


def _load_state_from_tracker(config: dict[str, Any]) -> PipelineState:
    from pds_core.utils.excel_io import read_workbook

    path = tracker_path(config)
    wb = read_workbook(path)
    state = _get_state(config)
    state.master = wb.get("MASTER_PORTFOLIO", wb.get("MASTER", pd.DataFrame()))
    state.sheets = wb
    return state
