"""
FINANCIAL ANALYSIS — Calculates ratios, growth rates, and a DCF valuation.

WHAT YOU'RE LEARNING HERE:
- How analysts evaluate a company using ratios (profitability, leverage, efficiency)
- How to compute year-over-year growth rates from financial statements
- How a simplified Discounted Cash Flow (DCF) model works
- How to safely handle missing data (NaN) without crashing

KEY CONCEPTS:
- Ratios turn raw numbers into comparable metrics (e.g., "30% margin" vs "$50B profit")
- Growth rates show the TREND, which matters more than a single year's number
- DCF estimates what a company is worth based on its future cash flows
"""

import math


# ---- HELPER FUNCTIONS ----

def safe_get(df, row_name, col_index=0):
    """
    Safely pull a value from a DataFrame by row name and column index.

    WHY THIS EXISTS:
    Financial data is messy — some companies don't report every line item,
    and yfinance column names can vary. This prevents crashes from missing data.

    Returns None if the row doesn't exist or the value is NaN.
    """
    if df is None or df.empty:
        return None
    if row_name not in df.index:
        return None
    val = df.iloc[df.index.get_loc(row_name), col_index]
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    return val


def safe_divide(numerator, denominator):
    """
    Division that returns None instead of crashing on zero or missing values.
    In finance, dividing by zero is common (e.g., a company with zero debt).
    """
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def pct(value):
    """Convert a decimal ratio to a percentage string: 0.312 → '31.2%'"""
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"


# ---- RATIO CALCULATIONS ----

def calculate_ratios(data):
    """
    Calculates the key financial ratios an equity analyst looks at.

    These are organized into 4 categories (same grouping you'd see in CFA L2):
      1. Valuation   — Is the stock cheap or expensive?
      2. Profitability — How efficiently does the company make money?
      3. Leverage     — How much debt risk is there?
      4. Efficiency   — How well does the company use its assets?

    Args:
        data: The dictionary returned by fetch_company_data()

    Returns:
        A dictionary of ratios, each with a human-readable label and value.
    """
    info = data["info"]
    income = data["income_stmt"]
    balance = data["balance_sheet"]
    cash_flow = data["cash_flow"]

    # Most recent year is column 0 (yfinance sorts descending)
    revenue = safe_get(income, "Total Revenue", 0)
    gross_profit = safe_get(income, "Gross Profit", 0)
    operating_income = safe_get(income, "Operating Income", 0)
    net_income = safe_get(income, "Net Income From Continuing Operation Net Minority Interest", 0)
    ebitda = safe_get(income, "EBITDA", 0)

    total_assets = safe_get(balance, "Total Assets", 0)
    total_equity = safe_get(balance, "Stockholders Equity", 0)
    total_debt = safe_get(balance, "Total Debt", 0)
    cash = safe_get(balance, "Cash And Cash Equivalents", 0)

    capex = safe_get(cash_flow, "Capital Expenditure", 0)
    fcf = safe_get(cash_flow, "Free Cash Flow", 0)

    market_cap = info.get("marketCap")

    ratios = {}

    # ---- 1. VALUATION RATIOS ----
    # These tell you how the market is pricing the company relative to its fundamentals

    ratios["pe_trailing"] = {
        "label": "P/E Ratio (Trailing)",
        "value": info.get("trailingPE"),
        "description": "Price per dollar of earnings — higher means more expensive",
    }
    ratios["pe_forward"] = {
        "label": "P/E Ratio (Forward)",
        "value": info.get("forwardPE"),
        "description": "P/E based on next year's estimated earnings",
    }
    ratios["ev_ebitda"] = {
        "label": "EV/EBITDA",
        "value": info.get("enterpriseToEbitda"),
        "description": "Enterprise value per dollar of EBITDA — capital-structure neutral",
    }
    ratios["price_to_book"] = {
        "label": "Price/Book",
        "value": info.get("priceToBook"),
        "description": "Market price vs. accounting book value per share",
    }
    ratios["price_to_sales"] = {
        "label": "Price/Sales",
        "value": safe_divide(market_cap, revenue),
        "description": "Market cap per dollar of revenue",
    }

    # ---- 2. PROFITABILITY RATIOS ----
    # These measure how much profit the company squeezes from its revenue and assets

    ratios["gross_margin"] = {
        "label": "Gross Margin",
        "value": safe_divide(gross_profit, revenue),
        "description": "Revenue left after cost of goods sold",
        "format": "pct",
    }
    ratios["operating_margin"] = {
        "label": "Operating Margin",
        "value": safe_divide(operating_income, revenue),
        "description": "Revenue left after all operating expenses",
        "format": "pct",
    }
    ratios["net_margin"] = {
        "label": "Net Margin",
        "value": safe_divide(net_income, revenue),
        "description": "Bottom-line profit per dollar of revenue",
        "format": "pct",
    }
    ratios["roe"] = {
        "label": "Return on Equity (ROE)",
        "value": safe_divide(net_income, total_equity),
        "description": "Profit generated per dollar of shareholder equity",
        "format": "pct",
    }
    ratios["roa"] = {
        "label": "Return on Assets (ROA)",
        "value": safe_divide(net_income, total_assets),
        "description": "Profit generated per dollar of total assets",
        "format": "pct",
    }

    # ---- 3. LEVERAGE RATIOS ----
    # These measure financial risk — how much debt the company carries

    ratios["debt_to_equity"] = {
        "label": "Debt/Equity",
        "value": safe_divide(total_debt, total_equity),
        "description": "Total debt relative to shareholder equity",
    }
    ratios["net_debt_to_ebitda"] = {
        "label": "Net Debt/EBITDA",
        "value": safe_divide(
            (total_debt - cash) if total_debt and cash else None,
            ebitda
        ),
        "description": "Years of EBITDA needed to pay off net debt",
    }
    ratios["interest_coverage"] = {
        "label": "Interest Coverage",
        "value": safe_divide(
            operating_income,
            safe_get(income, "Interest Expense", 0)
        ),
        "description": "Operating income available to cover interest payments",
    }

    # ---- 4. EFFICIENCY / CASH FLOW RATIOS ----

    ratios["fcf_yield"] = {
        "label": "FCF Yield",
        "value": safe_divide(fcf, market_cap),
        "description": "Free cash flow as a percentage of market cap",
        "format": "pct",
    }
    ratios["fcf_margin"] = {
        "label": "FCF Margin",
        "value": safe_divide(fcf, revenue),
        "description": "Free cash flow per dollar of revenue",
        "format": "pct",
    }
    ratios["capex_to_revenue"] = {
        "label": "CapEx/Revenue",
        "value": safe_divide(abs(capex) if capex else None, revenue),
        "description": "Capital investment intensity relative to revenue",
        "format": "pct",
    }

    return ratios


