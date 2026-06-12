# Guía de aplicación — Nuevo cliente PDS_2026

Esta guía permite desplegar PDS_2026 en **cualquier cliente** sin modificar código Python.
Solo se editan archivos en `config/clients/{cliente}/`.

---

## Requisitos previos

- Python 3.10 o superior
- Git (opcional, para clonar desde GitHub)
- Excel (para completar plantillas)

---

## Paso 0 — Instalar el sistema (una vez por máquina)

```powershell
git clone <URL_REPOSITORIO> PDS_2026
cd PDS_2026
python -m venv venv
.\venv\Scripts\activate          # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
pip install -e .                 # instala pds_core como paquete
python -m pytest tests/ -q       # verificar instalación
```

---

## Paso 1 — Crear carpeta del cliente

```powershell
python scripts/setup_cliente.py mi_cliente --name "Mi Empresa SA"
```

Esto copia `config/clients/template/` → `config/clients/mi_cliente/` con 10 archivos de configuración.

### Archivos a editar (checklist)

| Archivo | Qué configurar |
|---------|----------------|
| `client.yaml` | Nombre, código, locale, rutas storage/salidas, SharePoint |
| `sources.yaml` | Rutas Excel de entrada (GESTION, SOURCING, PERMITS, FINANCE) |
| `mapeo_columnas.csv` | Columnas del Excel del cliente → nombres canónicos |
| `pm_aliases.csv` | Variantes de nombres de PM |
| `intervention_types.yaml` | Tipos de obra y duraciones H6→H7 |
| `procurement_types.yaml` | Tipos DDO/GC y columnas de licitación |
| `portfolio_filters.yaml` | Etapas excluidas de cartera activa |
| `traffic_lights.yaml` | Reglas de semáforos (5 ejes) |
| `forecast_rules.yaml` | Duraciones entre hitos H1→H11 |
| `risk_thresholds.yaml` | Umbrales de riesgo y plantillas de alertas |

Validar configuración:

```powershell
python scripts/validar_cliente.py mi_cliente
```

---

## Paso 2 — FASE 1: Generar plantilla Excel

```powershell
python scripts/generar_plantilla_excel.py --client mi_cliente
```

**Salida:** `entrada_canonica/PDS_PLANTILLA_{CLIENTE}_YYYYMMDD.xlsx`

Entregar esta plantilla al equipo de PMO. Completar datos con nombres **display** del cliente (según `mapeo_columnas.csv`).

---

## Paso 3 — FASE 2: Ingestar datos

Cuando el usuario devuelve el Excel completado:

```powershell
python scripts/ingestar.py --client mi_cliente --ruta "ruta\al\excel_completado.xlsx"
```

**Salida en `entrada_canonica/`:**
- `PDS_GESTION.xlsx`
- `PDS_SOURCING.xlsx`
- `PDS_PERMITS.xlsx`
- `PDS_FINANCE.xlsx`

Los datos quedan en **nombres canónicos** listos para el pipeline.

---

## Paso 4 — FASE 3: Ejecutar pipeline

```powershell
python scripts/run_pipeline.py --client mi_cliente
```

**Salidas en `out_/` (o ruta definida en `client.yaml`):**

| Archivo | Uso |
|---------|-----|
| `PDS_TRACKER.xlsx` | Tracker multi-hoja (comité, operación) |
| `PDS_TRACKER_PBI.xlsx` | Star schema para Power BI |
| `PDS_TRACKER.html` | Vista web estática |
| `PDS_TRACKER.csv` | Exportación plana |
| `DATA_QUALITY_REPORT.json` | Calidad de datos |
| `backup/YYYYMMDD/` | Respaldo automático |

---

## Rutas de storage por tipo de despliegue

### Solo local (desarrollo / demo)

```yaml
# client.yaml
storage:
  entrada_canonica:
    provider: local
    local_path: entrada_canonica/
  salidas:
    provider: local
    local_path: out_/
```

### Híbrido (producción con SharePoint)

```yaml
storage:
  entrada_canonica:
    provider: hybrid
    local_path: /data/entrada_canonica/
    sharepoint_folder: M44/Descargas
    read_from: local_first
    write_to: both
  salidas:
    provider: hybrid
    local_path: /data/out_/
    sharepoint_folder: M43/Reportes
    write_to: both
  sharepoint_site: "https://tenant.sharepoint.com/sites/PMO"
```

> SharePoint upload real requiere configuración adicional (`.env`). Ver `.env.example`.

---

## Ciclo operativo (cada semana / mes)

```
1. Usuario completa Excel  →  2. ingestar.py  →  3. run_pipeline.py  →  4. Publicar out_/
```

No es necesario regenerar plantilla salvo que cambien columnas o reglas de negocio.

---

## Solución de problemas

| Error | Acción |
|-------|--------|
| `Config no existe` | Verificar `config/clients/{cliente}/client.yaml` |
| `PDS_GESTION.xlsx not found` | Ejecutar Fase 2 antes del pipeline |
| `File is open/locked` | Cerrar Excel antes de ejecutar |
| Semáforos incorrectos | Revisar `traffic_lights.yaml`, no el código |
| Forecast incorrecto | Revisar `forecast_rules.yaml` |

---

## Referencia rápida de comandos

```powershell
# Onboarding
python scripts/setup_cliente.py {cliente} --name "{nombre}"
python scripts/validar_cliente.py {cliente}

# Operación
python scripts/generar_plantilla_excel.py --client {cliente}
python scripts/ingestar.py --client {cliente} --ruta {excel}
python scripts/run_pipeline.py --client {cliente}

# Pipeline alternativo (config unificado Parte 3)
python src/run_pipeline.py --config config/clients/{cliente}/client.yaml

# Demo incluido
python scripts/seed_demo.py
```

---

## Principio clave

> **Un codebase, N clientes.**  
> Agregar cliente = crear carpeta `config/clients/{cliente}/` + ejecutar 3 fases.  
> **Nunca** modificar `pds_core/` ni `src/pipeline/` por cliente.
