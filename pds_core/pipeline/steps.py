"""All 21 pipeline steps (M1-M21)."""

from __future__ import annotations

import json
import shutil
import time
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

import pandas as pd

from pds_core.pipeline.state import PipelineState
from pds_core.rules.manager import RulesManager
from pds_core.rules.yaml_engine import alert_from_risk, build_semaforos_row, eval_risks, fill_forecast
from pds_core.utils.dates import add_days, date_to_str, days_between, is_overdue, next_business_day, parse_date

STATE_PRIORITY = {"BLACK": 0, "RED": 1, "ORANGE": 2, "YELLOW": 3, "GREEN": 4, "WHITE": 5}
STATE_ICONS = {"BLACK": "BLACK", "RED": "RED", "ORANGE": "ORANGE", "YELLOW": "YELLOW", "GREEN": "GREEN", "WHITE": "WHITE"}


class PipelineStep(ABC):
    def __init__(self, nombre: str, logger=None):
        self.nombre = nombre
        self.logger = logger
        self.duracion = 0.0

    def execute(self, state: PipelineState) -> PipelineState:
        inicio = time.time()
        self._log(f"Ejecutando {self.nombre}...")
        try:
            state = self._procesar(state)
            self._log(f"[OK] {self.nombre} completado")
        except Exception as exc:
            self._log(f"[ERROR] {self.nombre}: {exc}")
            raise
        finally:
            self.duracion = time.time() - inicio
        return state

    @abstractmethod
    def _procesar(self, state: PipelineState) -> PipelineState:
        pass

    def _log(self, msg: str) -> None:
        print(msg)


def _col(df: pd.DataFrame, *names: str) -> str | None:
    aliases = {
        "Nro_Sucursal": "Site_ID",
        "Nombre": "Name",
        "Etapa": "Project_Stage",
        "Tipo_Intervención": "Intervention_Type",
        "Licitación_DDO": "DDO_Status",
        "Licitación_GC": "GC_Status",
        "Status_Permiso": "PERMIT_Status",
        "BC_Nro": "BC_Number",
    }
    expanded = list(names)
    for n in names:
        if n in aliases:
            expanded.append(aliases[n])
        for es, en in aliases.items():
            if n == en:
                expanded.append(es)
    for n in expanded:
        if n in df.columns:
            return n
    return None


def _worst_state(states: list[str]) -> str:
    valid = [s for s in states if s in STATE_PRIORITY]
    if not valid:
        return "WHITE"
    return min(valid, key=lambda s: STATE_PRIORITY[s])


# --- M1: Master Append ---
class Step01MasterAppend(PipelineStep):
    def __init__(self, logger=None):
        super().__init__("M01: Master Append", logger)

    def _procesar(self, state: PipelineState) -> PipelineState:
        df = state.master.drop_duplicates(subset=["Project_ID"], keep="first")
        state.master = df
        state.set_sheet("MASTER", df.copy())
        self._log(f"Master consolidado: {len(df)} proyectos")
        return state


# --- M2-M5: Enrichment (finance + permits metrics on master) ---
class Step02EnrichFinance(PipelineStep):
    def __init__(self, logger=None):
        super().__init__("M02-M04: Enrich Finance/Permits", logger)

    def _procesar(self, state: PipelineState) -> PipelineState:
        df = state.master.copy()
        approved = _col(df, "BC_Preaprobado", "Budget_Approved", "Monto_BC_Final")
        actual = _col(df, "Total_Contabilizado", "Budget_Actual")
        committed = _col(df, "Total_Comprometido", "Budget_Committed")

        if approved:
            denom = pd.to_numeric(df[approved], errors="coerce")
            num = pd.to_numeric(df.get(actual, 0), errors="coerce").fillna(0)
            num += pd.to_numeric(df.get(committed, 0), errors="coerce").fillna(0)
            df["Pct_Consumed"] = ((num / denom.replace(0, pd.NA)) * 100).round(1).fillna(0)

        h8 = _col(df, "H8")
        if h8:
            today = date.today()
            df["PERMIT_Days_Pending"] = df[h8].apply(
                lambda v: days_between(parse_date(v), today) if parse_date(v) else None
            )

        state.master = df
        return state


