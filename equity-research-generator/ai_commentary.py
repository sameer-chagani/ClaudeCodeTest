"""
AI COMMENTARY — Uses Claude to generate analyst-style written commentary.

WHAT YOU'RE LEARNING HERE:
- How to call the Claude API using the Anthropic Python SDK
- How to structure a prompt with financial data for high-quality output
- How streaming works (getting the response token by token)
- How to handle API errors gracefully

KEY CONCEPTS:
- The Anthropic SDK sends your prompt + data to Claude and gets back text
- A "system prompt" tells Claude what role to play (equity research analyst)
- We feed it the calculated ratios/growth/DCF so it writes about real numbers
"""

import anthropic

from financial_analysis import pct, safe_divide


def build_financial_summary(data, ratios, growth, dcf):
    """
    Builds a structured text summary of all financial data to feed to Claude.

    WHY NOT JUST DUMP RAW DATA?
    Claude works best with clean, labeled text — not raw DataFrames.
    This function converts our calculated numbers into a readable brief
    that Claude can analyze and write commentary about.
    """
    info = data["info"]
    lines = []

    # ---- Company Overview ----
    lines.append(f"COMPANY: {info.get('longName', data['ticker'])}")
    lines.append(f"TICKER: {data['ticker']}")
    lines.append(f"SECTOR: {info.get('sector', 'N/A')}")
    lines.append(f"INDUSTRY: {info.get('industry', 'N/A')}")
    lines.append(f"DESCRIPTION: {info.get('longBusinessSummary', 'N/A')[:500]}")
    lines.append("")

    # ---- Market Data ----
    lines.append("MARKET DATA:")
    market_cap = info.get("marketCap", 0)
    if market_cap >= 1e12:
        lines.append(f"  Market Cap: ${market_cap/1e12:.2f}T")
    elif market_cap >= 1e9:
        lines.append(f"  Market Cap: ${market_cap/1e9:.2f}B")
    else:
        lines.append(f"  Market Cap: ${market_cap/1e6:.2f}M")

    lines.append(f"  Current Price: ${info.get('currentPrice', 'N/A')}")
    lines.append(f"  52-Week High: ${info.get('fiftyTwoWeekHigh', 'N/A')}")
    lines.append(f"  52-Week Low: ${info.get('fiftyTwoWeekLow', 'N/A')}")
    lines.append(f"  Dividend Yield: {info.get('dividendYield', 'N/A')}")
    lines.append("")

    # ---- Key Ratios ----
    lines.append("KEY FINANCIAL RATIOS:")
    for _, r in ratios.items():
        val = r["value"]
        if val is None:
            formatted = "N/A"
        elif r.get("format") == "pct":
            formatted = pct(val)
        else:
            formatted = f"{val:.2f}" if isinstance(val, float) else str(val)
        lines.append(f"  {r['label']}: {formatted}")
    lines.append("")

    # ---- Growth Rates ----
    lines.append("GROWTH RATES:")
    for _, g in growth.items():
        label = g["label"]
        yoy = g["yoy_rates"]
        cagr = g["cagr"]
        yoy_str = ", ".join(pct(r) for r in yoy)
        lines.append(f"  {label}: YoY [{yoy_str}], CAGR: {pct(cagr)}")
    lines.append("")

    # ---- DCF Summary ----
    lines.append("DCF VALUATION:")
    if "error" in dcf:
        lines.append(f"  {dcf['error']}")
    else:
        lines.append(f"  Base FCF: ${dcf['base_fcf']/1e9:.2f}B")
        lines.append(f"  Estimated Growth: {pct(dcf['estimated_growth'])}")
        lines.append(f"  WACC: {pct(dcf['wacc'])}")
        lines.append(f"  Terminal Growth: {pct(dcf['terminal_growth'])}")
        lines.append(f"  Enterprise Value: ${dcf['enterprise_value']/1e9:.2f}B")
        lines.append(f"  Equity Value: ${dcf['equity_value']/1e9:.2f}B")
        lines.append(f"  Implied Price: ${dcf['implied_price']:.2f}")
        lines.append(f"  Current Price: ${dcf['current_price']:.2f}")
        if dcf["upside"] is not None:
            direction = "Upside" if dcf["upside"] >= 0 else "Downside"
            lines.append(f"  Implied {direction}: {pct(abs(dcf['upside']))}")

    return "\n".join(lines)


