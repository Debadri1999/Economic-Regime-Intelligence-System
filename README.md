# ERIS — Economic Regime Intelligence System

ERIS is an end-to-end AI platform that analyzes financial text streams (news, Federal Reserve communications, earnings calls, macro reports) to detect early signals of **economic regime shifts** and translate them into actionable risk intelligence.

Unlike traditional sentiment or classification approaches, ERIS performs **structural market change detection** by combining:

- **Multi-modal NLP**: FinBERT sentiment, BERTopic narratives, semantic embeddings  
- **Statistical regime detection**: Hidden Markov Models, change-point detection  
- **ML classifier**: XGBoost regime prediction from NLP features  
- **LLM layer**: GPT-4–powered narrative generation  

---

## Architecture (high level)

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ Data collection │────▶│ Preprocessing     │────▶│ documents_processed  │
│ News, Fed,      │     │ Clean, dedup,     │     │ (clean, aligned)     │
│ Market, Earnings│     │ time-align        │     └──────────┬───────────┘
└─────────────────┘     └──────────────────┘                │
                                                             ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ Streamlit app   │◀────│ Regime engine   │◀────│ NLP signals         │
│ Dashboard,      │     │ HMM, XGBoost,    │     │ Sentiment, topics,   │
│ Sentiment, etc. │     │ ensemble         │     │ embeddings           │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
```

---

## Project structure

```
eris/
├── app.py                    # Streamlit entry
├── config.yaml               # Parameters (no secrets)
├── requirements.txt
├── .env.example              # Copy to .env and add API keys
├── data/
│   ├── collectors/           # NewsAPI, Fed scraper, market, earnings
│   ├── preprocessing/        # Cleaner, dedup, time alignment
│   └── storage/              # schema.sql, db_manager
├── models/                   # Sentiment, topic, embedding, regime
├── pages/                    # Streamlit pages 1–6
├── components/               # charts.py, data_loader.py
├── utils/
├── validation/               # Granger, predictive regression, event studies
├── notebooks/
└── tests/
```

---

## Setup

1. **Clone and install**

   ```bash
   cd Economic-Regime-Intelligence-System
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```

2. **Environment**

   - Copy `.env.example` to `.env`.
   - Add `NEWSAPI_KEY`, `FRED_API_KEY`, and (for Phase 5) `OPENAI_API_KEY`.

3. **Database**

   - Default: SQLite at `data/raw/eris.db`. Tables are created on first run.
   - Optional: set `DATABASE_URL` for PostgreSQL.

4. **Spacy (optional, for sentence segmentation)**

   ```bash
   python -m spacy download en_core_web_sm
   ```

---

## Data collection (Phase 1)

- **News**: `python -m data.collectors.news_collector` — cycles through queries, deduplicates by URL, stores in `raw_articles`.
- **Fed**: `python -m data.collectors.fed_scraper` — scrapes FOMC calendar and speeches, stores in `fed_documents`.
- **Market**: `python -m data.collectors.market_collector` — yfinance + FRED, writes `market_daily` and `macro_indicators`.
- **Kaggle (financial news)**: `python -m data.collectors.kaggle_collector` — downloads the [Sentiment Analysis for Financial News](https://www.kaggle.com/datasets/ankurzing/sentiment-analysis-for-financial-news) dataset and ingests into `raw_articles`. Requires `pip install kaggle` and a `kaggle.json` API key in `~/.kaggle/` (or `%USERPROFILE%\.kaggle\` on Windows). Get the key from [Kaggle Account → Create New Token](https://www.kaggle.com/settings).
- **Earnings (CSV)**: Put a CSV with columns `company`, `ticker`, `date`, `section`, `text` at `data/raw/earnings.csv`, then run `python -m data.collectors.earnings_collector` to load into `earnings_transcripts`. You can use any Kaggle earnings dataset you download manually.
- **Preprocessing**: `python -m data.preprocessing.preprocess` — cleans, deduplicates (MinHash), time-aligns, writes `documents_processed`.

Initialize schema once:

```python
from data.storage.db_manager import ensure_schema
ensure_schema()
```

---

## Fill all data (one command)

To populate the dashboard so no sections are blank (market data, sentiment, regime):

```bash
python run_all_data.py
```

This runs: schema → news, Fed, market (and optional Kaggle) collectors → preprocessing → Phase 2 (FinBERT sentiment) → Phase 3 (HMM regime). Optional afterward: `python -m models.topic_engine` for Topics page labels.

---

## Run the dashboard

```bash
python -m streamlit run app.py
```

Open the URL (e.g. http://localhost:8501). Use the sidebar for time range and data source. Pages: Dashboard, Sentiment, Topics, Regime, Market Link, AI Briefing.

---

## Next: Phase 2 & 3 (populate regime states)

After data and preprocessing (Phase 1), run the NLP and regime pipeline so the dashboard shows **regime states** and **sentiment**:

```bash
python run_phase2_and_3.py
```

This script:

1. **Phase 2:** Runs FinBERT on `documents_processed` and writes **nlp_signals** (sentiment per document/date).
2. **Phase 3:** Aggregates sentiment by date, fits an HMM, and writes **regime_states** (Risk-On / Transitional / Risk-Off per day).

**Requirements:** `transformers`, `torch`, `hmmlearn` (in `requirements.txt`). First run may download the FinBERT model (~400MB).

Then refresh the Streamlit app; the main dashboard should show the current regime and history.

---

## Remaining steps to complete the project

After Phases 1–3 and the dashboard updates, these steps will finish the system:

1. **Ensure all pages have data**
   - **Sentiment:** Daily chart + raw signals (done). Run `python run_phase2_and_3.py` if empty.
   - **Topics:** Document volume by source (done). For BERTopic topic labels, run when implemented: `python -m models.topic_engine`.
   - **Regime:** Table of regime states (done).
   - **Market Link:** SPY chart + regime overlay (done). Run `python -m data.collectors.market_collector` for market data.
   - **AI Briefing:** Latest regime summary + history (done). Phase 5 will add LLM narrative.

2. **Phase 2 extension – BERTopic**
   - Wire `models.topic_engine.run_topic_pipeline()` to write `topic_id` / `topic_label` (e.g. into `nlp_signals` or a topic table), then run: `python -m models.topic_engine`.

3. **Phase 3 extension – XGBoost / ensemble**
   - Add XGBoost classifier from NLP features to regime; optionally combine with HMM (ensemble). Expose on Regime page.

4. **Phase 4 – Market linkage**
   - Implement or wire `validation/granger_tests.py`, `validation/predictive_regression.py`, `validation/event_studies.py`. Show results on Market Link page.

5. **Phase 5 – LLM briefing**
   - Call OpenAI (or other LLM) with latest regime + metrics; write to `llm_briefings` and show on AI Briefing page. Requires `OPENAI_API_KEY` in `.env`.

6. **Testing and deployment**
   - Add tests for collectors, preprocessing, sentiment, regime. Optionally deploy Streamlit (e.g. Streamlit Cloud, Docker).

**Commands to run the app end-to-end (from project root):**

```bash
# Optional: refresh data
python -m data.collectors.news_collector
python -m data.collectors.market_collector
python -m data.preprocessing.preprocess
python run_phase2_and_3.py

