"""ETL module 20 — 20_data_quality (PROMPTS 34-41)."""

from pds_core.pipeline.config_pipeline import run_step


def run(config: dict) -> None:
    """Entry point config-driven del modulo 20."""
    run_step("20", config)