# --- M6: Build Portfolio ---
class Step06BuildPortfolio(PipelineStep):
    EXCLUDE_STAGES = {"ETAPA 0", "FINALIZADO", "CANCELADO", "ON HOLD", "COMPLETED", "CANCELLED"}

    def __init__(self, rules_manager: RulesManager | None = None, logger=None):
        super().__init__("M06: Build Portfolio", logger)
        self.rules = rules_manager

    def _procesar(self, state: PipelineState) -> PipelineState:
        df = state.master.copy()
        state.set_sheet("MASTER_PORTFOLIO_ALL", df.copy())

        pf = self.rules.get_portfolio_filters() if self.rules else {}
        exclude = {s.upper() for s in pf.get("exclude_stages", list(self.EXCLUDE_STAGES))}

        etapa_col = _col(df, "Etapa", "Project_Stage")
        if etapa_col:
            portfolio = df[~df[etapa_col].astype(str).str.upper().isin(exclude)].copy()
        else:
            portfolio = df.copy()

        state.set_sheet("MASTER_PORTFOLIO", portfolio)
        state.master = portfolio

        for seg_name, seg_cfg in (pf.get("segments") or {}).items():
            filt = seg_cfg.get("filter", {})
            key = filt.get("intervention_type", "")
            tipo_col = _col(portfolio, "Tipo_Intervención", "Intervention_Type")
            if tipo_col and key:
                seg_df = portfolio[portfolio[tipo_col].astype(str).str.upper() == key.upper()]
                sheet = seg_cfg.get("sheet", f"MASTER_{seg_name}")
                state.set_sheet(sheet, seg_df)

        self._log(f"Cartera activa: {len(portfolio)} proyectos")
        return state


# --- M7: Traffic Lights (5 axes) ---
class Step07TrafficLights(PipelineStep):
    def __init__(self, rules_manager: RulesManager | None = None, logger=None):
        super().__init__("M07: Semáforos", logger)
        self.rules = rules_manager

    def _procesar(self, state: PipelineState) -> PipelineState:
        df = state.portfolio.copy()
        tl = self.rules.get_traffic_lights_yaml() if self.rules else {}
        rows = []

        if tl.get("axes"):
            for _, row in df.iterrows():
                r = build_semaforos_row(row.to_dict(), tl)
                r["Updated_Date"] = datetime.now().isoformat()
                rows.append(r)
        else:
            sem = self.rules.get_semaforos_rules() if self.rules else None
            for _, row in df.iterrows():
                pid = row.get("Project_ID")
                ddo_col = _col(df, "Licitación_DDO", "DDO_Status")
                gc_col = _col(df, "Licitación_GC", "GC_Status")
                perm_col = _col(df, "Status_Permiso", "PERMIT_Status")
                ddo = sem.calcular_ddo(str(row.get(ddo_col, ""))) if sem and ddo_col else "WHITE"
                gc = sem.calcular_gc(str(row.get(gc_col, ""))) if sem and gc_col else "WHITE"
                permits = sem.calcular_permits(str(row.get(perm_col, ""))) if sem and perm_col else "WHITE"
                finance = sem.calcular_finance(row.get("Pct_Consumed", 0) or 0) if sem else "WHITE"
                construction = "GREEN" if parse_date(row.get("H6")) else "YELLOW"
                overall = _worst_state([ddo, gc, permits, finance, construction])
                rows.append(
                    {
                        "Project_ID": pid,
                        "DDO_State": ddo, "DDO_Icon": STATE_ICONS.get(ddo, ddo),
                        "GC_State": gc, "GC_Icon": STATE_ICONS.get(gc, gc),
                        "PERMITS_State": permits, "PERMITS_Icon": STATE_ICONS.get(permits, permits),
                        "FINANCE_State": finance, "FINANCE_Icon": STATE_ICONS.get(finance, finance),
                        "CONSTRUCTION_State": construction, "CONSTRUCTION_Icon": STATE_ICONS.get(construction, construction),
                        "Estado_Global": overall, "Updated_Date": datetime.now().isoformat(),
                    }
                )

        state.set_sheet("SEMAFOROS", pd.DataFrame(rows))
        merged = df.merge(state.sheets["SEMAFOROS"], on="Project_ID", how="left")
        state.master = merged
        return state


