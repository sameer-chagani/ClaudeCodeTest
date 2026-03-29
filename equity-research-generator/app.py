"""
Flask web server for the Equity Research Platform.
Provides a browser-based interface for generating and viewing
real-time equity research reports.
"""

import json
import os
import threading
import uuid
import math

from flask import Flask, jsonify, render_template, request

from data_fetcher import fetch_company_data, format_number
from financial_analysis import calculate_ratios, calculate_growth_rates, run_dcf, pct

app = Flask(__name__)

jobs = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """Kick off report generation in a background thread."""
    body = request.get_json()
    ticker = body.get("ticker", "").strip().upper()

    if not ticker or not ticker.isalpha() or len(ticker) > 5:
        return jsonify({"error": "Invalid ticker symbol"}), 400

    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"status": "running", "progress": "Initializing..."}

    def run():
        try:
            jobs[job_id]["progress"] = "Fetching financial data..."
            data = fetch_company_data(ticker)

            jobs[job_id]["progress"] = "Calculating financial ratios..."
            ratios = calculate_ratios(data)

            jobs[job_id]["progress"] = "Computing growth rates..."
            growth = calculate_growth_rates(data)

            jobs[job_id]["progress"] = "Running DCF valuation model..."
            dcf = run_dcf(data)

            # Build result payload
            info = data["info"]
            market_cap = info.get("marketCap", 0)
            if market_cap >= 1e12:
                cap_str = f"${market_cap/1e12:.2f}T"
            elif market_cap >= 1e9:
                cap_str = f"${market_cap/1e9:.2f}B"
            else:
                cap_str = f"${market_cap/1e6:.2f}M"

            # Format ratios
            ratios_formatted = {}
            for key, r in ratios.items():
                val = r["value"]
                if val is None:
                    formatted = "N/A"
                elif r.get("format") == "pct":
                    formatted = pct(val)
                else:
                    formatted = f"{val:.2f}" if isinstance(val, float) else str(val)
                ratios_formatted[key] = {
                    "label": r["label"],
                    "value": formatted,
                    "description": r.get("description", ""),
                }

            # Format growth
            growth_formatted = {}
            for key, g in growth.items():
                growth_formatted[key] = {
                    "label": g["label"],
                    "yoy_rates": [pct(r) for r in g["yoy_rates"]],
                    "cagr": pct(g["cagr"]),
                }

            # Format DCF
            dcf_formatted = {}
            if "error" in dcf:
                dcf_formatted["error"] = dcf["error"]
            else:
                dcf_formatted = {
                    "base_fcf": format_number(dcf["base_fcf"]),
                    "estimated_growth": pct(dcf["estimated_growth"]),
                    "terminal_growth": pct(dcf["terminal_growth"]),
                    "wacc": pct(dcf["wacc"]),
                    "projection_years": dcf["projection_years"],
                    "enterprise_value": format_number(dcf["enterprise_value"]),
                    "equity_value": format_number(dcf["equity_value"]),
                    "implied_price": f"${dcf['implied_price']:.2f}",
                    "current_price": f"${dcf['current_price']:.2f}" if dcf["current_price"] else "N/A",
                    "upside": pct(dcf["upside"]) if dcf["upside"] is not None else "N/A",
                    "upside_raw": dcf["upside"],
                    "net_debt": format_number(dcf["net_debt"]) if dcf["net_debt"] is not None else "N/A",
                    "projected_fcf": [
                        {
                            "year": p["year"],
                            "growth_rate": pct(p["growth_rate"]),
                            "fcf": format_number(p["fcf"]),
                            "pv": format_number(pv),
                        }
                        for p, pv in zip(dcf["projected_fcf"], dcf["pv_fcfs"])
                    ],
                    "terminal_value": format_number(dcf["terminal_value"]),
                    "pv_terminal": format_number(dcf["pv_terminal"]),
                }

            # Price history for chart (sample every 3rd day)
            price_data = []
            ph = data["price_history"]
            if not ph.empty:
                sampled = ph.iloc[::3]
                for date, row in sampled.iterrows():
                    price_data.append({
                        "date": date.strftime("%Y-%m-%d"),
                        "close": round(row["Close"], 2),
                        "volume": int(row["Volume"]),
                    })

            # Revenue chart data
            revenue_data = []
            income = data["income_stmt"]
            if not income.empty:
                for col in income.columns:
                    year = col.strftime("%Y")
                    rev = income.loc["Total Revenue", col] if "Total Revenue" in income.index else 0
                    gp = income.loc["Gross Profit", col] if "Gross Profit" in income.index else 0
                    ni_key = "Net Income From Continuing Operation Net Minority Interest"
                    ni = income.loc[ni_key, col] if ni_key in income.index else 0

                    def clean(v):
                        if v is None or (isinstance(v, float) and math.isnan(v)):
                            return 0
                        return round(v / 1e9, 2)

                    revenue_data.append({
                        "year": year,
                        "revenue": clean(rev),
                        "gross_profit": clean(gp),
                        "net_income": clean(ni),
                    })
                revenue_data.reverse()

            jobs[job_id] = {
                "status": "complete",
                "result": {
                    "ticker": ticker,
                    "company_name": info.get("longName", ticker),
                    "sector": info.get("sector", "N/A"),
                    "industry": info.get("industry", "N/A"),
                    "current_price": info.get("currentPrice", "N/A"),
                    "market_cap": cap_str,
                    "high_52w": info.get("fiftyTwoWeekHigh", "N/A"),
                    "low_52w": info.get("fiftyTwoWeekLow", "N/A"),
                    "pe_trailing": info.get("trailingPE", "N/A"),
                    "dividend_yield": pct(info.get("dividendYield")) if info.get("dividendYield") else "N/A",
                    "description": info.get("longBusinessSummary", "")[:300],
                    "ratios": ratios_formatted,
                    "growth": growth_formatted,
                    "dcf": dcf_formatted,
                    "price_data": price_data,
                    "revenue_data": revenue_data,
                },
            }
        except Exception as e:
            jobs[job_id] = {"status": "error", "error": str(e)}

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/status/<job_id>")
def api_status(job_id):
    """Poll job status."""
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(job)


if __name__ == "__main__":
    print("\n  Equity Research Platform")
    print("  Open http://127.0.0.1:8000 in your browser\n")
    app.run(debug=True, host="0.0.0.0", port=8000)
