#!/usr/bin/env python
"""CLI Fase 3: ejecuta pipeline ETL."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta pipeline PDS")
    parser.add_argument("--client", default="hackathon", help="Nombre cliente")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin guardar")
    parser.add_argument("--debug", action="store_true", help="Logs detallados")
    args = parser.parse_args()

    try:
        from pds_core.config.loader import CargadorConfiguracion
        from pds_core.integration.storage import StorageManager
        from pds_core.pipeline.executor import PipelineExecutor
        from pds_core.rules.manager import RulesManager

        print(f"\nEjecutando pipeline para {args.client}...")
        config = CargadorConfiguracion.load(args.client)
        storage = StorageManager(config.storage)
        rules = RulesManager(config)

        executor = PipelineExecutor(
            client_name=args.client,
            storage_manager=storage,
            rules_manager=rules,
            config=config,
        )
        resultado = executor.run(dry_run=args.dry_run)

        print("\n=== RESULTADO PIPELINE ===")
        print(f"Cliente: {resultado['client']}")
        print(f"Proyectos: {resultado['total_proyectos']}")
        print(f"Exitosos: {resultado['exitosos']}")
        print(f"Errores: {resultado['errores']}")
        print(f"Duracion: {resultado['duracion_segundos']:.2f}s")

        if args.dry_run:
            print("\n(DRY-RUN: no se guardaron salidas)")
        else:
            print("\n[OK] Salidas guardadas en: out_/")
            print("[OK] Reporte en: logs/")

        if resultado.get("errores"):
            sys.exit(1)

    except Exception as exc:
        print(f"[ERROR] {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
