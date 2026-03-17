"""
REPORT GENERATOR — Creates a professional PDF equity research report.

WHAT YOU'RE LEARNING HERE:
- How to generate PDFs programmatically with fpdf2
- How to create financial charts with matplotlib
- How to lay out a multi-page document with headers, tables, and images
- How to save matplotlib charts as temporary images and embed them in a PDF

KEY CONCEPTS:
- fpdf2 builds PDFs by placing text, lines, and images at exact coordinates
- matplotlib creates charts that we save as PNG files, then embed in the PDF
- We use tempfile to avoid leaving chart images on disk after the report is done
"""

import math
import os
import tempfile

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend — no GUI window needed
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from fpdf import FPDF

from data_fetcher import format_number
from financial_analysis import pct


# ---- CHART GENERATION ----

def create_price_chart(data, output_path):
    """
    Creates a stock price history chart (line chart with volume bars).
    Saves it as a PNG file at output_path.
    """
    price_history = data["price_history"]
    if price_history.empty:
        return False

    fig, ax1 = plt.subplots(figsize=(8, 3.5))
    fig.patch.set_facecolor("#FAFBFC")
    ax1.set_facecolor("#FAFBFC")

    # Price line with gradient fill
    ax1.plot(price_history.index, price_history["Close"], color="#1a56db", linewidth=2)
    ax1.fill_between(price_history.index, price_history["Close"], alpha=0.08, color="#1a56db")
    ax1.set_ylabel("Price ($)", fontsize=9, fontweight="bold", color="#333")
    ax1.tick_params(axis="both", labelsize=8, colors="#555")
    ax1.grid(True, alpha=0.2, linestyle="--")
    ax1.spines["top"].set_visible(False)

    # Volume bars on secondary axis
    ax2 = ax1.twinx()
    ax2.bar(price_history.index, price_history["Volume"], alpha=0.12, color="#94a3b8", width=1)
    ax2.set_ylabel("Volume", fontsize=9, color="#888")
    ax2.tick_params(axis="y", labelsize=7, colors="#888")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1e6:.0f}M"))
    ax2.spines["top"].set_visible(False)

    plt.title(f"{data['ticker']} - 2-Year Price History", fontsize=12, fontweight="bold", color="#1a1a2e", pad=12)
    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="#FAFBFC")
    plt.close(fig)
    return True


def create_revenue_profit_chart(data, output_path):
    """
    Creates a bar chart comparing Revenue, Gross Profit, and Net Income over time.
    """
    income = data["income_stmt"]
    if income.empty:
        return False

    years = [col.strftime("%Y") for col in income.columns]

    def get_values(row_name):
        if row_name not in income.index:
            return [0] * len(years)
        vals = []
        for v in income.loc[row_name]:
            if v is None or (isinstance(v, float) and math.isnan(v)):
                vals.append(0)
            else:
                vals.append(v / 1e9)  # Convert to billions
        return vals

    revenue = get_values("Total Revenue")
    gross_profit = get_values("Gross Profit")
    net_income = get_values("Net Income From Continuing Operation Net Minority Interest")

    x = range(len(years))
    width = 0.25

    fig, ax = plt.subplots(figsize=(8, 3.5))
    fig.patch.set_facecolor("#FAFBFC")
    ax.set_facecolor("#FAFBFC")

    ax.bar([i - width for i in x], revenue, width, label="Revenue", color="#1a56db", zorder=3)
    ax.bar(x, gross_profit, width, label="Gross Profit", color="#059669", zorder=3)
    ax.bar([i + width for i in x], net_income, width, label="Net Income", color="#d97706", zorder=3)

    ax.set_ylabel("$ Billions", fontsize=9, fontweight="bold", color="#333")
    ax.set_xticks(x)
    ax.set_xticklabels(years, fontsize=9)
    ax.legend(fontsize=8, framealpha=0.9, edgecolor="#ddd")
    ax.grid(True, axis="y", alpha=0.2, linestyle="--", zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(colors="#555")
    plt.title(f"{data['ticker']} - Revenue & Profitability", fontsize=12, fontweight="bold", color="#1a1a2e", pad=12)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="#FAFBFC")
    plt.close(fig)
    return True


