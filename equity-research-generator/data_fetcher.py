"""
DATA FETCHER — Pulls financial data for any stock ticker.

WHAT YOU'RE LEARNING HERE:
- How to use a Python library (yfinance) to get real financial data
- How to work with pandas DataFrames (think of them as Excel spreadsheets in Python)
- How functions work — each one does ONE thing and returns data

KEY CONCEPTS:
- yfinance connects to Yahoo Finance and pulls real market data
- A DataFrame is like a table with rows and columns
- We organize data into a dictionary (like a labeled filing cabinet)
"""

import math
import yfinance as yf


def fetch_company_data(ticker_symbol):
    """
    Fetches all financial data we need for the research report.

    Args:
        ticker_symbol: Stock ticker like "AAPL", "MSFT", "JPM"

    Returns:
        A dictionary containing company info, financials, and price data.
        Think of it as a structured folder with all the data organized.
    """

    # Create a Ticker object — this is our connection to Yahoo Finance
    # It's like opening a file on a specific company
    ticker = yf.Ticker(ticker_symbol)

    # Pull company info (name, sector, description, market cap, etc.)
    info = ticker.info

    # Pull financial statements — these are the 3 core statements from CFA
    # Each one returns a DataFrame (table) with years as columns
    income_stmt = ticker.financials          # Revenue, net income, EBITDA
    balance_sheet = ticker.balance_sheet     # Assets, liabilities, equity
    cash_flow = ticker.cashflow             # Operating CF, CapEx, FCF

    # Pull stock price history for the last 2 years (for charts later)
    price_history = ticker.history(period="2y")

    # Package everything into one clean dictionary
    # This makes it easy to pass around — one variable holds everything
    data = {
        "ticker": ticker_symbol.upper(),
        "info": info,
        "income_stmt": income_stmt,
        "balance_sheet": balance_sheet,
        "cash_flow": cash_flow,
        "price_history": price_history,
    }

    return data


def display_summary(data):
    """
    Prints a quick summary to the terminal so you can verify the data looks right.
    This is a debugging/sanity-check function — always good practice to have one.
    """

    info = data["info"]

    print(f"\n{'='*60}")
    print(f"  {info.get('longName', data['ticker'])}")
    print(f"  Ticker: {data['ticker']}")
    print(f"  Sector: {info.get('sector', 'N/A')}")
    print(f"  Industry: {info.get('industry', 'N/A')}")
    print(f"{'='*60}")

    # Market data
    market_cap = info.get("marketCap", 0)
    if market_cap >= 1e12:
        cap_str = f"${market_cap/1e12:.2f}T"
    elif market_cap >= 1e9:
        cap_str = f"${market_cap/1e9:.2f}B"
    else:
        cap_str = f"${market_cap/1e6:.2f}M"

    print(f"  Market Cap:     {cap_str}")
    print(f"  Current Price:  ${info.get('currentPrice', 'N/A')}")
    print(f"  52-Wk High:     ${info.get('fiftyTwoWeekHigh', 'N/A')}")
    print(f"  52-Wk Low:      ${info.get('fiftyTwoWeekLow', 'N/A')}")
    print(f"  P/E (Trailing): {info.get('trailingPE', 'N/A')}")
    print(f"  Dividend Yield: {info.get('dividendYield', 'N/A')}")

    # Show what years of data we have
    if not data["income_stmt"].empty:
        years = [col.strftime("%Y") for col in data["income_stmt"].columns]
        print(f"\n  Financial data available: {', '.join(years)}")
    else:
        print("\n  WARNING: No financial statement data found.")

    print(f"  Price history: {len(data['price_history'])} trading days")
    print(f"{'='*60}\n")


def format_number(value):
    """
    Converts raw numbers into readable format.

    Examples:
        1,447,480,000,000 → "$1,447.5B"
        112,010,000,000   → "$112.0B"
        NaN               → "—"

    WHY THIS MATTERS:
    Financial data comes as raw numbers (in dollars, not millions/billions).
    Nobody wants to count zeros — this function makes them human-readable,
    just like how you'd see them in a 10-K or equity research report.
    """
    # Handle missing data — NaN means the data point doesn't exist
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"

    abs_val = abs(value)
    sign = "-" if value < 0 else ""

    if abs_val >= 1e12:
        return f"{sign}${abs_val/1e12:,.1f}T"
    elif abs_val >= 1e9:
        return f"{sign}${abs_val/1e9:,.1f}B"
    elif abs_val >= 1e6:
        return f"{sign}${abs_val/1e6:,.1f}M"
    elif abs_val >= 1e3:
        return f"{sign}${abs_val/1e3:,.1f}K"
    else:
        return f"{sign}${abs_val:,.0f}"


