"""
MAIN — Entry point for the Equity Research Report Generator.

Run this file to generate a full report for any stock ticker:
    python main.py AAPL
    python main.py MSFT
    python main.py JPM

Or just run it with no arguments and it will ask you for a ticker.

WHAT THIS FILE DOES:
1. Fetches live financial data from Yahoo Finance
2. Calculates key ratios, growth rates, and a DCF valuation
3. (Optional) Generates AI commentary via Claude API
4. Outputs a professional PDF report with charts
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
from ai_commentary import generate_commentary, display_commentary
from report_generator import generate_report


def main():
    # ---- GET TICKER ----
    if len(sys.argv) > 1:
        symbol = sys.argv[1].strip().upper()
    else:
        symbol = input("Enter a stock ticker (e.g. AAPL, MSFT, JPM): ").strip().upper()

    if not symbol:
        print("Error: No ticker provided.")
        sys.exit(1)

    # ---- STEP 1: FETCH DATA ----
    print(f"\n[1/4] Fetching financial data for {symbol}...")
    try:
        data = fetch_company_data(symbol)
    except Exception as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

    display_summary(data)

    # ---- STEP 2: ANALYZE ----
    print("[2/4] Running financial analysis...")
    ratios = calculate_ratios(data)
    growth = calculate_growth_rates(data)
    dcf = run_dcf(data)

    display_ratios(ratios)
    display_growth(growth)
    display_dcf(dcf)

    # ---- STEP 3: AI COMMENTARY (optional) ----
    print("[3/4] AI commentary...")
    commentary = generate_commentary(data, ratios, growth, dcf)
    if commentary:
        display_commentary(commentary)

    # ---- STEP 4: GENERATE PDF ----
    print("[4/4] Generating PDF report...")
    output_file = generate_report(data, ratios, growth, dcf, commentary)
    print(f"\n  Report saved: {output_file}")
    print(f"  Open it with: open {output_file}\n")


if __name__ == "__main__":
    main()
