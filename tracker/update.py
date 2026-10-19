"""Download everything, value both portfolios, save to data/. Run: python -m tracker.update"""
from .portfolio import build_all, load_config, save


def main() -> None:
    cfg = load_config()
    result, fx_usd, estr = build_all(cfg)
    save(result, fx_usd, estr)

    for name, positions in result.items():
        total = sum(df["value_eur"] for df in positions.values())
        change = total.iloc[-1] / total.iloc[0] - 1
        print(f"{name:<10} {total.index[-1].date()}  €{total.iloc[-1]:>12,.2f}  ({change:+.2%})")

    last_day = fx_usd.index[-1]
    for positions in result.values():
        for pid, df in positions.items():
            last_obs = df["last_obs"].iloc[0]
            if (last_day - last_obs).days > 3:
                print(f"WARNING: last real price for {pid} is {last_obs.date()} -> update it")


if __name__ == "__main__":
    main()
