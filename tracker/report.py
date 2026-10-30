"""Export charts (PNG) and tables (CSV) for the slides. Run: python -m tracker.report"""
from pathlib import Path

import pandas as pd

from . import charts, metrics
from .analysis import REF, TEAM, load_all

OUT = Path("output")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    d = load_all()
    totals, labels, names, market = d["totals"], d["labels"], d["names"], d["market"]

    summary = pd.DataFrame({labels[p]: metrics.absolute_summary(totals[p], market["estr"]) for p in (TEAM, REF)})
    relative = pd.Series(metrics.relative_summary(totals[TEAM], totals[REF]), name="Team vs reference")
    attr = metrics.pnl_attribution(d["pos"])
    attr.insert(2, "name", attr["id"].map(names))

    summary.to_csv(OUT / "summary.csv")
    relative.to_csv(OUT / "relative.csv")
    attr.to_csv(OUT / "attribution.csv", index=False)
    totals.to_csv(OUT / "daily_values.csv")

    all_returns = metrics.daily_returns(pd.concat(d["pos_values"].values(), axis=1))
    figures = {
        "01_cumulative": charts.cumulative(totals, labels, d["events"]),
        "02_drawdown": charts.drawdown(totals, labels),
        "03_active_returns": charts.active_returns(totals),
        "04_correlation": charts.correlation(all_returns, names),
        "05_risk_contrib_team": charts.risk_contributions(
            metrics.risk_contributions(d["pos_values"][TEAM]), names, f"{labels[TEAM]}: weight vs risk"),
        "06_risk_contrib_reference": charts.risk_contributions(
            metrics.risk_contributions(d["pos_values"][REF]), names, f"{labels[REF]}: weight vs risk"),
        "07_risk_return": charts.risk_return(metrics.risk_return_points(d["pos_values"], totals), labels, names),
        "08_attribution": charts.attribution(attr, names),
        "09_currency_exposure": charts.currency_exposure(metrics.currency_exposure(d["pos"], d["meta"]), labels),
        "10_eurusd": charts.eurusd(market),
    }
    print("\nFINAL RESULT (EUR)")
    for p in (TEAM, REF):
        v = totals[p]
        print(f"  {labels[p]:<22} €{v.iloc[0]:>11,.2f} -> €{v.iloc[-1]:>11,.2f}  "
              f"P&L €{v.iloc[-1] - v.iloc[0]:>+10,.2f}  ({v.iloc[-1] / v.iloc[0] - 1:+.2%})")
    print(f"  Gap (team - reference): €{totals[TEAM].iloc[-1] - totals[REF].iloc[-1]:+,.2f}")
    try:
        for name, fig in figures.items():
            fig.write_image(OUT / f"{name}.png", width=1400, height=750, scale=2)
    except Exception as exc:  # usually: Chrome missing for kaleido
        print(f"\nPNG export failed ({exc}).\nRun `plotly_get_chrome` once, then re-run this script.")
    print(f"\nFiles written to {OUT.resolve()}")


if __name__ == "__main__":
    main()