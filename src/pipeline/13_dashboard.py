"""ETL module 13 — 13_dashboard (PROMPTS 34-41)."""

from pds_core.pipeline.config_pipeline import run_step


def run(config: dict) -> None:
    """Entry point config-driven del modulo 13."""
    run_step("13", config)
