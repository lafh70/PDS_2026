"""ETL module 10 — 10_risk_engine (PROMPTS 34-41)."""

from pds_core.pipeline.config_pipeline import run_step


def run(config: dict) -> None:
    """Entry point config-driven del modulo 10."""
    run_step("10", config)
