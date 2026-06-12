"""Sample DataFrames for unit tests."""

from datetime import datetime

import pandas as pd

SAMPLE_GESTION = pd.DataFrame(
    {
        "Project_ID": ["HK-9001-2026-01", "HK-9002-2026-01"],
        "Nro_Sucursal": ["9001", "9002"],
        "Nombre": ["Proyecto Alpha", "Proyecto Beta"],
        "PM": ["John Smith", "Mary Johnson"],
        "Etapa": ["ETAPA 1", "ETAPA 2"],
        "Tipo_Intervención": ["INTEGRAL", "MEDIA"],
        "H1": [datetime(2026, 1, 15), datetime(2026, 2, 1)],
        "H6": [datetime(2026, 3, 1), None],
        "H11": [datetime(2026, 9, 1), datetime(2026, 10, 1)],
    }
)

SAMPLE_SOURCING = pd.DataFrame(
    {
        "Project_ID": ["HK-9001-2026-01"],
        "Licitación_DDO": ["ADJUDICADO"],
        "Licitación_GC": ["EN PROCESO"],
    }
)

SAMPLE_FINANCE = pd.DataFrame(
    {
        "Project_ID": ["HK-9001-2026-01"],
        "BC_Nro": ["BC-001"],
        "BC_Preaprobado": [100000],
        "Total_Contabilizado": [45000],
        "Total_Comprometido": [20000],
    }
)
