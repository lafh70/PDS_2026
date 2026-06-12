"""ETL module 16 — 16_export_html (PROMPTS 34-41)."""

from pds_core.pipeline.config_pipeline import run_step


def run(config: dict) -> None:
    """Entry point config-driven del modulo 16."""
    run_step("16", config)
