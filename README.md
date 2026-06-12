# PDS_2026 — Project Delivery System (Multicliente)

Plataforma PMO **config-driven** para seguimiento de portafolio de obras.
**Un solo código Python, cualquier cliente:** solo editar `config/clients/{cliente}/`.

## Características

- 3 fases: Plantilla Excel → Ingesta → Pipeline ETL (21 módulos)
- Reglas de negocio en YAML (semáforos, forecast, riesgos)
- Multicliente: local, híbrido o SharePoint (stub)
- Salidas: Tracker xlsx, Power BI, HTML, CSV, reportes calidad

## Inicio rápido

**Windows — doble clic o terminal:**

```powershell
PDS_2026.bat              # menu interactivo
PDS_2026.bat install      # primera instalacion
PDS_2026.bat demo         # demo hackathon
```

```powershell
git clone <URL> PDS_2026 && cd PDS_2026
python -m venv venv && .\venv\Scripts\activate
pip install -r requirements.txt && pip install -e .
python -m pytest tests/ -q
python scripts/seed_demo.py          # demo incluido
```

## Aplicar a un cliente nuevo

```powershell
python scripts/setup_cliente.py mi_cliente --name "Mi Empresa SA"
python scripts/validar_cliente.py mi_cliente
python scripts/generar_plantilla_excel.py --client mi_cliente
python scripts/ingestar.py --client mi_cliente --ruta excel_completado.xlsx
python scripts/run_pipeline.py --client mi_cliente
```

**Guía completa:** [GUIA_APLICACION_CLIENTE.md](GUIA_APLICACION_CLIENTE.md)

## Estructura

```
PDS_2026/
├── pds_core/              # Motor ETL (NO editar por cliente)
├── src/pipeline/          # 21 módulos config-driven
├── config/clients/
│   ├── template/          # Plantilla copiable
│   ├── hackathon/         # Demo local
│   └── galicia/           # Ejemplo hybrid
├── scripts/               # CLI operativos
├── tests/                 # 35+ tests
├── entrada_canonica/      # Datos normalizados (input pipeline)
└── out_/                  # Salidas generadas
```

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [GUIA_APLICACION_CLIENTE.md](GUIA_APLICACION_CLIENTE.md) | Onboarding paso a paso |
| [INSTALL.md](INSTALL.md) | Instalación detallada |
| [GITHUB.md](GITHUB.md) | Publicar en GitHub |
| [config/clients/template/README.md](config/clients/template/README.md) | Archivos de config |

## Clientes de ejemplo

| Cliente | Config | Storage |
|---------|--------|---------|
| hackathon | `config/clients/hackathon/` | Local |
| galicia | `config/clients/galicia/` | Hybrid + SharePoint stub |

## Requisitos

- Python 3.10+
- Ver `requirements.txt` (flexible) o `requirements-pinned.txt` (reproducible)

## Licencia

Uso interno JLL / equipo PMO. Ver [LICENSE](LICENSE).
