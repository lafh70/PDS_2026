"""Dynamic business rules injected from client configuration."""

from datetime import date, datetime, timedelta
from typing import Any, Union

from pds_core.config.schema.clients_schema import (
    ClienteConfig,
    ForecastConfig,
    SemaforosConfig,
)

DateLike = Union[date, datetime, None]

class SemaforosRules:
    """Traffic-light rules driven by client config."""

    def __init__(self, config: SemaforosConfig):
        self.config = config

    def calcular_ddo(self, licitacion_ddo: str) -> str:
        return self._calcular_eje(
            licitacion_ddo,
            self.config.ddo_negro_keywords,
            self.config.ddo_verde_keywords,
            self.config.ddo_amarillo_keywords,
        )

    def calcular_gc(self, licitacion_gc: str) -> str:
        return self._calcular_eje(
            licitacion_gc,
            self.config.gc_negro_keywords,
            self.config.gc_verde_keywords,
            self.config.gc_amarillo_keywords,
        )

    def calcular_permits(self, status: str) -> str:
        return self._calcular_eje(
            status,
            self.config.permits_negro_keywords,
            self.config.permits_verde_keywords,
            self.config.permits_amarillo_keywords,
        )

    def calcular_finance(self, pct_consumed: float) -> str:
        pct = float(pct_consumed or 0)
        threshold = self.config.finance_alerta_porcentaje
        if pct <= threshold - 15:
            return "GREEN"
        if pct <= threshold:
            return "YELLOW"
        return "RED"

    def _calcular_eje(self, texto: str, negro, verde, amarillo) -> str:
        texto = (texto or "").upper()
        if any(kw.upper() in texto for kw in negro):
            return "BLACK"
        if any(kw.upper() in texto for kw in verde):
            return "GREEN"
        if any(kw.upper() in texto for kw in amarillo):
            return "YELLOW"
        return "WHITE" if not texto.strip() else "YELLOW"


class ForecastRules:
    """Forecast rules driven by client config."""

    def __init__(self, config: ForecastConfig):
        self.config = config

    def calcular_h7(
        self, h6: DateLike, tipo_intervencion: str
    ) -> date | None:
        """
        Compute H7 = H6 + duraciones_obras[tipo_intervencion].

        H6 is a real milestone and is never overwritten; this returns the forecast H7.
        """
        if h6 is None or (isinstance(h6, float) and str(h6) == "nan"):
            return None

        if isinstance(h6, datetime):
            base = h6.date()
        elif isinstance(h6, date):
            base = h6
        else:
            parsed = datetime.fromisoformat(str(h6)[:10])
            base = parsed.date()

        tipo = (tipo_intervencion or "").upper().strip()
        duracion = self.config.duraciones_obras.get(tipo, 90)
        return base + timedelta(days=duracion)


class RulesManager:
    """Injects dynamic rules from ClienteConfig + optional YAML bundle."""

    def __init__(self, client_config: ClienteConfig, yaml_bundle: dict[str, Any] | None = None):
        self.client_config = client_config
        self.semaforos = client_config.semaforos
        self.forecast = client_config.forecast
        self.yaml = yaml_bundle or {}
        self._semaforos_rules: SemaforosRules | None = None
        self._forecast_rules: ForecastRules | None = None

    @property
    def has_yaml(self) -> bool:
        return bool(self.yaml.get("traffic_lights") or self.yaml.get("forecast_rules"))

    def get_traffic_lights_yaml(self) -> dict:
        return self.yaml.get("traffic_lights", {})

    def get_forecast_rules_yaml(self) -> dict:
        return self.yaml.get("forecast_rules", {})

    def get_risk_thresholds_yaml(self) -> dict:
        return self.yaml.get("risk_thresholds", {})

    def get_portfolio_filters(self) -> dict:
        return self.yaml.get("portfolio_filters", {})
    def get_semaforos_rules(self) -> SemaforosRules:
        if self._semaforos_rules is None:
            self._semaforos_rules = SemaforosRules(self.semaforos)
        return self._semaforos_rules

    def get_forecast_rules(self) -> ForecastRules:
        if self._forecast_rules is None:
            self._forecast_rules = ForecastRules(self.forecast)
        return self._forecast_rules

    def inject_semaforos_rules(self) -> SemaforosRules:
        return self.get_semaforos_rules()

    def inject_forecast_rules(self) -> ForecastRules:
        return self.get_forecast_rules()
