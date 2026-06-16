import math

from core.utils.statistics import (
    ROBUST_Z_THRESHOLD,
    MIN_SAMPLE_N,
    robust_z_score,
    bonferroni_z_threshold,
)


def _history(n: int, value: float = 10.0) -> list[float]:
    # Konstante Streuung um 10.0 mit MAD > 0 (abwechselnd 9 / 11)
    return [value - 1.0 if i % 2 == 0 else value + 1.0 for i in range(n)]


def test_robust_z_konstanten():
    assert ROBUST_Z_THRESHOLD == 3.5
    assert MIN_SAMPLE_N == 20


def test_robust_z_zu_kurze_historie_ist_null():
    # len(history)=19 < MIN_SAMPLE_N=20 → 0.0
    assert robust_z_score(100.0, _history(19)) == 0.0


def test_robust_z_mad_null_ist_null():
    # Alle Werte identisch → MAD == 0 → 0.0 (kein ZeroDivision)
    assert robust_z_score(50.0, [7.0] * 25) == 0.0


def test_robust_z_normalwert_klein():
    # current == median → Zähler 0 → 0.0
    assert robust_z_score(10.0, _history(25)) == 0.0


def test_robust_z_iglewicz_hoaglin_formel():
    # history = [1..9], median=5, |x-5|=[4,3,2,1,0,1,2,3,4], MAD=median=2
    # current=11 → 0.6745*(11-5)/2 = 0.6745*3 = 2.0235
    history = [float(i) for i in range(1, 10)]
    assert abs(robust_z_score(11.0, history, min_n=9) - 2.0235) < 1e-6


def test_robust_z_mad_robust_gegen_ausreisser():
    # 24 Werte eng um 10 (abwechselnd 9 / 11) + 1 grober Ausreißer 1000.
    # Der MAD-Z des Ausreißers ist sehr groß (> ROBUST_Z_THRESHOLD),
    # während ein klassischer Sample-Z durch denselben Ausreißer in der
    # Varianz "verwässert" und kleiner ausfiele.
    base = _history(24)                      # 12x 9.0, 12x 11.0
    history = base + [1000.0]                # 25 Punkte
    z = robust_z_score(1000.0, history)
    # 25 Werte sortiert: 12x9, 12x11, 1x1000 → median = 11.0
    # |x-11| = 12x2 + 12x0 + 989 → sortiert (25 Werte) median = 2.0 → MAD = 2.0
    # 0.6745*(1000-11)/2.0 = 333.54025
    assert z > ROBUST_Z_THRESHOLD
    assert abs(z - 333.54025) < 1e-2


def test_bonferroni_keine_korrektur_bei_einem_test():
    # n_tests=1 → unveränderte Schwelle (bis auf Rundungsrauschen)
    assert abs(bonferroni_z_threshold(2.5, 1) - 2.5) < 1e-6


def test_bonferroni_strenger_bei_mehr_tests():
    # Mehr Tests → strengere (höhere) Schwelle
    base = 2.5
    assert bonferroni_z_threshold(base, 10) > base


def test_bonferroni_konkreter_wert():
    # base=1.96 → alpha = 2*(1-Phi(1.96)) ≈ 0.05; n=5 → alpha_adj=0.01
    # Phi^-1(1-0.005)=Phi^-1(0.995) ≈ 2.5758
    assert abs(bonferroni_z_threshold(1.96, 5) - 2.5758) < 1e-2
