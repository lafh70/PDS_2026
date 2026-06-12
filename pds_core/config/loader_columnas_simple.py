"""Carga columnas default con overrides opcionales desde YAML de cliente."""

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

import yaml

from pds_core.config.schema.columnas_default import COLUMNAS_DEFAULT, ColumnaDef


class CargadorColumnasSimple:
    """Carga columnas: DEFAULT + overrides opcionales."""

    @staticmethod
    def _config_path(client_name: str) -> Path:
        return (
            Path(__file__).parent.parent.parent
            / "config"
            / "clients"
            / f"{client_name}.yaml"
        )

    @staticmethod
    def load(client_name: str = "hackathon") -> Dict[str, List[ColumnaDef]]:
        """
        Carga estructura de columnas.

        Precedencia:
        1. COLUMNAS_DEFAULT
        2. overrides desde config/clients/{client_name}.yaml (si existen)
        """
        columnas_finales = {
            tabla: [ColumnaDef(**vars(col)) for col in cols]
            for tabla, cols in COLUMNAS_DEFAULT.items()
        }

        config_path = CargadorColumnasSimple._config_path(client_name)
        if not config_path.exists():
            return columnas_finales

        with open(config_path, encoding="utf-8") as f:
            config_dict = yaml.safe_load(f) or {}

        override = config_dict.get("columnas_override", {})
        if not override:
            return columnas_finales

        renames = {k: v for k, v in override.items() if isinstance(v, str)}
        CargadorColumnasSimple._apply_renames(columnas_finales, renames)

        cols_adicionales = override.get("columnas_adicionales", {})
        if cols_adicionales:
            CargadorColumnasSimple._apply_columnas_adicionales(
                columnas_finales, cols_adicionales
            )

        for columnas in columnas_finales.values():
            columnas.sort(key=lambda c: c.orden_default)

        return columnas_finales

    @staticmethod
    def _dict_to_dataclass(data: Dict[str, Any]) -> ColumnaDef:
        """Convierte dict YAML parcial a ColumnaDef."""
        nombre = data["nombre_canónico"]
        return ColumnaDef(
            nombre_canónico=nombre,
            nombre_display=data.get("nombre_display", nombre),
            tipo=data.get("tipo", "text"),
            obligatorio=data.get("obligatorio", False),
            descripción=data.get("descripción", ""),
            validación_tipo=data.get("validación_tipo"),
            valores_desde=data.get("valores_desde"),
            tabla=data.get("tabla", "GESTION"),
            orden_default=data.get("orden", data.get("orden_default", 999)),
        )

    @staticmethod
    def _apply_renames(
        columnas_finales: Dict[str, List[ColumnaDef]],
        renames: Dict[str, str],
    ) -> None:
        """Aplica mapeos de nombre display (ej. Nombre -> Nombre_Proyecto)."""
        for columnas in columnas_finales.values():
            for col in columnas:
                if col.nombre_canónico in renames:
                    col.nombre_display = renames[col.nombre_canónico]

    @staticmethod
    def _apply_columnas_adicionales(
        columnas_finales: Dict[str, List[ColumnaDef]],
        cols_adicionales: Dict[str, Any],
    ) -> None:
        """Agrega columnas extra definidas en columnas_override.columnas_adicionales."""
        for nombre_canonico, def_col in cols_adicionales.items():
            if not isinstance(def_col, dict):
                continue
            def_copy = deepcopy(def_col)
            def_copy.setdefault("nombre_canónico", nombre_canonico)
            nueva_col = CargadorColumnasSimple._dict_to_dataclass(def_copy)
            tabla = nueva_col.tabla
            if tabla in columnas_finales:
                columnas_finales[tabla].append(nueva_col)
