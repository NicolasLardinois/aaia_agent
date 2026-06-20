import asyncio
from unittest.mock import MagicMock

from agents.stock_deep_dive.equity.insider_agent import InsiderAgent, _net_value, _signal
from core.domain.models import InsiderSnapshot, Signal


def _make_agent(transactions: list[dict]) -> InsiderAgent:
    provider = MagicMock()
    provider.get_insider_activity.return_value = transactions
    return InsiderAgent(provider, MagicMock())


# ── wertgewichtet statt Anzahl ────────────────────────────────────────────

def test_grosser_kauf_schlaegt_viele_kleine_verkaeufe():
    """1 Conviction-Kauf 1.0M vs. 10 kleine Verkäufe à 10k → netto BULLISH."""
    txns = [{"type": "buy", "value": 1_000_000}] + \
           [{"type": "sell", "value": 10_000} for _ in range(10)]
    result = asyncio.run(_make_agent(txns).run("X"))
    assert result.signal == Signal.BULLISH
    assert result.net_direction == "net_buy"


def test_alte_anzahl_logik_haette_net_sell_gegeben():
    """Gegenprobe: nach Anzahl wären 10 Verkäufe > 1 Kauf → der Bug ist behoben."""
    txns = [{"type": "buy", "value": 1_000_000}] + \
           [{"type": "sell", "value": 10_000} for _ in range(10)]
    assert _net_value(txns) > 0   # wertgewichtet positiv


# ── Käufe stärker gewichtet ───────────────────────────────────────────────

def test_kaeufe_staerker_gewichtet_als_verkaeufe():
    """Gleicher Dollar-Betrag Kauf vs. Verkauf → Netto positiv (Käufe signalstärker)."""
    txns = [{"type": "buy", "value": 100_000}, {"type": "sell", "value": 100_000}]
    assert _net_value(txns) > 0


# ── 10b5-1 / Optionsausübung herausrechnen ────────────────────────────────

def test_10b5_1_verkaeufe_werden_ignoriert():
    """Geplante 10b5-1-Verkäufe zählen nicht; nur der Open-Market-Kauf bleibt."""
    txns = [
        {"type": "buy", "value": 50_000},
        {"type": "sell", "value": 500_000, "plan": "10b5-1"},
    ]
    result = asyncio.run(_make_agent(txns).run("X"))
    assert result.signal == Signal.BULLISH


def test_optionsausuebung_wird_ignoriert():
    txns = [
        {"type": "sell", "value": 80_000, "acquisition_type": "option_exercise"},
        {"type": "buy", "value": 80_000},
    ]
    assert _net_value(txns) > 0


# ── Fallback shares, wenn value fehlt ─────────────────────────────────────

def test_fallback_auf_shares_ohne_value():
    txns = [{"type": "buy", "shares": 10_000}, {"type": "sell", "shares": 1_000}]
    assert _net_value(txns) > 0


# ── Schwellen-Signal ──────────────────────────────────────────────────────

def test_ausgeglichen_ist_neutral():
    assert _signal(0.0, total_abs=0.0) == Signal.NEUTRAL


def test_leere_liste_neutral():
    result = asyncio.run(_make_agent([]).run("X"))
    assert result.signal == Signal.NEUTRAL


# ── Bug #44: Exception-Guard auf Provider-Response ────────────────────────
# Konsistent zum FundamentalsAgent: weder ein geworfener Fehler noch eine als
# Wert zurückgegebene Exception dürfen run() crashen — Rückfall auf neutralen
# Default (AGENTS.md §2: ausgefallene Datenquelle darf die Analyse nie killen).

def test_run_provider_wirft_liefert_neutralen_snapshot():
    """Provider wirft → run() liefert neutralen InsiderSnapshot statt zu crashen."""
    provider = MagicMock()
    provider.get_insider_activity.side_effect = ValueError("API down")
    result = asyncio.run(InsiderAgent(provider, MagicMock()).run("FAIL"))
    assert isinstance(result, InsiderSnapshot)
    assert result.signal == Signal.NEUTRAL
    assert result.net_direction == "neutral"
    assert result.recent_transactions == 0


def test_run_provider_gibt_exception_zurueck_liefert_neutralen_snapshot():
    """Provider gibt eine Exception als Wert zurück → run() crasht nicht."""
    provider = MagicMock()
    provider.get_insider_activity.return_value = ValueError("bad data")
    result = asyncio.run(InsiderAgent(provider, MagicMock()).run("FAIL"))
    assert isinstance(result, InsiderSnapshot)
    assert result.signal == Signal.NEUTRAL
    assert result.recent_transactions == 0
