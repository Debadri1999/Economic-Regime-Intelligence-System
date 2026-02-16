"""ERIS Market validation and predictive analysis."""
import streamlit as st
from components.data_loader import load_market_daily, load_regime_states

st.title("Market Linkage")
st.caption("Granger causality and event studies (Phase 4).")
market = load_market_daily(ticker="SPY", days=st.session_state.get("days", 365))
regime = load_regime_states(days=st.session_state.get("days", 365))
if market.empty:
    st.info("No market data. Run market_collector (Phase 1).")
else:
    st.line_chart(market.set_index("date")[["close"]])
if regime.empty:
    st.info("No regime data for overlay. Run Phase 3.")
else:
    st.write("Signal–market overlays and Granger results will appear here after Phase 4.")
