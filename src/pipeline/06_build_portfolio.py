"""ETL module 06 — 06_build_portfolio (PROMPTS 34-41)."""

from pds_core.pipeline.config_pipeline import run_step


def run(config: dict) -> None:
    """Entry point config-driven del modulo 06."""
    run_step("06", config)
