"""ETL module 02 — 02_enrich_procurement (PROMPTS 34-41)."""

from pds_core.pipeline.config_pipeline import run_step


def run(config: dict) -> None:
    """Entry point config-driven del modulo 02."""
    run_step("02", config)