# ---- GROWTH RATE CALCULATIONS ----

def calculate_growth_rates(data):
    """
    Calculates year-over-year growth rates for key line items.

    WHY GROWTH MATTERS:
    A single year's revenue is just a number. But "revenue grew 15% YoY
    for the last 3 years" tells a story. Analysts care about TRENDS.

    Returns a dictionary with growth rates for each available year pair.
    """
    income = data["income_stmt"]
    cash_flow = data["cash_flow"]

    if income.empty or len(income.columns) < 2:
        return {}

    # Items to calculate growth for
    growth_items = {
        "revenue": ("Total Revenue", income),
        "gross_profit": ("Gross Profit", income),
        "operating_income": ("Operating Income", income),
        "net_income": ("Net Income From Continuing Operation Net Minority Interest", income),
        "ebitda": ("EBITDA", income),
        "operating_cf": ("Operating Cash Flow", cash_flow),
        "fcf": ("Free Cash Flow", cash_flow),
    }

    growth = {}

    for key, (row_name, df) in growth_items.items():
        if df is None or df.empty or row_name not in df.index:
            continue

        row = df.loc[row_name]
        rates = []

        # Calculate YoY growth for each consecutive year pair
        # Columns are in reverse chronological order (newest first)
        for i in range(len(row) - 1):
            current = row.iloc[i]
            previous = row.iloc[i + 1]

            if previous is None or current is None:
                rates.append(None)
                continue
            if isinstance(previous, float) and math.isnan(previous):
                rates.append(None)
                continue
            if isinstance(current, float) and math.isnan(current):
                rates.append(None)
                continue
            if previous == 0:
                rates.append(None)
                continue

            rates.append((current - previous) / abs(previous))

        # CAGR (Compound Annual Growth Rate) if we have enough years
        # CAGR smooths out lumpy growth into a single annualized number
        first_val = row.iloc[-1]  # oldest
        last_val = row.iloc[0]    # newest
        n_years = len(row) - 1
        cagr = None

        if (first_val and last_val and n_years > 0
                and not (isinstance(first_val, float) and math.isnan(first_val))
                and not (isinstance(last_val, float) and math.isnan(last_val))
                and first_val > 0 and last_val > 0):
            cagr = (last_val / first_val) ** (1 / n_years) - 1

        growth[key] = {
            "label": row_name.replace("Net Income From Continuing Operation Net Minority Interest", "Net Income"),
            "yoy_rates": rates,
            "cagr": cagr,
        }

    return growth


