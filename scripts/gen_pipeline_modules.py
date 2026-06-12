from pathlib import Path

MODULES = [
    "01_append_master",
    "02_enrich_procurement",
    "03_enrich_permits",
    "04_enrich_finance",
    "05_enrich_external_sources",
    "06_build_portfolio",
    "07_traffic_lights",
    "08_milestones",
    "09_forecast",
    "10_risk_engine",
    "11_alerts",
    "12_kpi",
    "13_dashboard",
    "14_gantt",
    "15_project_card",
    "16_export_html",
    "17_export_csv",
    "18_export_pbi",
    "19_backup",
    "20_data_quality",
    "21_verification",
]

base = Path(__file__).resolve().parent.parent / "src" / "pipeline"
base.mkdir(parents=True, exist_ok=True)

for name in MODULES:
    num = name[:2]
    path = base / f"{name}.py"
    path.write_text(
        f'"""ETL module {num} — {name} (PROMPTS 34-41)."""\n\n'
        f"from pds_core.pipeline.config_pipeline import run_step\n\n\n"
        f"def run(config: dict) -> None:\n"
        f'    """Entry point config-driven del modulo {num}."""\n'
        f'    run_step("{num}", config)\n',
        encoding="utf-8",
    )
    print("wrote", path)
