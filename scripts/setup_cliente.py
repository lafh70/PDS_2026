#!/usr/bin/env python3
"""Crea carpeta config/clients/{cliente}/ desde template."""

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "config" / "clients" / "template"


def main() -> int:
    p = argparse.ArgumentParser(description="Onboarding nuevo cliente PDS_2026")
    p.add_argument("cliente", help="Codigo cliente (ej: acme)")
    p.add_argument("--name", default="", help="Nombre display")
    args = p.parse_args()

    dest = ROOT / "config" / "clients" / args.cliente.lower()
    if dest.exists():
        print(f"Ya existe: {dest}")
        return 1

    shutil.copytree(TEMPLATE, dest)
    client_yaml = dest / "client.yaml"
    text = client_yaml.read_text(encoding="utf-8")
    name = args.name or args.cliente.title()
    code = args.cliente.upper()
    text = text.replace('name: "ACME Corp"', f'name: "{name}"')
    text = text.replace('code: "ACME"', f'code: "{code}"')
    text = text.replace("output/", "out_/")
    client_yaml.write_text(text, encoding="utf-8")
    print(f"Cliente creado: {dest}")
    print(f"Editar YAML y ejecutar: python scripts/generar_plantilla_excel.py --client {args.cliente.lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
