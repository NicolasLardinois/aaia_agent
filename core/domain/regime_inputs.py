"""Reine Montage der Regime-Eingaben (state + sub_signals) aus den Roh-Ergebnissen.
Geteilt von MacroChiefAgent (Live) und dem Regime-Replay — eine Quelle, kein Drift."""
from core.domain.models import Signal


def _sig_score(sig) -> float | None:
    """Signal → ±1.0-Score fürs Regime (None = unbekannt → ignoriert)."""
    if sig == Signal.BULLISH:  return  1.0
    if sig == Signal.BEARISH:  return -1.0
    if sig == Signal.NEUTRAL:  return  0.0
    return None


def assemble_regime_inputs(
    economic_state: dict,
    usa_10y3m: float | None,
    eu_spreads: dict,
    ch_spreads: dict,
    sub_signal_map: dict,
) -> tuple[dict, dict]:
    """Baut (state, sub_signals) exakt wie der bisherige Inline-Code im MacroChiefAgent.

    - economic_state: Ergebnis von get_economic_state() (wird kopiert, nicht mutiert).
    - usa_10y3m: USA-Zinskurve 10y-3m (Gewicht 0,17). None → kein Key.
    - eu_spreads/ch_spreads: dicts mit Keys "10y2y"/"10y3m" (heute meist leer → übersprungen).
    - sub_signal_map: {"money_supply"|"credit"|"labor"|"buffett": Signal}.
    """
    state = dict(economic_state)

    def _add(key, val):
        if isinstance(val, (int, float)):
            state[key] = val

    _add("yield_curve_10y3m_usa", usa_10y3m)
    _add("yield_curve_10y2y_eu",  eu_spreads.get("10y2y"))
    _add("yield_curve_10y3m_eu",  eu_spreads.get("10y3m"))
    _add("yield_curve_10y3m_ch",  ch_spreads.get("10y3m"))

    sub_signals = {}
    for key, sig in sub_signal_map.items():
        score = _sig_score(sig)
        if score is not None:
            sub_signals[key] = score
    return state, sub_signals