def create_margin_chart(ratios, output_path):
    """
    Creates a horizontal bar chart of key profitability margins.
    """
    margin_keys = [
        ("gross_margin", "Gross Margin"),
        ("operating_margin", "Operating Margin"),
        ("net_margin", "Net Margin"),
        ("roe", "ROE"),
        ("roa", "ROA"),
        ("fcf_margin", "FCF Margin"),
    ]

    labels = []
    values = []
    for key, label in margin_keys:
        if key in ratios and ratios[key]["value"] is not None:
            labels.append(label)
            values.append(ratios[key]["value"] * 100)  # Convert to percentage

    if not values:
        return False

    fig, ax = plt.subplots(figsize=(8, 2.5))
    fig.patch.set_facecolor("#FAFBFC")
    ax.set_facecolor("#FAFBFC")

    colors = ["#1a56db" if v >= 0 else "#dc2626" for v in values]
    bars = ax.barh(labels, values, color=colors, height=0.5, zorder=3)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=8, fontweight="bold", color="#333")

    ax.set_xlabel("Percentage (%)", fontsize=9, fontweight="bold", color="#333")
    ax.tick_params(axis="both", labelsize=8, colors="#555")
    ax.grid(True, axis="x", alpha=0.2, linestyle="--", zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.title("Profitability & Return Metrics", fontsize=12, fontweight="bold", color="#1a1a2e", pad=12)

    fig.tight_layout()
    fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor="#FAFBFC")
    plt.close(fig)
    return True


# ---- PDF REPORT CLASS ----

def _sanitize(text):
    """
    Replace unicode characters that Helvetica (latin-1) can't render.
    fpdf2's built-in fonts only support latin-1, so em-dashes, curly quotes,
    etc. need to be replaced with ASCII equivalents.
    """
    replacements = {
        "\u2014": "-",   # em-dash
        "\u2013": "-",   # en-dash
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2022": "*",   # bullet
        "\u2026": "...", # ellipsis
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


class ResearchReport(FPDF):
    """
    Custom FPDF subclass for our equity research report.

    WHY SUBCLASS?
    fpdf2 lets you override header() and footer() so they automatically
    appear on every page. This keeps the layout consistent without
    repeating code.
    """

    def __init__(self, ticker, company_name):
        super().__init__()
        self.ticker = ticker
        self.company_name = company_name
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 6, f"{self.ticker} | Equity Research Report", align="L")
        self.ln(3)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title):
        """Prints a bold section header with a colored underline."""
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(25, 25, 112)  # Dark blue
        self.cell(0, 10, title)
        self.ln(8)
        self.set_draw_color(25, 25, 112)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def body_text(self, text):
        """Prints regular body text with proper wrapping."""
        self.set_font("Helvetica", "", 9)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5, _sanitize(text))
        self.ln(2)

    def key_value_row(self, label, value, bold_value=False):
        """Prints a label: value pair on one line."""
        self.set_font("Helvetica", "", 9)
        self.set_text_color(80, 80, 80)
        self.cell(70, 5, _sanitize(label))
        style = "B" if bold_value else ""
        self.set_font("Helvetica", style, 9)
        self.set_text_color(40, 40, 40)
        self.cell(0, 5, _sanitize(str(value)))
        self.ln(5)


# ---- REPORT BUILDER ----

