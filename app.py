"""Streamlit dashboard. Run locally: streamlit run app.py"""
from pathlib import Path

import pandas as pd
import streamlit as st

from tracker import charts, metrics
from tracker.analysis import REF, TEAM, load_all

st.set_page_config(page_title="Trading Game: Portfolio Tracker", layout="wide")


@st.cache_data(ttl=3600)
def get_data():
    return load_all()


d = get_data()
totals, labels, names, market = d["totals"], d["labels"], d["names"], d["market"]
cfg = d["cfg"]

st.title("Trading Game: Team vs Reference Portfolio")
st.caption(f"Buy-and-hold from {cfg['start_date']} to {cfg['end_date']}, "
           f"€{cfg['capital']:,} notional each. Last data point: {totals.index[-1].date()}.")

summary = pd.DataFrame({labels[p]: metrics.absolute_summary(totals[p], market["estr"]) for p in (TEAM, REF)})
attr = metrics.pnl_attribution(d["pos"])

tabs = st.tabs(["Result in €", "Absolute vs relative risk", "Diversification", "Risk vs return",
                "Currency risk", "Attribution", "News", "Methodology"])

with tabs[0]:
    cols = st.columns(3)
    for col, p in zip(cols, (TEAM, REF)):
        v = totals[p]
        col.metric(labels[p], f"€{v.iloc[-1]:,.2f}", f"€{v.iloc[-1] - v.iloc[0]:+,.2f} ({v.iloc[-1] / v.iloc[0] - 1:+.2%})")
    gap = totals[TEAM].iloc[-1] - totals[REF].iloc[-1]
    cols[2].metric("Team minus reference", f"€{gap:+,.2f}")
    st.plotly_chart(charts.cumulative(totals, labels, d["events"]), width="stretch")
    st.dataframe(summary.style.format("{:,.4f}"), width="stretch")

with tabs[1]:
    left, right = st.columns(2)
    left.subheader("Absolute risk: each portfolio on its own")
    left.dataframe(summary.loc[["Volatility (annualised)", "Max drawdown", "1-day VaR 95% (€)", "Worst day"]]
                   .style.format("{:,.4f}"))
    right.subheader("Relative risk: team vs reference")
    rel = metrics.relative_summary(totals[TEAM], totals[REF])
    right.dataframe(pd.Series({k: f"{v:.4f}" if isinstance(v, float) else v for k, v in rel.items()}, name="value"))
    st.plotly_chart(charts.drawdown(totals, labels), width="stretch")
    st.plotly_chart(charts.active_returns(totals), width="stretch")

with tabs[2]:
    all_returns = metrics.daily_returns(pd.concat(d["pos_values"].values(), axis=1))
    st.plotly_chart(charts.correlation(all_returns, names), width="stretch")
    for p in (TEAM, REF):
        pv = d["pos_values"][p]
        st.metric(f"Diversification ratio, {labels[p]}", f"{metrics.diversification_ratio(pv):.2f}")
        st.plotly_chart(charts.risk_contributions(metrics.risk_contributions(pv), names,
                                                  f"{labels[p]}: capital weight vs share of risk"),
                        width="stretch")

with tabs[3]:
    points = metrics.risk_return_points(d["pos_values"], totals)
    st.plotly_chart(charts.risk_return(points, labels, names), width="stretch")
    st.dataframe(summary.loc[["Period return", "Volatility (annualised)", "Sharpe ratio (annualised)"]]
                 .style.format("{:,.4f}"))

with tabs[4]:
    st.plotly_chart(charts.currency_exposure(metrics.currency_exposure(d["pos"], d["meta"]), labels),
                    width="stretch")
    st.plotly_chart(charts.eurusd(market), width="stretch")
    usd = attr[attr["id"].map(lambda i: d["meta"][i]["currency"]) == "USD"]
    st.dataframe(usd.set_index("id")[["pnl", "price_effect", "carry_effect", "fx_effect"]]
                 .rename(index=names).style.format("€{:,.2f}"))

with tabs[5]:
    st.plotly_chart(charts.attribution(attr, names), width="stretch")
    show = attr.assign(name=attr["id"].map(names)).set_index(["portfolio", "name"])
    st.dataframe(show[["value_start", "value_end", "pnl", "return", "contribution",
                       "price_effect", "carry_effect", "income", "fx_effect"]].style.format("{:,.2f}"))

with tabs[6]:
    contrib = metrics.daily_contributions(d["pos_values"])
    ev = d["events"].reset_index(drop=True)
    ev.index = [f"E{i}" for i in range(1, len(ev) + 1)]

    st.subheader("Key events of the period")
    st.caption("Each event is marked E1, E2… on the cumulative chart in the first tab.")
    st.dataframe(ev, width="stretch",
                 column_config={"url": st.column_config.LinkColumn("source link")})

    st.subheader("What moved the portfolios on an event day")
    pick = st.selectbox("Event", ev.index, format_func=lambda e: f"{e} · {ev.loc[e, 'date'].date()} · {ev.loc[e, 'title']}")
    day = ev.loc[pick, "date"]
    trading_day = contrib.index[contrib.index <= day].max()  # weekend event -> previous trading day
    if pd.isna(trading_day):
        st.info("This event is before the first return of the game.")
    else:
        row = contrib.loc[trading_day]
        team_r, ref_r = row["team"].sum() * 100, row["reference"].sum() * 100
        c1, c2, c3 = st.columns(3)
        c1.metric(labels[TEAM], f"{team_r:+.2f}%")
        c2.metric(labels[REF], f"{ref_r:+.2f}%")
        c3.metric("Gap (team − reference)", f"{team_r - ref_r:+.2f} pts")
        st.plotly_chart(charts.event_drivers(row, names, labels, f"Drivers on {trading_day.date()}"), width="stretch")
        st.markdown(f"**{ev.loc[pick, 'title']}**: {ev.loc[pick, 'summary']}")

    st.subheader("Biggest gap days (computed from prices)")
    st.caption("Use this table to find days that still need an explanation in events.csv.")
    st.dataframe(metrics.biggest_gap_days(contrib, names).style.format(
        {"gap (pts)": "{:+.2f}", "team return (%)": "{:+.2f}", "reference return (%)": "{:+.2f}"}), width="stretch")

with tabs[7]:
    readme = Path("README.md")
    st.markdown(readme.read_text(encoding="utf-8") if readme.exists() else "Write README.md (Step 15).")

with st.expander("Data freshness: last real price per position"):
    fresh = d["pos"].groupby("id")["last_obs"].first().rename(index=names)
    st.dataframe(fresh)