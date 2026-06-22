from adapters.api.app_factory import _allowed_origins


def test_default_origins_are_localhost_dev():
    origins = _allowed_origins(None)
    assert "http://localhost:5173" in origins
    assert "http://localhost:3000" in origins


def test_env_origins_are_appended_and_trimmed():
    origins = _allowed_origins("https://dash.onrender.com, https://x.example.com")
    assert "https://dash.onrender.com" in origins
    assert "https://x.example.com" in origins
    # Dev-Origins bleiben erhalten
    assert "http://localhost:5173" in origins


def test_blank_env_is_ignored():
    assert _allowed_origins("") == _allowed_origins(None)
    assert _allowed_origins("  ,  ") == _allowed_origins(None)
