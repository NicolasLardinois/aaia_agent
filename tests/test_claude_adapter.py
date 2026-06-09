from unittest.mock import MagicMock, call, patch

from adapters.llm.claude_adapter import ClaudeAdapter, DEFAULT_TOKENS, MAX_RETRIES


def _make_adapter():
    adapter = ClaudeAdapter.__new__(ClaudeAdapter)
    adapter.model = "claude-sonnet-4-6"
    adapter.client = MagicMock()
    return adapter


def _empty_response():
    message = MagicMock()
    message.content = []
    return message


def _mock_response(text: str):
    block = MagicMock()
    block.text = text
    message = MagicMock()
    message.content = [block]
    return message


# ── Problem A: leere Content-Liste ───────────────────────────────────────────

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


# ── Retry-Mechanismus ────────────────────────────────────────────────────────

def test_retry_constant_exists():
    """MAX_RETRIES muss definiert sein und mindestens 2 betragen."""
    assert MAX_RETRIES >= 2


def test_retries_when_content_is_empty_and_succeeds_on_second_attempt():
    """Erste Antwort leer → retry → zweite Antwort hat Text → Text zurückgeben."""
    adapter = _make_adapter()
    adapter.client.messages.create.side_effect = [
        _empty_response(),
        _mock_response("Burggraben vorhanden."),
    ]

    with patch("time.sleep"):
        result = adapter.complete("Analysiere den Burggraben")

    assert result == "Burggraben vorhanden."
    assert adapter.client.messages.create.call_count == 2


def test_returns_empty_string_after_all_retries_exhausted_with_empty_content():
    """Alle Versuche liefern leere Antwort → leeren String zurückgeben."""
    adapter = _make_adapter()
    adapter.client.messages.create.return_value = _empty_response()

    with patch("time.sleep"):
        result = adapter.complete("test")

    assert result == ""
    assert adapter.client.messages.create.call_count == MAX_RETRIES + 1


def test_retries_on_api_exception_and_succeeds():
    """API wirft einen Fehler → retry → zweiter Versuch klappt → Text zurückgeben."""
    adapter = _make_adapter()
    adapter.client.messages.create.side_effect = [
        Exception("Rate limit"),
        _mock_response("Analyse erfolgreich."),
    ]

    with patch("time.sleep"):
        result = adapter.complete("test")

    assert result == "Analyse erfolgreich."


def test_returns_empty_string_after_all_retries_exhausted_with_exceptions():
    """Alle Versuche werfen Fehler → leeren String zurückgeben, kein Absturz."""
    adapter = _make_adapter()
    adapter.client.messages.create.side_effect = Exception("API down")

    with patch("time.sleep"):
        result = adapter.complete("test")

    assert result == ""
    assert adapter.client.messages.create.call_count == MAX_RETRIES + 1


def test_no_retry_on_successful_first_attempt():
    """Erste Antwort hat Text → kein Retry nötig, nur ein API-Call."""
    adapter = _make_adapter()
    adapter.client.messages.create.return_value = _mock_response("Antwort.")

    result = adapter.complete("test")

    assert result == "Antwort."
    assert adapter.client.messages.create.call_count == 1
