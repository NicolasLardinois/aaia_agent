"""Test-Hermetik: sicherheitsrelevante Ambient-Env-Variablen sind im Testlauf neutralisiert.

`config/settings.py` ruft beim **Import** `load_dotenv()` auf — eine lokale `.env` mit
`AAIA_ACCESS_TOKEN`/`RENDER` leckt damit prozessweit nach `os.environ`, sobald irgendein
Modul `config.settings` importiert (PR-#47-Bug-Klasse: token-lose Routen-Tests bekamen im
Gesamtlauf `401` statt `204/202`). Die `autouse`-Wurzelfixture in `tests/conftest.py` muss
diese Variablen je Test leeren, sodass **jedes** Modul (nicht nur das API-Paket) einen
sauberen, deterministischen Ausgangszustand hat.

Der Import unten löst die potenzielle Verschmutzung bewusst aus — die Fixture muss sie heilen.
"""
import os

import config.settings  # noqa: F401 — Import triggert load_dotenv() (potenzielle Env-Verschmutzung)


def test_aaia_access_token_im_testlauf_neutralisiert():
    # Auch wenn die lokale .env ein Token enthält: im Test ist es geleert (Auth-Default AUS).
    assert "AAIA_ACCESS_TOKEN" not in os.environ


def test_render_flag_im_testlauf_neutralisiert():
    # RENDER leer halten: leeres Token UND gesetztes RENDER lässt create_app fail-closed werfen.
    assert "RENDER" not in os.environ
