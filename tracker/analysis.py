"""Load saved data once and prepare the tables the dashboard and report need."""
import pandas as pd

from .portfolio import load_config

TEAM, REF = "team", "reference"


def load_all(data_dir: str = "data") -> dict:
    cfg = load_config()
    pos = pd.read_csv(f"{data_dir}/positions.csv", parse_dates=["date", "last_obs"])
    market = pd.read_csv(f"{data_dir}/market.csv", parse_dates=["date"], index_col="date")
    events = pd.read_csv(f"{data_dir}/events.csv", parse_dates=["date"]).sort_values("date")
    meta = {p["id"]: {**p, "portfolio": name}
            for name, pf in cfg["portfolios"].items() for p in pf["positions"]}
    totals = pos.groupby(["date", "portfolio"])["value_eur"].sum().unstack()[[TEAM, REF]]
    pos_values = {pf: g.pivot(index="date", columns="id", values="value_eur")
                  for pf, g in pos.groupby("portfolio")}
    labels = {name: pf["label"] for name, pf in cfg["portfolios"].items()}
    names = {pid: m["name"] for pid, m in meta.items()}
    return {"cfg": cfg, "pos": pos, "market": market, "events": events, "meta": meta,
            "totals": totals, "pos_values": pos_values, "labels": labels, "names": names}
