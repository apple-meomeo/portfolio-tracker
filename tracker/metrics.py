"""Risk, return, diversification and attribution metrics."""
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def daily_returns(values):
    return values.pct_change().dropna(how="all")


def max_drawdown(values: pd.Series) -> float:
    return (values / values.cummax() - 1).min()


# ---------- absolute risk: one portfolio on its own ----------
def absolute_summary(values: pd.Series, estr: pd.Series) -> dict:
    r = daily_returns(values)
    rf_daily = estr.reindex(r.index) / TRADING_DAYS  # approximation of daily €STR accrual
    vol_d = r.std()
    return {
        "Start value (€)": values.iloc[0],
        "End value (€)": values.iloc[-1],
        "P&L (€)": values.iloc[-1] - values.iloc[0],
        "Period return": values.iloc[-1] / values.iloc[0] - 1,
        "Volatility (annualised)": vol_d * np.sqrt(TRADING_DAYS),
        "Sharpe ratio (annualised)": (r - rf_daily).mean() / vol_d * np.sqrt(TRADING_DAYS) if vol_d > 0 else np.nan,
        "Max drawdown": max_drawdown(values),
        "1-day VaR 95% (€)": 1.645 * vol_d * values.iloc[-1],
        "Worst day": r.min(),
        "Best day": r.max(),
    }


# ---------- relative risk: team vs reference ----------
def relative_summary(team: pd.Series, ref: pd.Series) -> dict:
    rt, rb = daily_returns(team), daily_returns(ref)
    active = rt - rb
    te = active.std() * np.sqrt(TRADING_DAYS)
    return {
        "Active return (period)": team.iloc[-1] / team.iloc[0] - ref.iloc[-1] / ref.iloc[0],
        "Tracking error (annualised)": te,
        "Information ratio": active.mean() * TRADING_DAYS / te if te > 0 else np.nan,
        "Beta vs reference": np.cov(rt, rb)[0, 1] / np.var(rb, ddof=1),
        "Correlation with reference": rt.corr(rb),
        "Days team beat reference": f"{(active > 0).sum()} / {len(active)}",
    }


# ---------- diversification ----------
def start_weights(pos_values: pd.DataFrame) -> pd.Series:
    return pos_values.iloc[0] / pos_values.iloc[0].sum()


def risk_contributions(pos_values: pd.DataFrame) -> pd.DataFrame:
    """Share of the portfolio's variance that comes from each position."""
    r = daily_returns(pos_values)
    w = start_weights(pos_values)
    cov = r.cov()
    port_var = w @ cov @ w
    return pd.DataFrame({"weight": w, "risk_contribution": w * (cov @ w) / port_var})


def diversification_ratio(pos_values: pd.DataFrame) -> float:
    """Weighted average of asset vols / portfolio vol. Above 1 = diversification is working."""
    r = daily_returns(pos_values)
    w = start_weights(pos_values)
    return (w @ r.std()) / np.sqrt(w @ r.cov() @ w)


# ---------- risk vs return ----------
def risk_return_points(pos_values: dict, totals: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pf, df in pos_values.items():
        for pid in df:
            v = df[pid]
            rows.append({"label": pid, "group": pf, "kind": "Asset",
                         "vol": daily_returns(v).std() * np.sqrt(TRADING_DAYS),
                         "ret": v.iloc[-1] / v.iloc[0] - 1})
    for pf in totals:
        v = totals[pf]
        rows.append({"label": pf, "group": pf, "kind": "Portfolio",
                     "vol": daily_returns(v).std() * np.sqrt(TRADING_DAYS),
                     "ret": v.iloc[-1] / v.iloc[0] - 1})
    return pd.DataFrame(rows)


# ---------- attribution: where the euros came from ----------
def pnl_attribution(pos: pd.DataFrame) -> pd.DataFrame:
    """Split each position's P&L (€) into price, carry (accrued interest), income and FX."""
    rows = []
    for (pf, pid), d in pos.groupby(["portfolio", "id"], sort=False):
        d = d.sort_values("date")
        a, b = d.iloc[0], d.iloc[-1]
        u = a["units"]
        rows.append({
            "portfolio": pf, "id": pid,
            "value_start": a["value_eur"], "value_end": b["value_eur"],
            "price_effect": u * (b["clean"] - a["clean"]) / a["fx"],
            "carry_effect": u * (b["accrued"] - a["accrued"]) / a["fx"],
            "income": b["income_eur"],
            "fx_effect": u * b["price_local"] * (1 / b["fx"] - 1 / a["fx"]),
        })
    df = pd.DataFrame(rows)
    df["pnl"] = df["value_end"] - df["value_start"]
    df["return"] = df["pnl"] / df["value_start"]
    df["contribution"] = df["pnl"] / df.groupby("portfolio")["value_start"].transform("sum")
    return df


def currency_exposure(pos: pd.DataFrame, meta: dict) -> pd.DataFrame:
    first = pos[pos["date"] == pos["date"].min()].copy()
    first["currency"] = first["id"].map(lambda i: meta[i]["currency"])
    out = first.groupby(["portfolio", "currency"])["value_eur"].sum()
    return (out / out.groupby(level=0).transform("sum")).rename("weight").reset_index()
