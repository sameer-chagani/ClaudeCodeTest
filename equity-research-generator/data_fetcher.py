"""
Data fetching module — pulls live financial data from Yahoo Finance
for any publicly traded stock ticker.
"""

import math
import os
import json
import time
import hashlib
from datetime import datetime, timedelta

import yfinance as yf

# Simple file-based cache to avoid repeated Yahoo Finance requests
CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
CACHE_TTL = 3600  # 1 hour


def _cache_key(ticker_symbol):
    return os.path.join(CACHE_DIR, f"{ticker_symbol.upper()}.json")


def _get_cached(ticker_symbol):
    """Return cached data if fresh enough, else None."""
    path = _cache_key(ticker_symbol)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            cached = json.load(f)
        if time.time() - cached.get("_ts", 0) < CACHE_TTL:
            return cached
    except (json.JSONDecodeError, IOError):
        pass
    return None


def _set_cache(ticker_symbol, data):
    """Save serializable data to cache."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    data["_ts"] = time.time()
    path = _cache_key(ticker_symbol)
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except IOError:
        pass


def fetch_company_data(ticker_symbol, retries=3):
    """
    Fetches all financial data needed for the research report.

    Args:
        ticker_symbol: Stock ticker like "AAPL", "MSFT", "JPM"
        retries: Number of retry attempts on failure

    Returns:
        Dictionary containing company info, financial statements, and price history.
    """
    import pandas as pd

    ticker_symbol = ticker_symbol.upper()

    # Check cache first
    cached = _get_cached(ticker_symbol)
    if cached:
        # Reconstruct DataFrames from cached dicts
        return _deserialize(cached, ticker_symbol)

    last_error = None
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

            result = {
                "ticker": ticker_symbol,
                "info": info,
                "income_stmt": income_stmt,
                "balance_sheet": balance_sheet,
                "cash_flow": cash_flow,
                "price_history": price_history,
            }

            # Cache the result
            _set_cache(ticker_symbol, _serialize(result))
            return result

        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
                continue

    raise RuntimeError(f"Failed to fetch data for {ticker_symbol}: {last_error}")


def _serialize(data):
    """Convert DataFrames to JSON-serializable dicts for caching."""
    def df_to_dict(df):
        if df is None or df.empty:
            return None
        d = df.copy()
        d.columns = [str(c) for c in d.columns]
        return d.to_dict()

    ph = data["price_history"]
    ph_dict = None
    if ph is not None and not ph.empty:
        ph_copy = ph.copy()
        ph_copy.index = [str(i) for i in ph_copy.index]
        ph_dict = ph_copy.to_dict()

    return {
        "ticker": data["ticker"],
        "info": data["info"],
        "income_stmt": df_to_dict(data["income_stmt"]),
        "balance_sheet": df_to_dict(data["balance_sheet"]),
        "cash_flow": df_to_dict(data["cash_flow"]),
        "price_history": ph_dict,
    }


def _deserialize(cached, ticker_symbol):
    """Reconstruct DataFrames from cached dicts."""
    import pandas as pd

    def dict_to_df(d):
        if d is None:
            return pd.DataFrame()
        df = pd.DataFrame(d)
        df.columns = [pd.Timestamp(c) for c in df.columns]
        return df

    ph_data = cached.get("price_history")
    if ph_data:
        ph = pd.DataFrame(ph_data)
        ph.index = pd.to_datetime(ph.index)
    else:
        ph = pd.DataFrame()

    return {
        "ticker": ticker_symbol,
        "info": cached["info"],
        "income_stmt": dict_to_df(cached.get("income_stmt")),
        "balance_sheet": dict_to_df(cached.get("balance_sheet")),
        "cash_flow": dict_to_df(cached.get("cash_flow")),
        "price_history": ph,
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
