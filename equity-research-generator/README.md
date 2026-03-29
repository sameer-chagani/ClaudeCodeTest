# Equity Research Platform

A full-stack web application that generates comprehensive equity research reports for any publicly traded stock. Enter a ticker symbol and get real-time financial analysis including ratio calculations, growth metrics, and DCF valuation — all presented in an interactive dashboard.

**[Live Demo](https://equity-research-generator.onrender.com)** _(update this link after deployment)_

## Features

- **Real-Time Data** — Fetches live financial statements and market data via Yahoo Finance
- **15+ Financial Ratios** — Valuation (P/E, EV/EBITDA, P/B), profitability (margins, ROE, ROA), leverage (D/E, interest coverage), and cash flow metrics
- **Growth Analysis** — Year-over-year growth rates and CAGR for revenue, earnings, EBITDA, and free cash flow
- **DCF Valuation Model** — 5-year discounted cash flow projection with terminal value (Gordon Growth Model) to derive implied share price
- **Interactive Charts** — Price history, revenue breakdown, and profitability margin visualizations
- **Responsive Design** — Works on desktop and mobile

## Screenshots

![Dashboard](https://via.placeholder.com/800x450?text=Dashboard+Screenshot)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask |
| Data | yfinance, pandas |
| Frontend | Vanilla JS, Chart.js |
| Styling | Custom CSS (dark theme) |

## Getting Started

```bash
# Clone the repo
git clone https://github.com/sameer-chagani/ClaudeCodeTest.git
cd ClaudeCodeTest/equity-research-generator

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py
```

Then open [http://localhost:8000](http://localhost:8000) in your browser.

### CLI Mode

```bash
python main.py AAPL
```

## Project Structure

```
equity-research-generator/
├── app.py                 # Flask server & API endpoints
├── data_fetcher.py        # Yahoo Finance data retrieval
├── financial_analysis.py  # Ratio calculations, growth rates, DCF model
├── main.py                # CLI entry point
├── templates/
│   └── index.html         # Single-page frontend
├── requirements.txt
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serve the web UI |
| `POST` | `/api/generate` | Start analysis job (`{"ticker": "AAPL"}`) |
| `GET` | `/api/status/<job_id>` | Poll job progress and results |

## How It Works

1. User enters a stock ticker
2. Backend fetches financial data from Yahoo Finance (income statement, balance sheet, cash flow, 2-year price history)
3. Calculates financial ratios, YoY growth rates, and CAGR
4. Runs a DCF valuation model with projected free cash flows and terminal value
5. Returns structured data to the frontend for interactive visualization

## Author

**Sameer Chagani** — [GitHub](https://github.com/sameer-chagani)
