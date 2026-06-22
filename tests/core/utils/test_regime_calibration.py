from datetime import date
from core.domain.models import MarketRegime
from core.utils.regime_calibration import bias_grid, f1_for_bias, best_bias_on


def test_bias_grid_umfang_und_raender():
    g = bias_grid()
    assert len(g) == 41
    assert g[0] == -0.40 and g[-1] == 0.40
    assert 0.0 in g


def _rec(y, m, composite):
    # Trend None (für diese Tests irrelevant) — Regime hängt nur am (composite + b)
    return (date(y, m, 1), composite, None)


def test_f1_perfekt_bei_passender_grenze():
    # Composite knapp unter 0.15 in Rezessionsmonaten, klar darüber sonst.
    # Bei Bias 0 liegt die Risk-off-Grenze bei ~0.15 → perfekte Trennung → F1 = 1.0.
    records = [_rec(2001, 1, 0.5), _rec(2001, 2, 0.5),
               _rec(2001, 3, 0.0), _rec(2001, 4, 0.0)]   # 0.0 → SLOWDOWN (risk-off)
    usrec = {"2001-01": 0, "2001-02": 0, "2001-03": 1, "2001-04": 1}
    assert f1_for_bias(records, usrec, 0.0) == 1.0


def test_best_bias_findet_optimum_und_bevorzugt_default_bei_gleichstand():
    # Daten, bei denen Bias 0 bereits perfekt trennt → b_star muss 0.0 sein
    # (auch wenn andere b ebenfalls F1=1.0 erreichen — Tie-Break: betragskleinst).
    records = [_rec(2001, 1, 0.5), _rec(2001, 2, 0.5),
               _rec(2001, 3, 0.0), _rec(2001, 4, 0.0)]
    usrec = {"2001-01": 0, "2001-02": 0, "2001-03": 1, "2001-04": 1}
    b_star, f1 = best_bias_on(records, usrec, bias_grid())
    assert f1 == 1.0
    assert b_star == 0.0