# --- M8: Milestones (real dates only) ---
class Step08Milestones(PipelineStep):
    HITO_COLS = [f"H{i}" for i in range(1, 12)]

    def __init__(self, logger=None):
        super().__init__("M08: Hitos", logger)

    def _procesar(self, state: PipelineState) -> PipelineState:
        cols = ["Project_ID"] + [c for c in self.HITO_COLS if c in state.portfolio.columns]
        hitos = state.portfolio[cols].copy()
        state.set_sheet("HITOS", hitos)
        return state


# --- M9: Forecast ---
class Step09Forecast(PipelineStep):
    IMMUTABLE = {"H6", "H11"}
    HITO_COLS = [f"H{i}" for i in range(1, 12)]

    def __init__(self, rules_manager: RulesManager | None = None, logger=None):
        super().__init__("M09: Forecast", logger)
        self.rules = rules_manager

    def _procesar(self, state: PipelineState) -> PipelineState:
        hitos = state.sheets.get("HITOS", state.portfolio)
        fr_yaml = self.rules.get_forecast_rules_yaml() if self.rules else {}
        forecast_rules = self.rules.get_forecast_rules() if self.rules else None
        rows = []
        validations = []

        for _, row in hitos.iterrows():
            if fr_yaml:
                result = fill_forecast(row.to_dict(), fr_yaml)
            else:
                result = {}
                for h in self.HITO_COLS:
                    real = row.get(h)
                    parsed = parse_date(real)
                    if parsed:
                        result[h] = parsed
                    elif h in self.IMMUTABLE:
                        result[h] = None
                    elif h == "H7" and forecast_rules:
                        h6 = parse_date(row.get("H6"))
                        tipo = row.get("Tipo_Intervención", "")
                        result[h] = forecast_rules.calcular_h7(h6, str(tipo)) if h6 else None
                    elif h == "H1" and not parsed:
                        result[h] = next_business_day()
                    else:
                        result[h] = None
                result["Project_ID"] = row["Project_ID"]

            if result.get("H6") and result.get("H1"):
                h6d, h1d = parse_date(result["H6"]), parse_date(result["H1"])
                if h6d and h1d and h6d < h1d:
                    validations.append({"Project_ID": row["Project_ID"], "warning": "H6 anterior a H1"})
            if "Project_ID" not in result:
                result["Project_ID"] = row["Project_ID"]
            rows.append(result)

        state.set_sheet("FORECAST", pd.DataFrame(rows))
        if validations:
            state.set_sheet("FORECAST_VALIDATION", pd.DataFrame(validations))
        return state


# --- M10: Risk Engine ---
class Step10RiskEngine(PipelineStep):
    def __init__(self, rules_manager: RulesManager | None = None, logger=None):
        super().__init__("M10: Risk Engine", logger)
        self.rules = rules_manager

    def _procesar(self, state: PipelineState) -> PipelineState:
        df = state.master
        sem = state.sheets.get("SEMAFOROS", pd.DataFrame())
        rt = self.rules.get_risk_thresholds_yaml() if self.rules else {}
        risks = []

        for _, row in df.iterrows():
            pid = row.get("Project_ID")
            sem_row = sem[sem["Project_ID"] == pid].iloc[0].to_dict() if not sem.empty and pid in sem["Project_ID"].values else None
            if rt:
                risks.extend(eval_risks(row.to_dict(), rt, sem_row))
            else:
                cfg = self.rules.semaforos if self.rules else None
                crit_pct = cfg.finance_alerta_porcentaje if cfg else 85
                warn_pct = max(crit_pct - 10, 70)
                pct = float(row.get("Pct_Consumed", 0) or 0)
                if pct >= crit_pct:
                    risks.append(self._risk(pid, "BUDGET_OVERRUN", "CRITICA", f"Consumo {pct}%"))
                elif pct >= warn_pct:
                    risks.append(self._risk(pid, "BUDGET_WARNING", "ALTA", f"Consumo {pct}%"))
                if is_overdue(row.get("H6")):
                    risks.append(self._risk(pid, "MILESTONE_DELAYED", "ALTA", "H6 vencido"))
                if sem_row and sem_row.get("Estado_Global") in ("RED", "BLACK"):
                    risks.append(self._risk(pid, "TRAFFIC_CRITICAL", "ALTA", "Semáforo crítico"))

        state.set_sheet("RIESGOS", pd.DataFrame(risks) if risks else pd.DataFrame(
            columns=["Project_ID", "Risk_Type", "Severity", "Description"]
        ))
        return state

    @staticmethod
    def _risk(pid, rtype, severity, desc):
        return {"Project_ID": pid, "Risk_Type": rtype, "Severity": severity, "Description": desc}


