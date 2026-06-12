"""PROMPT 18/42 — CLI pipeline (config-driven, Parte 3)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pds_core.config.config_loader import load_config
from pds_core.pipeline.config_pipeline import run_all, run_step


def main() -> int:
    parser = argparse.ArgumentParser(description="PDS_2026 ETL Pipeline (21 modulos)")
    parser.add_argument(
        "--config",
        default="config/clients/hackathon/client.yaml",
        help="Ruta a client.yaml",
    )
    parser.add_argument("--client", help="Alias: config/clients/{client}/client.yaml")
    parser.add_argument("--module", help="Ejecutar solo un modulo (01-21)")
    parser.add_argument("--dry-run", action="store_true", help="Reservado para tests")
    args = parser.parse_args()

    config_path = args.config
    if args.client:
        config_path = f"config/clients/{args.client}/client.yaml"

    config = load_config(config_path)
    out = Path(config.get("output", {}).get("tracker_filename", "out_/PDS_TRACKER.xlsx")).parent
    out.mkdir(parents=True, exist_ok=True)

    if args.module:
        run_step(args.module.zfill(2), config)
    else:
        run_all(config)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
