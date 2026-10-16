"""Find Yahoo tickers for each ISIN. Run: python -m tracker.resolve_tickers"""
import yaml
import yfinance as yf


def main() -> None:
    with open("config/portfolios.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for pf in cfg["portfolios"].values():
        for pos in pf["positions"]:
            if not pos.get("isin"):
                continue
            print(f"\n== {pos['name']}  ({pos['isin']}, expected currency {pos['currency']})")
            try:
                quotes = yf.Search(pos["isin"], max_results=10).quotes
            except Exception as exc:  # network or Yahoo hiccup
                print(f"   search failed: {exc}")
                continue
            if not quotes:
                print("   nothing found on Yahoo -> keep source: manual")
            for q in quotes:
                symbol = q.get("symbol")
                try:
                    info = yf.Ticker(symbol).fast_info
                    ccy, last = info.currency, f"{info.last_price:,.4f}"
                except Exception:
                    ccy, last = "?", "?"
                print(f"   {symbol:<16} {q.get('exchange', ''):<6} {ccy:<4} last={last:<12} "
                      f"{q.get('longname') or q.get('shortname')}")


if __name__ == "__main__":
    main()
