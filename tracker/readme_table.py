"""Write the result tables into README.md. Run after tracker.report: python -m tracker.readme_table

The tables go between these two lines in README.md (add them once where you want the tables):
<!-- RESULTS:START -->
<!-- RESULTS:END -->
"""
import re
from pathlib import Path

import pandas as pd

OUT = Path("output")
LABELS = {"team": "Team", "reference": "Reference"}


def eur(x: float, sign: bool = True) -> str:
    if abs(x) < 0.005:
        return "–"
    s = f"{x:+,.2f}" if sign else f"{x:,.2f}"
    return s.replace("-", "−")


def pct(x: float) -> str:
    return f"{x:+.2%}".replace("-", "−")


def build_markdown() -> str:
    attr = pd.read_csv(OUT / "attribution.csv")
    summary = pd.read_csv(OUT / "summary.csv", index_col=0)
    effects = ["price_effect", "carry_effect", "income", "fx_effect"]

    totals = attr.groupby("portfolio", sort=False)[["value_start", "value_end", "pnl"] + effects].sum()
    totals["return"] = totals["pnl"] / totals["value_start"]
    totals["local_return"] = (totals["pnl"] - totals["fx_effect"]) / totals["value_start"]

    lines = ["| Portfolio | 18 Sep | 16 Oct | P&L | Return (EUR) | Return (local ccy) | Volatility (ann.) | Max drawdown | Sharpe |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for pf, t in totals.iterrows():
        col = [c for c in summary.columns if c.lower().startswith(pf[:4])][0]
        s = summary[col]
        lines.append(f"| **{LABELS[pf]}** | €{t.value_start:,.2f} | €{t.value_end:,.2f} | {eur(t.pnl)} € | "
                     f"{pct(t['return'])} | {pct(t.local_return)} | {float(s['Volatility (annualised)']):.2%} | "
                     f"{pct(float(s['Max drawdown']))} | {float(s['Sharpe ratio (annualised)']):.2f} |".replace("-", "−"))
    gap = totals.loc["team", "value_end"] - totals.loc["reference", "value_end"]
    lines += ["", f"Team minus reference: **{eur(gap)} €**. Local-currency return = P&L excluding the EUR/USD effect.", "",
              "### Where the P&L came from (€)", "",
              "| Position | 18 Sep | 16 Oct | P&L | Return | Price | Carry | Dividends | FX |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for pf, g in attr.groupby("portfolio", sort=False):
        lines.append(f"| **{LABELS[pf]}** | | | | | | | | |")
        for _, r in g.iterrows():
            lines.append(f"| {r['name']} | {r.value_start:,.2f} | {r.value_end:,.2f} | {eur(r.pnl)} | {pct(r['return'])} | "
                         + " | ".join(eur(r[e]) for e in effects) + " |")
        t = totals.loc[pf]
        lines.append(f"| **Total {LABELS[pf].lower()}** | **{t.value_start:,.2f}** | **{t.value_end:,.2f}** | "
                     f"**{eur(t.pnl)}** | **{pct(t['return'])}** | "
                     + " | ".join(f"**{eur(t[e])}**" for e in effects) + " |")
    lines += ["", "Price = change in clean price; Carry = accrued interest on bonds; FX = effect of EUR/USD on USD assets. "
              "The NEU CP gain is its yield accruing, shown under Price."]
    return "\n".join(lines)


def main() -> None:
    md = build_markdown()
    readme = Path("README.md")
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    pattern = r"(<!-- RESULTS:START -->)(.*?)(<!-- RESULTS:END -->)"
    if re.search(pattern, text, flags=re.S):
        readme.write_text(re.sub(pattern, lambda m: f"{m[1]}\n{md}\n{m[3]}", text, flags=re.S), encoding="utf-8")
        print("README.md updated.")
    else:
        print(md)
        print("\n(No RESULTS markers in README.md: copy the tables above, or add the markers and re-run.)")


if __name__ == "__main__":
    main()