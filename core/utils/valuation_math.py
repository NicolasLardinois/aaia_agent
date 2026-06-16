"""Reine Finanzmathematik für Bewertungs-Agenten (DCF, CAPM, ERP, CAPE).

Seiteneffektfrei und provider-unabhängig: alle Funktionen erhalten nur Zahlen
und sind isoliert testbar. Genutzt von equity/index/precious-metals Valuation-Agenten.
"""
import statistics


def capm_wacc(
    rf: float,
    beta: float,
    erp: float,
    cost_of_debt: float,
    tax_rate: float,
    equity_weight: float,
    debt_weight: float,
) -> float:
    """Bottom-up WACC via CAPM.

    cost_of_equity = rf + beta*erp
    after_tax_kd   = cost_of_debt * (1 - tax_rate)
    WACC = w_e*cost_of_equity + w_d*after_tax_kd

    Gewichte werden auf Summe 1.0 normiert (robust gegen w_e+w_d != 1).
    """
    total_w = equity_weight + debt_weight
    if total_w <= 0:
        # Fallback: vollständig eigenfinanziert
        w_e, w_d = 1.0, 0.0
    else:
        w_e = equity_weight / total_w
        w_d = debt_weight / total_w
    cost_of_equity = rf + beta * erp
    after_tax_kd = cost_of_debt * (1.0 - tax_rate)
    return w_e * cost_of_equity + w_d * after_tax_kd
