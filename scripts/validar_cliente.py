#!/usr/bin/env python3
"""Valida que un cliente tiene todos los archivos config requeridos."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REQUIRED = [
    "client.yaml",
    "sources.yaml",
    "mapeo_columnas.csv",
    "pm_aliases.csv",
    "intervention_types.yaml",
    "procurement_types.yaml",
    "portfolio_filters.yaml",
    "traffic_lights.yaml",
    "forecast_rules.yaml",
    "risk_thresholds.yaml",
]


def main() -> int:
    p = argparse.ArgumentParser(description="Validar config de cliente PDS_2026")
    p.add_argument("cliente", help="Codigo del cliente (ej: hackathon)")
    args = p.parse_args()

    folder = ROOT / "config" / "clients" / args.cliente.lower()
    if not folder.is_dir():
        print(f"[ERROR] No existe: {folder}")
        print("Crear con: python scripts/setup_cliente.py", args.cliente)
        return 1

    missing = [f for f in REQUIRED if not (folder / f).exists()]
    if missing:
        print(f"[ERROR] Archivos faltantes en {folder}:")
        for f in missing:
            print(f"  - {f}")
        return 1

    try:
        from pds_core.config.config_loader import load_config
        cfg = load_config(str(folder / "client.yaml"))
        print(f"[OK] Config valido: {cfg['client']['name']} ({cfg['client']['code']})")
    except Exception as exc:
        print(f"[ERROR] Config invalido: {exc}")
        return 1

    try:
        from pds_core.config.loader import CargadorConfiguracion
        from pds_core.config.validator import ValidadorConfiguracion
        cc = CargadorConfiguracion.load(args.cliente.lower())
        ValidadorConfiguracion.validar(cc)
    except Exception as exc:
        print(f"[WARN] Validacion ClienteConfig: {exc}")

    print(f"[OK] Cliente '{args.cliente}' listo para Fase 1-3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
