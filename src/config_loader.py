"""PROMPT 28 — re-export unified config loader."""

from pds_core.config.config_loader import get_logger, load_config, load_config_for_client

__all__ = ["load_config", "load_config_for_client", "get_logger"]
