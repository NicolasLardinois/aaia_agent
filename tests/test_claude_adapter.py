from unittest.mock import MagicMock

from adapters.llm.claude_adapter import ClaudeAdapter, DEFAULT_TOKENS


def _make_adapter():
    adapter = ClaudeAdapter.__new__(ClaudeAdapter)
    adapter.model = "claude-sonnet-4-6"
    adapter.client = MagicMock()
    return adapter


def _mock_response(text: str):
    block = MagicMock()
    block.text = text
    message = MagicMock()
    message.content = [block]
    return message


# ── Problem A: leere Content-Liste ───────────────────────────────────────────

def test_complete_returns_empty_string_when_content_list_is_empty():
    """Wenn die API keine Content-Blöcke zurückgibt, kein Absturz — leerer String."""
    adapter = _make_adapter()
    message = MagicMock()
    message.content = []
    adapter.client.messages.create.return_value = message

    result = adapter.complete("test prompt")

    assert result == ""


def test_complete_returns_text_on_normal_response():
    """Normaler Fall: Text aus dem ersten Content-Block zurückgeben."""
    adapter = _make_adapter()
    adapter.client.messages.create.return_value = _mock_response("Aktie ist unterbewertet.")

    result = adapter.complete("Analysiere diese Aktie")

    assert result == "Aktie ist unterbewertet."


# ── Problem B: Token-Limit zu niedrig ────────────────────────────────────────

def test_default_tokens_is_at_least_4096():
    """Standard-Token-Limit muss gross genug für vollständige Analysen sein."""
    assert DEFAULT_TOKENS >= 4096
