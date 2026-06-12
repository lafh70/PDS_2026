"""Export, backup, QA and verification (M16-M21)."""

import json
import shutil
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import pandas as pd

from pds_core.pipeline.state import PipelineState
from pds_core.utils.dates import date_to_str, parse_date
from pds_core.utils.excel_io import read_workbook, write_sheet


def export_html(state: PipelineState, output_dir: Path, client_name: str) -> Path:
    """M16: Static HTML tracker."""
    df = state.portfolio
    sem = state.sheets.get("SEMAFOROS", pd.DataFrame())
    rows_html = []
    for _, row in df.iterrows():
        pid = row["Project_ID"]
        s = sem[sem["Project_ID"] == pid]["Estado_Global"].iloc[0] if not sem.empty and pid in sem["Project_ID"].values else "WHITE"
        color = {"GREEN": "#22c55e", "YELLOW": "#eab308", "RED": "#ef4444", "BLACK": "#111", "WHITE": "#94a3b8"}.get(s, "#94a3b8")
        rows_html.append(
            f"<tr><td>{pid}</td><td>{row.get('Nombre','')}</td>"
            f"<td style='background:{color}'>{s}</td>"
            f"<td>{row.get('Pct_Consumed','')}</td></tr>"
        )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>PDS Tracker - {client_name}</title>
