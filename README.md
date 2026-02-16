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
- **Preprocessing**: `python -m data.preprocessing.preprocess` — cleans, deduplicates (MinHash), time-aligns, writes `documents_processed`.

Initialize schema once:

```python
from data.storage.db_manager import ensure_schema
ensure_schema()
```

---

## Run the dashboard

```bash
streamlit run app.py
```

Open the URL (e.g. http://localhost:8501). Use the sidebar for time range and data source. Pages: Dashboard, Sentiment, Topics, Regime, Market Link, AI Briefing.

---

## Roadmap

| Phase | Focus | Status |
|-------|--------|--------|
| 1 | Data infrastructure & collection | ✅ Scripts, schema, preprocessing |
| 2 | Text intelligence (FinBERT, BERTopic, embeddings) | 🔲 Stubs in place |
| 3 | Regime detection (HMM, change-point, XGBoost, ensemble) | 🔲 Stubs in place |
| 4 | Market linkage (Granger, predictive regression, event studies) | 🔲 Planned |
| 5 | LLM explanation layer | 🔲 Planned |
| 6 | Streamlit app (all modules wired) | 🔲 Skeleton in place |
| 7 | Testing, docs, deployment | 🔲 Planned |

---

## Data sources and methodology

- **News**: NewsAPI (free tier), regime-relevant queries; dedup by URL hash.
- **Fed**: federalreserve.gov (FOMC statements, minutes, speeches); HTML scraping.
- **Market**: Yahoo Finance (SPY, VIX, GLD, TLT, HYG), FRED (yields, spreads, CPI, unemployment).
- **Earnings**: Placeholder for Kaggle or CSV upload; table `earnings_transcripts`.

See `config.yaml` for query lists, tickers, and FRED series.

---

## License and disclaimer

This project is for research and portfolio demonstration. Not financial advice. Use at your own risk.
