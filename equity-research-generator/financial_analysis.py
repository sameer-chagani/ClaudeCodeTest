"""
Financial analysis module — calculates ratios, growth rates, and DCF valuation.
"""

import math


def safe_get(df, row_name, col_index=0):
    """Safely pull a value from a DataFrame by row name and column index."""
    if df is None or df.empty:
        return None
    if row_name not in df.index:
        return None
    val = df.iloc[df.index.get_loc(row_name), col_index]
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    return val


def safe_divide(numerator, denominator):
    """Division that returns None instead of crashing on zero or missing values."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def pct(value):
    """Convert a decimal ratio to a percentage string: 0.312 -> '31.2%'"""
    if value is None:
        return "\u2014"
    return f"{value * 100:.1f}%"


def calculate_ratios(data):
    """
    Calculates key financial ratios grouped into:
    Valuation, Profitability, Leverage, and Cash Flow.
    """
    info = data["info"]
    income = data["income_stmt"]
    balance = data["balance_sheet"]
    cash_flow = data["cash_flow"]

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

    # Valuation
    ratios["pe_trailing"] = {
        "label": "P/E Ratio (Trailing)",
        "value": info.get("trailingPE"),
        "description": "Price per dollar of earnings",
    }
    ratios["pe_forward"] = {
        "label": "P/E Ratio (Forward)",
        "value": info.get("forwardPE"),
        "description": "P/E based on next year's estimated earnings",
    }
    ratios["ev_ebitda"] = {
        "label": "EV/EBITDA",
        "value": info.get("enterpriseToEbitda"),
        "description": "Enterprise value per dollar of EBITDA",
    }
    ratios["price_to_book"] = {
        "label": "Price/Book",
        "value": info.get("priceToBook"),
        "description": "Market price vs. book value per share",
    }
    ratios["price_to_sales"] = {
        "label": "Price/Sales",
        "value": safe_divide(market_cap, revenue),
        "description": "Market cap per dollar of revenue",
    }

    # Profitability
    ratios["gross_margin"] = {
        "label": "Gross Margin",
        "value": safe_divide(gross_profit, revenue),
        "description": "Revenue retained after COGS",
        "format": "pct",
    }
    ratios["operating_margin"] = {
        "label": "Operating Margin",
        "value": safe_divide(operating_income, revenue),
        "description": "Revenue retained after operating expenses",
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

    # Leverage
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

    # Cash Flow
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


def calculate_growth_rates(data):
    """Calculates year-over-year growth rates and CAGR for key metrics."""
    income = data["income_stmt"]
    cash_flow = data["cash_flow"]

    if income.empty or len(income.columns) < 2:
        return {}

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

        first_val = row.iloc[-1]
        last_val = row.iloc[0]
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


def run_dcf(data, projection_years=5, terminal_growth=0.025, wacc=0.10):
    """
    Runs a simplified DCF valuation model.

    Projects FCF forward, calculates terminal value via Gordon Growth Model,
    discounts back to present, and derives an implied share price.
    """
    cash_flow = data["cash_flow"]
    info = data["info"]

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

    # Estimate FCF growth from historical data
    growth_data = calculate_growth_rates(data)
    fcf_growth = growth_data.get("fcf", {})
    yoy_rates = fcf_growth.get("yoy_rates", [])
    valid_rates = [r for r in yoy_rates if r is not None and abs(r) < 1.0]

    if valid_rates:
        estimated_growth = sum(valid_rates) / len(valid_rates)
        estimated_growth = max(-0.10, min(estimated_growth, 0.25))
    else:
        rev_growth = growth_data.get("revenue", {})
        rev_rates = rev_growth.get("yoy_rates", [])
        valid_rev = [r for r in rev_rates if r is not None and abs(r) < 1.0]
        if valid_rev:
            estimated_growth = sum(valid_rev) / len(valid_rev)
            estimated_growth = max(-0.05, min(estimated_growth, 0.20))
        else:
            estimated_growth = 0.05

    # Project FCF with linear growth fade toward terminal rate
    projected_fcf = []
    for year in range(1, projection_years + 1):
        fade_factor = year / projection_years
        year_growth = estimated_growth * (1 - fade_factor) + terminal_growth * fade_factor
        fcf_value = base_fcf * (1 + year_growth) ** year
        projected_fcf.append({
            "year": year,
            "growth_rate": year_growth,
            "fcf": fcf_value,
        })

    # Terminal value (Gordon Growth Model)
    final_fcf = projected_fcf[-1]["fcf"]
    terminal_value = final_fcf * (1 + terminal_growth) / (wacc - terminal_growth)

    # Discount to present value
    pv_fcfs = []
    for proj in projected_fcf:
        pv = proj["fcf"] / (1 + wacc) ** proj["year"]
        pv_fcfs.append(pv)

    pv_terminal = terminal_value / (1 + wacc) ** projection_years

    # Enterprise value -> equity value -> implied price
    enterprise_value = sum(pv_fcfs) + pv_terminal

    equity_value = enterprise_value
    if net_debt is not None:
        equity_value = enterprise_value - net_debt

    implied_price = equity_value / shares_outstanding

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


def display_ratios(ratios):
    """Prints all calculated ratios in a grouped format."""
    from data_fetcher import format_number

    print(f"\n{'='*60}")
    print(f"  KEY FINANCIAL RATIOS")
    print(f"{'='*60}")

    for _, r in ratios.items():
        val = r["value"]
        if val is None:
            formatted = "\u2014"
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
