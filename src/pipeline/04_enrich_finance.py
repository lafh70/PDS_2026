"""ETL module 04 — 04_enrich_finance (PROMPTS 34-41)."""

from pds_core.pipeline.config_pipeline import run_step


def run(config: dict) -> None:
    """Entry point config-driven del modulo 04."""
    run_step("04", config)
