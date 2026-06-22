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


# ---------------------------------------------------------------------------
# Hilfsdaten: Tuning gewinnt (negativer Bias notwendig)
# ---------------------------------------------------------------------------

def _series_tuning_wins(n_per_phase=6):
    """Rezessionsmonate composite 0.25 (bei b=0 risk-on → verpasst), gesund 0.6.
    Ein negativer Bias schiebt 0.25 unter die ~0.15-Grenze → erwischt → F1 steigt OOS."""
    records, usrec = [], {}
    y = 1970
    for block in range(8):
        composite = 0.6 if block % 2 == 0 else 0.25
        rec = 0 if block % 2 == 0 else 1
        for m in range(1, n_per_phase + 1):
            from datetime import date
            d = date(y, m, 1)
            records.append((d, composite, None))
            usrec[f"{y:04d}-{m:02d}"] = rec
        y += 1
    return records, usrec


# ---------------------------------------------------------------------------
# Fix 1: adopt-Pfad getestet (bisher unabgedeckt)
# ---------------------------------------------------------------------------

def test_walk_forward_tuning_gewinnt_oos():
    """Composite 0.25 in Rezessionen → bei b=0 risk-on (verpasst, FN).
    Ein negativer Bias drückt 0.25 unter ~0.15 → risk-off → erwischt → F1 steigt OOS."""
    records, usrec = _series_tuning_wins()
    wf = walk_forward(records, usrec, folds=3, grid=bias_grid())
    assert wf["tuning_wins"] is True
    assert wf["tuned_oos_f1"] > wf["default_oos_f1"]
    # Negativer Bias nötig, um 0.25 unter die ~0.15-Grenze zu schieben
    assert all(f["b"] < 0 for f in wf["per_fold"])


def test_calibrate_urteil_adopt():
    """Wenn Tuning OOS gewinnt und b* ≠ 0, muss das Urteil 'adopt' sein."""
    records, usrec = _series_tuning_wins()
    report = calibrate(records, usrec, sp_price_on=None, folds=3)
    assert report["verdict"] == "adopt"
    assert report["b_star"] < 0.0


# ---------------------------------------------------------------------------
# Fix 2: Guard gegen zu wenige Datenpunkte
# ---------------------------------------------------------------------------

import pytest

def test_walk_forward_zu_wenig_daten_raises():
    """Weniger Punkte als (folds+1)*2 → ValueError statt stiller Fehler."""
    records = [(date(2000, 1, 1), 0.0, None), (date(2000, 2, 1), 0.5, None)]
    with pytest.raises(ValueError):
        walk_forward(records, {"2000-01": 1, "2000-02": 0}, folds=3, grid=bias_grid())


# ---------------------------------------------------------------------------
# Fix 3: A-Check mit Stub-Preisfunktion befüllt
# ---------------------------------------------------------------------------

def test_calibrate_a_check_befuellt_mit_stub():
    """sp_price_on injiziert → a_check darf nicht None sein und enthält b_star-Horizonte."""
    records, usrec = _series_tuning_wins()
    report = calibrate(records, usrec, sp_price_on=lambda d: 100.0 + d.month, folds=3)
    assert report["a_check"] is not None
    assert 6 in report["a_check"]["b_star"]


# ---------------------------------------------------------------------------
# Review PR #33: A-Vorbehalt auf Mehrheit der Horizonte (nicht nur 6M)
# ---------------------------------------------------------------------------

def test_a_warning_mehrheit_der_horizonte():
    """A-Vorbehalt greift, wenn b* auf der MEHRHEIT der Horizonte schlechter ist — nicht nur 6M."""
    from core.utils.regime_calibration import _a_warning
    # schlechter auf 2 von 3 → Warnung
    assert _a_warning({3: 0.5, 6: 0.5, 12: 0.6}, {3: 0.6, 6: 0.6, 12: 0.6}) is True
    # schlechter nur auf 1 von 3 (6M) → KEINE Warnung (früher hätte 6M allein gewarnt)
    assert _a_warning({3: 0.6, 6: 0.5, 12: 0.6}, {3: 0.6, 6: 0.6, 12: 0.6}) is False
    # None-Horizonte werden ignoriert (nur 6M vergleichbar, dort schlechter → Warnung)
    assert _a_warning({3: None, 6: 0.5}, {3: 0.6, 6: 0.6}) is True
