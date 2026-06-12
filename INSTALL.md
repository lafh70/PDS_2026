# Instalacion — PDS_2026

## Requisitos

- Python 3.10+
- pip

## Instalacion

```powershell
cd PDS_2026
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
python -m pytest tests/ -q
```

## Aplicar a un cliente

Ver **[GUIA_APLICACION_CLIENTE.md](GUIA_APLICACION_CLIENTE.md)** — guía completa paso a paso.

Resumen:

```powershell
python scripts/setup_cliente.py {cliente} --name "{nombre}"
python scripts/validar_cliente.py {cliente}
python scripts/generar_plantilla_excel.py --client {cliente}
python scripts/ingestar.py --client {cliente} --ruta {excel}
python scripts/run_pipeline.py --client {cliente}
```

## Demo incluido

```powershell
python scripts/seed_demo.py
```

## Publicar en GitHub

Ver [GITHUB.md](GITHUB.md).

## Troubleshooting

**ModuleNotFoundError: pds_core** — Ejecutar `pip install -e .` desde la raíz.

**Config no existe** — Crear cliente con `setup_cliente.py` o copiar `config/clients/template/`.

**Excel bloqueado** — Cerrar Excel antes de ejecutar pipeline.