SYSTEM_PROMPT = """You are a senior equity research analyst at a top-tier investment bank.
You write clear, professional research notes that combine quantitative analysis
with qualitative insight. Your tone is authoritative but accessible — think
Goldman Sachs or Morgan Stanley research, not academic papers.

Guidelines:
- Reference specific numbers from the data provided (margins, growth rates, ratios)
- Compare metrics to what's typical for the sector when relevant
- Be balanced — highlight both strengths and risks
- Keep each section concise (3-5 sentences)
- Use professional financial language but explain complex concepts briefly
- Do NOT make up numbers — only use data provided to you
- Express the investment thesis clearly with a rating (Buy/Hold/Sell)
"""


def generate_commentary(data, ratios, growth, dcf):
    """
    Calls Claude to generate a full equity research commentary.

    Returns a dictionary with separate sections:
    - executive_summary
    - financial_analysis
    - growth_assessment
    - valuation_analysis
    - risk_factors
    - investment_thesis
    """
    financial_summary = build_financial_summary(data, ratios, growth, dcf)

    user_prompt = f"""Based on the following financial data, write a professional equity research
commentary for {data['ticker']}. Structure your response with these exact section headers:

## Executive Summary
(2-3 sentence overview of the company and its current position)

## Financial Analysis
(Analyze profitability margins, return metrics, and leverage. Reference specific ratios.)

## Growth Assessment
(Evaluate revenue and earnings growth trends. Discuss CAGR and trajectory.)

## Valuation Analysis
(Discuss the DCF-implied value vs current price. Comment on P/E, EV/EBITDA relative to peers.)

## Risk Factors
(Identify 3-4 key risks based on the financial data — leverage, margin pressure, growth deceleration, etc.)

## Investment Thesis
(Clear Buy/Hold/Sell recommendation with 1-2 sentence justification and the DCF-implied target price.)

FINANCIAL DATA:
{financial_summary}
"""

    client = anthropic.Anthropic()

    # Use streaming to handle long responses without timeout
    commentary = ""
    print("\n  Generating AI commentary", end="", flush=True)

    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        for text in stream.text_stream:
            commentary += text
            # Print dots as progress indicator
            if len(commentary) % 200 < len(text):
                print(".", end="", flush=True)

    print(" done.\n")

    # Parse sections from the response
    sections = parse_sections(commentary)
    return sections


def parse_sections(commentary):
    """
    Splits Claude's response into named sections based on ## headers.

    Returns a dict like:
    {
        "executive_summary": "...",
        "financial_analysis": "...",
        ...
        "full_text": "..."  # the complete unstructured response
    }
    """
    section_map = {
        "executive summary": "executive_summary",
        "financial analysis": "financial_analysis",
        "growth assessment": "growth_assessment",
        "valuation analysis": "valuation_analysis",
        "risk factors": "risk_factors",
        "investment thesis": "investment_thesis",
    }

    sections = {"full_text": commentary}
    current_key = None
    current_lines = []

    for line in commentary.split("\n"):
        stripped = line.strip()
        # Check if this line is a section header
        if stripped.startswith("## "):
            # Save previous section
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()

            header_text = stripped[3:].strip().lower()
            current_key = section_map.get(header_text)
            current_lines = []
        else:
            current_lines.append(line)

    # Save last section
    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    return sections


def display_commentary(sections):
    """Prints the AI-generated commentary to the terminal."""
    print(f"{'='*60}")
    print(f"  AI-GENERATED EQUITY RESEARCH COMMENTARY")
    print(f"{'='*60}\n")

    display_order = [
        ("executive_summary", "EXECUTIVE SUMMARY"),
        ("financial_analysis", "FINANCIAL ANALYSIS"),
        ("growth_assessment", "GROWTH ASSESSMENT"),
        ("valuation_analysis", "VALUATION ANALYSIS"),
        ("risk_factors", "RISK FACTORS"),
        ("investment_thesis", "INVESTMENT THESIS"),
    ]

    for key, title in display_order:
        if key in sections:
            print(f"  {title}")
            print(f"  {'-'*40}")
            # Indent each line for clean formatting
            for line in sections[key].split("\n"):
                print(f"  {line}")
            print()

    print(f"{'='*60}\n")


# ---- RUN DIRECTLY TO TEST ----

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from data_fetcher import fetch_company_data
    from financial_analysis import calculate_ratios, calculate_growth_rates, run_dcf

    if len(sys.argv) > 1:
        symbol = sys.argv[1]
    else:
        symbol = input("Enter a stock ticker (e.g. AAPL, MSFT, JPM): ").strip().upper()

    print(f"Fetching data for {symbol}...")
    data = fetch_company_data(symbol)

    print("Calculating ratios and growth rates...")
    ratios = calculate_ratios(data)
    growth = calculate_growth_rates(data)
    dcf = run_dcf(data)

    sections = generate_commentary(data, ratios, growth, dcf)
    display_commentary(sections)
