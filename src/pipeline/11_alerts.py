"""ETL module 11 — 11_alerts (PROMPTS 34-41)."""

from pds_core.pipeline.config_pipeline import run_step


def run(config: dict) -> None:
    """Entry point config-driven del modulo 11."""
    run_step("11", config)
