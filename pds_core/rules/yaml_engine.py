"""Evaluador de reglas desde YAML (traffic_lights, forecast_rules, risk_thresholds)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from pds_core.utils.dates import add_days, next_business_day, parse_date

PRIORITY = ["BLACK", "RED", "ORANGE", "YELLOW", "GREEN", "WHITE"]
CHAIN = [
    ("H1", "H2", "H1_to_H2"),
    ("H2", "H3", "H2_to_H3"),
    ("H3", "H4", "H3_to_H4"),
    ("H4", "H5", "H4_to_H5"),
    ("H5", "H6", "H5_to_H6"),
    ("H6", "H7", "H6_to_H7"),
    ("H7", "H8", "H7_to_H8"),
    ("H8", "H9", "H8_to_H9"),
    ("H9", "H10", "H9_to_H10"),
    ("H10", "H11", "H10_to_H11"),
]
IMMUTABLE = {"H6", "H11"}
CANCEL = {"CANCELADO", "NO REQUIERE", "CANCELLED", "N/A"}
AWARDED = {"ADJUDICADO", "ADJUDICADA", "AWARDED", "ADJUDIC"}


def _v(row: dict, *names: str, default=None):
    for n in names:
        if n in row and row[n] is not None and str(row[n]).strip() not in ("", "nan", "None"):
            return row[n]
    return default


def _txt(v) -> str:
    return str(v or "").upper()


def eval_axis(row: dict, axis_key: str, tl: dict) -> tuple[str, str]:
    axes = tl.get("axes", {})
    axis = axes.get(axis_key, {})
    rules = axis.get("rules", {})
    icons = tl.get("icons", {})
    today = date.today()

    if axis_key == "procurement_ddo":
        status = _txt(_v(row, "Licitación_DDO", "DDO_Status"))
        h4 = parse_date(_v(row, "H4", "Fecha_Adj_DDO"))
        if any(k in status for k in CANCEL):
            return "BLACK", rules.get("BLACK", {}).get("reason_es", "DDO cancelado")
        if any(k in status for k in AWARDED):
            return "GREEN", rules.get("GREEN", {}).get("reason_es", "DDO adjudicado")
        if not status and not h4:
            return "WHITE", rules.get("WHITE", {}).get("reason_es", "DDO no iniciado")
        if h4 and h4 < today and not any(k in status for k in AWARDED):
            return "RED", rules.get("RED", {}).get("reason_es", "DDO vencido")
        return "YELLOW", rules.get("YELLOW", {}).get("reason_es", "DDO en proceso")

    if axis_key == "procurement_gc":
        status = _txt(_v(row, "Licitación_GC", "GC_Status"))
        h4 = parse_date(_v(row, "H4", "Fecha_Adj_GC"))
        if any(k in status for k in CANCEL):
            return "BLACK", rules.get("BLACK", {}).get("reason_es", "GC cancelado")
        if any(k in status for k in AWARDED):
            return "GREEN", rules.get("GREEN", {}).get("reason_es", "GC adjudicado")
        if not status and not h4:
            return "WHITE", rules.get("WHITE", {}).get("reason_es", "GC no iniciado")
        if h4 and h4 < today and not any(k in status for k in AWARDED):
            return "RED", rules.get("RED", {}).get("reason_es", "GC vencido")
        return "YELLOW", rules.get("YELLOW", {}).get("reason_es", "GC en proceso")

    if axis_key == "procurement_transport":
        status = _txt(_v(row, "Licitación_Transportista", "Transportista", "Transport_Status"))
        h11 = parse_date(_v(row, "H11"))
        critical_days = int(axis.get("critical_days_to_h11", 14))
        if not status or status == "TBD":
            return "WHITE", rules.get("WHITE", {}).get("reason_es", "Transporte por definir")
        if any(k in status for k in CANCEL) or "MOVIMIENTO DE LATAS" in status or "MOVIMIENTO" in status:
            return "BLACK", rules.get("BLACK", {}).get("reason_es", "Transporte NO REQUIERE")
        if any(k in status for k in AWARDED):
            return "GREEN", rules.get("GREEN", {}).get("reason_es", "Transportista adjudicado")
        if h11 and not any(k in status for k in AWARDED):
            days_to_h11 = (h11 - today).days
            if ("A COTIZAR" in status or "COTIZAR" in status) and 1 <= days_to_h11 <= critical_days:
                reason = rules.get("RED", {}).get("reason_es", "Transporte sin adjudicar; H11 proximo")
                return "RED", f"{reason} ({days_to_h11}d)"
        if "EN PROCESO" in status:
            return "YELLOW", rules.get("YELLOW", {}).get("reason_es", "Licitacion transportista en proceso")
        if "A COTIZAR" in status or "COTIZAR" in status:
            return "ORANGE", rules.get("ORANGE", {}).get("reason_es", "A la espera de cotizaciones")
        if "POR INICIAR" in status:
            return "WHITE", rules.get("WHITE", {}).get("reason_es", "Transporte por iniciar")
        return "YELLOW", rules.get("YELLOW", {}).get("reason_es", "Transporte en seguimiento")

    if axis_key == "permits":
        status = _txt(_v(row, "Status_Permiso", "PERMIT_Status"))
        h9 = parse_date(_v(row, "H9"))
        h10 = parse_date(_v(row, "H10"))
        if any(k in status for k in CANCEL):
            return "BLACK", rules.get("BLACK", {}).get("reason_es", "Permiso no requerido")
        if h10 or "OBTEN" in status or "APROB" in status:
            return "GREEN", rules.get("GREEN", {}).get("reason_es", "Permiso aprobado")
        if not h9:
            return "WHITE", rules.get("WHITE", {}).get("reason_es", "Permiso no solicitado")
        pending = (today - h9).days if h9 else 0
        if pending > 60:
            return "RED", rules.get("RED", {}).get("reason_es", f"Permiso +{pending}d")
        return "YELLOW", rules.get("YELLOW", {}).get("reason_es", "Permiso en tramite")

    if axis_key == "finance":
        th = axis.get("thresholds", {})
        green_max = th.get("green_max", 70)
        yellow_max = th.get("yellow_max", 85)
        bc = _v(row, "BC_Nro", "BC_Number")
        pct = float(_v(row, "Pct_Consumed", default=0) or 0)
        if not bc:
            return "WHITE", rules.get("WHITE", {}).get("reason_es", "Sin BC")
        if pct <= green_max:
            return "GREEN", rules.get("GREEN", {}).get("reason_es", f"Consumo {pct:.1f}%")
        if pct <= yellow_max:
            return "YELLOW", rules.get("YELLOW", {}).get("reason_es", f"Consumo {pct:.1f}%")
        return "RED", rules.get("RED", {}).get("reason_es", f"Consumo critico {pct:.1f}%")

    if axis_key == "construction_start":
        h6 = parse_date(_v(row, "H6"))
        if h6 and h6 <= today:
            return "GREEN", rules.get("GREEN", {}).get("reason_es", "Obra iniciada")
        if not h6:
            return "WHITE", rules.get("WHITE", {}).get("reason_es", "Obra no programada")
        if h6 < today - timedelta(days=30):
            return "RED", rules.get("RED", {}).get("reason_es", "Inicio obra vencido")
        return "YELLOW", rules.get("YELLOW", {}).get("reason_es", "Obra pendiente")

    return "WHITE", ""


def worst_state(states: list[str]) -> str:
    order = {s: i for i, s in enumerate(PRIORITY)}
    valid = [s for s in states if s in order]
    return min(valid, key=lambda s: order[s]) if valid else "WHITE"


def build_semaforos_row(row: dict, tl: dict) -> dict:
    axes = [
        ("procurement_ddo", "DDO"),
        ("procurement_gc", "GC"),
        ("procurement_transport", "TRANSPORT"),
        ("permits", "PERMITS"),
        ("finance", "FINANCE"),
        ("construction_start", "CONSTRUCTION"),
    ]
    icons = tl.get("icons", {})
    out = {"Project_ID": row.get("Project_ID")}
    states = []
    for key, prefix in axes:
        st, reason = eval_axis(row, key, tl)
        states.append(st)
        out[f"{prefix}_State"] = st
        out[f"{prefix}_Icon"] = icons.get(st, st)
        out[f"{prefix}_Reason"] = reason
    out["Estado_Global"] = worst_state(states)
    return out


def _dur(fr: dict, key: str, tipo: str) -> int:
    ov = fr.get("overrides_by_intervention_type", {}).get(tipo, {})
    if key in ov:
        return int(ov[key])
    return int(fr.get("default_durations", {}).get(key, 21))


def fill_forecast(row: dict, fr: dict) -> dict:
    immutable = set(fr.get("immutable_milestones", ["H6", "H11"]))
    tipo = str(_v(row, "Tipo_Intervención", "Intervention_Type", default="") or "").upper()
    result: dict[str, Any] = {"Project_ID": row.get("Project_ID")}

    for h in [f"H{i}" for i in range(1, 12)]:
        parsed = parse_date(row.get(h))
        result[h] = parsed if parsed else None

    if not result.get("H1") and "H1" not in immutable:
        result["H1"] = next_business_day()

    for h_from, h_to, dur_key in CHAIN:
        if result.get(h_to):
            continue
        if h_to in immutable:
            continue
        base = result.get(h_from)
        if not base:
            continue
        days = _dur(fr, dur_key, tipo)
        if dur_key == "H6_to_H7" and tipo:
            days = _dur(fr, "H6_to_H7", tipo)
        result[h_to] = add_days(base, days)

    if result.get("H9") and not result.get("H10"):
        result["H10"] = add_days(result["H9"], 180)

    for h in immutable:
        if not parse_date(row.get(h)):
            result[h] = None
        else:
            result[h] = parse_date(row.get(h))

    return result


def eval_risks(row: dict, rt: dict, sem_row: dict | None = None) -> list[dict]:
    th = rt.get("risk_thresholds", rt)
    warn = float(th.get("budget_warning_pct", 71))
    crit = float(th.get("budget_critical_pct", 86))
    permit_crit = int(th.get("permit_days_pending_critical", 60))
    pid = row.get("Project_ID")
    risks = []
    pct = float(_v(row, "Pct_Consumed", default=0) or 0)
    name = _v(row, "Nombre", "Name", default=pid)

    if pct >= crit:
        risks.append(_risk(pid, "BUDGET_OVERRUN", "CRITICA", f"Consumo {pct:.1f}% >= {crit}%"))
    elif pct >= warn:
        risks.append(_risk(pid, "BUDGET_WARNING", "ALTA", f"Consumo {pct:.1f}% >= {warn}%"))

    h6 = parse_date(_v(row, "H6"))
    if h6 and h6 < date.today():
        risks.append(_risk(pid, "MILESTONE_DELAYED", "ALTA", "H6 vencido"))

    ddo = _txt(_v(row, "Licitación_DDO", "DDO_Status"))
    if h6 and h6 < date.today() and not any(k in ddo for k in AWARDED):
        risks.append(_risk(pid, "PROCUREMENT_PENDING", "MEDIA", "DDO sin adjudicar"))

    h9 = parse_date(_v(row, "H9"))
    if h9 and (date.today() - h9).days > permit_crit:
        risks.append(_risk(pid, "PERMIT_EXPIRED", "ALTA", f"Permiso +{(date.today()-h9).days}d"))

    if sem_row and sem_row.get("Estado_Global") in ("RED", "BLACK"):
        risks.append(_risk(pid, "TRAFFIC_CRITICAL", "ALTA", "Semáforo global crítico"))

    return risks


def alert_from_risk(risk: dict, rt: dict, row: dict) -> dict:
    tpl = rt.get("alert_templates", {}).get(risk["Risk_Type"], {})
    name = _v(row, "Nombre", "Name", default=risk["Project_ID"])
    pct = _v(row, "Pct_Consumed", default=0)
    title = tpl.get("title_es", risk["Risk_Type"]).format(project_name=name, pct=pct, days=0, hito="H6", type="DDO")
    desc = tpl.get("description_es", risk["Description"]).format(project_name=name, pct=pct, days=0, hito="H6", type="DDO")
    return {
        "Project_ID": risk["Project_ID"],
        "Proyecto": name,
        "Alert_Type": risk["Risk_Type"],
        "Alert_Title": title,
        "Alert_Description": desc,
        "Severity": risk["Severity"],
        "Action_Required": tpl.get("action_es", "Revisar con PM"),
        "Detected_Date": date.today().isoformat(),
    }


def _risk(pid, rtype, severity, desc):
    return {"Project_ID": pid, "Risk_Type": rtype, "Severity": severity, "Description": desc}
