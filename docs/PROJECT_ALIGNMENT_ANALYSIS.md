# ERIS Project Alignment Analysis
## Dataset (dataset.pdf), Guidelines (general_guidelines.pdf), and Required Changes

This document summarizes the **course dataset**, **project guidelines**, and **concrete changes** needed so ERIS stays conceptually the same (regime intelligence, sentiment, stress) while using the official data and satisfying every deliverable and result expected in the dashboard.

---

## 1. Dataset Summary (dataset.pdf)

### 1.1 Overview
- **Source**: CRSP + Compustat via WRDS; structure aligned with Gu, Kelly & Xiu (2020).
- **Span**: **January 1957 – December 2021** (monthly).
- **Format**: Panel data; main delivery is **Parquet** (e.g. `202112.parquet`). Raw sources: **datashare.csv** (firm characteristics), **tidy_finance_python.sqlite** (CRSP monthly + macro).

### 1.2 Variables

| Category | Variables | Description |
|----------|-----------|-------------|
| **Identifiers** | `permno`, `month` | PERMNO = permanent security ID; month = end-of-month for returns, start-of-month for others. |
| **Target** | `ret_excess` | Monthly excess return (Ri,t − Rf,t) — **main prediction target**. |
| **Macro (macro_*)** | e.g. `macro_dp`, `macro_tbl`, `macro_tms` | Welch & Goyal (2008) style: dividend-price ratio, T-bill rate, term spread, etc. **Same for all firms in a given month.** |
| **Firm characteristics (characteristic_*)** | 94 features | Green, Hand & Zhang (2017) style; rank-transformed to **[-1, 1]**; e.g. momentum, size, book-to-market. |
| **Industry** | `sic2_*` | One-hot from first two digits of SIC (broad sector). |

### 1.3 Data Layout
- **Panel**: One row per (permno, month).
- **Parquet**: One file per period (e.g. `YYYYMM.parquet`); load with `pyarrow.parquet` or `pandas.read_parquet`.
- **Raw**: `datashare.csv` → firm characteristics; `tidy_finance_python.sqlite` → tables such as `crsp_monthly` (returns) and macro series.

---

## 2. General Guidelines Summary (general_guidelines.pdf)

### 2.1 Goal
- Apply **machine learning** to **empirical asset pricing** using the provided high-dimensional dataset.
- **Task**: Predict monthly stock returns (standard), **or** another reasonable task: e.g. **volatility prediction**, **regime classification**, or **portfolio optimization**. ERIS’s regime + stress fits “regime classification” and can be extended with return/volatility prediction.

### 2.2 Data Choice
- **Option A**: Full sample **1957–2021**.
- **Option B**: Recent **2001–2021** (or smaller subset) — faster, less RAM; must **justify** in presentation (e.g. “modern era”, computational limits).

### 2.3 Deliverables
1. **Presentation slides** (final: 8 min, graded).
2. **Codebase**: Clean **.ipynb** or **script(s)**.

### 2.4 Evaluation (ICML/NeurIPS style; peer review)
- **Innovation & design**: Custom architectures / hybrid models; justify design (e.g. use of time series).
- **Understanding**: Why the model behaves as it does; assumptions and limitations; **no look-ahead** (e.g. rolling/expanding window for time series).
- **Clarity & significance**: Clear narrative; effective results (e.g. cumulative return plots, not only MSE); conclusions supported by evidence.

### 2.5 AI Policy
- AI tools allowed; **AI Acknowledgment** section required in slides (tools used and for what).

---

## 3. Data1 and Data2 Folders

- **Finding**: No folders named **Data1** or **Data2** were found under the repository root. The course materials refer to:
  - **Processed panel data**: Parquet files (e.g. by year-month).
  - **Raw data**: `datashare.csv` and `tidy_finance_python.sqlite`.

**Recommendation** (once you have the files):

