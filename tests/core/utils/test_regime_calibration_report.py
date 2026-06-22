# tests/core/utils/test_regime_calibration_report.py
from core.utils.regime_calibration import build_calib_report_md


def _report(verdict="keep_default", a_check=None):
    return {
        "b_star": 0.0, "default_bias": 0.0,
        "full_f1_b_star": 0.62, "full_f1_default": 0.62,
        "walk_forward": {"tuned_oos_f1": 0.55, "default_oos_f1": 0.58, "tuning_wins": False,
                         "per_fold": [{"fold": 1, "b": -0.04, "n_test": 120,
                                       "test_f1": 0.5, "default_test_f1": 0.56}]},
        "a_check": a_check, "verdict": verdict,
        "n_recession_months": 90, "n_records": 600,
    }


def test_report_keep_default_enthaelt_urteil_und_kennzahlen():
    md = build_calib_report_md(_report())
    assert "Default behalten" in md or "keep_default" in md
    assert "Out-of-Sample" in md
    assert "0.58" in md            # default OOS-F1
    assert "Rezessionsmonate" in md


def test_report_a_warnung_sichtbar():
    md = build_calib_report_md(_report(verdict="adopt", a_check={
        "b_star": {3: 0.6, 6: 0.55, 12: 0.6}, "default": {3: 0.6, 6: 0.62, 12: 0.6},
        "warning": True}))
    assert "Warnung" in md


def test_report_adopt_mit_a_vorbehalt_entschaerft_urteil():
    """adopt UND A-Warnung gleichzeitig → das Urteil benennt den A-Vorbehalt, statt nur 'übernehmen'."""
    report = _report(verdict="adopt", a_check={
        "b_star": {3: 0.5, 6: 0.5, 12: 0.6}, "default": {3: 0.6, 6: 0.6, 12: 0.6},
        "warning": True})
    report["b_star"] = -0.10
    md = build_calib_report_md(report)
    assert "übernehmen" in md
    assert "A-Vorbehalt" in md
