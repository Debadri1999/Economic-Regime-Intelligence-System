# Validation module

This folder was designed for **Phase 4 – Market linkage** of the original NLP-ERIS pipeline: Granger causality (text/NLP signals → market variables), predictive regression (NLP → next-period returns/VIX), and event studies around specific dates (e.g. COVID, SVB).

For the **course ML pipeline** (Gu, Kelly & Xiu asset pricing), validation is implemented in **`ml/validation.py`**: expanding-window split, OOS R², and regime-conditional R². No Granger or event-study code is required for the course deliverable.

The scripts here are stubs for future extension. To implement Granger causality on macro → returns, use `statsmodels.tsa.stattools.grangercausalitytests` on the course panel (e.g. macro variables vs. `ret_excess`).
