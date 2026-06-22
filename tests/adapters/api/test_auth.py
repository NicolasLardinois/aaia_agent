from adapters.api.auth import token_valid


def test_empty_expected_token_disables_auth(monkeypatch):
    monkeypatch.delenv("AAIA_ACCESS_TOKEN", raising=False)
    assert token_valid(None) is True
    assert token_valid("irgendwas") is True


def test_set_token_requires_exact_match(monkeypatch):
    monkeypatch.setenv("AAIA_ACCESS_TOKEN", "geheim")
    assert token_valid("geheim") is True
    assert token_valid("falsch") is False
    assert token_valid(None) is False
    assert token_valid("") is False
