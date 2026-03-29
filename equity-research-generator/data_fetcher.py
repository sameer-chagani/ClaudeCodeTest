"""
Data fetching module — pulls live financial data from
Financial Modeling Prep API for any publicly traded stock ticker.
"""

import math
import os
from datetime import datetime, timedelta

import requests
import pandas as pd

FMP_BASE = "https://financialmodelingprep.com/stable"
API_KEY = os.environ.get("FMP_API_KEY", "")


def _get(endpoint, params=None):
    """Make a request to the FMP API."""
    params = params or {}
    params["apikey"] = API_KEY
    url = f"{FMP_BASE}/{endpoint}"
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict) and "Error Message" in data:
        raise ValueError(data["Error Message"])
    return data


def fetch_company_data(ticker_symbol):
    """
    Fetches all financial data needed for the research report.

    Args:
        ticker_symbol: Stock ticker like "AAPL", "MSFT", "JPM"

    Returns:
        Dictionary containing company profile, financial statements, and price history.
    """
    ticker_symbol = ticker_symbol.upper()

    # Fetch all data from FMP
    profile_list = _get("profile", {"symbol": ticker_symbol})
    if not profile_list:
        raise ValueError(f"No data found for ticker '{ticker_symbol}'")
    profile = profile_list[0]

    income_data = _get("income-statement", {"symbol": ticker_symbol, "period": "annual", "limit": 4})
    balance_data = _get("balance-sheet-statement", {"symbol": ticker_symbol, "period": "annual", "limit": 4})
    cashflow_data = _get("cash-flow-statement", {"symbol": ticker_symbol, "period": "annual", "limit": 4})

    today = datetime.now().strftime("%Y-%m-%d")
    two_years_ago = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
    price_data = _get("historical-price-eod/full", {"symbol": ticker_symbol, "from": two_years_ago, "to": today})

    # Build price history DataFrame
    if price_data:
        ph = pd.DataFrame(price_data)
        ph["date"] = pd.to_datetime(ph["date"])
        ph = ph.set_index("date").sort_index()
        ph = ph.rename(columns={"close": "Close", "volume": "Volume", "open": "Open", "high": "High", "low": "Low"})
    else:
        ph = pd.DataFrame()

    # Build info dict (matching the keys used by financial_analysis and app.py)
    price_range = profile.get("range", "0-0")
    range_parts = price_range.split("-")
    low_52w = float(range_parts[0]) if len(range_parts) >= 2 else None
    high_52w = float(range_parts[1]) if len(range_parts) >= 2 else None

    shares_outstanding = None
    if income_data:
        shares_outstanding = income_data[0].get("weightedAverageShsOut")

    # Compute trailing P/E
    current_price = profile.get("price")
    trailing_eps = income_data[0].get("eps") if income_data else None
    trailing_pe = None
    if current_price and trailing_eps and trailing_eps != 0:
        trailing_pe = current_price / trailing_eps

    # Compute forward P/E from forward EPS if available (use diluted EPS next year)
    forward_pe = None

    # Dividend yield
    last_dividend = profile.get("lastDividend", 0) or 0
    dividend_yield = None
    if current_price and current_price > 0 and last_dividend > 0:
        dividend_yield = last_dividend / current_price

    info = {
        "longName": profile.get("companyName", ticker_symbol),
        "sector": profile.get("sector", "N/A"),
        "industry": profile.get("industry", "N/A"),
        "longBusinessSummary": profile.get("description", ""),
        "marketCap": profile.get("marketCap", 0),
        "currentPrice": current_price,
        "fiftyTwoWeekHigh": high_52w,
        "fiftyTwoWeekLow": low_52w,
        "trailingPE": trailing_pe,
        "forwardPE": forward_pe,
        "dividendYield": dividend_yield,
        "sharesOutstanding": shares_outstanding,
        "enterpriseToEbitda": None,
        "priceToBook": None,
    }

    # Compute EV/EBITDA and P/B from data
    if income_data and balance_data:
        ebitda = income_data[0].get("ebitda")
        total_debt = balance_data[0].get("totalDebt", 0) or 0
        cash = balance_data[0].get("cashAndCashEquivalents", 0) or 0
        mc = profile.get("marketCap", 0) or 0
        ev = mc + total_debt - cash
        if ebitda and ebitda != 0:
            info["enterpriseToEbitda"] = ev / ebitda

        total_equity = balance_data[0].get("totalStockholdersEquity", 0)
        if total_equity and shares_outstanding and shares_outstanding > 0:
            book_per_share = total_equity / shares_outstanding
            if book_per_share and book_per_share != 0 and current_price:
                info["priceToBook"] = current_price / book_per_share

    # Build financial statement DataFrames in the format financial_analysis expects
    income_stmt = _build_statement_df(income_data, {
        "revenue": "Total Revenue",
        "grossProfit": "Gross Profit",
        "operatingIncome": "Operating Income",
        "netIncome": "Net Income From Continuing Operation Net Minority Interest",
        "ebitda": "EBITDA",
        "costOfRevenue": "Reconciled Cost Of Revenue",
        "interestExpense": "Interest Expense",
        "eps": "Basic EPS",
    })

    balance_sheet = _build_statement_df(balance_data, {
        "totalAssets": "Total Assets",
        "totalStockholdersEquity": "Stockholders Equity",
        "totalDebt": "Total Debt",
        "cashAndCashEquivalents": "Cash And Cash Equivalents",
        "totalLiabilities": "Total Liabilities Net Minority Interest",
    })

    cash_flow = _build_statement_df(cashflow_data, {
        "netCashProvidedByOperatingActivities": "Operating Cash Flow",
        "investmentsInPropertyPlantAndEquipment": "Capital Expenditure",
        "freeCashFlow": "Free Cash Flow",
    })

    return {
        "ticker": ticker_symbol,
        "info": info,
        "income_stmt": income_stmt,
        "balance_sheet": balance_sheet,
        "cash_flow": cash_flow,
        "price_history": ph,
    }


def _build_statement_df(data_list, field_map):
    """
    Convert FMP API response list into a DataFrame matching the format
    that financial_analysis.py expects (rows = metric names, columns = dates).
    """
    if not data_list:
        return pd.DataFrame()

    records = {}
    dates = []
    for item in data_list:
        date = pd.Timestamp(item["date"])
        dates.append(date)
        for fmp_key, our_key in field_map.items():
            if our_key not in records:
                records[our_key] = []
            records[our_key].append(item.get(fmp_key))

    df = pd.DataFrame(records, index=dates).T
    df.columns = dates
    return df


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
                    line += f"{chr(8212):>12s}"
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
