from core.domain.models import (
    AnomalyReport, ShortAssessment, ShortAction, PositionState, MarketRegime,
)
from core.domain.short_flags import SHORT_FLAGS
from core.domain.recommendation import _position_size_pct

_RISK_ON  = {MarketRegime.BOOM, MarketRegime.EXPANSION, MarketRegime.RECOVERY}
_RISK_OFF = {MarketRegime.SLOWDOWN, MarketRegime.RECESSION, MarketRegime.DEPRESSION}
_BASE = {"distress": 0.60, "broken_growth": 0.62, "secular_decline": 0.58}
_THRESHOLD = 0.50


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


def _action(pos, confidence) -> ShortAction:
    if pos == PositionState.LONG:
        return ShortAction.NONE
    if pos == PositionState.SHORT:
        return ShortAction.HOLD if confidence >= _THRESHOLD else ShortAction.COVER
    return ShortAction.SHORT if confidence >= _THRESHOLD else ShortAction.NONE


def _mk(asset_class, action, conf, archetypes, flags, regime, squeeze, htb, size=None, stop=None):
    return ShortAssessment(
        asset_class=asset_class, short_action=action, confidence=round(conf, 2),
        archetypes=archetypes, thesis_flags=flags, regime_effect=regime,
        squeeze_risk=squeeze, hard_to_borrow=htb, suggested_size_pct=size, stop_pct=stop)


def derive_short_assessment(bottom_up, cockpit, current_position,
                            top_down_available, bu_anomaly, td_anomaly) -> ShortAssessment:
    asset_class = getattr(bottom_up, "asset_class", "equity")
    regime = _regime_effect(cockpit)
    squeeze, htb, dtc = _squeeze(getattr(bottom_up, "short_interest", None))

    if asset_class != "equity":
        action = ShortAction.HOLD if current_position == PositionState.SHORT else ShortAction.NONE
        return _mk(asset_class, action, 0.10, [],
                   ["Fallback: klassenspezifische Short-Logik folgt"], regime, squeeze, htb)

    if not top_down_available:
        action = ShortAction.HOLD if current_position == PositionState.SHORT else ShortAction.NONE
        return _mk(asset_class, action, 0.10, [],
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
        return _mk(asset_class, _action(current_position, conf), conf, [],
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

    action = _action(current_position, conf)
    size = None
    if action == ShortAction.SHORT:
        size = round(_position_size_pct(conf) * 0.5, 1)
        if squeeze == "high":
            size = round(size * 0.5, 1)
    stop = 10.0 if squeeze == "high" else 15.0
    return _mk(asset_class, action, conf, archetypes, details, regime, squeeze, htb, size, stop)
