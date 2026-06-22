from core.domain.models import ConflictItem

# Verdikt-Severity: HOLD (mild) < EXIT < REVERSE (scharf).
# Ein erledigter Konflikt öffnet nur wieder, wenn das neue Verdikt SCHÄRFER ist —
# kein erneutes Nerven bei gleichem oder milderem Signal (besseres UX).
_VERDICT_SEVERITY: dict[str, int] = {
    "HOLD": 0,
    "EXIT": 1,
    "REVERSE": 2,
}


def record_conflict(
    store,
    ticker: str,
    direction: str,
    verdict: str,
    reason: str,
    source: str,
) -> ConflictItem | None:
    """Lebenszyklus eines Konflikts: Dedupe → Reopen-Prüfung → Anlegen.

    Regeln:
    1. Offener Konflikt vorhanden → sofort überspringen (Dedupe).
    2. Zuletzt erledigter Konflikt hat gleiches oder schärferes Verdikt → überspringen
       (kein Rauschen wenn sich die Lage nicht verschlechtert hat).
    3. Sonst neuen ConflictItem anlegen, speichern und zurückgeben.

    Reine Logik gegen den ConflictStorePort — kein I/O, kein Async.
    Gibt den angelegten ConflictItem zurück oder None (übersprungen).
    """
    # Regel 1: Dedupe — bereits ein offener Eintrag für ticker+direction
    if store.find_open(ticker, direction) is not None:
        return None

    # Regel 2: Reopen-Schwelle — nur bei schärferem Verdikt als der letzte erledigte
    last = store.find_latest_resolved(ticker, direction)
    if last is not None:
        neue_severity = _VERDICT_SEVERITY.get(verdict, 0)
        letzte_severity = _VERDICT_SEVERITY.get(last.verdict, 0)
        if neue_severity <= letzte_severity:
            return None

    # Regel 3: Neuen offenen Konflikt anlegen
    item = ConflictItem(
        ticker=ticker,
        direction=direction,
        verdict=verdict,
        reason=reason,
        status="open",
        source=source,
    )
    store.save(item)
    return item
