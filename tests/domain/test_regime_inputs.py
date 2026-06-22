from core.domain.models import Signal
from core.domain.regime_inputs import assemble_regime_inputs


def test_state_anreicherung_und_subsignal_scores():
    econ = {"gdp_growth": 2.0, "inflation": 2.1, "yield_curve": 0.5}
    state, subs = assemble_regime_inputs(
        economic_state=econ,
        usa_10y3m=0.8,
        eu_spreads={},
        ch_spreads={},
        sub_signal_map={
            "money_supply": Signal.NEUTRAL,
            "credit":       Signal.BULLISH,
            "labor":        Signal.BEARISH,
            "buffett":      Signal.NEUTRAL,
        },
    )
    # Anreicherung: USA 10y-3m landet unter dem Gewichts-Key des Detektors
    assert state["yield_curve_10y3m_usa"] == 0.8
    # Ursprüngliche econ-Keys bleiben erhalten
    assert state["gdp_growth"] == 2.0
    # Signal → ±1.0-Score
    assert subs == {"money_supply": 0.0, "credit": 1.0, "labor": -1.0, "buffett": 0.0}


def test_fehlende_spreads_werden_uebersprungen():
    state, subs = assemble_regime_inputs({"gdp_growth": 1.0}, None, {}, {}, {})
    assert "yield_curve_10y3m_usa" not in state   # None → kein Key
    assert subs == {}


def test_unbekanntes_signal_wird_aus_sub_signals_entfernt():
    """Ein Wert, der kein bekanntes Signal-Enum ist → _sig_score None → Key entfällt."""
    _, subs = assemble_regime_inputs(
        {"gdp_growth": 1.0},
        None,
        {},
        {},
        {"money_supply": "kein_signal"},  # Invalid signal value
    )
    assert "money_supply" not in subs
