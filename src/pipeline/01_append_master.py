"""ETL module 01 — 01_append_master (PROMPTS 34-41)."""

from pds_core.pipeline.config_pipeline import run_step


def run(config: dict) -> None:
    """Entry point config-driven del modulo 01."""
    run_step("01", config)
