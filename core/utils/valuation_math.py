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


# Mindestabstand WACC - terminal_growth zur Vermeidung ökonomischer Instabilität.
# Bei WACC <= g_term + _MIN_SPREAD wird der Nenner auf _MIN_SPREAD geklemmt
# (Gordon-Term explodiert sonst gegen unendlich bzw. wird negativ).
_MIN_WACC_GROWTH_SPREAD = 0.01


def two_stage_dcf(
    fcf0: float,
    growth: float,
    terminal_growth: float,
    wacc: float,
    years: int = 5,
) -> float:
    """2-Stufen-DCF auf Basis des Free Cash Flow.

    Stufe 1: explizite Projektion von FCF über `years` Jahre mit Rate `growth`.
    Stufe 2: Terminal Value via Gordon mit konsistenter `terminal_growth`-Rate.
    Alle Cashflows werden mit `wacc` auf t0 diskontiert.

    Stabilität: der Diskont-/Wachstumsabstand (wacc - terminal_growth) wird auf
    mindestens `_MIN_WACC_GROWTH_SPREAD` geklemmt, um ökonomische Instabilität bei
    wacc ~= terminal_growth abzufangen.
    """
    if years < 1:
        years = 1

    pv_explicit = 0.0
    fcf_t = fcf0
    discounted_last = fcf0
    for t in range(1, years + 1):
        fcf_t = fcf0 * (1.0 + growth) ** t
        discount = (1.0 + wacc) ** t
        pv_explicit += fcf_t / discount
        if t == years:
            discounted_last = discount

    # Terminal Value (Gordon) am Ende von Stufe 1, dann auf t0 diskontiert.
    spread = wacc - terminal_growth
    if spread < _MIN_WACC_GROWTH_SPREAD:
        spread = _MIN_WACC_GROWTH_SPREAD
    terminal_value = fcf_t * (1.0 + terminal_growth) / spread
    pv_terminal = terminal_value / discounted_last

    return pv_explicit + pv_terminal


def earnings_yield(pe: float | None) -> float | None:
    """Earnings Yield = 1/PE. None bei fehlendem oder nicht-positivem PE."""
    if pe is None or pe <= 0:
        return None
    return 1.0 / pe


def equity_risk_premium(ey: float | None, riskfree: float | None) -> float | None:
    """ERP = Earnings Yield - risikofreier Zins (Fed-Modell-Brücke).

    `riskfree` als Dezimalzahl (0.03 = 3 %), konsistent zu `earnings_yield`.
    """
    if ey is None or riskfree is None:
        return None
    return ey - riskfree


def shiller_cape(price: float | None, eps_10y_real: list[float]) -> float | None:
    """Shiller-CAPE = Preis / Mittelwert der 10J inflationsbereinigten EPS.

    None, falls Preis fehlt oder der Mittelwert nicht positiv ist.
    """
    if price is None or not eps_10y_real:
        return None
    mean_eps = statistics.fmean(eps_10y_real)
    if mean_eps <= 0:
        return None
    return price / mean_eps
