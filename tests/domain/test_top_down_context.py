from core.domain.top_down_context import _buffett_fallback_note


def test_swiss_fallback_uses_ch_corridor():
    # CH bei 230% ohne z-Score → mit CH-Korridor NICHT als "teuer" (>135) markiert
    notes = _buffett_fallback_note("CHE", ratio=230.0)
    assert notes == []   # 230 liegt im CH-Normalkorridor


def test_swiss_fallback_flags_extreme():
    notes = _buffett_fallback_note("CHE", ratio=300.0)
    assert notes and "teuer" in notes[0].lower()


def test_german_fallback_uses_de_corridor():
    # DE bei 90% ist für DE bereits erhöht (Korridor ~50–70)
    notes = _buffett_fallback_note("DEU", ratio=90.0)
    assert notes and "erhöht" in notes[0].lower() or "teuer" in notes[0].lower()


def test_us_fallback_unchanged():
    notes = _buffett_fallback_note("USA", ratio=200.0)
    assert notes and "teuer" in notes[0].lower()
