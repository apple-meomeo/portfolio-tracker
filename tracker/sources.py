"""Download market data from free sources: Yahoo Finance and the ECB."""
import io

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


def fetch_ecb(flow: str, key: str, start, end) -> pd.Series:
    params = {
        "startPeriod": pd.Timestamp(start).strftime("%Y-%m-%d"),
        "endPeriod": pd.Timestamp(end).strftime("%Y-%m-%d"),
        "format": "csvdata",
    }
    resp = requests.get(ECB_URL.format(flow=flow, key=key), params=params, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    series = pd.Series(df["OBS_VALUE"].astype(float).values, index=pd.to_datetime(df["TIME_PERIOD"]))
    return series.sort_index()


def fetch_eurusd(start, end) -> pd.Series:
    """ECB reference rate: how many USD for 1 EUR."""
    return fetch_ecb("EXR", "D.USD.EUR.SP00.A", start, end)


def fetch_estr(start, end) -> pd.Series:
    """Euro short-term rate (€STR) as a decimal, e.g. 0.0193 for 1.93%."""
    return fetch_ecb("EST", "B.EU000A2X2A25.WT", start, end) / 100