| Folder   | Suggested path              | Contents |
|----------|-----------------------------|----------|
| **Data1** | `Data1/` (repo root) or `data/raw/Data1/` | Parquet files (e.g. `202112.parquet`, or one file per YYYYMM). |
| **Data2** | `Data2/` (repo root) or `data/raw/Data2/` | `datashare.csv`, `tidy_finance_python.sqlite`. |

- In code, use config paths (e.g. `data.course.parquet_dir`, `data.course.raw_dir`) pointing to these folders so you can switch between root-level `Data1`/`Data2` and a layout like `data/raw/course/parquet/` and `data/raw/course/raw/` without code changes.

---

## 4. Gap: Current ERIS vs Course Requirements

| Aspect | Current ERIS | Course dataset / guidelines |
|--------|----------------|-----------------------------|
| **Market / price data** | yfinance (SPY, VIX, etc.) + FRED; daily; stored in `market_daily`, `macro_indicators` | CRSP monthly panel; macro_* and ret_excess; Parquet + SQLite |
| **Firm-level data** | None (only tickers) | 94 characteristic_* per permno/month; sic2_* |
| **Target variable** | None | ret_excess (and optionally volatility) |
| **Time granularity** | Daily (market, regime) | **Monthly** (dataset) |
| **Regime** | HMM on **daily** sentiment (nlp_signals) | Can keep; add **regime from asset-pricing features** (macro + characteristics) for alignment |
| **Validation** | Not explicit in app | **Rolling/expanding window**; no look-ahead; must be documented |
| **Results in dashboard** | Sentiment, regime, stress, topics, KPIs | Should add: **return/vol prediction metrics**, **strategy backtest** (e.g. cumulative returns), **model interpretation** |

---

## 5. Suggested Changes (End-to-End)

Keep the **main conceptual data** (regime, stress, sentiment, topics) and make the following adjustments so the project is clearly aligned with the dataset and guidelines.

### 5.1 Config (`config.yaml`)

- Add a **course data** section, e.g.:
  - `data.course.parquet_dir`: path to Data1 (Parquet) or `data/raw/Data1`.
  - `data.course.raw_dir`: path to Data2 (raw CSV + SQLite) or `data/raw/Data2`.
  - `data.course.sample`: `"full"` (1957–2021) or `"recent"` (e.g. 2001–2021); document choice in slides.
  - Optional: `data.course.parquet_files`: list of filenames or pattern if not scanning directory.

### 5.2 Data Layer

1. **New loader for course dataset**
   - **Parquet**: Scan Data1 (or configured dir); load one or more `YYYYMM.parquet`; concatenate; filter by date range (full vs recent).
   - **Columns to use**: `permno`, `month`, `ret_excess`, all `macro_*`, selected or all `characteristic_*`, and `sic2_*` as needed.
   - Expose one or more functions, e.g. `load_course_panel(sample="full"|"recent")` returning a DataFrame with a `date` (or `month`) index/column.

2. **Raw fallback (optional)**
   - From Data2: read `datashare.csv`; connect to `tidy_finance_python.sqlite` and query `crsp_monthly` (and macro tables) for the same date range.
   - Use for validation or for building a pipeline that matches the PDF’s “raw source” description.

3. **Integration with existing pipeline**
   - **Option A**: Add a pipeline step “Course data” that loads Parquet (and optionally raw), then writes to ERIS DB (see schema below).
   - **Option B**: Keep course data as the **primary** source for macro and returns; keep yfinance/FRED as **supplement** for daily dashboard (e.g. latest SPY). Prefer one “source of truth” for graded deliverables (course data).

### 5.3 Schema (DB)

