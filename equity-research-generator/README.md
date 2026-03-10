# Equity Research Report Generator

Auto-generate professional equity research reports for any publicly traded stock.

## What It Does
- Pulls live financial data (income statement, balance sheet, cash flow)
- Calculates key ratios (P/E, ROE, margins, growth rates)
- Runs a simplified DCF valuation
- Uses Claude AI to generate analyst-style commentary
- Outputs a formatted PDF report with charts

## Tech Stack
- Python 3.10+
- yfinance — financial data
- pandas — data manipulation
- matplotlib — charts
- anthropic — Claude AI for commentary
- fpdf2 — PDF generation

## Usage
```bash
python main.py AAPL
```

## Project Structure
```
equity-research-generator/
├── main.py              # Entry point — run this
├── data_fetcher.py      # Pull financial data from APIs
├── financial_analysis.py # Ratios, growth rates, DCF
├── ai_commentary.py     # Claude API integration
├── report_generator.py  # PDF output with charts
├── requirements.txt     # Dependencies
└── README.md
```

## Author
Built as a portfolio project combining CFA L2 knowledge with Python and AI.
