# ERIS Course Data Pipeline (Gu, Kelly & Xiu)

Offline pipeline using the course dataset (monthly panel: 94 characteristics + 8 macro + industry dummies). No text/NLP in this pipeline.

## Data

- **Data1**: Folder of Parquet files named `YYYYMM.parquet` (e.g. `200101.parquet`, `202112.parquet`).
- Place **Data1** at project root or set `course.parquet_dir` in `config.yaml`.
- Columns expected: `permno`, `month`, `ret_excess`, `mktcap_lag`, `macro_*`, `characteristic_*`, `sic2_*`.

## Config (`config.yaml` → `course`)

- `parquet_dir`: Path to Data1 (default `Data1`).
- `sample`: `"recent"` (2001–2021) or `"full"` (1957–2021).
- `first_prediction_year`: First OOS month (e.g. `2010`); expanding window trains on all data before that month.
- `macro_cols`: List of 8 macro column names (used for HMM and stress index).
- `stress_weights`: Weights for stress index (e.g. `macro_tms: -1`, `macro_dfy: 1`, `macro_svar: 1`).

## Run offline pipeline

From **project root**:

```bash
python scripts/run_offline_pipeline.py
```

Steps:

1. Load panel from Data1 (stack parquet, drop null `ret_excess`, median impute).
2. Expanding-window validation (no look-ahead).
3. Baselines: OLS, Ridge, RF, XGBoost.
4. Regime-Aware NN (macro → regime embedding; char + embedding → `ret_excess`).
5. Regime: HMM on macro (Bull / Transition / Bear) + stress index.
6. Portfolio: decile long-short (value-weighted by `mktcap_lag`), cumulative returns, Sharpe, max DD, alpha.
7. SHAP and feature importance by regime.
8. Write artifacts to `data/processed/course/`.

## Outputs (`data/processed/course/`)

- `predictions.parquet`: `month_dt`, `permno`, `ret_excess`, `pred_OLS`, `pred_Ridge`, `pred_RF`, `pred_XGBoost`, `pred_RegimeNN` (if run).
- `regime_states.parquet`: `month_dt`, `hmm_state`, `regime_label`, `stress_index`.
- `macro_monthly.parquet`: One row per month, macro + `stress_index`.
- `portfolio_returns.parquet`: `month_dt`, `strategy_return`, `market_return`, `cum_strategy`, `cum_market`.
- `metrics.json`: Baseline OOS R² and portfolio metrics (Sharpe, max DD, alpha).
- `feature_columns.json`: List of feature names used.
- `shap_importance_*.csv`: Feature importance by regime (Bull, Bear, Transition).

## Dashboard

The Streamlit app can be updated to read from `data/processed/course/` for:

- Model comparison (OOS R²).
- Cumulative return plot (strategy vs market).
- Regime timeline and stress index.
- SHAP / feature importance by regime.

Run the offline pipeline first to generate these files.