- **New or extended tables** (conceptually; exact names can vary):
  - **Course panel (monthly)**  
    e.g. `course_monthly` or `crsp_monthly`: `permno`, `month`, `ret_excess`, key `macro_*` columns, and a subset of `characteristic_*` (or link to a wide table). Store at least what you need for models and dashboard.
  - **Macro from course**  
    Either add columns to existing `macro_indicators` with a `source` (e.g. `course` vs `fred`) or a dedicated `course_macro` with `month`, `macro_dp`, `macro_tbl`, `macro_tms`, etc.
  - **Aggregate / time-aligned series for regime**
  - Keep `market_daily` for **daily** series if you still use yfinance for recent SPY/VIX (optional).
  - Keep `regime_states`, `nlp_signals`, `documents_processed` for existing sentiment/regime/topics.

- **Important**: Ensure **month** is stored in a standard type (e.g. first day of month as DATE or a YYYYMM integer) and aligned with `ret_excess` (end-of-month) vs characteristics (start-of-month) as per dataset.pdf.

### 5.4 Feature Engineering

- **Already in dataset**: rank-transformed characteristics [-1, 1]; macro_*; sic2_*.
- **In code**:
  - Document that **no extra transformation** is applied to characteristic_* beyond what’s in the Parquet (unless you justify it).
  - **Engineer only**:
    - Lags of `ret_excess` or macro if needed for models.
    - Rolling features **over time** (e.g. rolling mean of macro) if you use them, with **strict no look-ahead** (only past data).
  - **Alignment with dashboard**: Any feature used in “feature importance” or “model card” should be defined here and documented.

### 5.5 Models

- **Regime (existing)**  
  - Keep HMM on **daily** sentiment for the **dashboard** (Risk-On / Transitional / Risk-Off).
  - **For the course**: Add a **monthly** regime (or return/volatility) model that uses **course data only** (macro_* + characteristic_*), e.g.:
    - HMM or simple classifier on macro + (optionally) aggregated characteristics.
    - Or use regime as a **secondary task** and keep **return prediction** as the primary ML task (aligns with “standard task” in guidelines).

- **Return prediction (new, recommended)**  
  - Train a model (e.g. linear, tree, or small NN) on **past** macro_* and characteristic_* to predict `ret_excess` next month.
  - **Validation**: Rolling or expanding window; train up to month t, predict t+1; no future data. Document in slides and in code.

- **Volatility (optional)**  
  - If you choose “volatility prediction”, define target (e.g. realized vol from returns) and use same validation discipline.

- **NLP (existing)**  
  - Keep FinBERT sentiment and BERTopic for **narrative** and “alternative data” angle; in slides, state that they complement the **asset-pricing dataset** (course data).

### 5.6 Pipeline (`utils/run_pipeline.py`)

- Add step **“Course data”** (or “Load Parquet”):  
  - Load from Data1/Data2 (per config); optionally backfill `course_monthly` / `course_macro`; then run rest of pipeline.
- Order suggestion: Schema → **Course data** → (optional) Market [yfinance/FRED] → News → Fed → Kaggle → Earnings → Preprocess → Sentiment → Regime → (optional) Topics.
- For **grading**, ensure a single run (or notebook) reproduces: load course data → features → train model(s) → write results used by dashboard.

### 5.7 Dashboard (Streamlit) – “Every Result Needed”

- **Home / Overview**
  - Short note: “Primary data: course dataset 1957–2021 (or 2001–2021); Option A/B and justification.”

