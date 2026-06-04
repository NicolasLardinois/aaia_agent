from core.domain.models import AnomalyReport, Signal
from core.utils.statistics import Z_THRESHOLD, compute_severity, z_score


def _contradicts(a: Signal, b: Signal) -> bool:
    return (a == Signal.BULLISH and b == Signal.BEARISH) or \
           (a == Signal.BEARISH and b == Signal.BULLISH)


def _build_summary(statistical: list[str], contradictions: list[str], severity: str) -> str:
    if severity == "none":
        return "Keine Bottom-Up-Anomalien erkannt."
    lines = [f"Bottom-Up Anomalie-Bericht (Schwere: {severity.upper()}):"]
    for s in statistical:
        lines.append(f"  [STATISTISCH] {s}")
    for c in contradictions:
        lines.append(f"  [WIDERSPRUCH] {c}")
    return "\n".join(lines)


class BottomUpAnomalyAgent:

    def run(self, bottom_up, history: list[dict]) -> AnomalyReport:
        statistical: list[str] = []
        contradictions: list[str] = []

        is_equity = bottom_up.asset_class in ("equity", "etf")
        snapshots = [
            h.get("indicators_snapshot") or {}
            for h in history
            if h.get("indicators_snapshot")
        ]
        enough_history = len(snapshots) >= 5

        # Z-Score Checks (nur Equity, nur bei genug History)
        if is_equity and enough_history:
            def _check(label: str, current, key: str):
                if current is None:
                    return
                vals = [s[key] for s in snapshots if key in s and s[key] is not None]
                if len(vals) < 5:
                    return
                z = z_score(float(current), [float(v) for v in vals])
                if abs(z) > Z_THRESHOLD:
                    dir_ = "hoch" if z > 0 else "niedrig"
                    statistical.append(
                        f"{label}={current:.1f} ist ungewöhnlich {dir_} (Z={z:.1f})"
                    )

            fu  = bottom_up.fundamentals
            si  = bottom_up.short_interest
            ins = bottom_up.insider

            if fu:
                _check("KGV", fu.pe_ratio, "pe_ratio")
            if si:
                _check("Short-Float", si.short_float_pct, "short_float_pct")
            if ins and ins.recent_transactions is not None and ins.recent_transactions > 10:
                statistical.append(
                    f"Ungewöhnlich hohe Insider-Aktivität: {ins.recent_transactions} Transaktionen"
                )

        # Widerspruchs-Checks (nur Equity)
        if is_equity:
            fu_sig  = bottom_up.fundamentals.signal if bottom_up.fundamentals else Signal.NEUTRAL
            val_sig = bottom_up.valuation_range.signal if bottom_up.valuation_range else Signal.NEUTRAL
            ear_sig = bottom_up.earnings_trend.signal if bottom_up.earnings_trend else Signal.NEUTRAL
            qua_sig = bottom_up.quality.signal if bottom_up.quality else Signal.NEUTRAL

            signals = {
                "Fundamentals": fu_sig,
                "Valuation":    val_sig,
                "Earnings":     ear_sig,
                "Quality":      qua_sig,
            }
            bearish_count = sum(1 for s in signals.values() if s == Signal.BEARISH)

            if _contradicts(fu_sig, val_sig):
                contradictions.append(
                    "Fundamentals widerspricht Valuation-Signal"
                )
            if _contradicts(ear_sig, qua_sig):
                contradictions.append(
                    "Earnings widerspricht Quality-Signal"
                )
            if bearish_count >= 3:
                bearish_names = [n for n, s in signals.items() if s == Signal.BEARISH]
                contradictions.append(
                    f"Mehrheit der Bottom-Up-Signale bearish: {', '.join(bearish_names)}"
                )

        severity = compute_severity(statistical, contradictions)
        summary  = _build_summary(statistical, contradictions, severity)

        return AnomalyReport(
            has_anomalies=bool(statistical or contradictions),
            statistical=statistical,
            contradictions=contradictions,
            severity=severity,
            summary=summary,
        )
