from datetime import date

from core.domain.run_context import RunContext


def test_memo_startet_leer_und_ist_pro_instanz_isoliert():
    a = RunContext(as_of=date(2026, 7, 1))
    assert a.as_of == date(2026, 7, 1)
    assert a.memo == {}

    a.memo[("ecb", "cpi")] = 2.5
    b = RunContext(as_of=date(2026, 7, 1))
    # Kein geteilter Default-Zustand zwischen zwei Läufen.
    assert b.memo == {}
    assert a.memo[("ecb", "cpi")] == 2.5