def generate_report(data, ratios, growth, dcf, commentary=None, output_path=None):
    """
    Generates the full PDF report and saves it to disk.

    Args:
        data: Raw financial data from fetch_company_data()
        ratios: Calculated ratios from calculate_ratios()
        growth: Growth rates from calculate_growth_rates()
        dcf: DCF results from run_dcf()
        commentary: AI-generated sections (optional, can be None)
        output_path: Where to save the PDF (optional, defaults to {ticker}_equity_research.pdf)

    Returns:
        The file path of the generated PDF.
    """
    info = data["info"]
    ticker = data["ticker"]
    company_name = info.get("longName", ticker)

    pdf = ResearchReport(ticker, company_name)
    pdf.alias_nb_pages()
    pdf.add_page()

    # ---- COVER / TITLE ----
    # Colored header bar
    pdf.set_fill_color(25, 25, 112)
    pdf.rect(10, pdf.get_y() - 2, 190, 50, "F")

    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 18, company_name, align="C")
    pdf.ln(14)

    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(200, 210, 255)
    pdf.cell(0, 8, f"{ticker}  |  {info.get('sector', '')}  |  {info.get('industry', '')}", align="C")
    pdf.ln(8)

    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(180, 190, 220)
    pdf.cell(0, 6, "Equity Research Report", align="C")
    pdf.ln(18)

    # Reset text color
    pdf.set_text_color(40, 40, 40)

    # ---- MARKET SNAPSHOT ----
    pdf.section_title("Market Snapshot")

    market_cap = info.get("marketCap", 0)
    if market_cap >= 1e12:
        cap_str = f"${market_cap/1e12:.2f}T"
    elif market_cap >= 1e9:
        cap_str = f"${market_cap/1e9:.2f}B"
    else:
        cap_str = f"${market_cap/1e6:.2f}M"

    snapshot_items = [
        ("Current Price", f"${info.get('currentPrice', 'N/A')}"),
        ("Market Cap", cap_str),
        ("52-Week High", f"${info.get('fiftyTwoWeekHigh', 'N/A')}"),
        ("52-Week Low", f"${info.get('fiftyTwoWeekLow', 'N/A')}"),
        ("P/E (Trailing)", f"{info.get('trailingPE', 'N/A')}"),
        ("Dividend Yield", pct(info.get('dividendYield')) if info.get('dividendYield') else "N/A"),
    ]

    for label, value in snapshot_items:
        pdf.key_value_row(label, value)
    pdf.ln(5)

    # ---- PRICE CHART ----
    with tempfile.TemporaryDirectory() as tmpdir:
        price_chart_path = os.path.join(tmpdir, "price_chart.png")
        rev_chart_path = os.path.join(tmpdir, "rev_chart.png")
        margin_chart_path = os.path.join(tmpdir, "margin_chart.png")

        if create_price_chart(data, price_chart_path):
            pdf.image(price_chart_path, x=10, w=190)
            pdf.ln(5)

        # ---- AI COMMENTARY (if available) ----
        if commentary:
            commentary_sections = [
                ("executive_summary", "Executive Summary"),
                ("financial_analysis", "Financial Analysis"),
                ("growth_assessment", "Growth Assessment"),
                ("valuation_analysis", "Valuation Analysis"),
                ("risk_factors", "Risk Factors"),
                ("investment_thesis", "Investment Thesis"),
            ]

            for key, title in commentary_sections:
                if key in commentary:
                    pdf.add_page()
                    pdf.section_title(title)
                    pdf.body_text(commentary[key])

        # ---- KEY RATIOS TABLE ----
        pdf.add_page()
        pdf.section_title("Key Financial Ratios")

        ratio_groups = [
            ("Valuation", ["pe_trailing", "pe_forward", "ev_ebitda", "price_to_book", "price_to_sales"]),
            ("Profitability", ["gross_margin", "operating_margin", "net_margin", "roe", "roa"]),
            ("Leverage", ["debt_to_equity", "net_debt_to_ebitda", "interest_coverage"]),
            ("Cash Flow", ["fcf_yield", "fcf_margin", "capex_to_revenue"]),
        ]

        for group_name, keys in ratio_groups:
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(25, 25, 112)
            pdf.cell(0, 7, group_name)
            pdf.ln(6)

            for key in keys:
                if key not in ratios:
                    continue
                r = ratios[key]
                val = r["value"]
                if val is None:
                    formatted = "N/A"
                elif r.get("format") == "pct":
                    formatted = pct(val)
                else:
                    formatted = f"{val:.2f}" if isinstance(val, float) else str(val)
                pdf.key_value_row(f"  {r['label']}", formatted)

            pdf.ln(3)

        # ---- REVENUE & PROFITABILITY CHART ----
        if create_revenue_profit_chart(data, rev_chart_path):
            pdf.add_page()
            pdf.section_title("Revenue & Profitability")
            pdf.image(rev_chart_path, x=10, w=190)
            pdf.ln(5)

        # ---- MARGIN CHART ----
        if create_margin_chart(ratios, margin_chart_path):
            pdf.image(margin_chart_path, x=10, w=190)
            pdf.ln(5)

        # ---- GROWTH RATES ----
        pdf.add_page()
        pdf.section_title("Growth Rates")

        for _, g in growth.items():
            label = g["label"]
            yoy = g["yoy_rates"]
            cagr = g["cagr"]
            yoy_str = ", ".join(pct(r) for r in yoy)
            pdf.key_value_row(label, f"YoY: {yoy_str}  |  CAGR: {pct(cagr)}")

        pdf.ln(5)

        # ---- DCF VALUATION ----
        pdf.add_page()
        pdf.section_title("DCF Valuation")

        if "error" in dcf:
            pdf.body_text(dcf["error"])
        else:
            dcf_items = [
                ("Base Free Cash Flow", format_number(dcf["base_fcf"])),
                ("Estimated Growth Rate", pct(dcf["estimated_growth"])),
                ("Terminal Growth Rate", pct(dcf["terminal_growth"])),
                ("WACC (Discount Rate)", pct(dcf["wacc"])),
                ("Projection Period", f"{dcf['projection_years']} years"),
                ("", ""),  # Spacer
                ("Enterprise Value", format_number(dcf["enterprise_value"])),
                ("Equity Value", format_number(dcf["equity_value"])),
                ("", ""),
                ("Implied Share Price", f"${dcf['implied_price']:.2f}"),
                ("Current Price", f"${dcf['current_price']:.2f}"),
            ]

            if dcf["upside"] is not None:
                direction = "Upside" if dcf["upside"] >= 0 else "Downside"
                dcf_items.append((f"Implied {direction}", pct(abs(dcf["upside"]))))

            for label, value in dcf_items:
                if label == "":
                    pdf.ln(2)
                else:
                    bold = label in ("Implied Share Price", "Current Price")
                    pdf.key_value_row(label, value, bold_value=bold)

            # Projected FCF table
            pdf.ln(5)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(25, 25, 112)
            pdf.cell(0, 7, "Projected Free Cash Flows")
            pdf.ln(6)

            # Table header
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(255, 255, 255)
            pdf.set_fill_color(25, 25, 112)
            pdf.cell(30, 6, "Year", border=1, fill=True, align="C")
            pdf.cell(40, 6, "Growth Rate", border=1, fill=True, align="C")
            pdf.cell(50, 6, "FCF", border=1, fill=True, align="C")
            pdf.cell(50, 6, "PV(FCF)", border=1, fill=True, align="C")
            pdf.ln()

            # Table rows
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(40, 40, 40)
            for proj, pv in zip(dcf["projected_fcf"], dcf["pv_fcfs"]):
                pdf.cell(30, 5, str(proj["year"]), border=1, align="C")
                pdf.cell(40, 5, pct(proj["growth_rate"]), border=1, align="C")
                pdf.cell(50, 5, format_number(proj["fcf"]), border=1, align="C")
                pdf.cell(50, 5, format_number(pv), border=1, align="C")
                pdf.ln()

            # Terminal value row
            pdf.set_font("Helvetica", "B", 8)
            pdf.cell(70, 5, "Terminal Value", border=1, align="C")
            pdf.cell(50, 5, format_number(dcf["terminal_value"]), border=1, align="C")
            pdf.cell(50, 5, format_number(dcf["pv_terminal"]), border=1, align="C")
            pdf.ln()

        # ---- DISCLAIMER ----
        pdf.add_page()
        pdf.section_title("Disclaimer")
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(120, 120, 120)
        pdf.multi_cell(0, 4,
            "This report was auto-generated for educational purposes only. "
            "It does not constitute investment advice, a recommendation, or an offer to buy or sell securities. "
            "The financial data is sourced from Yahoo Finance and may contain errors or delays. "
            "The DCF valuation uses simplified assumptions and should not be relied upon for investment decisions. "
            "AI-generated commentary (if included) is produced by a language model and may contain inaccuracies. "
            "Always consult a qualified financial advisor before making investment decisions."
        )

    # ---- SAVE ----
    output_filename = output_path or f"{ticker}_equity_research.pdf"
    pdf.output(output_filename)
    return output_filename


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

    print("Generating PDF report...")
    output = generate_report(data, ratios, growth, dcf)
    print(f"Report saved: {output}")