# ---- SIMPLIFIED DCF VALUATION ----

def run_dcf(data, projection_years=5, terminal_growth=0.025, wacc=0.10):
    """
    Runs a simplified Discounted Cash Flow (DCF) valuation.

    HOW DCF WORKS (the core of CFA L2 equity valuation):
    1. Take the company's most recent Free Cash Flow (FCF)
    2. Project it forward for N years using an assumed growth rate
    3. Calculate a "terminal value" for all cash flows beyond year N
    4. Discount everything back to today using the WACC
    5. Divide by shares outstanding to get an implied price per share

    Args:
        data: The dictionary from fetch_company_data()
        projection_years: How many years to project FCF (default 5)
        terminal_growth: Long-term growth rate after projection period (default 2.5%)
        wacc: Weighted Average Cost of Capital — the discount rate (default 10%)

    Returns:
        A dictionary with all DCF components and the implied share price.
    """
    cash_flow = data["cash_flow"]
    info = data["info"]

    # Get most recent FCF
    base_fcf = safe_get(cash_flow, "Free Cash Flow", 0)
    shares_outstanding = info.get("sharesOutstanding")
    current_price = info.get("currentPrice")
    net_debt = None

    total_debt = safe_get(data["balance_sheet"], "Total Debt", 0)
    cash = safe_get(data["balance_sheet"], "Cash And Cash Equivalents", 0)
    if total_debt is not None and cash is not None:
        net_debt = total_debt - cash

    if base_fcf is None or shares_outstanding is None:
        return {
            "error": "Insufficient data for DCF (missing FCF or shares outstanding)",
        }

    # Estimate FCF growth rate from historical data
    # Use the average of available YoY growth rates, capped for sanity
    growth_data = calculate_growth_rates(data)
    fcf_growth = growth_data.get("fcf", {})
    yoy_rates = fcf_growth.get("yoy_rates", [])
    valid_rates = [r for r in yoy_rates if r is not None and abs(r) < 1.0]

    if valid_rates:
        estimated_growth = sum(valid_rates) / len(valid_rates)
        # Cap growth rate to reasonable bounds
        estimated_growth = max(-0.10, min(estimated_growth, 0.25))
    else:
        # Fall back to revenue growth if FCF growth is unavailable
        rev_growth = growth_data.get("revenue", {})
        rev_rates = rev_growth.get("yoy_rates", [])
        valid_rev = [r for r in rev_rates if r is not None and abs(r) < 1.0]
        if valid_rev:
            estimated_growth = sum(valid_rev) / len(valid_rev)
            estimated_growth = max(-0.05, min(estimated_growth, 0.20))
        else:
            estimated_growth = 0.05  # Conservative default

    # Step 1: Project FCF for each year
    projected_fcf = []
    for year in range(1, projection_years + 1):
        # Linearly fade growth toward terminal rate over the projection period
        # This reflects the assumption that high growth slows over time
        fade_factor = year / projection_years
        year_growth = estimated_growth * (1 - fade_factor) + terminal_growth * fade_factor
        fcf_value = base_fcf * (1 + year_growth) ** year
        projected_fcf.append({
            "year": year,
            "growth_rate": year_growth,
            "fcf": fcf_value,
        })

    # Step 2: Calculate terminal value (Gordon Growth Model)
    # TV = FCF_final * (1 + g) / (WACC - g)
    final_fcf = projected_fcf[-1]["fcf"]
    terminal_value = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)

    # Step 3: Discount everything back to present value
    pv_fcfs = []
    for proj in projected_fcf:
        pv = proj["fcf"] / (1 + wacc) ** proj["year"]
        pv_fcfs.append(pv)

    pv_terminal = terminal_value / (1 + wacc) ** projection_years

    # Step 4: Sum up to get enterprise value, then equity value
    enterprise_value = sum(pv_fcfs) + pv_terminal

    equity_value = enterprise_value
    if net_debt is not None:
        equity_value = enterprise_value - net_debt

    implied_price = equity_value / shares_outstanding

    # Upside/downside relative to current price
    upside = None
    if current_price and current_price > 0:
        upside = (implied_price / current_price) - 1

    return {
        "base_fcf": base_fcf,
        "estimated_growth": estimated_growth,
        "terminal_growth": terminal_growth,
        "wacc": wacc,
        "projection_years": projection_years,
        "projected_fcf": projected_fcf,
        "terminal_value": terminal_value,
        "pv_fcfs": pv_fcfs,
        "pv_terminal": pv_terminal,
        "enterprise_value": enterprise_value,
        "net_debt": net_debt,
        "equity_value": equity_value,
        "shares_outstanding": shares_outstanding,
        "implied_price": implied_price,
        "current_price": current_price,
        "upside": upside,
    }