# --- M11: Alerts ---
class Step11Alerts(PipelineStep):
    def __init__(self, rules_manager: RulesManager | None = None, logger=None):
        super().__init__("M11: Alertas", logger)
        self.rules = rules_manager

    def _procesar(self, state: PipelineState) -> PipelineState:
        riesgos = state.sheets.get("RIESGOS", pd.DataFrame())
        if riesgos.empty:
            for name in ("ALERTAS_TODAS", "ALERTAS_CRITICAS", "ALERTAS_ALTAS"):
                state.set_sheet(name, pd.DataFrame())
            return state

        portfolio = state.portfolio.set_index("Project_ID")
        rt = self.rules.get_risk_thresholds_yaml() if self.rules else {}
        alerts = []
        for _, r in riesgos.iterrows():
            pid = r["Project_ID"]
            row = portfolio.loc[pid].to_dict() if pid in portfolio.index else {"Project_ID": pid}
            if rt.get("alert_templates"):
                alerts.append(alert_from_risk(r.to_dict(), rt, row))
            else:
                name = row.get("Nombre", row.get("Name", pid))
                alerts.append(
                    {
                        "Project_ID": pid, "Proyecto": name,
                        "Alert_Type": r["Risk_Type"], "Alert_Title": f"{r['Risk_Type']}: {name}",
                        "Alert_Description": r["Description"], "Severity": r["Severity"],
                        "Detected_Date": date.today().isoformat(), "Action_Required": "Revisar con PM",
                    }
                )

        df_alerts = pd.DataFrame(alerts)
        state.set_sheet("ALERTAS_TODAS", df_alerts)
        state.set_sheet("ALERTAS_CRITICAS", df_alerts[df_alerts["Severity"] == "CRITICA"])
        state.set_sheet("ALERTAS_ALTAS", df_alerts[df_alerts["Severity"] == "ALTA"])
        return state


# --- M12: KPI ---
class Step12Kpi(PipelineStep):
    def __init__(self, logger=None):
        super().__init__("M12: KPI", logger)

    def _procesar(self, state: PipelineState) -> PipelineState:
        df = state.portfolio
        sem = state.sheets.get("SEMAFOROS", pd.DataFrame())
        riesgos = state.sheets.get("RIESGOS", pd.DataFrame())

        total = len(df)
        verde = len(sem[sem["Estado_Global"] == "GREEN"]) if not sem.empty else 0
        crit = len(riesgos[riesgos["Severity"] == "CRITICA"]) if not riesgos.empty else 0

        kpi_rows = [
            {"Metric": "Total_Proyectos_Activos", "Value": total},
            {"Metric": "Pct_Verde_Global", "Value": round(100 * verde / total, 1) if total else 0},
            {"Metric": "Riesgos_Criticos", "Value": crit},
        ]

        etapa_col = _col(df, "Etapa", "Project_Stage")
        if etapa_col:
            for etapa, cnt in df[etapa_col].value_counts().items():
                kpi_rows.append({"Metric": f"Etapa_{etapa}", "Value": int(cnt)})

        state.set_sheet("KPI_PORTFOLIO", pd.DataFrame(kpi_rows))

        scorecard = pd.DataFrame(
            [
                {"Indicador": "Portafolio activo", "Valor": total, "Estado": "OK"},
                {"Indicador": "% en verde", "Valor": kpi_rows[1]["Value"], "Estado": "OK" if verde else "ATENCION"},
                {"Indicador": "Alertas críticas", "Valor": crit, "Estado": "CRITICO" if crit else "OK"},
            ]
        )
        state.set_sheet("SCORECARD_COMITE", scorecard)
        return state


