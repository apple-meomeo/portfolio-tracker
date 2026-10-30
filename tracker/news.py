"""Collect candidate headlines from GDELT 
"""
import sys
import time

import pandas as pd
import requests

from .portfolio import load_config

GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"
SITES = "(domain:ft.com OR domain:reuters.com OR domain:bfmtv.com OR domain:lesechos.fr OR domain:bloomberg.com)"
TOPICS = {
    "totalenergies": '"TotalEnergies"',
    "oil": '"oil prices" OR "Brent crude"',
    "eu_banks": '"European banks" OR "bank stocks"',
    "ecb": '"ECB" OR "Lagarde"',
    "fed": '"Federal Reserve" OR "Powell"',
    "bunds": '"Bund yields" OR "German bonds"',
    "us_tech": '"Nasdaq" OR "tech stocks"',
    "barclays": '"Barclays"',
    "renault": '"Renault"',
    "gold": '"gold price"',
    "eurusd": '"euro dollar" OR "EUR/USD"',
}


def build_query(topic_query: str, sites: str) -> str:
    """GDELT only accepts parentheses around OR'd terms."""
    if " OR " in topic_query:
        topic_query = f"({topic_query})"
    return f"{topic_query} {sites}".strip()


def fetch(query: str, start: str, end: str, retries: int = 4) -> list:
    params = {"query": query, "mode": "ArtList", "format": "json", "maxrecords": 50,
              "sort": "DateDesc", "startdatetime": start, "enddatetime": end}
    for attempt in range(retries):
        resp = requests.get(GDELT, params=params, timeout=30)
        try:
            return resp.json().get("articles", [])
        except ValueError:  # GDELT answers errors in plain text, not JSON
            message = resp.text.strip()
            if "limit requests" in message and attempt < retries - 1:
                wait = 15 * (attempt + 1)
                print(f"   rate-limited, waiting {wait} s...")
                time.sleep(wait)
                continue
            print(f"   GDELT says: {message[:200]}")
            return []
    return []


def main() -> None:
    cfg = load_config()
    sites = "" if "--all-sites" in sys.argv else SITES
    start = pd.Timestamp(cfg["start_date"]).strftime("%Y%m%d000000")
    end = pd.Timestamp(cfg["end_date"]).strftime("%Y%m%d235959")
    rows = []
    for topic, query in TOPICS.items():
        try:
            articles = fetch(build_query(query, sites), start, end)
        except requests.RequestException as exc:
            print(f"   request failed: {exc}")
            articles = []
        print(f"{topic}: {len(articles)} articles")
        for a in articles:
            rows.append({"topic": topic, "date": a["seendate"][:8], "domain": a.get("domain"),
                         "title": a.get("title"), "url": a.get("url")})
        time.sleep(10)  # GDELT asks for at most one request every 5 seconds
    if not rows:
        print("\nNo articles found. Read the 'GDELT says' lines above to see why.")
        return
    df = pd.DataFrame(rows).drop_duplicates("url")
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    df.sort_values(["date", "topic"]).to_csv("data/news_candidates.csv", index=False)
    print(f"\nSaved {len(df)} candidates to data/news_candidates.csv")


if __name__ == "__main__":
    main()