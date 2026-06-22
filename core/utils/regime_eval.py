"""Reine Bewertung von Regime-Urteilen: (A) Markt-Wahrheit (Forward-S&P) und
(B) Wirtschafts-Wahrheit (NBER). Kein I/O — Kursabruf/USREC werden injiziert."""
from datetime import date

from dateutil.relativedelta import relativedelta

from core.domain.models import MarketRegime
from core.utils.backtest import forward_return, is_correct, hit_rate_ci

_BULLISH = {MarketRegime.BOOM, MarketRegime.EXPANSION, MarketRegime.RECOVERY}
RISK_OFF = {MarketRegime.SLOWDOWN, MarketRegime.RECESSION, MarketRegime.DEPRESSION}


def regime_direction(regime: MarketRegime) -> str:
    """Regime → erwartete Marktrichtung. Wachstums-/Erholungsphasen bullish, Schwächephasen bearish."""
    return "bullish" if regime in _BULLISH else "bearish"


def evaluate_market(judgments: list, sp_price_on, horizons_months: tuple = (3, 6, 12)) -> dict:
    """Pro Horizont (Monate): Hit-Rate + Wilson-CI, gesamt und je Regime.
    sp_price_on(d: date) -> float | None liefert den S&P-Schlusskurs am/nach d."""
    report = {}
    for h in horizons_months:
        correct = 0
        total = 0
        by_regime: dict[str, dict] = {}
        for j in judgments:
            as_of = j["as_of"]
            regime = j["regime"]
            entry_px = sp_price_on(as_of)
            fwd_px = sp_price_on(as_of + relativedelta(months=h))
            # Fehlender Forward-Kurs (Fenster-Rand: Datum liegt noch in der Zukunft) → NICHT
            # auswertbar. forward_return(entry, None) liefert -1.0 (Survivorship für delistete
            # Einzelwerte); für einen noch nicht existierenden Index-Kurs wäre das falsch.
            if entry_px is None or fwd_px is None:
                continue
            ret = forward_return(entry_px, fwd_px)
            if ret is None:
                continue
            direction = regime_direction(regime)
            ok = is_correct(direction, ret)
            total += 1
            correct += 1 if ok else 0
            rk = regime.value
            b = by_regime.setdefault(rk, {"n": 0, "correct": 0})
            b["n"] += 1
            b["correct"] += 1 if ok else 0
        lo, hi = hit_rate_ci(correct, total)
        report[h] = {
            "n": total,
            "hit_rate": round(correct / total, 3) if total else None,
            "ci_low": lo,
            "ci_high": hi,
            "by_regime": {
                k: {"n": v["n"], "hit_rate": round(v["correct"] / v["n"], 3) if v["n"] else None}
                for k, v in by_regime.items()
            },
        }
    return report


def _month_key(d: date) -> str:
    """date → Formatstring "YYYY-MM"."""
    return f"{d.year:04d}-{d.month:02d}"


def _nber_episodes(usrec_by_month: dict) -> list:
    """Zusammenhängende Rezessions-Episoden als Liste von (start_key, end_key)."""
    months = sorted(k for k, v in usrec_by_month.items() if v == 1)
    episodes = []
    start = prev = None
    for k in months:
        if start is None:
            start = prev = k
            continue
        y, m = int(prev[:4]), int(prev[5:7])
        nxt = f"{y + (m // 12):04d}-{(m % 12) + 1:02d}"
        if k == nxt:
            prev = k
        else:
            episodes.append((start, prev))
            start = prev = k
    if start is not None:
        episodes.append((start, prev))
    return episodes


def _key_diff_months(a: str, b: str) -> int:
    """a - b in Monaten (a, b im Format YYYY-MM)."""
    ay, am = int(a[:4]), int(a[5:7])
    by, bm = int(b[:4]), int(b[5:7])
    return (ay - by) * 12 + (am - bm)


