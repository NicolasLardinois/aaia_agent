import logging
from typing import Any, Callable

import config.settings as settings
from core.domain.run_context import RunContext
from core.ports.data_provider import EcbDataProvider, MarketDataProvider
from core.ports.snapshot_store import SnapshotStore
from core.utils.dataframe_codec import decode_frame, encode_frame

_log = logging.getLogger(__name__)

_DEFAULT_TTL_DAYS = 1


def _identity(x: Any) -> Any:
    return x


class _CachingBase:
    """Cache-aside-Logik, geteilt von allen Port-Decorators.

    Ablauf je Aufruf: (1) In-Lauf-Memo → (2) frischer SnapshotStore-Treffer →
    (3) Live-Fetch + write-through. Bei Exception/None: letzter bekannter Store-Wert
    (Offline-Resilienz), sonst None/Default des inneren Adapters. Wirft NIE selbst.
    """

    def __init__(self, inner: Any, run: RunContext, store: SnapshotStore) -> None:
        self._inner = inner
        self._run = run
        self._store = store

    def _is_fresh(self, obs_date) -> bool:
        ttl = getattr(settings, "SNAPSHOT_TTL_DAYS", _DEFAULT_TTL_DAYS)
        return (self._run.as_of - obs_date).days < ttl

    def _cached(
        self,
        namespace: str,
        key: str,
        fetch: Callable[[], Any],
        encode: Callable[[Any], Any] = _identity,
        decode: Callable[[Any], Any] = _identity,
    ) -> Any:
        memo_key = (namespace, key)
        if memo_key in self._run.memo:                       # 1. In-Lauf-Memo
            return self._run.memo[memo_key]

        def _safe_decode(raw: Any) -> Any:
            """Store-Wert decodieren; bei Fehler None (→ wie Store-Miss), nie Exception.
            Persistierte Werte sind nie None (write-through nur bei non-None), daher ist
            ein None-Ergebnis eindeutig ein Decode-Fehler."""
            try:
                return decode(raw)
            except Exception as exc:
                _log.warning("Caching %s:%s Store-Decode fehlgeschlagen (%s)", namespace, key, exc)
                return None

        try:                                                 # Store-Read ist best effort
            dated = self._store.get(namespace, key, self._run.as_of)
        except Exception as exc:
            _log.warning("Caching %s:%s Store-Read fehlgeschlagen (%s)", namespace, key, exc)
            dated = None

        if dated is not None and self._is_fresh(dated[0]):   # 2. frischer Store-Treffer
            decoded = _safe_decode(dated[1])
            if decoded is not None:
                self._run.memo[memo_key] = decoded
                return decoded
            # Decode fehlgeschlagen → wie Store-Miss behandeln und Live-Fetch versuchen

        try:                                                 # 3. Live
            value = fetch()
        except Exception as exc:
            _log.warning("Caching %s:%s Live-Fetch fehlgeschlagen (%s)", namespace, key, exc)
            value = None

        if value is None:                                    # Offline-Resilienz: letzter bekannter (auch stale)
            value = _safe_decode(dated[1]) if dated is not None else None
        else:
            try:
                self._store.put(namespace, key, self._run.as_of, encode(value))
            except Exception as exc:                         # Store-Write ist best effort
                _log.warning("Caching %s:%s Store-Write fehlgeschlagen (%s)", namespace, key, exc)

        self._run.memo[memo_key] = value
        return value


class CachingEcbProvider(_CachingBase, EcbDataProvider):
    """Caching-Decorator für EcbDataProvider. Die 10 skalaren Makro-Werte werden
    pro Lauf memoisiert + datiert persistiert; Struktur-Rückgaben (dict/list) und
    ``get_aaa_10y_yield`` werden in v1 unverändert durchgereicht (Caching davon = Folge-Task)."""

    _NS = "ecb"

    # ── gecachte Skalare ─────────────────────────────────────────────────────
    def get_interest_rate(self):        return self._cached(self._NS, "interest_rate", self._inner.get_interest_rate)
    def get_m3_growth(self):            return self._cached(self._NS, "m3_growth", self._inner.get_m3_growth)
    def get_m2_growth(self):            return self._cached(self._NS, "m2_growth", self._inner.get_m2_growth)
    def get_balance_sheet_growth(self): return self._cached(self._NS, "balance_sheet_growth", self._inner.get_balance_sheet_growth)
    def get_cpi(self):                  return self._cached(self._NS, "cpi", self._inner.get_cpi)
    def get_core_cpi(self):             return self._cached(self._NS, "core_cpi", self._inner.get_core_cpi)
    def get_ppi(self):                  return self._cached(self._NS, "ppi", self._inner.get_ppi)
    def get_gdp_growth(self):           return self._cached(self._NS, "gdp_growth", self._inner.get_gdp_growth)
    def get_unemployment(self):         return self._cached(self._NS, "unemployment", self._inner.get_unemployment)
    def get_pmi(self):                  return self._cached(self._NS, "pmi", self._inner.get_pmi)

    # ── v1 unverändert durchgereicht ─────────────────────────────────────────
    def get_sovereign_yields(self):     return self._inner.get_sovereign_yields()
    def get_yield_spreads(self):        return self._inner.get_yield_spreads()

    def get_interest_rate_history(self, years: int = 2):
        return self._inner.get_interest_rate_history(years)

    def get_unemployment_history(self, months: int = 14):
        # Konkrete ABC-Default-Methode (gibt [] zurück) MUSS an inner delegiert
        # werden, sonst geht die echte EU-Arbeitslosen-Historie verloren (Sahm-Regel).
        return self._inner.get_unemployment_history(months)

    def get_aaa_10y_yield(self):
        # Nicht auf dem ABC, aber vom Realzins-Pfad genutzt (EurostatEcbProvider reicht es durch).
        return self._inner.get_aaa_10y_yield()


class CachingMarketProvider(_CachingBase, MarketDataProvider):
    """Caching-Decorator für MarketDataProvider. v1 cached ``get_price_history``
    (DataFrame → Payload-Codec); Preis-/Info- und Index-Methoden werden unverändert
    durchgereicht."""

    _NS = "yahoo.price_history"

    def get_price_history(self, ticker: str, period: str = "1y"):
        return self._cached(
            self._NS,
            f"{ticker}:{period}",
            lambda: self._inner.get_price_history(ticker, period),
            encode=encode_frame,
            decode=decode_frame,
        )

    # ── unverändert durchgereicht ────────────────────────────────────────────
    def get_current_price(self, ticker: str):
        return self._inner.get_current_price(ticker)

    def get_info(self, ticker: str) -> dict:
        return self._inner.get_info(ticker)

    def get_index_constituents(self, index_ticker: str) -> list[str]:
        return self._inner.get_index_constituents(index_ticker)

    def get_constituent_histories(self, index_ticker: str, period: str = "2y") -> dict:
        return self._inner.get_constituent_histories(index_ticker, period)

    def get_index_fundamentals(self, index_ticker: str) -> dict:
        return self._inner.get_index_fundamentals(index_ticker)

    def get_index_holdings(self, index_ticker: str) -> list:
        return self._inner.get_index_holdings(index_ticker)


def wrap_providers(ecb, market, run: RunContext, store: SnapshotStore):
    """Umhüllt die echten Adapter mit ihren Caching-Decorators."""
    return CachingEcbProvider(ecb, run, store), CachingMarketProvider(market, run, store)