# --- M13: Dashboard ---
class Step13Dashboard(PipelineStep):
    def __init__(self, logger=None):
        super().__init__("M13: Dashboard", logger)

    def _procesar(self, state: PipelineState) -> PipelineState:
        kpi = state.sheets.get("KPI_PORTFOLIO", pd.DataFrame())
        sem = state.sheets.get("SEMAFOROS", pd.DataFrame())
        df = state.portfolio

        dashboard = kpi.copy()
        if not sem.empty:
            for col in ("DDO_State", "GC_State", "FINANCE_State", "Estado_Global"):
                if col in sem.columns:
                    for val, cnt in sem[col].value_counts().items():
                        dashboard = pd.concat(
                            [dashboard, pd.DataFrame([{"Metric": f"{col}_{val}", "Value": int(cnt)}])],
                            ignore_index=True,
                        )

        graficos = df.copy()
        if "Estado_Global" in df.columns:
            graficos = sem[["Project_ID", "Estado_Global"]].merge(df, on="Project_ID", how="left")

        state.set_sheet("DASHBOARD", dashboard)
        state.set_sheet("DATOS_GRAFICOS", graficos)
        return state


# --- M14: Gantt ---
class Step14Gantt(PipelineStep):
    HITO_COLS = [f"H{i}" for i in range(1, 12)]

    def __init__(self, logger=None):
        super().__init__("M14: Gantt", logger)

    def _procesar(self, state: PipelineState) -> PipelineState:
        hitos = state.sheets.get("HITOS", pd.DataFrame())
        forecast = state.sheets.get("FORECAST", pd.DataFrame())
        name_col = _col(state.portfolio, "Nombre", "Name")

        def _gantt(source: pd.DataFrame) -> pd.DataFrame:
            cols = ["Project_ID"] + [
                c for c in ([name_col] if name_col and name_col in source.columns else [])
            ] + [c for c in self.HITO_COLS if c in source.columns]
            g = source[cols].copy()
            h6 = _col(g, "H6")
            if h6:
                g = g.sort_values(h6, na_position="last")
            return g

        state.set_sheet("GANTT_HITOS", _gantt(hitos))
        state.set_sheet("GANTT_FORECAST", _gantt(forecast))
        return state


# --- M15: Project Card ---
class Step15ProjectCard(PipelineStep):
    def __init__(self, logger=None):
        super().__init__("M15: Tarjeta Proyecto", logger)

    def _procesar(self, state: PipelineState) -> PipelineState:
        rows = []
        sem = state.sheets.get("SEMAFOROS", pd.DataFrame())
        riesgos = state.sheets.get("RIESGOS", pd.DataFrame())
        forecast = state.sheets.get("FORECAST", pd.DataFrame())

        for _, row in state.portfolio.iterrows():
            pid = row["Project_ID"]
            s = sem[sem["Project_ID"] == pid].iloc[0].to_dict() if not sem.empty and pid in sem["Project_ID"].values else {}
            r = riesgos[riesgos["Project_ID"] == pid]["Description"].tolist() if not riesgos.empty else []
            f = forecast[forecast["Project_ID"] == pid].iloc[0].to_dict() if not forecast.empty and pid in forecast["Project_ID"].values else {}

            rows.append(
                {
                    "Project_ID": pid,
                    "Nombre": row.get("Nombre", row.get("Name", "")),
                    "PM": row.get("PM", ""),
                    "Etapa": row.get("Etapa", ""),
                    "Tipo": row.get("Tipo_Intervención", ""),
                    "Estado_Global": s.get("Estado_Global", ""),
                    "Pct_Consumed": row.get("Pct_Consumed", ""),
                    "H6_Real": row.get("H6", ""),
                    "H7_Forecast": f.get("H7", ""),
                    "Riesgos_Activos": "; ".join(r),
                    "Resumen": f"Semáforo {s.get('Estado_Global', 'N/A')} | Riesgos: {len(r)}",
                }
            )

        state.set_sheet("TARJETA_PROYECTO", pd.DataFrame(rows))
        return state


def build_all_steps(rules_manager: RulesManager | None) -> list[PipelineStep]:
    """Return ordered list of all 21 pipeline steps."""
    return [
        Step01MasterAppend(),
        Step02EnrichFinance(),
        Step06BuildPortfolio(rules_manager=rules_manager),
        Step07TrafficLights(rules_manager=rules_manager),
        Step08Milestones(),
        Step09Forecast(rules_manager=rules_manager),
        Step10RiskEngine(rules_manager=rules_manager),
        Step11Alerts(rules_manager=rules_manager),
        Step12Kpi(),
        Step13Dashboard(),
        Step14Gantt(),
        Step15ProjectCard(),
    ]
