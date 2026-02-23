# ERIS — Economic Regime Intelligence System
## Complete Project Understanding Report

**Target audience:** Graduate students and stakeholders  
**Purpose:** Full documentation of datasets, models, evaluation criteria, and workflow  
**Last updated:** Per repository

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Dataset & Data Sources](#2-dataset--data-sources)
3. [Pipeline Architecture](#3-pipeline-architecture)
4. [Models & How They Work](#4-models--how-they-work)
5. [Regime Detection & Stress Index](#5-regime-detection--stress-index)
6. [Evaluation Parameters](#6-evaluation-parameters)
7. [Portfolio Construction](#7-portfolio-construction)
8. [Output Artifacts](#8-output-artifacts)
9. [Notebooks & Scripts](#9-notebooks--scripts)
10. [Dashboard & Visualization](#10-dashboard--visualization)

---

## 1. Project Overview

**ERIS** (Economic Regime Intelligence System) is an ML-driven system for:

- **Return prediction** — Predict monthly excess stock returns using firm characteristics and macro variables  
- **Regime detection** — Identify market regimes (Bull, Transition, Bear) via a Hidden Markov Model  
- **Stress index** — Composite indicator of market stress (0–100)  
- **Portfolio construction** — Decile long-short strategy based on predicted returns  
- **Interpretability** — SHAP-based feature importance by regime  
- **LLM integration** — Optional GPT-4 briefing for stakeholders (via Streamlit app)

**Core idea:** The relationship between firm characteristics and returns changes across regimes. The Regime-Aware Neural Network explicitly models this.

---

## 2. Dataset & Data Sources

### Primary Dataset: Gu, Kelly & Xiu (2020)

- **Source:** CRSP/Compustat monthly panel, processed per Gu, Kelly & Xiu (GKX) methodology  
- **Location:** `Data1/` folder containing `YYYYMM.parquet` files (e.g. `200101.parquet`, `200102.parquet`)  
- **Format:** Parquet files; one file per month  
- **Date range:** Configurable; default **2001–2021** (“recent” sample)  
- **Alternative:** 1957–2021 (“full” sample) — set `course.sample: "full"` in `config.yaml`

### Panel Structure (per row)

| Column type | Examples | Description |
|-------------|----------|-------------|
| **Identifiers** | `permno`, `month`, `month_dt` | Stock ID, month (YYYYMM or period) |
| **Target** | `ret_excess` | Monthly excess return (stock − risk-free) |
| **Weight** | `mktcap_lag` | Lagged market cap (for value-weighting) |
| **Macro (8)** | `macro_dp`, `macro_tms`, `macro_dfy`, `macro_svar`, `macro_tbl`, `macro_ep`, `macro_ntis`, `macro_bm` | Dividend yield, term spread, default spread, stock variance, T-bill, earnings yield, net equity issuance, book-to-market |
| **Characteristics** | `characteristic_*` | ~94 firm characteristics (size, momentum, etc.) |
| **Industry** | `sic2_*` | SIC2 industry dummies |

### Macro Variables (8)

- **macro_dp** — Log dividend-to-price  
- **macro_tms** — Term spread (10Y − 3M Treasury)  
- **macro_dfy** — Default spread (Baa − Aaa corporate)  
- **macro_svar** — Stock market variance  
- **macro_tbl** — T-bill rate  
- **macro_ep** — Earnings-to-price  
- **macro_ntis** — Net equity issuance  
- **macro_bm** — Book-to-market  

### Feature Engineering

- **All features:** `macro_*` + `characteristic_*` + `sic2_*`  
- **Imputation:** Cross-sectional median per month for missing characteristics  
- **Target:** `ret_excess` (no transformation)  

---

## 3. Pipeline Architecture

### Validation: Expanding Window

- **No random split** — strictly time-ordered  
- **Train:** All months &lt; prediction month  
- **Test:** Single prediction month  
- **First OOS year:** 2010 (configurable)  
- **No look-ahead:** Features at month-start predict return at month-end  

### Retrain Schedule (Optimization)

| Component | Retrain every | Rationale |
|-----------|---------------|-----------|
| Baselines (OLS, Ridge, XGBoost, LightGBM) | 3 months | ~3× speedup, small R² impact |
| Regime-Aware NN | 6 months | NN is slower; relationships evolve slowly |

### Pipeline Steps (High Level)

1. Load panel from `Data1/*.parquet`  
2. Detect feature columns (macro, characteristic, industry)  
3. Run expanding-window baselines with quarterly retrain  
4. Run Regime-Aware NN with semi-annual retrain  
5. Fit HMM for regime detection; compute stress index  
6. Build decile long-short portfolio  
7. SHAP importance by regime  
8. Save artifacts to `data/processed/course/` or `results/`  

---

## 4. Models & How They Work

### 4.1 Baseline Models

| Model | Type | Parameters | Scaling |
|-------|------|------------|---------|
| **OLS** | Linear regression | — | StandardScaler |
| **Ridge** | L2-regularized linear | alpha=1.0 | StandardScaler |
| **XGBoost** | Gradient boosting | n_estimators=100, max_depth=6 | None |
| **LightGBM** | Gradient boosting | n_estimators=100, max_depth=6 | None |

**Input:** `all_features` (macro + characteristics + industry)  
**Output:** Predicted `ret_excess` per stock-month  

### 4.2 Regime-Aware Neural Network (Core Innovation)

**Architecture:**

```
Macro (8) → Regime Encoder (32 hidden → 16-dim embedding, ReLU)
                                            ↓
Characteristics + industry + embedding → Return Predictor (64 → 32 → 1, ReLU)
                                            ↓
                                    Predicted ret_excess
```

**Why it matters:** Baselines assume the same factor structure in all regimes. The Regime NN learns a regime embedding from macro variables and conditions the return predictor on it, so factor loadings can differ across Bull/Transition/Bear.

**Training:**
- Adam optimizer, MSE loss  
- 30 epochs, batch size 2048  
- Expanding window, semi-annual retrain  

**Inputs:**
- `X_macro`: 8 macro variables  
- `X_char`: characteristics + industry (≈100+ dimensions)  

---

## 5. Regime Detection & Stress Index

### Regime (HMM)

- **Method:** 3-state Gaussian HMM on 8 macro variables (z-scored)  
- **States:** Bull, Transition, Bear  
- **Labeling:** Ordered by mean of first macro (e.g. dividend yield): low → Bull, high → Bear  
- **Output:** One regime label per month (`regime_states.parquet`)  

### Stress Index (0–100)

**Formula:**  
`Stress = −macro_tms + macro_dfy + macro_svar`  
Then min-max normalized to 0–100.

**Interpretation:**
- **0–25 Low** — Favorable macro (positive term spread, low default spread, low volatility)  
- **25–50 Medium** — Moderate uncertainty  
- **50–75 High** — Elevated stress  
- **75–100 Extreme** — Severe stress (e.g. inverted curve, wide spreads)  

**Components:**
- **macro_tms** (negative weight): Inverted yield curve → stress  
- **macro_dfy**: Wider credit spread → stress  
- **macro_svar**: Higher stock variance → stress  

---

## 6. Evaluation Parameters

### 6.1 Model-Level Metrics (per model)

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **OOS R²** | 1 − SS_res/SS_tot | Fraction of variance explained. 0 = mean forecast; &gt;0 = better; &lt;0 = worse. For monthly returns, 1–3% is strong. |
| **OOS RMSE** | √(mean((y−ŷ)²)) | Root mean squared error. Lower = better. |
| **OOS MAE** | mean(\|y−ŷ\|) | Mean absolute error. Lower = better. |
| **IC (optional)** | Spearman corr(pred, ret) | Information coefficient. Higher = better rank correlation. |

### 6.2 Portfolio Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **Sharpe ratio** | (μ − r_f)/σ × √12 | Risk-adjusted return. Good: &gt;1.0; Medium: 0.5–1.0; Poor: &lt;0.5. |
| **Max drawdown** | min((cum − run_max)/run_max) | Largest peak-to-trough decline. More negative = worse. |
| **Annualized alpha** | (μ_strat − μ_mkt) × 12 | Excess return vs. value-weighted market. |
| **Long-short spread (mean)** | mean(long_ret − short_ret) | Average monthly decile spread. Positive = strategy adds value. |

### 6.3 Regime-Conditional Metrics

| Metric | Description |
|--------|-------------|
| **Regime-conditional R²** | OOS R² computed separately in Bull, Bear, Transition. Shows whether models perform differently across regimes. |

### 6.4 Where Each Metric Is Computed

| Metric | Module | Location |
|--------|--------|----------|
| OOS R², RMSE, MAE | `ml/validation.py` | `oos_r2()`, `oos_rmse()`, `oos_mae()` |
| Regime-conditional R² | `ml/validation.py` | `regime_conditional_r2()` |
| Sharpe, MaxDD, Alpha | `ml/portfolio.py` | `portfolio_metrics()` |
| SHAP importance | `ml/interpretability.py` | `feature_importance_by_regime()` |

---

## 7. Portfolio Construction

- **Strategy:** Decile long-short  
  - Long top 10% by predicted return  
  - Short bottom 10%  
- **Weighting:** Value-weighted by `mktcap_lag`  
- **Benchmark:** Value-weighted market return (same panel)  
- **Output:** Monthly strategy return, cumulative returns, portfolio metrics  

---

## 8. Output Artifacts

| File | Description |
|------|-------------|
| `predictions.parquet` | month_dt, permno, ret_excess, pred_OLS, pred_Ridge, pred_XGBoost, pred_LightGBM, pred_RegimeNN |
| `regime_states.parquet` | month_dt, regime_label, hmm_state, stress_index, macro_* |
| `portfolio_returns.parquet` | month_dt, strategy_return, market_return, cum_strategy, cum_market |
| `metrics.json` | baseline_metrics (per model: oos_r2, oos_rmse, oos_mae), portfolio_metrics, regime_conditional_r2 |
| `shap_importance_{Bull,Bear,Transition}.csv` | feature, importance (SHAP) |
| `feature_columns.json` | all_features, macro, characteristic |

**Output directories:**
- **Pipeline:** `data/processed/course/`  
- **Notebook:** `results/`  

---

## 9. Notebooks & Scripts

### Notebooks

| Notebook | Purpose | Evaluation criteria |
|----------|---------|---------------------|
| **ERIS_Optimized_Pipeline.ipynb** | **Main / updated notebook** — full walkthrough | OOS R², RMSE, MAE, IC, Sharpe, MaxDD, Alpha, regime-conditional R² |

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/run_offline_pipeline.py` | Run full pipeline; outputs to `data/processed/course/` |
| `scripts/export_dashboard_data.py` | Export artifacts to `dashboard/data/*.json` |
| `run_course_pipeline.sh` | Shell wrapper to run pipeline |

### Config

- **config.yaml** — `course.parquet_dir`, `first_prediction_year`, `retrain_baselines_every`, `retrain_nn_every`, `macro_cols`, `stress_weights`  

---

## 10. Dashboard & Visualization

- **Location:** `dashboard/index.html`  
- **Data:** `dashboard/data/*.json` (from export script)  
- **Serving:** `serve.bat` or `python -m http.server 8080` in `dashboard/`  
- **Tabs:** Main Dashboard, Regime System, Data Briefing, Market Signals, AI Briefing, Regime NN  

**Key visualizations:**
- Stress gauge (0–100)  
- Regime timeline (Bull/Transition/Bear)  
- Stress index over time  
- Model comparison (OOS R² bar chart)  
- Cumulative returns (strategy vs market)  
- SHAP importance by regime  
- Model evaluation table (OOS R², RMSE, MAE)  

---

## Quick Reference: Evaluation Parameters Summary

| Category | Metrics |
|----------|---------|
| **Prediction** | OOS R², OOS RMSE, OOS MAE |
| **Portfolio** | Sharpe ratio, Max drawdown, Annualized alpha, Long-short spread mean |
| **Regime** | Regime-conditional R² (per regime per model) |
| **Interpretability** | SHAP importance by regime (Bull, Bear, Transition) |

---

## References

- Gu, S., Kelly, B., & Xiu, D. (2020). Empirical asset pricing via machine learning. *Review of Financial Studies*, 33(5), 2223–2273.
- `dataset.pdf` — Course dataset documentation  
- `general_guidelines.pdf` — Project guidelines  
