from adapters.api.app_factory import _allowed_origins


def test_default_origins_are_localhost_dev():
    origins = _allowed_origins(None)
    assert "http://localhost:5173" in origins
    assert "http://localhost:3000" in origins


def test_env_origins_replace_dev_origins_in_production():
    # Sind Origins gesetzt (Produktion), gelten NUR diese (getrimmt) -> localhost
    # steht NICHT in der Prod-Allowlist (Hygiene; Review PR #27).
    origins = _allowed_origins("https://dash.onrender.com, https://x.example.com")
    assert origins == ["https://dash.onrender.com", "https://x.example.com"]
    assert "http://localhost:5173" not in origins


def test_blank_env_is_ignored():
    assert _allowed_origins("") == _allowed_origins(None)
    assert _allowed_origins("  ,  ") == _allowed_origins(None)