<style>body{{font-family:Segoe UI,sans-serif;margin:2rem}}table{{border-collapse:collapse;width:100%}}
th,td{{border:1px solid #ddd;padding:8px}}th{{background:#1f4e79;color:#fff}}</style></head>
<body><h1>PDS Tracker — {client_name}</h1>
<p>Generado: {datetime.now().isoformat()}</p>
<table><tr><th>Project_ID</th><th>Nombre</th><th>Estado</th><th>% Consumo</th></tr>
{''.join(rows_html)}</table></body></html>"""

    path = output_dir / "PDS_TRACKER.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def export_csv(state: PipelineState, output_dir: Path) -> Path:
    """M17: CSV export UTF-8 BOM."""
    path = output_dir / "PDS_TRACKER.csv"
    df = state.master.copy()
    for col in df.columns:
        if df[col].dtype == "datetime64[ns]":
            df[col] = df[col].apply(date_to_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def export_pbi(state: PipelineState, output_dir: Path) -> Path:
    """M18: Star schema for Power BI."""
    path = output_dir / "PDS_TRACKER_PBI.xlsx"
    portfolio = state.portfolio.drop_duplicates(subset=["Project_ID"]).copy()
    sem = state.sheets.get("SEMAFOROS", pd.DataFrame()).drop_duplicates(subset=["Project_ID"])
    riesgos = state.sheets.get("RIESGOS", pd.DataFrame())
    alertas = state.sheets.get("ALERTAS_TODAS", pd.DataFrame())

    date_cols = [f"H{i}" for i in range(1, 12)]
    for col in date_cols:
        if col in portfolio.columns:
            portfolio[col] = portfolio[col].apply(lambda v: date_to_str(v) or "")

    finance_cols = ["Project_ID"] + [c for c in portfolio.columns if c in ("Pct_Consumed", "BC_Nro", "BC_Preaprobado", "Monto_BC_Final", "Total_Contabilizado", "Total_Comprometido")]
    sourcing_cols = ["Project_ID"] + [c for c in portfolio.columns if "Licit" in c or c.startswith("GC_") or "DDO" in c]
    permits_cols = ["Project_ID"] + [c for c in portfolio.columns if "Perm" in c or "H8" in c or "H9" in c or "H10" in c or "Status_Permiso" in c]

    tables = {
        "tblPROJECTS": portfolio,
        "tblTRAFFIC_LIGHTS": sem,
        "tblFINANCE": portfolio[finance_cols].drop_duplicates(subset=["Project_ID"]) if len(finance_cols) > 1 else portfolio[["Project_ID"]],
        "tblSOURCING": portfolio[sourcing_cols].drop_duplicates(subset=["Project_ID"]) if len(sourcing_cols) > 1 else portfolio[["Project_ID"]],
        "tblPERMITS": portfolio[permits_cols].drop_duplicates(subset=["Project_ID"]) if len(permits_cols) > 1 else portfolio[["Project_ID"]],
        "tblALERTAS": alertas if not alertas.empty else pd.DataFrame(columns=["Project_ID"]),
        "tblRIESGOS": riesgos if not riesgos.empty else pd.DataFrame(columns=["Project_ID"]),
    }

    if path.exists():
        path.unlink()

    for sheet, df in tables.items():
        write_sheet(path, sheet, df)

    return path


def run_backup(output_dir: Path, retention_days: int = 7) -> Path | None:
    """M19: Daily backup snapshot."""
    backup_root = output_dir / "backup" / date.today().strftime("%Y%m%d")
    if backup_root.exists():
        return backup_root
    backup_root.mkdir(parents=True, exist_ok=True)
    for f in output_dir.glob("PDS_*"):
        if f.is_file():
            shutil.copy2(f, backup_root / f.name)

    cutoff = datetime.now().timestamp() - retention_days * 86400
    for old in (output_dir / "backup").glob("*"):
        if old.is_dir() and old.stat().st_mtime < cutoff:
            shutil.rmtree(old, ignore_errors=True)
    return backup_root


def run_data_quality(state: PipelineState, output_dir: Path) -> dict:
    """M20: Data quality report."""
    df = state.portfolio
    total = len(df)
    metrics = {"timestamp": datetime.now().isoformat(), "total_projects": total, "columns": {}}

    for col in df.columns:
        non_null = int(df[col].notna().sum())
        metrics["columns"][col] = {"completeness_pct": round(100 * non_null / total, 1) if total else 0}

    pid_valid = 0
    if "Project_ID" in df.columns:
        import re

        pat = re.compile(r"^[A-Z]{2}-\d{4}-\d{4}-\d{2}$")
        pid_valid = int(df["Project_ID"].astype(str).str.match(pat).sum())

    seq_ok = 0
    if all(c in df.columns for c in ("H1", "H6", "H7")):
        for _, row in df.iterrows():
            h1, h6, h7 = parse_date(row.get("H1")), parse_date(row.get("H6")), parse_date(row.get("H7"))
            if h1 is None or h6 is None:
                continue
            if h6 >= h1 and (h7 is None or h7 >= h6):
                seq_ok += 1

    metrics["consistency_project_id_pct"] = round(100 * pid_valid / total, 1) if total else 0
    metrics["accuracy_date_sequence_pct"] = round(100 * seq_ok / total, 1) if total else 0
    metrics["quality_score"] = round(
        (metrics["consistency_project_id_pct"] + metrics["accuracy_date_sequence_pct"]) / 2, 1
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "DATA_QUALITY_REPORT.json"
    txt_path = output_dir / "DATA_QUALITY_REPORT.txt"
    json_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    txt_path.write_text(
        f"PDS Data Quality Report\nScore: {metrics['quality_score']}/100\nProjects: {total}\n",
        encoding="utf-8",
    )
    return metrics


def run_verification(tracker_path: Path, pbi_path: Path, dq_path: Path) -> None:
    """M21: Structural verification (fail-fast)."""
    errors = []
    required_sheets = [
        "MASTER",
        "MASTER_PORTFOLIO",
        "SEMAFOROS",
        "HITOS",
        "FORECAST",
        "KPI_PORTFOLIO",
    ]

    if not tracker_path.exists():
        errors.append(f"Missing Tracker: {tracker_path}")
    else:
        wb = read_workbook(tracker_path)
        missing = [s for s in required_sheets if s not in wb]
        if missing:
            errors.append(f"Missing sheets in Tracker: {missing}")

    if not pbi_path.exists():
        errors.append(f"Missing PBI export: {pbi_path}")
    else:
        wb_pbi = read_workbook(pbi_path)
        if "tblPROJECTS" in wb_pbi:
            dupes = wb_pbi["tblPROJECTS"]["Project_ID"].duplicated().sum()
            if dupes:
                errors.append(f"tblPROJECTS has {dupes} duplicate Project_IDs")

    if not dq_path.exists():
        errors.append("Missing DATA_QUALITY_REPORT.json")

    if errors:
        raise SystemExit("VERIFICATION FAILED:\n" + "\n".join(errors))