# Run dashboard
python -m streamlit run app.py
```

---

## Roadmap

| Phase | Focus | Status |
|-------|--------|--------|
| 1 | Data infrastructure & collection | ✅ Done |
| 2 | Text intelligence (FinBERT, BERTopic, embeddings) | ✅ FinBERT; BERTopic stub |
| 3 | Regime detection (HMM, change-point, XGBoost, ensemble) | ✅ HMM; XGBoost/ensemble planned |
| 4 | Market linkage (Granger, predictive regression, event studies) | 🔲 Planned |
| 5 | LLM explanation layer | 🔲 Planned |
| 6 | Streamlit app (all modules wired) | ✅ Pages filled; Topics/LLM partial |
| 7 | Testing, docs, deployment | 🔲 Planned |

---

## Data sources and methodology

- **News**: NewsAPI (free tier), regime-relevant queries; dedup by URL hash.
- **Fed**: federalreserve.gov (FOMC statements, minutes, speeches); HTML scraping.
- **Market**: Yahoo Finance (SPY, VIX, GLD, TLT, HYG), FRED (yields, spreads, CPI, unemployment).
- **Kaggle**: Financial news (e.g. [Sentiment Analysis for Financial News](https://www.kaggle.com/datasets/ankurzing/sentiment-analysis-for-financial-news)) via `data.collectors.kaggle_collector`; earnings via CSV at `data/raw/earnings.csv` and `earnings_collector`.

See `config.yaml` for query lists, tickers, and FRED series.

---

## License and disclaimer

This project is for research and portfolio demonstration. Not financial advice. Use at your own risk.