- **Data**
  - **Data sources**: Add “Course dataset (Data1 Parquet + Data2 raw)” with brief description (CRSP/Compustat, macro_*, characteristic_*, ret_excess).
  - **Coverage**: Date range and cross-section (e.g. # permnos, # months) from course data.

- **Feature engineering**
  - One page or section: list of macro_* and characteristic_* (or a subset) used; note “rank [-1,1] as in dataset”; any lags/rolling you add.

- **Models**
  - **Return prediction**: Metric(s) (e.g. MSE, correlation, or IC); time period; validation scheme (rolling window).
  - **Regime**: Keep current regime + stress view; add a sentence: “Monthly regime from course data (macro + characteristics)” if you add that model.
  - **Sentiment / Topics**: Keep as is; label as “NLP / alternative data”.

- **Results**
  - **Cumulative return plot**: As per guidelines (“cumulative return plots to compare strategies may be more convincing than reporting MSE”). E.g. long top decile of predicted return vs bottom decile, or vs market.
  - **Strategy**: If applicable, show simple long/short or long-only based on predicted ret_excess; document in slides.

- **KPI & project success**
  - Keep existing KPIs; add **course-specific** KPIs: e.g. number of months/permnos loaded; train/validation date split; return prediction metric; “no look-ahead” stated clearly.

- **Technical terminology**
  - Add terms: **permno**, **ret_excess**, **macro_* (Welch–Goyal)**, **characteristic_* (Green–Hand–Zhang)**, **rank transformation**, **rolling window validation**, **look-ahead bias**.

### 5.8 Presentation / Slides

- **Data**: “We use the course dataset (1957–2021 or 2001–2021); Option A/B and justification.”
- **Task**: “Primary task: monthly excess return prediction; secondary: regime classification (HMM on sentiment + course macro).”
- **Validation**: “Rolling (or expanding) window; no look-ahead; train on t, predict t+1.”
- **Results**: Cumulative return plot; table of metrics; model understanding (e.g. which macro_* / characteristic_* matter).
- **AI Acknowledgment**: Tools used and for what (e.g. code generation, documentation).

### 5.9 Codebase Deliverable

- **Notebook or script** that:
  1. Loads Data1 (Parquet) and optionally Data2.
  2. Applies feature engineering (with no look-ahead).
  3. Trains return (and optionally regime/volatility) model with rolling validation.
  4. Reports metrics and (if applicable) saves artifacts used by the Streamlit app (e.g. predictions, regime labels).
- Keep the repo clean: one main entry (e.g. `run_pipeline.py` or `notebooks/full_pipeline.ipynb`) that reproduces the results shown in the dashboard.

---

## 6. Checklist of Required Changes

- [ ] **Config**: Add `data.course` (parquet_dir, raw_dir, sample).
- [ ] **Data1/Data2**: Place Parquet in Data1, raw CSV/SQLite in Data2 (or documented paths).
- [ ] **Loader**: Implement `load_course_panel()` (and optional raw loader) with date filter (full vs recent).
- [ ] **Schema**: Add tables for course monthly panel and course macro (or extend existing).
- [ ] **Pipeline**: Add “Course data” step; document order and no look-ahead.
- [ ] **Features**: Document macro_* and characteristic_*; add only justified lags/rolling; no look-ahead.
- [ ] **Models**: Add return prediction (rolling validation); optionally monthly regime from course data; keep daily regime + sentiment for dashboard.
- [ ] **Dashboard**: Data sources + course coverage; feature list; return prediction metrics; cumulative return plot; course KPIs and “no look-ahead”.
- [ ] **Slides**: Data choice justification; task; validation; results; AI Acknowledgment.
- [ ] **Deliverable**: One clean notebook or script that reproduces pipeline and results.

---

## 7. Summary

- **Dataset**: Monthly panel 1957–2021 with `permno`, `month`, `ret_excess`, `macro_*`, 94× `characteristic_*`, `sic2_*`; Parquet + raw CSV/SQLite.
- **Guidelines**: ML for asset pricing; return prediction or regime/volatility/portfolio; Option A or B for date range; rolling validation; clear results (e.g. cumulative returns); slides + code; AI acknowledgment.
- **Data1/Data2**: Not in repo yet; use Data1 for Parquet, Data2 for raw; or `data/raw/course/parquet` and `data/raw/course/raw`.
- **Concept**: Keep regime, stress, sentiment, topics; **add** course data as primary for grading, return prediction model, and dashboard results (metrics + cumulative return plot), with strict no look-ahead and documented validation.

This structure keeps your main conceptual data the same while making the project fully aligned with the dataset and each requirement in the guidelines and dashboard.
