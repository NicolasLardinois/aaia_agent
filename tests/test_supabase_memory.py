from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import MagicMock

from core.domain.models import ShortAction
from adapters.memory.supabase_memory import SupabaseMemory


def _result(short_action):
    """Minimaler DeepDiveResult-Stub für save_analysis (bottom_up=None überspringt den BU-Block)."""
    return SimpleNamespace(
        ticker="XYZ", asset_class="equity", market="USA",
        top_down_context="ctx", alignment="aligned_bearish", dominant_signal="BEARISH",
        recommendation=SimpleNamespace(action=SimpleNamespace(value="NONE")),
        confidence=0.7, xai_explanation="why",
        bottom_up=None, conflict_resolution=None,
        top_down_anomaly=None, bottom_up_anomaly=None,
        short_action=short_action,
    )


def test_save_analysis_persists_short_action(monkeypatch):
    """save_analysis muss die Short-Aktion separat persistieren (Spalte short_action),
    weil die Long-Linse bei Short-Positionen auf NONE deferiert und der echte
    COVER/HOLD-Wert sonst nie in der History landet."""
    cur = MagicMock()

    @contextmanager
    def fake_cursor():
        yield cur

    conn = MagicMock()
    conn.cursor.side_effect = fake_cursor

    @contextmanager
    def fake_connect(self):
        yield conn

    monkeypatch.setattr(SupabaseMemory, "_connect", fake_connect)

    mem = SupabaseMemory.__new__(SupabaseMemory)  # __init__ umgehen (kein SUPABASE_DB_URL nötig)
    mem.save_analysis(_result(ShortAction.COVER))

    sql, params = cur.execute.call_args.args
    assert "short_action" in sql, "INSERT muss die Spalte short_action enthalten"
    assert "COVER" in params, f"short_action-Wert COVER fehlt in den INSERT-Parametern: {params}"


# ---------------------------------------------------------------------------
# Portfolio-Snapshot: Risiko-Kennzahlen als metrics-jsonb persistieren (P2 / F4a-Review)
# ---------------------------------------------------------------------------

def _patched_cursor(monkeypatch, cur):
    @contextmanager
    def fake_cursor():
        yield cur

    conn = MagicMock()
    conn.cursor.side_effect = fake_cursor

    @contextmanager
    def fake_connect(self):
        yield conn

    monkeypatch.setattr(SupabaseMemory, "_connect", fake_connect)
    return SupabaseMemory.__new__(SupabaseMemory)  # __init__ umgehen (kein SUPABASE_DB_URL nötig)


def test_save_portfolio_snapshot_persists_metrics(monkeypatch):
    """Die Risiko-Kennzahlen (net_beta, Vola, Exposure …) müssen als JSON in der
    metrics-Spalte landen — sonst kann 3b sie später nicht aus dem Snapshot lesen."""
    import json
    cur = MagicMock()
    mem = _patched_cursor(monkeypatch, cur)
    snapshot = {
        "total_positions": 2, "total_value_usd": 1000.0,
        "cluster_risks": [], "alerts": [], "overall_health": "green",
        "net_beta": {"USA": -8000.0}, "net_beta_pct": {"USA": -0.8},
        "net_exposure": 300.0, "gross_exposure": 700.0,
        "portfolio_volatility": 0.0424, "portfolio_max_drawdown": -0.1,
    }
    mem.save_portfolio_snapshot(snapshot)

    sql, params = cur.execute.call_args.args
    assert "metrics" in sql, "INSERT muss die Spalte metrics enthalten"
    metrics_param = [p for p in params if isinstance(p, str) and "net_beta" in p]
    assert metrics_param, f"metrics-JSON mit net_beta fehlt in params: {params}"
    decoded = json.loads(metrics_param[0])
    assert decoded["net_beta"] == {"USA": -8000.0}
    assert decoded["net_exposure"] == 300.0
    assert decoded["portfolio_volatility"] == 0.0424


def test_load_portfolio_snapshot_unpacks_metrics(monkeypatch):
    """Beim Laden wird die metrics-Spalte wieder ins Top-Level entpackt, damit
    Konsumenten die Snapshot-Form sehen (snap["net_beta"], nicht snap["metrics"]["net_beta"])."""
    cur = MagicMock()
    cur.fetchone.return_value = {
        "total_positions": 2, "overall_health": "green",
        "metrics": {"net_beta": {"USA": -8000.0}, "net_exposure": 300.0},
    }
    mem = _patched_cursor(monkeypatch, cur)
    snap = mem.load_latest_portfolio_snapshot()
    assert snap["net_beta"] == {"USA": -8000.0}   # ins Top-Level entpackt
    assert snap["net_exposure"] == 300.0
    assert "metrics" not in snap                  # roher metrics-Container entfernt