# ---- DISPLAY FUNCTIONS ----

def display_ratios(ratios):
    """Prints all calculated ratios in a clean grouped format."""
    print(f"\n{'='*60}")
    print(f"  KEY FINANCIAL RATIOS")
    print(f"{'='*60}")

    for _, r in ratios.items():
        val = r["value"]
        if val is None:
            formatted = "—"
        elif r.get("format") == "pct":
            formatted = pct(val)
        else:
            formatted = f"{val:.2f}" if isinstance(val, float) else str(val)

        print(f"  {r['label']:30s} {formatted:>12s}")

    print()


def display_growth(growth):
    """Prints growth rates with CAGR."""
    print(f"\n{'='*60}")
    print(f"  GROWTH RATES (Year-over-Year)")
    print(f"{'='*60}")

    for _, g in growth.items():
        label = g["label"]
        yoy = g["yoy_rates"]
        cagr = g["cagr"]

        yoy_str = "  ".join(pct(r) for r in yoy)
        cagr_str = pct(cagr)

        print(f"  {label:30s} YoY: {yoy_str}")
        print(f"  {'':30s} CAGR: {cagr_str}")

    print()


def display_dcf(dcf):
    """Prints the DCF valuation summary."""
    from data_fetcher import format_number

    print(f"\n{'='*60}")
    print(f"  DCF VALUATION")
    print(f"{'='*60}")

    if "error" in dcf:
        print(f"  {dcf['error']}")
        return

    print(f"  Base FCF:           {format_number(dcf['base_fcf'])}")
    print(f"  Growth Rate (est):  {pct(dcf['estimated_growth'])}")
    print(f"  Terminal Growth:    {pct(dcf['terminal_growth'])}")
    print(f"  WACC (discount):    {pct(dcf['wacc'])}")
    print(f"  Projection Years:   {dcf['projection_years']}")
    print()

    print(f"  {'Year':>6s}  {'Growth':>8s}  {'FCF':>12s}  {'PV(FCF)':>12s}")
    print(f"  {'-'*42}")
    for proj, pv in zip(dcf["projected_fcf"], dcf["pv_fcfs"]):
        print(f"  {proj['year']:6d}  {pct(proj['growth_rate']):>8s}  "
              f"{format_number(proj['fcf']):>12s}  {format_number(pv):>12s}")

    print(f"\n  Terminal Value:      {format_number(dcf['terminal_value'])}")
    print(f"  PV(Terminal):       {format_number(dcf['pv_terminal'])}")
    print(f"  Enterprise Value:   {format_number(dcf['enterprise_value'])}")

    if dcf["net_debt"] is not None:
        print(f"  Net Debt:           {format_number(dcf['net_debt'])}")

    print(f"  Equity Value:       {format_number(dcf['equity_value'])}")
    print(f"\n  Implied Price:      ${dcf['implied_price']:.2f}")

    if dcf["current_price"]:
        print(f"  Current Price:      ${dcf['current_price']:.2f}")

    if dcf["upside"] is not None:
        direction = "upside" if dcf["upside"] >= 0 else "downside"
        print(f"  Implied {direction.title()}:   {pct(abs(dcf['upside']))}")

    print()


# ---- RUN DIRECTLY TO TEST ----

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from data_fetcher import fetch_company_data

    if len(sys.argv) > 1:
        symbol = sys.argv[1]
    else:
        symbol = input("Enter a stock ticker (e.g. AAPL, MSFT, JPM): ").strip().upper()

    print(f"Fetching data for {symbol}...")
    data = fetch_company_data(symbol)

    ratios = calculate_ratios(data)
    display_ratios(ratios)

    growth = calculate_growth_rates(data)
    display_growth(growth)

    dcf = run_dcf(data)
    display_dcf(dcf)
