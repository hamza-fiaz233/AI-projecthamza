import time
from datetime import datetime, timezone
from typing import Any, Dict, List
import yfinance as yf
from cachetools import TTLCache
from langchain_core.tools import tool

# Caches to prevent Yahoo Finance rate-limiting and reduce latency
_quote_cache: TTLCache = TTLCache(maxsize=256, ttl=60)        # 60 seconds for live quotes
_history_cache: TTLCache = TTLCache(maxsize=128, ttl=300)    # 5 minutes for historical series
_ratios_cache: TTLCache = TTLCache(maxsize=256, ttl=3600)    # 1 hour for fundamentals


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_ticker(ticker: str) -> str:
    if not ticker or not isinstance(ticker, str):
        raise ValueError("Ticker symbol must be a non-empty string.")
    cleaned = ticker.strip().upper()
    if not cleaned.replace(".", "").replace("-", "").isalnum():
        raise ValueError(f"Invalid ticker format: {ticker}")
    return cleaned


def _fetch_with_retry(fn, retries: int = 2, delay: float = 1.0):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(delay * (attempt + 1))
    raise last_exc


@tool
def get_quote(ticker: str) -> Dict[str, Any]:
    """Return the latest stock price, daily change percent, volume, and UTC timestamp for a US ticker (e.g., AAPL, MSFT, NVDA)."""
    symbol = _clean_ticker(ticker)
    if symbol in _quote_cache:
        cached = dict(_quote_cache[symbol])
        cached["cached"] = True
        return cached

    def _query():
        t = yf.Ticker(symbol)
        price = None
        prev_close = None
        volume = None
        currency = "USD"

        try:
            info = t.fast_info
            price = getattr(info, "last_price", None)
            prev_close = getattr(info, "previous_close", None)
            volume = getattr(info, "last_volume", None)
            currency = getattr(info, "currency", "USD") or "USD"
        except Exception:
            pass

        if price is None:
            hist = t.history(period="5d")
            if hist.empty:
                raise ValueError(f"No market data found for ticker '{symbol}'.")
            price = float(hist["Close"].iloc[-1])
            prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
            volume = int(hist["Volume"].iloc[-1])

        change_pct = None
        if price is not None and prev_close:
            change_pct = round(((float(price) - float(prev_close)) / float(prev_close)) * 100, 2)

        return {
            "ticker": symbol,
            "price": round(float(price), 2),
            "previous_close": round(float(prev_close), 2) if prev_close is not None else None,
            "change_percent": change_pct,
            "volume": int(volume) if volume is not None else None,
            "currency": currency,
            "as_of_utc": _utc_now(),
            "source": "yfinance",
        }

    try:
        result = _fetch_with_retry(_query)
        _quote_cache[symbol] = result
        return result
    except Exception as exc:
        return {
            "ticker": symbol,
            "error": f"Failed to fetch live quote for {symbol}: {str(exc)}",
            "as_of_utc": _utc_now(),
        }


@tool
def get_history(ticker: str, period: str = "1mo", interval: str = "1d") -> Dict[str, Any]:
    """Return historical OHLCV price series and summary statistics for a US ticker. Valid periods: 5d, 1mo, 3mo, 6mo, 1y, 5y. Valid intervals: 1d, 1wk, 1mo."""
    symbol = _clean_ticker(ticker)
    valid_periods = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd"}
    valid_intervals = {"1d", "5d", "1wk", "1mo"}

    period = period if period in valid_periods else "1mo"
    interval = interval if interval in valid_intervals else "1d"
    cache_key = f"{symbol}:{period}:{interval}"

    if cache_key in _history_cache:
        cached = dict(_history_cache[cache_key])
        cached["cached"] = True
        return cached

    def _query():
        t = yf.Ticker(symbol)
        df = t.history(period=period, interval=interval)
        if df.empty:
            raise ValueError(f"No historical price data found for '{symbol}' (period={period}).")

        records: List[Dict[str, Any]] = []
        for idx, row in df.iterrows():
            records.append({
                "date": idx.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })

        start_close = records[0]["close"]
        end_close = records[-1]["close"]
        period_return_pct = round(((end_close - start_close) / start_close) * 100, 2) if start_close else 0.0

        return {
            "ticker": symbol,
            "period": period,
            "interval": interval,
            "start_date": records[0]["date"],
            "end_date": records[-1]["date"],
            "start_close": start_close,
            "end_close": end_close,
            "period_return_percent": period_return_pct,
            "period_high": round(max(r["high"] for r in records), 2),
            "period_low": round(min(r["low"] for r in records), 2),
            "data_points": len(records),
            "series": records[-60:],
            "as_of_utc": _utc_now(),
            "source": "yfinance",
        }

    try:
        result = _fetch_with_retry(_query)
        _history_cache[cache_key] = result
        return result
    except Exception as exc:
        return {
            "ticker": symbol,
            "error": f"Failed to fetch history for {symbol}: {str(exc)}",
            "as_of_utc": _utc_now(),
        }


@tool
def get_ratios(ticker: str) -> Dict[str, Any]:
    """Return fundamental valuation ratios (P/E, forward P/E, EPS, market cap, dividend yield, 52-week range) for a US ticker."""
    symbol = _clean_ticker(ticker)
    if symbol in _ratios_cache:
        cached = dict(_ratios_cache[symbol])
        cached["cached"] = True
        return cached

    def _query():
        t = yf.Ticker(symbol)
        info = t.info or {}
        if not info or ("regularMarketPrice" not in info and "currentPrice" not in info and "shortName" not in info):
            raise ValueError(f"No fundamental ratio data found for '{symbol}'.")

        div_yield = info.get("dividendYield")
        return {
            "ticker": symbol,
            "company_name": info.get("shortName") or info.get("longName") or symbol,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "trailing_pe": round(float(info["trailingPE"]), 2) if info.get("trailingPE") is not None else None,
            "forward_pe": round(float(info["forwardPE"]), 2) if info.get("forwardPE") is not None else None,
            "trailing_eps": round(float(info["trailingEps"]), 2) if info.get("trailingEps") is not None else None,
            "market_cap": info.get("marketCap"),
            "dividend_yield_percent": round(float(div_yield), 2) if div_yield is not None else None,
            "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
            "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
            "profit_margins_percent": round(float(info["profitMargins"]) * 100, 2) if info.get("profitMargins") is not None else None,
            "as_of_utc": _utc_now(),
            "source": "yfinance",
        }

    try:
        result = _fetch_with_retry(_query)
        _ratios_cache[symbol] = result
        return result
    except Exception as exc:
        return {
            "ticker": symbol,
            "error": f"Failed to fetch ratios for {symbol}: {str(exc)}",
            "as_of_utc": _utc_now(),
        }
