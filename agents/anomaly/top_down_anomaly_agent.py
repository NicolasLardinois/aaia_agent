from core.domain.models import AnomalyReport, Signal
from core.utils.statistics import Z_THRESHOLD, compute_severity, z_score


def _contradicts(a: Signal, b: Signal) -> bool:
    return (a == Signal.BULLISH and b == Signal.BEARISH) or \
           (a == Signal.BEARISH and b == Signal.BULLISH)


def _dominant_sentiment(cockpit) -> Signal:
    signals = [
        cockpit.sentiment.vix.signal,
        cockpit.sentiment.fear_greed.signal,
        cockpit.sentiment.put_call.signal,
    ]
    bullish = signals.count(Signal.BULLISH)
    bearish = signals.count(Signal.BEARISH)
    if bullish > bearish:
        return Signal.BULLISH
    if bearish > bullish:
        return Signal.BEARISH
    return Signal.NEUTRAL


def _dominant_macro(cockpit) -> Signal:
    signals = [
        cockpit.macro.inflation.usa.signal,
        cockpit.macro.gdp.usa.signal,
    ]
    bullish = signals.count(Signal.BULLISH)
    bearish = signals.count(Signal.BEARISH)
    if bullish > bearish:
        return Signal.BULLISH
    if bearish > bullish:
        return Signal.BEARISH
    return Signal.NEUTRAL


def _dominant_commodity(cockpit) -> Signal:
    signals = [
        cockpit.commodities.energy.signal,
        cockpit.commodities.industrial_metals.signal,
    ]
    bullish = signals.count(Signal.BULLISH)
    bearish = signals.count(Signal.BEARISH)
    if bullish > bearish:
        return Signal.BULLISH
    if bearish > bullish:
        return Signal.BEARISH
    return Signal.NEUTRAL


def _build_summary(statistical: list[str], contradictions: list[str], severity: str) -> str:
    if severity == "none":
        return "Keine Top-Down-Anomalien erkannt."
    lines = [f"Top-Down Anomalie-Bericht (Schwere: {severity.upper()}):"]
    for s in statistical:
        lines.append(f"  [STATISTISCH] {s}")
    for c in contradictions:
        lines.append(f"  [WIDERSPRUCH] {c}")
    return "\n".join(lines)


class TopDownAnomalyAgent:

    def run(self, cockpit, history: list[dict], asset_class: str = "equity") -> AnomalyReport:
        statistical: list[str] = []
        contradictions: list[str] = []

        snapshots = [
            h.get("indicators_snapshot") or {}
            for h in history
            if h.get("indicators_snapshot")
        ]

        def _check(label: str, current, key: str):
            if current is None or len(snapshots) < 5:
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

        _check("VIX", cockpit.sentiment.vix.vix, "vix")
        _check("Fear&Greed", cockpit.sentiment.fear_greed.value, "fear_greed")
        _check("Yield-Spread 10J-2J", cockpit.yield_curve.yield_spreads.usa.spread_10y2y, "yield_spread_10y2y")
        _check("Inflation CPI", cockpit.macro.inflation.usa.cpi, "inflation_cpi_usa")

        if asset_class.lower() in {"equity", "etf", "index"}:
            buffett_countries = getattr(cockpit.macro.buffett_indicator, "countries", {})
            usa_point = buffett_countries.get("USA")
            if usa_point is not None:
                buffett_z = usa_point.z_score
                if buffett_z is not None and abs(buffett_z) > Z_THRESHOLD:
                    ratio_str = f"{usa_point.ratio_pct:.0f}%" if usa_point.ratio_pct is not None else "?"
                    dir_ = "hoch" if buffett_z > 0 else "niedrig"
                    statistical.append(
                        f"Buffett-Indikator USA={ratio_str} ist ungewöhnlich {dir_} "
                        f"gegenüber 10-Jahres-Historie (Z={buffett_z:.1f})"
                    )

        rc = cockpit.macro.regime_confidence
        if rc is not None and rc < 0.30:
            statistical.append(
                f"Regime-Konfidenz={rc:.0%} — Wirtschaftslage schwer einzuordnen"
            )

        macro_sig     = _dominant_macro(cockpit)
        sentiment_sig = _dominant_sentiment(cockpit)
        yield_sig     = cockpit.yield_curve.yield_spreads.usa.signal
        commodity_sig = _dominant_commodity(cockpit)

        area_signals = {
            "Macro":      macro_sig,
            "Sentiment":  sentiment_sig,
            "YieldCurve": yield_sig,
            "Commodity":  commodity_sig,
        }

        pairs = [
            ("Macro", "Sentiment"),
            ("Macro", "YieldCurve"),
            ("Commodity", "Macro"),
        ]
        for a, b in pairs:
            if _contradicts(area_signals[a], area_signals[b]):
                contradictions.append(
                    f"{a}={area_signals[a].value} widerspricht {b}={area_signals[b].value}"
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
