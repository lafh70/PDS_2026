"""ETL module 17 — 17_export_csv (PROMPTS 34-41)."""

from pds_core.pipeline.config_pipeline import run_step


def run(config: dict) -> None:
    """Entry point config-driven del modulo 17."""
    run_step("17", config)
