"""Reine Kalibrierung der Risk-off-Grenze des Regime-Motors: probiert einen Composite-Bias `b`
gegen die NBER-Wahrheit (Ziel F1), per Walk-Forward (Train/Test getrennt). Kein I/O —
Kursabruf/NBER werden injiziert. Nutzt die Trend-Shift-Invarianz: jedes `b` ist aus den
gespeicherten (composite, trend) je Stichtag nachrechenbar, ohne den Replay neu zu fahren."""
from datetime import date

from core.domain.regime import _regime_from
from core.utils.regime_eval import evaluate_nber


def bias_grid() -> list[float]:
    """1-D-Gitter der Bias-Kandidaten: -0.40 … +0.40 in 0.02-Schritten (41 Werte)."""
    return [round(-0.40 + 0.02 * i, 2) for i in range(41)]


def _confusion_for_bias(records: list[tuple[date, float, float | None]], usrec_by_month: dict, b: float) -> tuple[int, int, int]:
    """Konfusionszähler (tp, fp, fn) für einen Bias `b`: Regime via _regime_from(composite+b, trend),
    abgeglichen gegen NBER über die bestehende evaluate_nber."""
    biased = [{"as_of": d, "regime": _regime_from(c + b, t)} for (d, c, t) in records]
    nb = evaluate_nber(biased, usrec_by_month)
    return nb["tp"], nb["fp"], nb["fn"]


def f1_from_counts(tp: int, fp: int, fn: int) -> float:
    """F1 aus Konfusionszählern; 0.0 wenn nicht definiert (keine risk-off-Calls oder keine Rezession)."""
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    return 2 * p * r / (p + r) if (p + r) else 0.0


def f1_for_bias(records: list[tuple[date, float, float | None]], usrec_by_month: dict, b: float) -> float:
    """F1 (risk-off vs. NBER-Rezession) für einen einzelnen Bias-Wert `b`."""
    tp, fp, fn = _confusion_for_bias(records, usrec_by_month, b)
    return f1_from_counts(tp, fp, fn)


def best_bias_on(records: list[tuple[date, float, float | None]], usrec_by_month: dict, grid: list[float]) -> tuple[float, float]:
    """Bias mit maximalem F1 auf `records`. Tie-Break: betragskleinster Bias (Richtung Default 0)."""
    best_b, best_f1 = 0.0, -1.0
    for b in grid:
        f1 = f1_for_bias(records, usrec_by_month, b)
        if f1 > best_f1 + 1e-12 or (abs(f1 - best_f1) <= 1e-12 and abs(b) < abs(best_b)):
            best_b, best_f1 = b, f1
    return best_b, best_f1


# ---------------------------------------------------------------------------
# Walk-Forward-Validierung + Kalibrierungsurteil
# ---------------------------------------------------------------------------

def _slices(n: int, parts: int) -> list:
    """Zerlegt Index 0..n-1 in `parts` möglichst gleich große, zusammenhängende Slices
    (Indexgrenzen als Tupel). Wird für die Expanding-Window-Aufteilung genutzt."""
    bounds = [round(i * n / parts) for i in range(parts + 1)]
    return [(bounds[i], bounds[i + 1]) for i in range(parts)]