def display_financial_statements(data):
    """
    Prints the 3 financial statements in a clean, readable format.

    Only shows the KEY line items an analyst cares about — not the 50+
    rows that Yahoo Finance dumps. Think of this as the summary page
    at the top of a 10-K, not the full filing.
    """

    income_stmt = data["income_stmt"]
    balance_sheet = data["balance_sheet"]
    cash_flow = data["cash_flow"]

    # Get year labels from columns (e.g. "2025", "2024", ...)
    if income_stmt.empty:
        print("  No financial data available.\n")
        return

    years = [col.strftime("%Y") for col in income_stmt.columns]

    # Helper: safely get a value from a DataFrame
    # Some row names might not exist for every company
    def get_row(df, row_name):
        if row_name in df.index:
            return df.loc[row_name]
        return None

    # ---- INCOME STATEMENT ----
    # These are the line items any analyst looks at first
    income_items = [
        ("Total Revenue",           "Total Revenue"),
        ("Cost of Revenue",         "Reconciled Cost Of Revenue"),
        ("Gross Profit",            "Gross Profit"),
        ("Operating Income",        "Operating Income"),
        ("EBITDA",                  "EBITDA"),
        ("Net Income",              "Net Income From Continuing Operation Net Minority Interest"),
        ("EPS (Basic)",             "Basic EPS"),
    ]

    print(f"  INCOME STATEMENT")
    print(f"  {'-'*56}")

    # Print year headers
    header = f"  {'':30s}"
    for y in years:
        header += f"{y:>12s}"
    print(header)
    print(f"  {'-'*56}")

    for label, row_name in income_items:
        row = get_row(income_stmt, row_name)
        if row is None:
            continue
        line = f"  {label:30s}"
        for val in row:
            if label == "EPS (Basic)":
                # EPS is already per-share, show as dollars not billions
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    line += f"{'—':>12s}"
                else:
                    line += f"{'${:.2f}'.format(val):>12s}"
            else:
                line += f"{format_number(val):>12s}"
        print(line)

    # ---- BALANCE SHEET ----
    balance_items = [
        ("Total Assets",            "Total Assets"),
        ("Total Liabilities",       "Total Liabilities Net Minority Interest"),
        ("Total Equity",            "Stockholders Equity"),
        ("Cash & Equivalents",      "Cash And Cash Equivalents"),
        ("Total Debt",              "Total Debt"),
    ]

    print(f"\n  BALANCE SHEET")
    print(f"  {'-'*56}")
    print(header)
    print(f"  {'-'*56}")

    for label, row_name in balance_items:
        row = get_row(balance_sheet, row_name)
        if row is None:
            continue
        line = f"  {label:30s}"
        for val in row:
            line += f"{format_number(val):>12s}"
        print(line)

    # ---- CASH FLOW STATEMENT ----
    cashflow_items = [
        ("Operating Cash Flow",     "Operating Cash Flow"),
        ("Capital Expenditure",     "Capital Expenditure"),
        ("Free Cash Flow",          "Free Cash Flow"),
    ]

    print(f"\n  CASH FLOW STATEMENT")
    print(f"  {'-'*56}")
    print(header)
    print(f"  {'-'*56}")

    for label, row_name in cashflow_items:
        row = get_row(cash_flow, row_name)
        if row is None:
            continue
        line = f"  {label:30s}"
        for val in row:
            line += f"{format_number(val):>12s}"
        print(line)

    print()


# ---- RUN THIS FILE DIRECTLY TO TEST ----
# When you see `if __name__ == "__main__"`, it means:
# "Only run this code if I'm running THIS file directly"
# It won't run if another file imports this module.

if __name__ == "__main__":
    import sys

    # If a ticker was passed as an argument, use it
    # Otherwise, ask the user to type one
    if len(sys.argv) > 1:
        symbol = sys.argv[1]
    else:
        symbol = input("Enter a stock ticker (e.g. AAPL, MSFT, JPM): ").strip().upper()

    print(f"Fetching data for {symbol}...")
    data = fetch_company_data(symbol)
    display_summary(data)
    display_financial_statements(data)
