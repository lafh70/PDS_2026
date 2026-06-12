"""ETL module 21 — 21_verification (PROMPTS 34-41)."""

from pds_core.pipeline.config_pipeline import run_step


def run(config: dict) -> None:
    """Entry point config-driven del modulo 21."""
    run_step("21", config)
