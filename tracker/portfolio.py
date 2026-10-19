"""Turn the config + prices into daily position values in euros."""
import pandas as pd
import yaml

from . import pricing, sources

CONFIG_PATH = "config/portfolios.yaml"
MANUAL_PATH = "data/manual_prices.csv"


def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    seen = set()
    for name, pf in cfg["portfolios"].items():
        total = sum(p["weight"] for p in pf["positions"])
        if abs(total - 1) > 1e-9:
            raise ValueError(f"Weights of '{name}' sum to {total:.4f}, not 1")
        for p in pf["positions"]:
            if p["id"] in seen:
                raise ValueError(f"Duplicate position id: {p['id']}")
            seen.add(p["id"])
    return cfg


def date_index(cfg: dict) -> pd.DatetimeIndex:
    """Business days from the start date to the end date (or today, if earlier)."""
    start = pd.Timestamp(cfg["start_date"])
    end = min(pd.Timestamp(cfg["end_date"]), pd.Timestamp.today().normalize())
    return pd.bdate_range(start, end)


def load_manual(path: str = MANUAL_PATH) -> dict:
    df = pd.read_csv(path, parse_dates=["date"], comment="#")
    return {pid: g.set_index("date")["price"].sort_index() for pid, g in df.groupby("id")}


def align(series: pd.Series, idx: pd.DatetimeIndex) -> pd.Series:
    """Put a series on our business-day index; a missing day takes the last known value."""
    s = series.sort_index()
    s = s[~s.index.duplicated(keep="last")]
    return s.reindex(s.index.union(idx)).ffill().reindex(idx)


def build_position(pos: dict, idx: pd.DatetimeIndex, manual: dict, fx_usd: pd.Series):
    df = pd.DataFrame(index=idx)
    df["dividend_local"] = 0.0
    manual_s = manual.get(pos["id"], pd.Series(dtype=float))
    source = pos["source"]

    if source == "yahoo":
        hist = sources.fetch_yahoo(pos["ticker"], idx[0] - pd.Timedelta(days=10), idx[-1])
        raw = hist["Close"] if manual_s.empty else manual_s.combine_first(hist["Close"])
        df["dividend_local"] = hist["Dividends"].reindex(idx, fill_value=0.0)
    elif source == "manual":
        raw = manual_s
    elif source == "formula":
        cp = pos["cp"]
        raw = pd.Series([pricing.cp_price(d, cp["yield"], cp["maturity"]) for d in idx], index=idx)
    else:
        raise ValueError(f"Unknown source '{source}' for {pos['id']}")

    if raw.empty or (raw.index <= idx[0]).sum() == 0:
        raise ValueError(
            f"No price on or before {idx[0].date()} for '{pos['id']}'. "
            f"Add a line to {MANUAL_PATH}."
        )
    last_obs = raw.index[raw.index <= idx[-1]].max()

    df["clean"] = align(raw, idx)
    bond = pos.get("bond")
    df["accrued"] = [pricing.accrued_interest(d, **bond) for d in idx] if bond else 0.0
    df["price_local"] = df["clean"] + df["accrued"]

    if pos["currency"] == "EUR":
        df["fx"] = 1.0
    elif pos["currency"] == "USD":
        df["fx"] = fx_usd
    else:
        raise ValueError(f"Currency {pos['currency']} not supported")

    df["price_eur"] = df["price_local"] / df["fx"]
    df["dividend_eur"] = df["dividend_local"] / df["fx"]
    df.loc[idx[0], "dividend_eur"] = 0.0  # buying at the close on day 0: no dividend that day
    df["last_obs"] = last_obs
    return df


def build_portfolio(pf: dict, capital: float, idx, manual, fx_usd) -> dict:
    positions = {}
    for pos in pf["positions"]:
        df = build_position(pos, idx, manual, fx_usd)
        units = capital * pos["weight"] / df["price_eur"].iloc[0]  # bought at day-0 price
        df["units"] = units
        df["income_eur"] = units * df["dividend_eur"].cumsum()
        df["value_eur"] = units * df["price_eur"] + df["income_eur"]
        positions[pos["id"]] = df
    return positions


def build_all(cfg: dict):
    idx = date_index(cfg)
    lookback = idx[0] - pd.Timedelta(days=10)
    fx_usd = align(sources.fetch_eurusd(lookback, idx[-1]), idx)
    estr = align(sources.fetch_estr(lookback, idx[-1]), idx)
    manual = load_manual()
    result = {
        name: build_portfolio(pf, cfg["capital"], idx, manual, fx_usd)
        for name, pf in cfg["portfolios"].items()
    }
    return result, fx_usd, estr


def save(result: dict, fx_usd: pd.Series, estr: pd.Series, folder: str = "data") -> None:
    frames = []
    for pf_name, positions in result.items():
        for pid, df in positions.items():
            out = df.rename_axis("date").reset_index()
            out.insert(1, "portfolio", pf_name)
            out.insert(2, "id", pid)
            frames.append(out)
    pd.concat(frames).to_csv(f"{folder}/positions.csv", index=False, float_format="%.6f")
    market = pd.DataFrame({"eurusd": fx_usd, "estr": estr}).rename_axis("date")
    market.to_csv(f"{folder}/market.csv", float_format="%.6f")
