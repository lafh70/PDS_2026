#!/usr/bin/env python
"""CLI Fase 2: ingesta y normalizacion de datos."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingesta de datos + normalizacion")
    parser.add_argument("--client", default="hackathon", help="Nombre cliente")
    parser.add_argument("--ruta", type=Path, required=True, help="Excel de ingesta")
    parser.add_argument("--validar-solo", action="store_true", help="Solo validar")
    args = parser.parse_args()

    try:
        from pds_core.config.loader import CargadorConfiguracion
        from pds_core.ingestion.manager import OrquestadorIngesta
        from pds_core.integration.storage import StorageManager

        if not args.ruta.exists():
            raise FileNotFoundError(f"No existe: {args.ruta}")

        config = CargadorConfiguracion.load(args.client)
        storage = StorageManager(config.storage)

        print(f"\nIngesting {args.client}...")
        print(f"  Archivo: {args.ruta}")

        orquestador = OrquestadorIngesta(config, storage)
        config_ingesta = {
            tabla: {"tipo": "excel", "ruta": str(args.ruta), "sheet": tabla, "client_name": args.client}
            for tabla in OrquestadorIngesta.TABLAS
        }

        if args.validar_solo:
            from pds_core.ingestion.sources.excel_ingesta import IngestadorExcelIngesta

            for tabla, cfg in config_ingesta.items():
                ing = IngestadorExcelIngesta(tabla_canonica=tabla)
                res = ing.ingestar(cfg)
                print(f"  {tabla}: {res.estado.value} ({res.filas_validas} validas)")
            print("\n[OK] Validacion completada (sin guardar)")
            return

        resultados = orquestador.ingestar_todo(config_ingesta)

        print("\n=== RESUMEN INGESTA ===")
        for tabla, resultado in resultados.items():
            estado = "[OK]" if resultado.estado.value == "completado" else "[FAIL]"
            print(f"{estado} {tabla}: {resultado.filas_validas}/{resultado.filas_ingestion} filas")
            if resultado.errores:
                print(f"  Errores: {resultado.errores[0]}")

        print("\n[OK] Ingesta completada. Datos en: entrada_canonica/")

    except Exception as exc:
        print(f"[ERROR] {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
