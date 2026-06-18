from core.domain.models import AnomalyReport, Signal
from core.utils.statistics import (
    ROBUST_Z_THRESHOLD, bonferroni_z_threshold, compute_severity, robust_z_score,
)

_MIN_N = 20


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
        lean: dict[str, int] = {"bearish": 0, "bullish": 0}

        is_equity = bottom_up.asset_class in ("equity", "etf")
        snapshots = [
            h.get("indicators_snapshot") or {}
            for h in history
            if h.get("indicators_snapshot")
        ]
        enough_history = len(snapshots) >= _MIN_N

        # Z-Score Checks (nur Equity, nur bei genug History)
        if is_equity and enough_history:
            # Anzahl potenzieller Z-Checks für Multiple-Testing-Korrektur
            n_tests = 3  # KGV + Short-Float + Insider
            threshold = bonferroni_z_threshold(ROBUST_Z_THRESHOLD, n_tests)

            def _check(label: str, current, key: str, high_dir: str, low_dir: str):
                if current is None:
                    return
                vals = [s[key] for s in snapshots if key in s and s[key] is not None]
                if len(vals) < _MIN_N:
                    return
                z = robust_z_score(float(current), [float(v) for v in vals], min_n=_MIN_N)
                if abs(z) > threshold:
                    dir_ = "hoch" if z > 0 else "niedrig"
                    d = high_dir if z > 0 else low_dir
                    if d in lean:
                        lean[d] += 1
                    statistical.append(
                        f"{label}={current:.1f} ist ungewöhnlich {dir_} (robust-Z={z:.1f})"
                    )

            fu  = bottom_up.fundamentals
            si  = bottom_up.short_interest
            ins = bottom_up.insider

            if fu:
                _check("KGV", fu.pe_ratio, "pe_ratio", "bearish", "bullish")
            if si:
                _check("Short-Float", si.short_float_pct, "short_float_pct", "bearish", "neutral")

            # Insider: richtungs- und frequenznormiert statt absoluter ">10"-Schwelle
            if ins and ins.recent_transactions is not None:
                tx_vals = [s["insider_transactions"] for s in snapshots
                           if s.get("insider_transactions") is not None]
                if len(tx_vals) >= _MIN_N:
                    current_tx = float(ins.recent_transactions)
                    z_tx = robust_z_score(current_tx, [float(v) for v in tx_vals], min_n=_MIN_N)
                    # Fallback wenn MAD=0 (konstante History): relatives Vielfaches als Schwelle
                    med_tx = sorted([float(v) for v in tx_vals])[len(tx_vals) // 2]
                    is_anomalous = (z_tx > threshold) or (
                        z_tx == 0.0 and med_tx > 0 and current_tx / med_tx >= 5.0
                    )
                    if is_anomalous:
                        ins_direction = getattr(ins, "net_direction", "") or ""
                        kind = "Kauf-Cluster" if "buy" in ins_direction.lower() else \
                               ("Verkaufs-Cluster" if "sell" in ins_direction.lower() else "Aktivität")
                        if "buy" in ins_direction.lower():
                            lean["bullish"] += 1
                        elif "sell" in ins_direction.lower():
                            lean["bearish"] += 1
                        statistical.append(
                            f"Ungewöhnlich hohe Insider-{kind}: "
                            f"{ins.recent_transactions} Transaktionen (robust-Z={z_tx:.1f}, "
                            f"Richtung={ins_direction or 'n/v'})"
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
                lean["bearish"] += 1

        severity = compute_severity(statistical, contradictions)
        summary  = _build_summary(statistical, contradictions, severity)

        direction = (
            "bearish" if lean["bearish"] > lean["bullish"]
            else "bullish" if lean["bullish"] > lean["bearish"]
            else "neutral"
        )

        return AnomalyReport(
            has_anomalies=bool(statistical or contradictions),
            statistical=statistical,
            contradictions=contradictions,
            severity=severity,
            summary=summary,
            direction=direction,
        )
