"""SupabaseConflictStore — persistiert Konflikt-Einträge in der Supabase-DB.

Verbindungsmuster 1:1 von SupabaseMemory übernommen:
  - _connect() als contextmanager (psycopg2, RealDictCursor, SSL, 3 Versuche)
  - Jede Methode in try/except defensiv: DB-Fehler → None/[]/no-op, nie Crash.
"""
import logging
import os
import time
import urllib.parse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import psycopg2
import psycopg2.extras

from core.domain.models import ConflictItem
from core.ports.conflict_store import ConflictStorePort

_log = logging.getLogger(__name__)

# SQL-Spalten für SELECT: vollständige Liste aller ConflictItem-Felder
_SELECT_COLS = (
    "id, ticker, direction, verdict, reason, status, source, "
    "user_decision, created_at, resolved_at"
)


def _row_to_item(row: dict) -> ConflictItem:
    """Mappt eine DB-Zeile (RealDictRow oder dict) auf ein ConflictItem."""
    return ConflictItem(
        id=row["id"],
        ticker=row["ticker"],
        direction=row["direction"],
        verdict=row["verdict"],
        reason=row["reason"] or "",
        status=row["status"],
        source=row["source"],
        user_decision=row.get("user_decision"),
        created_at=str(row["created_at"]) if row.get("created_at") else None,
        resolved_at=str(row["resolved_at"]) if row.get("resolved_at") else None,
    )


class SupabaseConflictStore(ConflictStorePort):
    """Persistiert Konflikt-Einträge in der Supabase PostgreSQL-Datenbank.

    Implementiert ConflictStorePort (Hexagonal: Agenten kennen nur den Port,
    nie diesen Adapter direkt). Verbindungslogik identisch zu SupabaseMemory.
    """

    def __init__(self):
        self._url = os.getenv("SUPABASE_DB_URL")
        if not self._url:
            raise RuntimeError("SUPABASE_DB_URL nicht gesetzt.")

    @contextmanager
    def _connect(self):
        """Stellt eine psycopg2-Verbindung her (3 Versuche, SSL, RealDictCursor).

        Identisch zum _connect-Muster in SupabaseMemory — keine eigene
        Connect-Logik erfunden, sondern 1:1 übernommen für Konsistenz.
        """
        r = urllib.parse.urlparse(self._url)
        params = dict(
            host=r.hostname,
            port=r.port or 5432,
            user=r.username,
            password=urllib.parse.unquote(r.password or ""),
            dbname=r.path.lstrip("/"),
            cursor_factory=psycopg2.extras.RealDictCursor,
            sslmode="require",
        )
        conn = None
        for attempt in range(3):
            try:
                conn = psycopg2.connect(**params)
                break
            except psycopg2.Error:
                if attempt == 2:
                    raise
                time.sleep(2)
        try:
            yield conn
        finally:
            if conn is not None:
                conn.close()

    # ── find_open ──────────────────────────────────────────────────────────────

    def find_open(self, ticker: str, direction: str) -> ConflictItem | None:
        """Gibt den neusten offenen Konflikt für ticker+direction zurück oder None.

        ORDER BY id DESC LIMIT 1 → neusten offenen Eintrag (nicht den ältesten).
        """
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT {_SELECT_COLS}
                        FROM conflicts
                        WHERE ticker = %s AND direction = %s AND status = 'open'
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (ticker, direction),
                    )
                    row = cur.fetchone()
                    return _row_to_item(dict(row)) if row else None
        except Exception:
            _log.exception("find_open(%r, %r) fehlgeschlagen", ticker, direction)
            return None

    # ── find_latest_resolved ───────────────────────────────────────────────────

    def find_latest_resolved(self, ticker: str, direction: str) -> ConflictItem | None:
        """Gibt den neusten erledigten Konflikt für ticker+direction zurück oder None.

        ORDER BY resolved_at DESC LIMIT 1 → zeitlich zuletzt erledigten Eintrag.
        """
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT {_SELECT_COLS}
                        FROM conflicts
                        WHERE ticker = %s AND direction = %s AND status = 'resolved'
                        ORDER BY resolved_at DESC
                        LIMIT 1
                        """,
                        (ticker, direction),
                    )
                    row = cur.fetchone()
                    return _row_to_item(dict(row)) if row else None
        except Exception:
            _log.exception(
                "find_latest_resolved(%r, %r) fehlgeschlagen", ticker, direction
            )
            return None

    # ── save ───────────────────────────────────────────────────────────────────

    def save(self, item: ConflictItem) -> None:
        """Persistiert einen neuen Konflikt-Eintrag (INSERT).

        created_at wird von DB gesetzt (DEFAULT now()) — kein expliziter Wert nötig.
        """
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO conflicts
                            (ticker, direction, verdict, reason, status, source, created_at)
                        VALUES
                            (%s, %s, %s, %s, %s, %s, now())
                        """,
                        (
                            item.ticker,
                            item.direction,
                            item.verdict,
                            item.reason,
                            item.status,
                            item.source,
                        ),
                    )
                conn.commit()
        except Exception:
            _log.exception("save(%r) fehlgeschlagen", item.ticker)

    # ── load_open ──────────────────────────────────────────────────────────────

    def load_open(self) -> list[ConflictItem]:
        """Lädt alle offenen Konflikte (für die proaktive Inbox-Anzeige).

        ORDER BY id → chronologische Reihenfolge (ältester zuerst), damit die
        Inbox den ältesten unbearbeiteten Konflikt oben zeigt.
        """
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT {_SELECT_COLS}
                        FROM conflicts
                        WHERE status = 'open'
                        ORDER BY id
                        """
                    )
                    rows = cur.fetchall()
                    return [_row_to_item(dict(r)) for r in rows]
        except Exception:
            _log.exception("load_open() fehlgeschlagen")
            return []

    # ── resolve ────────────────────────────────────────────────────────────────

    def resolve(self, conflict_id: int, user_decision: str) -> None:
        """Markiert einen Konflikt als erledigt und speichert die Nutzer-Entscheidung.

        user_decision: 'held' (Position behalten) | 'closed' (Position geschlossen).
        resolved_at wird von DB auf now() gesetzt.
        Parameter-Reihenfolge im Tuple: (user_decision, conflict_id) — zuerst SET-Wert,
        dann WHERE-Bedingung.
        """
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE conflicts
                        SET status = 'resolved',
                            user_decision = %s,
                            resolved_at = now()
                        WHERE id = %s
                        """,
                        (user_decision, conflict_id),
                    )
                conn.commit()
        except Exception:
            _log.exception("resolve(id=%r) fehlgeschlagen", conflict_id)

    # ── load_for_backtest ──────────────────────────────────────────────────────

    def load_for_backtest(self, days: int = 180) -> list[ConflictItem]:
        """Lädt Konflikte mit created_at >= now()-days (für den Konflikt-Backtester)."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT {_SELECT_COLS}
                        FROM conflicts
                        WHERE created_at >= %s
                        ORDER BY created_at DESC
                        """,
                        (cutoff,),
                    )
                    return [_row_to_item(dict(r)) for r in cur.fetchall()]
        except Exception:
            _log.exception("load_for_backtest(%r) fehlgeschlagen", days)
            return []
