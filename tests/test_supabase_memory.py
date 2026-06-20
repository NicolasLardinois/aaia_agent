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
