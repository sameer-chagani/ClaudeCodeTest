"""
Run this locally to pre-fetch data for popular tickers.
The .cache/ directory is committed to the repo so the deployed
app can serve results without hitting Yahoo Finance.

Usage:
    python seed_cache.py
"""

import time
from data_fetcher import fetch_company_data

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "JPM", "META"]

def main():
    for ticker in TICKERS:
        print(f"Fetching {ticker}...", end=" ", flush=True)
        try:
            fetch_company_data(ticker)
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
        time.sleep(2)

    print("\nDone. Cache files saved to .cache/")
    print("Commit and push .cache/ to make them available on Render.")

if __name__ == "__main__":
    main()
