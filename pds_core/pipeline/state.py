"""Mutable state passed through pipeline steps."""

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class PipelineState:
    """Holds master dataframe and derived sheets for multi-tab Tracker output."""

    master: pd.DataFrame
    sheets: dict[str, pd.DataFrame] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def portfolio(self) -> pd.DataFrame:
        return self.sheets.get("MASTER_PORTFOLIO", self.master)

    def set_sheet(self, name: str, df: pd.DataFrame) -> None:
        self.sheets[name] = df
