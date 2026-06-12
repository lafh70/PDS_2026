"""ETL module 09 — 09_forecast (PROMPTS 34-41)."""

from pds_core.pipeline.config_pipeline import run_step


def run(config: dict) -> None:
    """Entry point config-driven del modulo 09."""
    run_step("09", config)
