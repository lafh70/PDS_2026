"""Valida ColumnMapper (display → canonical)."""

import pandas as pd

from pds_core.ingestion.normalizers.column_mapper import ColumnMapper
from tests.fixtures.sample_dataframes import SAMPLE_GESTION


def test_map_preserves_canonical_columns():
    df = ColumnMapper.map_display_to_canonical(SAMPLE_GESTION.copy(), "hackathon", "GESTION")
    assert "Project_ID" in df.columns
    assert "Nombre" in df.columns
    assert len(df) == 2


def test_map_case_insensitive():
    df = pd.DataFrame({"project_id": ["HK-9001-2026-01"], "nombre": ["Test"]})
    mapped = ColumnMapper.map_display_to_canonical(df, "hackathon", "GESTION")
    assert "Project_ID" in mapped.columns
    assert "Nombre" in mapped.columns


def test_map_empty_rename_when_already_canonical():
    df = pd.DataFrame({"Project_ID": ["HK-9001-2026-01"]})
    result = ColumnMapper.map_display_to_canonical(df, "hackathon", "GESTION")
    assert list(result.columns) == ["Project_ID"]
