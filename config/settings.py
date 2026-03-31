# config/settings.py

BOE_API_BASE_URL = "http://www.bankofengland.co.uk/boeapps/database/_iadb-FromShowColumns.asp"

# BoE IADB Series Codes (all verified working)
SERIES_CODES = {
    "base_rate": "IUMABEDR",        # Official Bank Rate
    "gbp_usd": "XUMAUSS",           # GBP/USD exchange rate
    "gbp_eur": "XUMAERS",           # GBP/EUR exchange rate
    "mortgage_rate": "IUMBV34",     # 2yr fixed mortgage rate 75% LTV
    "m4_money_supply": "LPMAUZI",   # M4 money supply (£m)
}

# API parameters
CSV_FORMAT = "TN"
USING_CODES = "Y"
VPD = "Y"

# Request settings
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

# Date range
DEFAULT_START_DATE = "01/Jan/2025"
DEFAULT_END_DATE = "now"

# Raw data output path
RAW_DATA_PATH = "data/raw"