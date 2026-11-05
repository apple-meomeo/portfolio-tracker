"""Download market data from free sources: Yahoo Finance and the ECB."""
import io
import time
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

ECB_URL = "https://data-api.ecb.europa.eu/service/data/{flow}/{key}"


def fetch_yahoo(ticker: str, start, end) -> pd.DataFrame:
    """Daily close and dividends (per share, in the listing currency)."""
    end_exclusive = pd.Timestamp(end) + pd.Timedelta(days=1)  # yfinance excludes `end`
    hist = yf.Ticker(ticker).history(
        start=pd.Timestamp(start).strftime("%Y-%m-%d"),
        end=end_exclusive.strftime("%Y-%m-%d"),
        auto_adjust=False,
        actions=True,
    )
    if hist.empty:
        raise ValueError(f"Yahoo returned no data for {ticker}")
    hist.index = hist.index.tz_localize(None).normalize()
    if "Dividends" not in hist:
        hist["Dividends"] = 0.0
    return hist[["Close", "Dividends"]]


def fetch_ecb(flow: str, key: str, start, end, cache_column: str | None = None,
              scale: float = 1.0) -> pd.Series:
    """Download one ECB series. Retries on timeouts; if the ECB stays unreachable,
    falls back to the copy saved in data/market.csv by the previous run."""
    params = {
        "startPeriod": pd.Timestamp(start).strftime("%Y-%m-%d"),
        "endPeriod": pd.Timestamp(end).strftime("%Y-%m-%d"),
        "format": "csvdata",
    }
    for attempt in range(1, 4):
        try:
            resp = requests.get(ECB_URL.format(flow=flow, key=key), params=params, timeout=60)
            resp.raise_for_status()
            df = pd.read_csv(io.StringIO(resp.text))
            series = pd.Series(df["OBS_VALUE"].astype(float).values, index=pd.to_datetime(df["TIME_PERIOD"]))
            return series.sort_index() * scale
        except requests.RequestException as exc:
            print(f"ECB {flow} attempt {attempt}/3 failed: {exc.__class__.__name__}")
            time.sleep(5 * attempt)
    if cache_column and Path("data/market.csv").exists():
        print(f"ECB unreachable: using the saved {cache_column} from data/market.csv")
        cached = pd.read_csv("data/market.csv", parse_dates=["date"], index_col="date")[cache_column]
        return cached.dropna()
    raise RuntimeError("ECB API unreachable and no saved data/market.csv: try again later")


def fetch_eurusd(start, end) -> pd.Series:
    """ECB reference rate: how many USD for 1 EUR."""
    return fetch_ecb("EXR", "D.USD.EUR.SP00.A", start, end, cache_column="eurusd")


def fetch_estr(start, end) -> pd.Series:
    """Euro short-term rate (€STR) as a decimal, e.g. 0.0193 for 1.93%."""
    return fetch_ecb("EST", "B.EU000A2X2A25.WT", start, end, cache_column="estr", scale=0.01)