def evaluate_nber(judgments: list, usrec_by_month: dict) -> dict:
    """Konfusionsmatrix risk-off × NBER + mittlerer Vorlauf je Rezessions-Episode.

    Rückgabe:
    - tp, fp, tn, fn: Konfusionsmatrix (risk-off vs. NBER-Rezession)
    - precision, recall: Metriken (None falls Division by zero)
    - n: Gesamtzahl Beobachtungen
    - mean_lead_months: Durchschn. Monate, die das System VOR Rezessions-Start auf risk-off schaltet
      (positiv = antizipierend, negativ = nacheilend)
    - episodes: Liste der Rezessions-Episoden [{"start": "YYYY-MM", "end": "YYYY-MM"}, ...]
    """
    tp = fp = tn = fn = 0
    risk_off_keys = set()
    for j in judgments:
        key = _month_key(j["as_of"])
        actual = usrec_by_month.get(key)
        if actual is None:
            continue
        called = j["regime"] in RISK_OFF
        if called:
            risk_off_keys.add(key)
        if called and actual == 1:
            tp += 1
        elif called and actual == 0:
            fp += 1
        elif not called and actual == 0:
            tn += 1
        else:
            fn += 1

    # Rezessions-Episoden einmal berechnen (wird für Vorlauf-Fenster und Rückgabe genutzt)
    episodes = _nber_episodes(usrec_by_month)

    # Vorlauf: erster risk-off-Monat im Fenster [-12, +6] um den Episoden-Start
    leads = []
    for start, _end in episodes:
        # risk-off-Monate im Fenster [Start-12, Start+6]: k-start liegt in [-12, +6]
        window = [k for k in risk_off_keys if -12 <= _key_diff_months(k, start) <= 6]
        if window:
            first = min(window)
            leads.append(_key_diff_months(start, first))  # >0 = vor dem Start (antizipierend)

    precision = round(tp / (tp + fp), 3) if (tp + fp) else None
    recall = round(tp / (tp + fn), 3) if (tp + fn) else None
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "n": tp + fp + tn + fn,
        "precision": precision,
        "recall": recall,
        "mean_lead_months": round(sum(leads) / len(leads), 1) if leads else None,
        "episodes": [{"start": s, "end": e} for s, e in episodes],
    }


def build_report_md(market: dict, nber: dict, n_judgments: int, window: str,
                    quality_counts: dict) -> str:
    """Lesbare Markdown-Zusammenfassung des Replay-Reports."""
    lines = [
        "# Regime-Replay-Report",
        "",
        f"- Fenster: **{window}**",
        f"- Urteile gesamt: **{n_judgments}**",
        f"- Datenqualität: " + ", ".join(f"{k}={v}" for k, v in sorted(quality_counts.items())),
        "",
        "## (A) Markt-Wahrheit — Forward-S&P",
        "",
        "| Horizont | N | Hit-Rate | 95 %-CI |",
        "|---|---|---|---|",
    ]
    for h in sorted(market):
        m = market[h]
        hr = f"{m['hit_rate']*100:.0f} %" if m["hit_rate"] is not None else "n/v"
        lines.append(f"| {h} M | {m['n']} | {hr} | {m['ci_low']*100:.0f}–{m['ci_high']*100:.0f} % |")
    lines += ["", "### Je Regime (kürzester Horizont)", ""]  # No f-strings here; plain strings
    if market:
        h0 = sorted(market)[0]
        for rk, v in sorted(market[h0]["by_regime"].items()):
            hr = f"{v['hit_rate']*100:.0f} %" if v["hit_rate"] is not None else "n/v"
            lines.append(f"- **{rk}**: N={v['n']}, Hit-Rate={hr}")
    lead = nber.get("mean_lead_months")
    lead_str = f"{lead:+.1f} Monate" if lead is not None else "n/v"
    lines += [
        "", "## (B) Wirtschafts-Wahrheit — NBER", "",
        f"- Precision (risk-off | NBER): **{(nber['precision'] or 0)*100:.0f} %**",
        f"- Recall: **{(nber['recall'] or 0)*100:.0f} %**",
        f"- Mittlerer **Vorlauf** vor Rezessionsbeginn: **{lead_str}** (positiv = antizipierend)",
        f"- Konfusion: TP={nber['tp']} FP={nber['fp']} TN={nber['tn']} FN={nber['fn']}",
        f"- Rezessions-Episoden im Fenster: {len(nber.get('episodes', []))}",
    ]  # lead_str uses f-string interpolation; keep those f-strings
    return "\n".join(lines)