def walk_forward(records: list, usrec_by_month: dict, folds: int, grid: list) -> dict:
    """Expanding-Window: Fold i trainiert auf Slices 0..i-1, testet blind auf Slice i.
    OOS-F1 wird über alle Test-Slices gepoolt (Konfusion aufsummiert) — getuntes b je Fold vs. b=0.

    Rückgabe:
    - tuned_oos_f1: gepoolter OOS-F1 des je-Fold-optimierten Bias
    - default_oos_f1: gepoolter OOS-F1 des Default-Bias b=0
    - tuning_wins: True wenn Tuning den Default out-of-sample um mehr als 1e-9 schlägt
    - per_fold: Liste mit Fold-Detailergebnissen (fold, b, n_test, test_f1, default_test_f1)
    """
    records = sorted(records, key=lambda r: r[0])
    # Guard: zu wenige Punkte → leere Train/Test-Splits → stille Fehler verhindern
    if len(records) < (folds + 1) * 2:
        raise ValueError(
            f"Zu wenige Datenpunkte ({len(records)}) für {folds} Folds — "
            f"mindestens {(folds + 1) * 2} nötig."
        )
    # Slice 0 dient ausschließlich als Trainings-Seed für Fold 1; folds+1 Segmente insgesamt
    slices = _slices(len(records), folds + 1)
    per_fold = []
    # Gepoolte Konfusionszähler über alle Test-Folds
    tp_t = fp_t = fn_t = 0      # getuntes b
    tp_d = fp_d = fn_d = 0      # Default b=0

    for i in range(1, folds + 1):
        # Expanding Train: alles bis Ende des (i-1)-ten Slices
        train = records[: slices[i - 1][1]]
        # Blinder Test: genau Slice i
        test = records[slices[i][0]: slices[i][1]]

        b_fold, _ = best_bias_on(train, usrec_by_month, grid)

        ttp, tfp, tfn = _confusion_for_bias(test, usrec_by_month, b_fold)
        dtp, dfp, dfn = _confusion_for_bias(test, usrec_by_month, 0.0)

        tp_t += ttp; fp_t += tfp; fn_t += tfn
        tp_d += dtp; fp_d += dfp; fn_d += dfn

        per_fold.append({
            "fold": i,
            "b": b_fold,
            "n_test": len(test),
            "test_f1": round(f1_from_counts(ttp, tfp, tfn), 3),
            "default_test_f1": round(f1_from_counts(dtp, dfp, dfn), 3),
        })

    tuned_oos = f1_from_counts(tp_t, fp_t, fn_t)
    default_oos = f1_from_counts(tp_d, fp_d, fn_d)
    return {
        "tuned_oos_f1": round(tuned_oos, 3),
        "default_oos_f1": round(default_oos, 3),
        # Schwelle 1e-9 verhindert Floating-Point-Rauschen als falschen Sieg
        "tuning_wins": tuned_oos > default_oos + 1e-9,
        "per_fold": per_fold,
    }


def _a_hit_rates(records: list, sp_price_on, b: float) -> dict:
    """Markt-Hit-Rate (Evaluator A) je Horizont für einen Bias b.
    sp_price_on(d: date) -> float | None wird injiziert (kein I/O im Modul selbst)."""
    from core.utils.regime_eval import evaluate_market
    judgments = [{"as_of": d, "regime": _regime_from(c + b, t)} for (d, c, t) in records]
    market = evaluate_market(judgments, sp_price_on, horizons_months=(3, 6, 12))
    return {h: market[h]["hit_rate"] for h in market}


def calibrate(records: list, usrec_by_month: dict, sp_price_on=None,
              folds: int = 4, grid: list | None = None) -> dict:
    """Walk-Forward-Urteil + finaler Vorschlag b* (bestes F1 auf voller Historie) + Markt-Härtetest A.

    Verdict-Logik:
    - 'adopt'        → Tuning gewinnt OOS UND b* ≠ 0 (echter Mehrwert gegenüber Default)
    - 'keep_default' → sonst (Default hält stand oder b* = 0 hat keine Wirkung)

    sp_price_on(d: date) -> float | None ist optional. Ohne Übergabe → a_check=None.
    """
    grid = grid or bias_grid()
    wf = walk_forward(records, usrec_by_month, folds, grid)
    b_star, full_f1 = best_bias_on(records, usrec_by_month, grid)
    default_full_f1 = f1_for_bias(records, usrec_by_month, 0.0)

    # Markt-Härtetest A: nur wenn Kursdaten injiziert werden
    a_check = None
    if sp_price_on is not None:
        hr_star = _a_hit_rates(records, sp_price_on, b_star)
        hr_default = _a_hit_rates(records, sp_price_on, 0.0)
        # Warnung wenn b* den Markt zum 6M-Horizont schlechter macht als der Default
        warn = (
            hr_star.get(6) is not None
            and hr_default.get(6) is not None
            and hr_star[6] < hr_default[6]
        )
        a_check = {"b_star": hr_star, "default": hr_default, "warning": warn}

    # Beide Bedingungen müssen erfüllt sein: OOS-Vorteil UND echter Bias-Wert
    adopt = wf["tuning_wins"] and b_star != 0.0
    n_rec = sum(1 for v in usrec_by_month.values() if v == 1)

    return {
        "b_star": b_star,
        "default_bias": 0.0,
        "full_f1_b_star": round(full_f1, 3),
        "full_f1_default": round(default_full_f1, 3),
        "walk_forward": wf,
        "a_check": a_check,
        "verdict": "adopt" if adopt else "keep_default",
        "n_recession_months": n_rec,
        "n_records": len(records),
    }


