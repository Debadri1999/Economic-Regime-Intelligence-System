-- ERIS Database Schema
-- Compatible with PostgreSQL; SQLite uses same structure (no SERIAL/CHECK differences for MVP)

-- Raw ingested news articles
CREATE TABLE IF NOT EXISTS raw_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source VARCHAR(128),
    title TEXT NOT NULL,
    content TEXT,
    description TEXT,
    published_at TIMESTAMP,
    url TEXT UNIQUE NOT NULL,
    url_hash VARCHAR(64) UNIQUE,
    query_term VARCHAR(128),
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_type VARCHAR(32) DEFAULT 'news'
);

CREATE INDEX IF NOT EXISTS idx_raw_articles_published ON raw_articles(published_at);
CREATE INDEX IF NOT EXISTS idx_raw_articles_url_hash ON raw_articles(url_hash);
CREATE INDEX IF NOT EXISTS idx_raw_articles_collected ON raw_articles(collected_at);

-- Federal Reserve documents
CREATE TABLE IF NOT EXISTS fed_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_type VARCHAR(64),
    title TEXT,
    full_text TEXT NOT NULL,
    date DATE,
    speaker VARCHAR(256),
    url TEXT,
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_fed_documents_date ON fed_documents(date);
CREATE INDEX IF NOT EXISTS idx_fed_documents_type ON fed_documents(doc_type);

-- Earnings call text segments
CREATE TABLE IF NOT EXISTS earnings_transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company VARCHAR(128),
    ticker VARCHAR(16),
    date DATE,
    section VARCHAR(64),
    text TEXT NOT NULL,
    fiscal_quarter VARCHAR(32),
    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_earnings_date ON earnings_transcripts(date);
CREATE INDEX IF NOT EXISTS idx_earnings_ticker ON earnings_transcripts(ticker);

-- Daily market data (OHLCV + derived)
CREATE TABLE IF NOT EXISTS market_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    ticker VARCHAR(32) NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    returns_1d REAL,
    returns_5d REAL,
    returns_21d REAL,
    returns_63d REAL,
    realized_vol_21d REAL,
    UNIQUE(date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_market_daily_date ON market_daily(date);
CREATE INDEX IF NOT EXISTS idx_market_daily_ticker ON market_daily(ticker);

-- FRED macro time series
CREATE TABLE IF NOT EXISTS macro_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    indicator_name VARCHAR(64) NOT NULL,
    value REAL,
    UNIQUE(date, indicator_name)
);

CREATE INDEX IF NOT EXISTS idx_macro_date ON macro_indicators(date);
CREATE INDEX IF NOT EXISTS idx_macro_name ON macro_indicators(indicator_name);

-- Preprocessed documents (after cleaning, dedup, time alignment)
CREATE TABLE IF NOT EXISTS documents_processed (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,
    source_table VARCHAR(64),
    source_type VARCHAR(32),
    title TEXT,
    content_clean TEXT NOT NULL,
    content_sentences TEXT,
    published_date DATE,
    topic_hint VARCHAR(128),
    word_count INTEGER,
    minhash_fingerprint BLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_docs_processed_date ON documents_processed(published_date);
CREATE INDEX IF NOT EXISTS idx_docs_processed_source_type ON documents_processed(source_type);

-- NLP computed features (daily granularity)
CREATE TABLE IF NOT EXISTS nlp_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    source_type VARCHAR(32),
    sentiment_score REAL,
    sentiment_positive_prob REAL,
    sentiment_negative_prob REAL,
    sentiment_neutral_prob REAL,
    sentiment_confidence REAL,
    daily_mean_sentiment REAL,
    daily_median_sentiment REAL,
    daily_sentiment_std REAL,
    daily_sentiment_skew REAL,
    document_count INTEGER,
    sentiment_drift REAL,
    sentiment_volatility REAL,
    topic_id INTEGER,
    topic_label VARCHAR(128),
    topic_prevalence REAL,
    embedding_distance REAL,
    semantic_drift REAL,
    semantic_acceleration REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_nlp_signals_date ON nlp_signals(date);
CREATE INDEX IF NOT EXISTS idx_nlp_signals_source ON nlp_signals(source_type);

-- Regime engine output
CREATE TABLE IF NOT EXISTS regime_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    regime_label VARCHAR(32),
    regime_probability REAL,
    regime_prob_risk_on REAL,
    regime_prob_transitional REAL,
    regime_prob_risk_off REAL,
    confidence VARCHAR(16),
    drivers TEXT,
    hmm_state INTEGER,
    changepoint_score INTEGER,
    xgb_prob_risk_off REAL,
    composite_prob REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_regime_states_date ON regime_states(date);

-- LLM explanation cache
CREATE TABLE IF NOT EXISTS llm_briefings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    regime_status TEXT,
    risk_assessment TEXT,
    key_drivers TEXT,
    market_implications TEXT,
    confidence_note TEXT,
    recommended_monitoring TEXT,
    raw_response TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_llm_briefings_date ON llm_briefings(date);
