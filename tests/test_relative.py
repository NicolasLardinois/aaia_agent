import pytest

from core.utils.relative import _winsorize, percentile_rank, zscore_vs_history


def test_percentile_leere_historie_ist_none():
    assert percentile_rank(5.0, []) is None


def test_winsorize_fraction_ab_0_5_wirft_valueerror():
    """Ab fraction>=0.5 ueberlappen die gekappten Tails (lo_idx>=hi_idx) → alle
    Werte kollabieren still auf einen Punkt. Statt dieser stillen Falle: fail-loud,
    weil fraction ein Code-Parameter (Programmierfehler), kein Datenwert ist."""
    history = [1.0, 2.0, 3.0, 4.0, 5.0]
    with pytest.raises(ValueError):
        _winsorize(history, 0.5)
    with pytest.raises(ValueError):
        _winsorize(history, 0.7)


def test_winsorize_knapp_unter_0_5_funktioniert():
    """Die obere gueltige Grenze (knapp < 0.5) kappt weiterhin sauber, kein Crash."""
    history = [1.0, 2.0, 3.0, 4.0, 5.0]
    out = _winsorize(history, 0.49)
    assert len(out) == len(history)
    # Bei n=5, fraction=0.49: lo_idx=int(0.49*4)=1 (→2.0), hi_idx=int(0.51*4)=2 (→3.0)
    assert min(out) == 2.0
    assert max(out) == 3.0


def test_percentile_rank_reicht_valueerror_durch():
    """Eine offensichtliche Fehlnutzung (winsorize>=0.5) bleibt nicht still."""
    with pytest.raises(ValueError):
        percentile_rank(3.0, [1.0, 2.0, 3.0, 4.0], winsorize=0.5)


def test_percentile_median_ist_50():
    # 4 Werte < 5 von 8 → 50.0
    history = [1.0, 2.0, 3.0, 4.0, 6.0, 7.0, 8.0, 9.0]
    assert percentile_rank(5.0, history) == 50.0


def test_percentile_groesser_als_alle_ist_100():
    history = [1.0, 2.0, 3.0, 4.0]
    assert percentile_rank(99.0, history) == 100.0


def test_percentile_kleiner_als_alle_ist_0():
    history = [1.0, 2.0, 3.0, 4.0]
    assert percentile_rank(0.0, history) == 0.0


def test_percentile_winsorisierung_kappt_ausreisser():
    # 10 Werte 1..10 plus ein grober Ausreißer 1000.
    # Ohne Winsorisierung: value=11 liegt über 10 von 11 Werten → 90.909...
    # Mit winsorize=0.1: oberster Wert (1000) wird auf das 90%-Quantil
    # gekappt; value=11 liegt dann über ALLE 11 (gekappten) Werte → 100.0.
    history = [float(i) for i in range(1, 11)] + [1000.0]
    ohne = percentile_rank(11.0, history, winsorize=0.0)
    mit = percentile_rank(11.0, history, winsorize=0.1)
    assert abs(ohne - 100.0 * 10 / 11) < 1e-6
    assert mit == 100.0


def test_zscore_vs_history_robust_default():
    # robust=True (default) → identisch zu robust_z_score
    from core.utils.statistics import robust_z_score
    history = [float(i) for i in range(1, 10)]
    assert zscore_vs_history(11.0, history, min_n=9) == robust_z_score(11.0, history, min_n=9)


def test_zscore_vs_history_klassisch():
    # robust=False → identisch zu z_score
    from core.utils.statistics import z_score
    history = [1.0, 3.0, 5.0]
    assert zscore_vs_history(5.0, history, robust=False) == z_score(5.0, history)
