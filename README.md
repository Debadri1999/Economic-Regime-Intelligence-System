# ERIS — Economic Regime Intelligence System

**Machine learning for empirical asset pricing** with a **regime-aware** architecture. This project uses the Gu, Kelly & Xiu (2020) monthly panel dataset (94 firm characteristics, 8 macro predictors, industry dummies) to predict excess returns, detect market regimes (HMM on macro variables), and evaluate a long–short decile portfolio. The design emphasizes **expanding-window validation** (no look-ahead bias), **regime-conditional performance**, and **interpretability** (SHAP by regime).

---

## Primary pipeline: Course ML (asset pricing)

The **main deliverable** is the course data pipeline and dashboard:

1. **Data:** Monthly parquet files (Data1: 2001–2021). Panel: `permno`, `month`, `ret_excess`, `mktcap_lag`, 8 macro, 94 characteristics, industry dummies.
2. **Validation:** Expanding window — train on all data before month *t*, predict month *t*. First OOS year configurable (default 2010).
3. **Models:** OLS, Ridge, Random Forest, XGBoost, LightGBM, and a **Regime-Aware Neural Network** (macro → regime embedding; characteristics + embedding → return).
4. **Regime:** HMM on 8 macro variables (Bull / Transition / Bear); stress index from term spread, default spread, stock variance.
5. **Portfolio:** Decile long–short (value-weighted by `mktcap_lag`); cumulative returns, Sharpe, max drawdown, alpha.
6. **Interpretability:** SHAP feature importance by regime; **regime-conditional OOS R²** (performance in Bull vs Bear vs Transition).

### Run the course pipeline

```bash
# From project root. Requires Data1/ with YYYYMM.parquet (or YYYYMM_0.parquet) files.
python scripts/run_offline_pipeline.py
```

Outputs go to `data/processed/course/`: `predictions.parquet`, `regime_states.parquet`, `portfolio_returns.parquet`, `metrics.json`, `shap_importance_*.csv`.

### View results

- **Streamlit:** Run `streamlit run app.py`, open **Course ML** in the sidebar. It reads from `data/processed/course/` and shows model comparison, cumulative returns, regime timeline, SHAP by regime, and regime-conditional R².
- **Static web dashboard:** After the pipeline, run `python scripts/export_dashboard_data.py`, then open `dashboard/index.html` (or serve `dashboard/` with a local server).

### One-line reproducibility (optional)

```bash
# Unix/macOS
./run_course_pipeline.sh

# Or manually
python scripts/run_offline_pipeline.py && python scripts/export_dashboard_data.py
```

---

## Project structure

```
├── config.yaml              # Course: parquet_dir, first_prediction_year, macro_cols
├── Data1/                   # Parquet files (YYYYMM.parquet or YYYYMM_0.parquet)
├── data/
│   ├── loaders/             # course_data.py: load panel, feature columns
│   └── processed/course/    # Pipeline outputs (predictions, regime, portfolio, metrics)
├── ml/                      # Course ML pipeline (primary for grading)
│   ├── validation.py       # ExpandingWindowSplit, oos_r2, regime_conditional_r2
│   ├── baselines.py        # OLS, Ridge, RF, XGBoost, LightGBM
│   ├── regime_aware_nn.py  # Two-headed PyTorch net
│   ├── regime_detection.py # HMM on macro, stress index
│   ├── portfolio.py        # Decile long-short, Sharpe, drawdown, alpha
│   └── interpretability.py # SHAP by regime
├── models/                  # Legacy NLP (sentiment, topics, text-based regime)
│   ├── sentiment_engine.py # FinBERT
│   ├── topic_engine.py     # BERTopic
│   └── regime_detector.py  # HMM on daily sentiment
├── scripts/
│   ├── run_offline_pipeline.py   # Full course pipeline (8 steps)
│   └── export_dashboard_data.py  # Export to dashboard/data/
├── dashboard/               # Static web dashboard (HTML/JS)
├── pages/                   # Streamlit pages
│   └── 8_Course_ML.py      # Course results (OOS R², portfolio, regime, SHAP)
├── notebooks/               # Jupyter notebook(s) for clarity deliverable
└── requirements-course.txt  # Minimal deps for course pipeline only
```

**Note:** `ml/` is the **course asset-pricing pipeline**. `models/` holds the original **NLP/text-based** components (FinBERT, BERTopic, daily regime from sentiment); these are secondary and can be used as “alternative data” or disabled for a course-only submission.

---

## Setup

### Full environment (Streamlit + NLP + course)

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### Course pipeline only (minimal)

```bash
pip install -r requirements-course.txt
```

Place parquet files in **Data1/** (or set `course.parquet_dir` in `config.yaml`). Configure `config.yaml` → `course`: `sample` (full 1957–2021 or recent 2001–2021), `first_prediction_year` (e.g. 2010), `macro_cols` (must match your parquet columns: e.g. `macro_dp`, `macro_tbl`, `macro_tms`, `macro_dfy`, `macro_svar`, `macro_ep`, `macro_ntis`, `macro_bm`).

---

## Deliverables (course guidelines)

- **Codebase:** `scripts/run_offline_pipeline.py` (script) and/or `notebooks/` (Jupyter notebook walking through load → EDA → models → results).
- **Presentation:** Slides covering task, data choice, validation, model comparison, regime-aware design, portfolio performance, regime-conditional R², SHAP, limitations. Include **AI Acknowledgment** if tools were used.
- **Dashboard:** Streamlit **Course ML** page and/or static `dashboard/` show model comparison, cumulative returns, regime, SHAP.

---

## Alternative: NLP/text pipeline (legacy)

ERIS originally combined **financial text** (news, Fed, earnings) with **NLP** (FinBERT, BERTopic) and **daily regime** detection. That pipeline is still available:

- **Data:** NewsAPI, Fed scraper, market (yfinance/FRED), Kaggle, earnings CSV → `raw_articles`, `fed_documents`, `market_daily`, etc.
- **Preprocessing:** `data/preprocessing/preprocess` → `documents_processed`.
- **NLP:** FinBERT → `nlp_signals`; BERTopic → topic labels.
- **Regime:** HMM on daily sentiment → `regime_states` (Risk-On / Transitional / Risk-Off).

Run from sidebar “Run pipeline now” or:

```bash
python run_phase2_and_3.py
streamlit run app.py
```

Pages: Dashboard, Sentiment, Topics, Regime, Market Link, AI Briefing, KPI, **Course ML**.

---

## License and disclaimer

This project is for research and course demonstration. Not financial advice. Use at your own risk.
