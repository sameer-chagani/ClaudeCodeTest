"""
Data fetching module — pulls live financial data from Yahoo Finance
for any publicly traded stock ticker.
"""

import math
import time

import yfinance as yf


def fetch_company_data(ticker_symbol, retries=3):
    """
    Fetches all financial data needed for the research report.

    Args:
        ticker_symbol: Stock ticker like "AAPL", "MSFT", "JPM"
        retries: Number of retry attempts on failure

    Returns:
        Dictionary containing company info, financial statements, and price history.
    """
    for attempt in range(retries):
        try:
            ticker = yf.Ticker(ticker_symbol)

            info = ticker.info
            if not info or not info.get("longName"):
                raise ValueError(f"No data found for ticker '{ticker_symbol}'")

            income_stmt = ticker.financials
            balance_sheet = ticker.balance_sheet
            cash_flow = ticker.cashflow
            price_history = ticker.history(period="2y")
            break
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f"Failed to fetch data for {ticker_symbol}: {e}")

    return {
        "ticker": ticker_symbol.upper(),
        "info": info,
        "income_stmt": income_stmt,
        "balance_sheet": balance_sheet,
        "cash_flow": cash_flow,
        "price_history": price_history,
    }


def display_summary(data):
    """Prints a quick summary of the fetched data to the terminal."""
    info = data["info"]

    print(f"\n{'='*60}")
    print(f"  {info.get('longName', data['ticker'])}")
    print(f"  Ticker: {data['ticker']}")
    print(f"  Sector: {info.get('sector', 'N/A')}")
    print(f"  Industry: {info.get('industry', 'N/A')}")
    print(f"{'='*60}")

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
    e.g. 1,447,480,000,000 -> "$1,447.5B"
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "\u2014"

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
    """Prints the 3 core financial statements in a clean format."""
    income_stmt = data["income_stmt"]
    balance_sheet = data["balance_sheet"]
    cash_flow = data["cash_flow"]

    if income_stmt.empty:
        print("  No financial data available.\n")
        return

    years = [col.strftime("%Y") for col in income_stmt.columns]

    def get_row(df, row_name):
        if row_name in df.index:
            return df.loc[row_name]
        return None

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
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    line += f"{'\u2014':>12s}"
                else:
                    line += f"{'${:.2f}'.format(val):>12s}"
            else:
                line += f"{format_number(val):>12s}"
        print(line)

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
