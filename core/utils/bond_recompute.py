from core.domain.models import Signal, RiskAffinity, CreditBand
from core.utils.bond_risk import aggregate_bond_signal


def _sig(v: str | None) -> Signal | None:
    return Signal(v) if v is not None else None


def recompute_bond_signal(blocks: dict, new_affinity: RiskAffinity) -> tuple[Signal, float]:
    """Gesamtsignal aus gespeicherten Bausteinen + neuer Risikoaffinität neu rechnen
    (kein Datenabruf). Bausteine entsprechen dem indicators_snapshot aus save_analysis."""
    band_v = blocks.get("bond_credit_band")
    band = CreditBand(band_v) if band_v is not None else None
    return aggregate_bond_signal(
        _sig(blocks.get("bond_metrics_signal")),
        _sig(blocks.get("bond_duration_signal")),
        _sig(blocks.get("bond_spread_signal")),
        band,
        new_affinity,
    )
