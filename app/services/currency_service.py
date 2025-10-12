import time
import requests
from functools import lru_cache
from typing import Dict, Any, Optional

class CurrencyService:
    """Fetch and cache currencies and exchange rates"""

    # Cache TTL in seconds
    RATES_TTL = 60 * 60  # 1 hour
    _rates_cache: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    @lru_cache(maxsize=1)
    def get_supported_currencies() -> Dict[str, Dict[str, str]]:
        """Return map of currency_code -> { name, symbol } using restcountries API"""
        url = 'https://restcountries.com/v3.1/all?fields=name,currencies'
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        out: Dict[str, Dict[str, str]] = {}
        for c in data:
            cur = c.get('currencies') or {}
            for code, meta in cur.items():
                if not code or not isinstance(meta, dict):
                    continue
                name = meta.get('name') or code
                symbol = meta.get('symbol') or ''
                # Prefer first seen symbol/name; do not overwrite
                out.setdefault(code, { 'name': name, 'symbol': symbol })
        return dict(sorted(out.items(), key=lambda kv: kv[0]))

    @classmethod
    def _get_rates(cls, base: str) -> Optional[Dict[str, Any]]:
        base = (base or 'INR').upper()
        cached = cls._rates_cache.get(base)
        now = time.time()
        if cached and (now - cached['ts'] < cls.RATES_TTL):
            return cached['data']
        url = f'https://api.exchangerate-api.com/v4/latest/{base}'
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return cached['data'] if cached else None
        data = resp.json()
        cls._rates_cache[base] = { 'ts': now, 'data': data }
        return data

    @classmethod
    def convert(cls, amount: float, from_ccy: str, to_ccy: str) -> Optional[float]:
        """Convert amount from one currency to another using public rates"""
        from_ccy = (from_ccy or 'INR').upper()
        to_ccy = (to_ccy or 'INR').upper()
        if from_ccy == to_ccy:
            return float(amount)
        # Strategy: get rates for from_ccy, then multiply by rate[to]
        data = cls._get_rates(from_ccy)
        if not data:
            return None
        rate = (data.get('rates') or {}).get(to_ccy)
        if not rate:
            return None
        try:
            return float(amount) * float(rate)
        except Exception:
            return None
