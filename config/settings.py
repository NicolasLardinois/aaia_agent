import os
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY      = os.getenv("FRED_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
FINNHUB_API_KEY   = os.getenv("FINNHUB_API_KEY", "")
FMP_API_KEY       = os.getenv("FMP_API_KEY", "")  # Financial Modeling Prep (LME-Metalle, EU/CH-CAPE)

if not FRED_API_KEY:
    raise EnvironmentError("FRED_API_KEY fehlt in .env")
if not ANTHROPIC_API_KEY:
    raise EnvironmentError("ANTHROPIC_API_KEY fehlt in .env")
