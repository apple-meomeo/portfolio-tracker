"""Plotly figures used by both the dashboard and the PNG report."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COLORS = {"team": "#2563eb", "reference": "#ea580c"}
LAYOUT = dict(template="plotly_white", font=dict(size=14), margin=dict(l=60, r=30, t=70, b=50))


def cumulative(totals: pd.DataFrame, labels: dict, events: pd.DataFrame | None = None) -> go.Figure:
    rebased = totals / totals.iloc[0] * 100
    fig = go.Figure()
    for col in rebased:
        fig.add_trace(go.Scatter(x=rebased.index, y=rebased[col], name=labels[col],
                                 mode="lines+markers", line=dict(color=COLORS[col], width=3)))
    if events is not None:
        for i, ev in enumerate(events.itertuples(), start=1):
            fig.add_vline(x=ev.date, line_dash="dot", line_color="grey")
            fig.add_annotation(x=ev.date, y=1.02, yref="paper", text=f"E{i}", showarrow=False)
    fig.update_layout(title="Portfolio value, base 100 on 18 Sep", yaxis_title="Index (18 Sep = 100)",
                      hovermode="x unified", **LAYOUT)
    return fig


def drawdown(totals: pd.DataFrame, labels: dict) -> go.Figure:
    dd = totals / totals.cummax() - 1
    fig = go.Figure([go.Scatter(x=dd.index, y=dd[c], name=labels[c], fill="tozeroy",
                                line=dict(color=COLORS[c])) for c in dd])
    fig.update_layout(title="Drawdown from previous peak", yaxis_tickformat=".1%", **LAYOUT)
    return fig


def active_returns(totals: pd.DataFrame) -> go.Figure:
    r = totals.pct_change().dropna()
    diff = r["team"] - r["reference"]
    fig = go.Figure(go.Bar(x=diff.index, y=diff,
                           marker_color=["#16a34a" if v >= 0 else "#dc2626" for v in diff]))
    fig.update_layout(title="Daily return of team minus reference (green = team ahead)",
                      yaxis_tickformat=".2%", **LAYOUT)
    return fig


def correlation(returns: pd.DataFrame, names: dict) -> go.Figure:
    corr = returns.corr().rename(index=names, columns=names)
    fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1, aspect="auto")
    fig.update_layout(title="Correlation of daily returns (all 10 positions)", **LAYOUT)
    return fig


def risk_contributions(rc: pd.DataFrame, names: dict, title: str) -> go.Figure:
    rc = rc.rename(index=names)
    fig = go.Figure([
        go.Bar(x=rc.index, y=rc["weight"], name="Weight (capital)", marker_color="#94a3b8"),
        go.Bar(x=rc.index, y=rc["risk_contribution"], name="Share of risk", marker_color="#0f172a"),
    ])
    fig.update_layout(title=title, barmode="group", yaxis_tickformat=".0%", **LAYOUT)
    return fig


def risk_return(points: pd.DataFrame, labels: dict, names: dict) -> go.Figure:
    fig = go.Figure()
    for pf in ("team", "reference"):
        a = points[(points.group == pf) & (points.kind == "Asset")]
        fig.add_trace(go.Scatter(x=a.vol, y=a.ret, mode="markers+text", name=f"{labels[pf]}: assets",
                                 text=a.label.map(names), textposition="top center",
                                 marker=dict(size=10, color=COLORS[pf], opacity=0.5)))
        p = points[(points.group == pf) & (points.kind == "Portfolio")]
        fig.add_trace(go.Scatter(x=p.vol, y=p.ret, mode="markers+text", name=labels[pf],
                                 text=[labels[pf]], textposition="bottom center",
                                 marker=dict(size=22, color=COLORS[pf], symbol="star")))
    fig.update_layout(title="Risk vs return (stars = portfolios)", xaxis_title="Volatility (annualised)",
                      yaxis_title="Return over the period", xaxis_tickformat=".0%", yaxis_tickformat=".1%",
                      **LAYOUT)
    return fig


def attribution(attr: pd.DataFrame, names: dict) -> go.Figure:
    d = attr.copy()
    d["name"] = d["id"].map(names)
    effects = {"price_effect": "Price", "carry_effect": "Carry (accrued interest)",
               "income": "Dividends", "fx_effect": "Currency (EUR/USD)"}
    fig = go.Figure([go.Bar(y=d["name"], x=d[col], name=lbl, orientation="h")
                     for col, lbl in effects.items()])
    fig.update_layout(title="Where each position's P&L came from (€)", barmode="relative",
                      xaxis_title="€", height=550, **LAYOUT)
    return fig


def currency_exposure(exp: pd.DataFrame, labels: dict) -> go.Figure:
    exp = exp.assign(portfolio=exp["portfolio"].map(labels))
    fig = px.bar(exp, x="portfolio", y="weight", color="currency", text_auto=".0%",
                 color_discrete_map={"EUR": "#2563eb", "USD": "#16a34a"})
    fig.update_layout(title="Currency exposure on 18 Sep (EUR-hedged funds count as EUR)",
                      yaxis_tickformat=".0%", **LAYOUT)
    return fig


def eurusd(market: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Scatter(x=market.index, y=market["eurusd"], line=dict(color="#16a34a", width=3)))
    fig.update_layout(title="EUR/USD (ECB reference rate). Up = euro stronger = USD assets lose value in €",
                      yaxis_title="USD per 1 EUR", **LAYOUT)
    return fig


def event_drivers(contrib_day: pd.Series, names: dict, labels: dict, title: str) -> go.Figure:
    """Horizontal bars: contribution of each position (in % points) to its portfolio on one day."""
    d = contrib_day.rename("c").reset_index()
    d.columns = ["portfolio", "id", "c"]
    d["name"] = d["id"].map(names)
    d = d.sort_values("c")
    fig = go.Figure([
        go.Bar(y=g["name"], x=g["c"] * 100, orientation="h", name=labels[pf],
               marker_color=COLORS[pf], text=[f"{v * 100:+.2f}" for v in g["c"]], textposition="outside")
        for pf, g in d.groupby("portfolio")
    ])
    fig.update_layout(title=title, xaxis_title="Contribution to the portfolio's daily return (% points)",
                      height=480, **LAYOUT)
    return fig