# ---------------------------------------------------------------------------
# Report-Builder — reine String-Funktion, kein I/O
# ---------------------------------------------------------------------------

def build_calib_report_md(report: dict) -> str:
    """Lesbare Markdown-Zusammenfassung des Kalibrier-Vorschlags."""
    wf = report["walk_forward"]
    adopt = report["verdict"] == "adopt"
    lines = [
        "# Regime-Kalibrierung — Vorschlag (Risk-off-Grenze)",
        "",
        f"- Datenpunkte (Monate): **{report['n_records']}**, davon Rezessionsmonate (NBER): "
        f"**{report['n_recession_months']}**",
        f"- Vorgeschlagener Bias **b\\* = {report['b_star']:+.2f}** "
        f"(Default = {report['default_bias']:+.2f})",
        f"- F1 auf voller Historie: b\\* = {report['full_f1_b_star']:.3f} vs. "
        f"Default {report['full_f1_default']:.3f}",
        "",
        "## Out-of-Sample (Walk-Forward) — der ehrliche Test",
        "",
        f"- **Getuntes b OOS-F1: {wf['tuned_oos_f1']:.3f}** vs. **Default OOS-F1: "
        f"{wf['default_oos_f1']:.3f}**",
        "",
        "| Fold | b (Train) | N Test | Test-F1 (b) | Test-F1 (Default) |",
        "|---|---|---|---|---|",
    ]
    for f in wf["per_fold"]:
        lines.append(f"| {f['fold']} | {f['b']:+.2f} | {f['n_test']} | "
                     f"{f['test_f1']:.3f} | {f['default_test_f1']:.3f} |")

    ac = report.get("a_check")
    if ac is not None:
        lines += ["", "## Markt-Härtetest (A) — Hit-Rate je Horizont", ""]
        for h in sorted(ac["b_star"]):
            s = ac["b_star"][h]; d = ac["default"][h]
            s_str = f"{s*100:.0f} %" if s is not None else "n/v"
            d_str = f"{d*100:.0f} %" if d is not None else "n/v"
            lines.append(f"- {h} M: b\\* {s_str} vs. Default {d_str}")
        if ac.get("warning"):
            lines.append("- ⚠️ **Warnung:** b\\* verbessert NBER, verschlechtert aber den Markt "
                         "(6M) — Übernahme fraglich.")

    lines += ["", "## Urteil", ""]
    if adopt:
        lines.append(f"**Bias b\\* = {report['b_star']:+.2f} übernehmen** — schlägt den Default "
                     f"out-of-sample (OOS-F1 {wf['tuned_oos_f1']:.3f} > {wf['default_oos_f1']:.3f}). "
                     "Übernahme per PR: `_REGIME_BIAS` in `core/domain/regime.py` setzen.")
    else:
        lines.append("**Default behalten — nichts ändern.** Die Hand-Einstellung (Bias 0) ist "
                     "out-of-sample nicht zu schlagen. Das bestätigt die heutige Grenze. "
                     "(keep_default)")
    lines += ["", f"_Hinweis: Mit nur {report['n_recession_months']} Rezessionsmonaten über "
              f"{len(wf['per_fold'])} Folds ist die OOS-Schätzung verrauscht — ein kleiner, über "
              "Folds stabiler Effekt ist glaubwürdiger als ein großer Einzelfund._"]
    return "\n".join(lines)
