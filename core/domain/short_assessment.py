from core.domain.models import (
    AnomalyReport, ShortAssessment, ShortAction, PositionState, MarketRegime,
)
from core.domain.short_flags import SHORT_FLAGS
from core.domain.recommendation import _position_size_pct
from core.domain.taxonomy import Underlying, Wrapper, legacy_to_taxonomy

_RISK_ON  = {MarketRegime.BOOM, MarketRegime.EXPANSION, MarketRegime.RECOVERY}
_RISK_OFF = {MarketRegime.SLOWDOWN, MarketRegime.RECESSION, MarketRegime.DEPRESSION}
_BASE = {"distress": 0.60, "broken_growth": 0.62, "secular_decline": 0.58}
_THRESHOLD = 0.50
_SHORT_PLUS_MIN_PROFIT_PCT = 5.0   # SHORT+ nur in einen klaren Gewinner-Short (Kurs ~5 %+ unter Einstand)


def _regime_effect(cockpit) -> str:
    reg = getattr(getattr(cockpit, "macro", None), "regime", None) if cockpit else None
    if reg in _RISK_ON:  return "headwind"
    if reg in _RISK_OFF: return "tailwind"
    return "neutral"


def _squeeze(si):
    dtc = getattr(si, "days_to_cover", None) if si else None
    flt = getattr(si, "short_float_pct", None) if si else None
    high = (dtc is not None and dtc >= 8) or (flt is not None and flt >= 20)
    elevated = dtc is not None and dtc >= 5
    risk = "high" if high else ("elevated" if elevated else "low")
    htb = (flt is not None and flt >= 20) and (dtc is not None and dtc >= 8)
    return risk, htb, dtc


def _anomaly_boost(rep) -> float:
    if rep is None or getattr(rep, "direction", "neutral") != "bearish":
        return 0.0
    return {"high": 0.10, "medium": 0.05}.get(getattr(rep, "severity", "none"), 0.0)


def _action(pos, confidence, pnl_pct=None, squeeze="low") -> ShortAction:
    if pos == PositionState.LONG:
        return ShortAction.NONE
    if pos == PositionState.SHORT:
        if confidence < _THRESHOLD:
            return ShortAction.COVER          # These gebrochen
        # These gilt weiter — nur in einen Gewinner nachlegen, nie in einen Squeeze:
        if pnl_pct is not None and pnl_pct >= _SHORT_PLUS_MIN_PROFIT_PCT and squeeze != "high":
            return ShortAction.SHORT_PLUS
        return ShortAction.HOLD
    return ShortAction.SHORT if confidence >= _THRESHOLD else ShortAction.NONE


def _mk(underlying, wrapper, action, conf, archetypes, flags, regime, squeeze, htb, size=None, stop=None):
    return ShortAssessment(
        underlying=underlying, wrapper=wrapper,
        short_action=action, confidence=round(conf, 2),
        archetypes=archetypes, thesis_flags=flags, regime_effect=regime,
        squeeze_risk=squeeze, hard_to_borrow=htb, suggested_size_pct=size, stop_pct=stop)


