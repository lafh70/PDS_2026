#!/usr/bin/env python3
"""
MÓDULO 01: append_master.py
Pipeline ETL — Staging vertical consolidado

Entrada:  config/ + input/*.xlsx
Salida:   output/Tracker.xlsx (hoja MASTER)
"""

import argparse
import time
from pathlib import Path
import pandas as pd
import yaml
import csv
from datetime import datetime

from config_loader import load_config
from utils.logger import get_logger
from utils.excel_io import read_sheet, write_sheet
from utils.project_id import normalize, validate_unique, validate_format


def run(config: dict) -> pd.DataFrame:
    """
    Consolida todas las fuentes de Excel en una hoja MASTER staging.
    
    Args:
        config: dict con todas las configuraciones cargadas
    
    Returns:
        pd.DataFrame con MASTER consolidado
    """
    log = get_logger("01_append_master", config)
    start = time.time()
    log.info("START: consolidar fuentes Excel → MASTER")
    
    # ─────────────────────────────────────────────────────
    # 1. Cargar mapeo de columnas (cliente → canónico)
    # ─────────────────────────────────────────────────────
    mapeo = _load_mapeo(config)
    log.info(f"Mapeo cargado: {len(mapeo)} columnas mapeadas")
    
    # ─────────────────────────────────────────────────────
    # 2. Iterar por fuentes habilitadas
    # ─────────────────────────────────────────────────────
    dfs = []
    sources = config.get("sources", {})
    
    for source_key, source_config in sources.items():
        if source_key == "external_sources":
            continue  # Las procesamos en módulo 05
        
        if not source_config.get("enabled"):
            log.info(f"[SKIP] {source_key} (disabled)")
            continue
        
        try:
            df = _read_source(source_key, source_config, mapeo, log)
            if df is not None and len(df) > 0:
                dfs.append(df)
                log.info(f"[OK] {source_key}: {len(df)} filas")
            else:
                log.warning(f"[EMPTY] {source_key}: sin filas")
        except Exception as e:
            log.error(f"[FAIL] {source_key}: {e}")
            raise SystemExit(1)
    
    # ─────────────────────────────────────────────────────
    # 3. Consolidar (union vertical)
    # ─────────────────────────────────────────────────────
    if not dfs:
        log.error("No data sources enabled or read successfully")
        raise SystemExit(1)
    
    master = pd.concat(dfs, axis=0, ignore_index=True, sort=False)
    log.info(f"Consolidado: {len(master)} filas totales, {len(master.columns)} columnas")
    
    # ─────────────────────────────────────────────────────
    # 4. Normalizar Project_ID
    # ─────────────────────────────────────────────────────
    if "Project_ID" not in master.columns:
        log.error("Project_ID column not found after consolidation")
        raise SystemExit(1)
    
    master["Project_ID"] = master["Project_ID"].apply(normalize)
    
    # ─────────────────────────────────────────────────────
    # 5. Validar unicidad
    # ─────────────────────────────────────────────────────
    dupes = validate_unique(master, "Project_ID")
    if dupes:
        log.error(f"Duplicate Project_IDs detected: {dupes}")
        raise SystemExit(1)
    log.info(f"[OK] Project_ID único validado: {len(master)} IDs únicos")
    
    # ─────────────────────────────────────────────────────
    # 6. Llenar metadata
    # ─────────────────────────────────────────────────────
    master["_processed_date"] = datetime.now().isoformat()
    master["_source_module"] = "01_append_master"
    
    # ─────────────────────────────────────────────────────
    # 7. Escribir a Excel (atómico)
    # ─────────────────────────────────────────────────────
    try:
        write_sheet("output/Tracker.xlsx", "MASTER", master)
        log.info("MASTER written to output/Tracker.xlsx")
    except PermissionError as e:
        log.error(f"Cannot write: {e}")
        raise SystemExit(1)
    
    # ─────────────────────────────────────────────────────
    # 8. Log final
    # ─────────────────────────────────────────────────────
    elapsed = round(time.time() - start, 2)
    log.info(f"DONE | rows={len(master)} | cols={len(master.columns)} | {elapsed}s")
    
    return master


def _load_mapeo(config: dict) -> dict:
    """Carga mapeo_columnas.csv → {col_canonica: col_cliente}"""
    config_dir = Path("config")
    mapeo_path = config_dir / "mapeo_columnas.csv"
    
    if not mapeo_path.exists():
        raise FileNotFoundError(f"Mapeo no encontrado: {mapeo_path}")
    
    mapeo = {}
    with open(mapeo_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            col_canon = row.get("col_canonica")
            col_cliente = row.get("col_cliente")
            fuente = row.get("fuente")
            if col_canon and col_cliente:
                mapeo[col_canon] = (col_cliente, fuente)
    
    return mapeo


def _read_source(source_key: str, source_config: dict, mapeo: dict, log) -> pd.DataFrame | None:
    """Lee una fuente Excel y aplica mapeo de columnas."""
    filepath = source_config.get("file")
    sheet_name = source_config.get("sheet")
    header_row = source_config.get("header_row", 1)
    
    if not filepath or not sheet_name:
        log.warning(f"{source_key}: config incompleta (file o sheet faltante)")
        return None
    
    # Leer con protección de locks
    try:
        df = read_sheet(filepath, sheet_name, header_row)
    except FileNotFoundError:
        log.warning(f"{source_key}: archivo no encontrado: {filepath}")
        return None
    except PermissionError as e:
        log.error(f"{source_key}: archivo bloqueado (abierto en Excel?): {e}")
        raise
    
    if df.empty:
        return None
    
    # Aplicar mapeo
    rename_dict = {}
    for col_canon, (col_cliente, fuente) in mapeo.items():
        if fuente == source_key and col_cliente in df.columns:
            rename_dict[col_cliente] = col_canon
    
    df_renamed = df.rename(columns=rename_dict)
    
    # Seleccionar solo columnas canonicas que existan
    cols_existentes = [c for c in rename_dict.values() if c in df_renamed.columns]
    df_final = df_renamed[cols_existentes].copy()
    
    return df_final


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Módulo 01: Append Master")
    parser.add_argument("--config", default="config/client.yaml", help="Path to client.yaml")
    args = parser.parse_args()
    
    config = load_config(args.config)
    run(config)
