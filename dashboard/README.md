# ERIS Web Dashboard

Modern, stakeholder-ready web dashboard for the Economic Regime Intelligence System. Shows model comparison, regime detection, portfolio performance, and SHAP interpretability.

## Setup

1. **Generate data** (after running the offline pipeline):
   ```bash
   # From project root
   python scripts/export_dashboard_data.py
   ```
   This writes `dashboard/data/metrics.json`, `portfolio.json`, `regime.json`, and `shap_by_regime.json` from `data/processed/course/`.

2. **Open the dashboard**:
   - **Option A — Local file:** Open `dashboard/index.html` in a browser. Some browsers block `fetch()` for `file://`; use Option B if charts don’t load.
   - **Option B — Local server:**
     ```bash
     cd dashboard
     python -m http.server 8080
     ```
     Then open http://localhost:8080

## Features

- **Hero KPIs:** Sharpe ratio, best OOS R², annualized alpha, max drawdown
- **Methodology:** Six-step overview (data → baselines → regime NN → regime & stress → portfolio → SHAP)
- **Model comparison:** Bar chart and table of out-of-sample R²
- **Regime:** HMM state timeline (Bull / Transition / Bear) and stress index over time
- **Portfolio:** Cumulative return of long–short strategy vs market (hero chart)
- **SHAP by regime:** Top feature importance in Bull, Bear, and Transition regimes
- **Theme:** Light/dark toggle (top-right)

## Tech

- Vanilla HTML/CSS/JS; no build step
- [ApexCharts](https://apexcharts.com/) for charts
- CSS variables for theming; responsive layout

## Deployment

- Upload the `dashboard/` folder to any static host (Netlify, Vercel, GitHub Pages, S3).
- Ensure `data/*.json` are included (run `export_dashboard_data.py` before deploy) or host the JSON elsewhere and set `DATA_BASE` in `js/app.js`.
