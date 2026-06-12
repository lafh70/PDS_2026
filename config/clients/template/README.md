# Template de configuración — Nuevo cliente

Copiar esta carpeta completa a `config/clients/{nombre_cliente}/`.

## Uso rápido

```powershell
python scripts/setup_cliente.py mi_cliente --name "Mi Empresa"
python scripts/validar_cliente.py mi_cliente
```

## Archivos

| Archivo | Obligatorio | Descripción |
|---------|-------------|-------------|
| `client.yaml` | Sí | Identidad, locale, storage, salidas |
| `sources.yaml` | Sí | Fuentes Excel de entrada |
| `mapeo_columnas.csv` | Sí | Mapeo display → canónico |
| `pm_aliases.csv` | Sí | Normalización PM |
| `intervention_types.yaml` | Sí | Tipos de intervención |
| `procurement_types.yaml` | Sí | DDO, GC, Transport |
| `portfolio_filters.yaml` | Sí | Filtros cartera activa |
| `traffic_lights.yaml` | Sí | Semáforos 5 ejes |
| `forecast_rules.yaml` | Sí | Duraciones H1→H11 |
| `risk_thresholds.yaml` | Sí | Riesgos y alertas |

Ver `GUIA_APLICACION_CLIENTE.md` en la raíz del proyecto.
