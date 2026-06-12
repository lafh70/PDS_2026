"""ETL module 18 — 18_export_pbi (PROMPTS 34-41)."""

from pds_core.pipeline.config_pipeline import run_step


def run(config: dict) -> None:
    """Entry point config-driven del modulo 18."""
    run_step("18", config)
