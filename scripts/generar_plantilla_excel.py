#!/usr/bin/env python
"""CLI Fase 1: genera plantilla Excel de ingesta."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera plantilla Excel dinamica")
    parser.add_argument("--client", default="hackathon", help="Nombre cliente")
    parser.add_argument("--output", type=Path, default=None, help="Directorio output")
    parser.add_argument("--listar-columnas", action="store_true", help="Listar columnas")
    args = parser.parse_args()

    try:
        from pds_core.config.loader_columnas_simple import CargadorColumnasSimple
        from pds_core.utils.excel_generator_simple import GeneradorExcelIngestaSimple

        columnas = CargadorColumnasSimple.load(args.client)

        if args.listar_columnas:
            print(f"\nCOLUMNAS CONFIGURADAS: {args.client.upper()}\n")
            for tabla, cols in columnas.items():
                print(f"{tabla}:")
                print("-" * 80)
                for col in cols:
                    marca = "* " if col.obligatorio else "  "
                    print(
                        f"{marca}{col.nombre_canónico:20} -> {col.nombre_display:25} ({col.tipo})"
                    )
            return

        output_dir = args.output or (ROOT / "entrada_canonica")
        output_dir.mkdir(parents=True, exist_ok=True)
        fecha = datetime.now().strftime("%Y%m%d")
        output_path = output_dir / f"PDS_PLANTILLA_{args.client.upper()}_{fecha}.xlsx"

        print(f"\nGenerando plantilla Excel para {args.client}...")
        GeneradorExcelIngestaSimple.generate(columnas, output_path)
        print(f"[OK] Plantilla creada: {output_path}\n")
        print("Proximos pasos:")
        print(f"  1. Complete el Excel: {output_path}")
        print(f"  2. python scripts/ingestar.py --client {args.client} --ruta <archivo>")
        print(f"  3. python scripts/run_pipeline.py --client {args.client}")

    except Exception as exc:
        print(f"[ERROR] {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