def derive_short_assessment(bottom_up, cockpit, current_position,
                            top_down_available, bu_anomaly, td_anomaly,
                            position_pnl_pct=None) -> ShortAssessment:
    # underlying/wrapper direkt lesen (neue Schema); Legacy-Stubs ohne diese Felder
    # werden über legacy_to_taxonomy (verhaltens-erhaltend) auf Underlying/Wrapper gemappt.
    if hasattr(bottom_up, "underlying") and hasattr(bottom_up, "wrapper"):
        underlying = bottom_up.underlying
        wrapper    = bottom_up.wrapper
    else:
        underlying, wrapper = legacy_to_taxonomy(getattr(bottom_up, "asset_class", "equity"))
    regime = _regime_effect(cockpit)
    squeeze, htb, dtc = _squeeze(getattr(bottom_up, "short_interest", None))

    if underlying != Underlying.EQUITY:
        # Phase 3: kurven-/kostengetriebener Futures-Short für Rohstoff/Edelmetall (wrapper=future).
        fs = getattr(bottom_up, "futures_short", None)
        if (underlying in (Underlying.COMMODITY, Underlying.PRECIOUS_METAL)
                and wrapper == Wrapper.FUTURE and fs is not None and fs.available):
            conf = fs.short_confidence
            action = _action(current_position, conf, position_pnl_pct, squeeze)
            dist = "n/v" if fs.floor_distance_pct is None else f"{fs.floor_distance_pct:.2f}"
            flags = [f"carry={fs.carry_state}", f"floor_distance={dist}",
                     "floor_binds" if fs.floor_binds else "floor_room"]
            size = None
            if action == ShortAction.SHORT:
                size = round(_position_size_pct(conf) * 0.5, 1)
            elif action == ShortAction.SHORT_PLUS:
                size = round(_position_size_pct(conf) * 0.25, 1)
            stop = 15.0
            return _mk(underlying, wrapper, action, conf, ["carry_short"], flags,
                       regime, squeeze, htb, size, stop)
        # andere Nicht-Equity (bond; oder commodity/metal ohne Future-Wrapper): bisheriger Fallback.
        action = ShortAction.HOLD if current_position == PositionState.SHORT else ShortAction.NONE
        return _mk(underlying, wrapper, action, 0.10, [],
                   ["Fallback: klassenspezifische Short-Logik folgt"], regime, squeeze, htb)

    if not top_down_available:
        action = ShortAction.HOLD if current_position == PositionState.SHORT else ShortAction.NONE
        return _mk(underlying, wrapper, action, 0.10, [],
                   ["Kein Top-Down — Short nicht bewertbar"], regime, squeeze, htb)

    kern, verst, details, archetypes = [], [], [], []
    for f in SHORT_FLAGS:
        try:
            if f.fires(bottom_up):
                details.append(f.detail(bottom_up))
                if f.kind == "kern":
                    kern.append(f)
                    if f.archetype and f.archetype not in archetypes:
                        archetypes.append(f.archetype)
                else:
                    verst.append(f)
        except (AttributeError, TypeError):
            continue

    if not kern:
        conf = 0.10
        return _mk(underlying, wrapper, _action(current_position, conf), conf, [],
                   details or ["Keine Kern-These"], regime, squeeze, htb)

    bases = [_BASE[f.archetype] for f in kern]
    q = getattr(bottom_up, "quality", None)
    if "distress" in archetypes and q is not None and getattr(q, "altman_z", None) is not None and q.altman_z < 1.0:
        bases.append(0.68)
    conf = max(bases)
    conf += 0.04 * (len(archetypes) - 1)
    conf += sum(f.weight for f in verst)
    if regime == "headwind":  conf -= 0.12
    elif regime == "tailwind": conf += 0.05
    if dtc is not None and dtc >= 8 and htb:
        conf -= 0.10
    conf += _anomaly_boost(bu_anomaly) + _anomaly_boost(td_anomaly)
    # Ohne Katalysator (earnings_collapse) ist 0.70 ein HARTER Deckel — erst NACH
    # allen Regime-/Anomalie-Anpassungen anwenden, damit Rueckenwind ihn nicht durchbricht.
    has_catalyst = any(f.name == "earnings_collapse" for f in kern)
    if not has_catalyst:
        conf = min(conf, 0.70)
    conf = max(0.10, min(1.0, conf))

    action = _action(current_position, conf, position_pnl_pct, squeeze)
    size = None
    if action == ShortAction.SHORT:
        size = round(_position_size_pct(conf) * 0.5, 1)
        if squeeze == "high":
            size = round(size * 0.5, 1)
    elif action == ShortAction.SHORT_PLUS:
        size = round(_position_size_pct(conf) * 0.25, 1)   # konservativer Top-up
    stop = 10.0 if squeeze == "high" else 15.0
    return _mk(underlying, wrapper, action, conf, archetypes, details, regime, squeeze, htb, size, stop)
