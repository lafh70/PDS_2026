"""ETL module 15 — 15_project_card (PROMPTS 34-41)."""

from pds_core.pipeline.config_pipeline import run_step


def run(config: dict) -> None:
    """Entry point config-driven del modulo 15."""
    run_step("15", config)
