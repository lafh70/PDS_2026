"""Map display column names to canonical names."""

import pandas as pd

from pds_core.config.loader_columnas_simple import CargadorColumnasSimple


class ColumnMapper:
    """Maps Excel display headers to canonical column names."""

    @staticmethod
    def map_display_to_canonical(
        df: pd.DataFrame, client_name: str, tabla: str
    ) -> pd.DataFrame:
        """
        Rename display columns to canonical names using client column config.

        Args:
            df: DataFrame with display column names.
            client_name: Client identifier for column overrides.
            tabla: Sheet name (GESTION, SOURCING, PERMITS, FINANCE).

        Returns:
            DataFrame with canonical column names.
        """
        columnas = CargadorColumnasSimple.load(client_name)
        columnas_tabla = columnas.get(tabla, [])

        mapeo: dict[str, str] = {}
        for col in columnas_tabla:
            display = col.nombre_display or col.nombre_canónico
            if display != col.nombre_canónico:
                mapeo[display] = col.nombre_canónico
            mapeo[col.nombre_canónico] = col.nombre_canónico

        lower_to_canonical = {k.lower(): v for k, v in mapeo.items()}
        en_aliases = {
            "site_id": "Nro_Sucursal", "name": "Nombre", "project_stage": "Etapa",
            "intervention_type": "Tipo_Intervención", "ddo_status": "Licitación_DDO",
            "gc_status": "Licitación_GC", "permit_status": "Status_Permiso",
            "bc_number": "BC_Nro",
        }
        lower_to_canonical.update(en_aliases)
        rename_map: dict[str, str] = {}
        for col_name in df.columns:
            canonical = lower_to_canonical.get(str(col_name).lower())
            if canonical:
                rename_map[col_name] = canonical

        if rename_map:
            df = df.rename(columns=rename_map)

        return df
