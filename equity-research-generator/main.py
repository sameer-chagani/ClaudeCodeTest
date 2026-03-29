"""
CLI entry point for the Equity Research Platform.

Usage:
    python main.py AAPL
    python main.py MSFT
    python main.py        (prompts for ticker)
"""

import sys

from data_fetcher import fetch_company_data, display_summary, display_financial_statements
from financial_analysis import (
    calculate_ratios,
    calculate_growth_rates,
    run_dcf,
    display_ratios,
    display_growth,
    display_dcf,
)


def main():
    if len(sys.argv) > 1:
        symbol = sys.argv[1].strip().upper()
    else:
        symbol = input("Enter a stock ticker (e.g. AAPL, MSFT, JPM): ").strip().upper()

    if not symbol:
        print("Error: No ticker provided.")
        sys.exit(1)

    print(f"\n[1/3] Fetching financial data for {symbol}...")
    try:
        data = fetch_company_data(symbol)
    except Exception as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

    display_summary(data)

    print("[2/3] Running financial analysis...")
    ratios = calculate_ratios(data)
    growth = calculate_growth_rates(data)
    dcf = run_dcf(data)

    display_ratios(ratios)
    display_growth(growth)
    display_dcf(dcf)

    print("[3/3] Analysis complete.")
    print(f"\n  Run 'python app.py' and open http://127.0.0.1:8000 for the full interactive report.\n")


if __name__ == "__main__":
    main()
