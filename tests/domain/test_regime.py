from core.domain.regime import _score_indicator, INDICATOR_WEIGHTS


def test_deflation_scores_negative():
    # <1% Inflation (Deflation) jetzt negativ statt 0.0
    assert _score_indicator("inflation", 0.3) < 0.0


def test_target_inflation_scores_positive():
    assert _score_indicator("inflation", 2.0) > 0.0


def test_high_inflation_scores_negative():
    assert _score_indicator("inflation", 7.0) < 0.0


def test_weights_sum_to_one():
    assert abs(sum(INDICATOR_WEIGHTS.values()) - 1.0) < 1e-6


def test_detect_mit_injizierter_historie_ignoriert_datei(tmp_path, monkeypatch):
    """history-Parameter: kein Datei-Read/Write, Trend kommt aus der injizierten Reihe."""
    import core.domain.regime as regime_mod
    # Falls die Implementierung doch die Datei anfasst, soll der Test hart scheitern:
    def _boom(*a, **k):
        raise AssertionError("Datei-I/O trotz injizierter history")
    monkeypatch.setattr(regime_mod, "_load_history", _boom)
    monkeypatch.setattr(regime_mod, "_save_history", _boom)

    det = regime_mod.RegimeDetector()
    state = {"gdp_growth": 3.5, "unemployment": 3.5, "inflation": 2.0}
    # steigende Composite-Historie → Aufwärtstrend
    hist = [("2020-01-01", -0.2), ("2020-02-01", 0.0), ("2020-03-01", 0.2)]
    regime, confidence, evidence = det.detect(state, sub_signals=None, history=hist)

    assert regime is not None
    assert 0.0 <= confidence <= 1.0
    assert "gdp_growth" in evidence
