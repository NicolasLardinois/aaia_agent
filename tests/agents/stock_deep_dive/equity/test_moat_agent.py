from agents.stock_deep_dive.equity.moat_agent import _overall, _signal
from core.domain.models import Signal, MoatScore


def _scores(**kw) -> list[MoatScore]:
    base = {"ia": 0, "sc": 0, "ne": 0, "ca": 0, "es": 0}
    base.update(kw)
    return [MoatScore(score=v, evidence="") for v in base.values()]


# ── Maximum-/Schwellen-pro-Kategorie ──────────────────────────────────────

def test_eine_dominante_quelle_begruendet_wide():
    """Ein einzelner sehr starker Netzwerkeffekt (2) → 'wide', auch wenn Rest 0."""
    assert _overall(_scores(ne=2)) == "wide"


def test_zwei_starke_quellen_sind_wide():
    assert _overall(_scores(ne=2, sc=2)) == "wide"


def test_eine_schwache_quelle_ist_narrow():
    """Genau eine Kategorie mit Score 1 → 'narrow'."""
    assert _overall(_scores(sc=1)) == "narrow"


def test_keine_quelle_ist_none():
    assert _overall(_scores()) == "none"


def test_alte_summenlogik_haette_narrow_gegeben():
    """Gegenprobe: Summe=2 (ein 2er) hätte alt 'none' ergeben; neu ist es 'wide'."""
    scores = _scores(ne=2)
    assert sum(s.score for s in scores) == 2     # alte Summe → wäre 'none'
    assert _overall(scores) == "wide"            # neue Maximum-Logik


# ── Moat von Empfehlung entkoppelt ────────────────────────────────────────

def test_wide_ist_bullish():
    assert _signal("wide") == Signal.BULLISH


def test_none_ist_neutral_nicht_bearish():
    """Fehlender Moat ist Bewertungssache, nicht per se bärisch."""
    assert _signal("none") == Signal.NEUTRAL


def test_narrow_ist_neutral():
    assert _signal("narrow") == Signal.NEUTRAL
