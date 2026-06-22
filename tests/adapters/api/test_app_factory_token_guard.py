import pytest
from adapters.api.ws_broadcaster import WebSocketBroadcaster
from adapters.api.run_manager import RunManager
from adapters.api.app_factory import create_app


def _rm():
    return RunManager(lambda bus: None, WebSocketBroadcaster())


def test_render_without_token_fails_closed(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("AAIA_ACCESS_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        create_app(_rm())


def test_render_with_token_does_not_raise(monkeypatch):
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("AAIA_ACCESS_TOKEN", "geheim")
    create_app(_rm())  # kein Raise


def test_local_without_token_only_warns(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("AAIA_ACCESS_TOKEN", raising=False)
    create_app(_rm())  # kein Raise (nur Warn-Log)
