# tests/core/utils/test_regime_calibration_wf.py
from datetime import date
from core.domain.models import MarketRegime
from core.utils.regime_calibration import walk_forward, calibrate, bias_grid


def _series(n_per_phase=6):
    """Konstruiert eine wiederkehrende Reihe: 'gesund' (0.5) dann 'krank' (0.0) im Wechsel,
    NBER=1 in den kranken Phasen. Bei Bias 0 trennt die ~0.15-Grenze sauber → Default ist gut."""
    records, usrec = [], {}
    y = 1970
    for block in range(8):
        composite = 0.5 if block % 2 == 0 else 0.0
        rec = 0 if block % 2 == 0 else 1
        for m in range(1, n_per_phase + 1):
            d = date(y, m, 1)
            records.append((d, composite, None))
            usrec[f"{y:04d}-{m:02d}"] = rec
        y += 1
    return records, usrec


def test_walk_forward_trennt_train_test_und_default_gewinnt():
    records, usrec = _series()
    wf = walk_forward(records, usrec, folds=3, grid=bias_grid())
    assert len(wf["per_fold"]) == 3
    # Default trennt hier sauber → Tuning bringt out-of-sample keinen Vorteil
    assert wf["tuning_wins"] is False
    assert wf["default_oos_f1"] >= wf["tuned_oos_f1"] - 1e-9


def test_calibrate_urteil_default_behalten_ohne_a_check():
    records, usrec = _series()
    report = calibrate(records, usrec, sp_price_on=None, folds=3)
    assert report["verdict"] == "keep_default"
    assert report["a_check"] is None
    assert report["default_bias"] == 0.0
