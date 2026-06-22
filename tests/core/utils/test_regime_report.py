from core.utils.regime_eval import build_report_md


def test_build_report_md_enthaelt_kernzahlen():
    market = {3: {"n": 100, "hit_rate": 0.62, "ci_low": 0.52, "ci_high": 0.71,
                  "by_regime": {"Aufschwung": {"n": 40, "hit_rate": 0.70}}}}
    nber = {"tp": 20, "fp": 10, "tn": 60, "fn": 10, "n": 100,
            "precision": 0.667, "recall": 0.667, "mean_lead_months": 1.5,
            "episodes": [{"start": "2001-04", "end": "2001-06"}]}
    md = build_report_md(market, nber, n_judgments=120, window="1960-01..2026-06",
                         quality_counts={"vintage": 30, "revised": 90})
    assert "Hit-Rate" in md
    assert "62" in md                  # 0.62 → 62 %
    assert "Vorlauf" in md
    assert "1960-01..2026-06" in md
