from datetime import date

from adapters.persistence.json_dated_history import JsonDatedHistory


def test_append_und_values_chronologisch(tmp_path):
    h = JsonDatedHistory(str(tmp_path / "hist.json"))
    # bewusst unsortierte Reihenfolge eingefuegt
    h.append("fed_rate", date(2026, 3, 1), 5.25)
    h.append("fed_rate", date(2026, 1, 1), 4.50)
    h.append("fed_rate", date(2026, 2, 1), 5.00)
    assert h.values("fed_rate") == [
        (date(2026, 1, 1), 4.50),
        (date(2026, 2, 1), 5.00),
        (date(2026, 3, 1), 5.25),
    ]


def test_append_idempotent_pro_tag(tmp_path):
    h = JsonDatedHistory(str(tmp_path / "hist.json"))
    h.append("fed_rate", date(2026, 1, 1), 4.50)
    h.append("fed_rate", date(2026, 1, 1), 4.75)  # gleicher Tag → ueberschreibt
    vals = h.values("fed_rate")
    assert len(vals) == 1
    assert vals == [(date(2026, 1, 1), 4.75)]


def test_unbekannte_serie_ist_leer(tmp_path):
    h = JsonDatedHistory(str(tmp_path / "hist.json"))
    assert h.values("nicht_da") == []
    assert h.latest("nicht_da") is None
    assert h.value_on_or_before("nicht_da", date(2026, 1, 1)) is None


def test_value_on_or_before(tmp_path):
    h = JsonDatedHistory(str(tmp_path / "hist.json"))
    h.append("fed_rate", date(2026, 1, 1), 4.50)
    h.append("fed_rate", date(2026, 3, 1), 5.25)
    # exakter Treffer
    assert h.value_on_or_before("fed_rate", date(2026, 3, 1)) == 5.25
    # zwischen zwei Punkten → vorheriger gilt
    assert h.value_on_or_before("fed_rate", date(2026, 2, 15)) == 4.50
    # vor dem ersten Punkt → None
    assert h.value_on_or_before("fed_rate", date(2025, 12, 31)) is None


def test_latest(tmp_path):
    h = JsonDatedHistory(str(tmp_path / "hist.json"))
    h.append("fed_rate", date(2026, 1, 1), 4.50)
    h.append("fed_rate", date(2026, 3, 1), 5.25)
    assert h.latest("fed_rate") == (date(2026, 3, 1), 5.25)


def test_persistenz_ueber_instanzen(tmp_path):
    path = str(tmp_path / "hist.json")
    h1 = JsonDatedHistory(path)
    h1.append("fed_rate", date(2026, 1, 1), 4.50)
    # neue Instanz liest dieselbe Datei
    h2 = JsonDatedHistory(path)
    assert h2.latest("fed_rate") == (date(2026, 1, 1), 4.50)


def test_mehrere_serien_getrennt(tmp_path):
    h = JsonDatedHistory(str(tmp_path / "hist.json"))
    h.append("fed_rate", date(2026, 1, 1), 4.50)
    h.append("ecb_rate", date(2026, 1, 1), 3.00)
    assert h.latest("fed_rate") == (date(2026, 1, 1), 4.50)
    assert h.latest("ecb_rate") == (date(2026, 1, 1), 3.00)


def test_implementiert_port():
    from core.ports.dated_history import DatedHistoryPort
    assert issubclass(JsonDatedHistory, DatedHistoryPort)
