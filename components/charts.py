"""
Plotly charts for ERIS: dark theme, production-ready.
"""

from typing import Optional
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Dark theme layout
DARK_LAYOUT = dict(
    paper_bgcolor="rgba(10,14,20,0.9)",
    plot_bgcolor="rgba(22,27,34,0.95)",
    font=dict(color="#e6edf3", size=12),
    margin=dict(t=50, b=50, l=60, r=40),
    xaxis=dict(gridcolor="#30363d", zerolinecolor="#30363d"),
    yaxis=dict(gridcolor="#30363d", zerolinecolor="#30363d"),
    legend=dict(bgcolor="rgba(22,27,34,0.8)", font=dict(color="#b1bac4")),
    height=320,
)


def _apply_dark(fig: go.Figure) -> go.Figure:
    fig.update_layout(**DARK_LAYOUT)
    return fig


def regime_timeseries(df: pd.DataFrame, prob_col: str = "regime_prob_risk_off") -> go.Figure:
    """Regime probability over time (dark theme)."""
    if df.empty or "date" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No regime data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="#8b949e"))
        return _apply_dark(fig)
    df = df.sort_values("date")
    col = prob_col if prob_col in df.columns else (df.get("regime_probability") if "regime_probability" in df.columns else df.columns[1])
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df[col],
            mode="lines",
            name="Risk-Off probability",
            line=dict(color="#58a6ff", width=2),
            fill="tozeroy",
            fillcolor="rgba(88,166,255,0.15)",
        )
    )
    fig.update_layout(
        title=dict(text="Regime (Risk-Off probability)", font=dict(size=14, color="#8b949e")),
        xaxis_title="Date",
        yaxis_title="Probability",
        yaxis=dict(range=[0, 1], tickformat=".0%"),
    )
    return _apply_dark(fig)


def sentiment_timeseries(daily: pd.DataFrame) -> go.Figure:
    """Daily mean sentiment over time (dark theme)."""
    if daily.empty or "daily_mean_sentiment" not in daily.columns:
        fig = go.Figure()
        fig.add_annotation(text="No sentiment data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="#8b949e"))
        return _apply_dark(fig)
    daily = daily.sort_values("date")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=daily["date"],
            y=daily["daily_mean_sentiment"],
            mode="lines",
            name="Daily mean sentiment",
            line=dict(color="#3fb950", width=2),
            fill="tozeroy",
            fillcolor="rgba(63,185,80,0.12)",
        )
    )
    fig.update_layout(
        title=dict(text="Sentiment trend", font=dict(size=14, color="#8b949e")),
        xaxis_title="Date",
        yaxis_title="Sentiment (−1 to +1)",
    )
    return _apply_dark(fig)


def topic_bar_chart(topic_df: pd.DataFrame, label_col: str = "topic_label", count_col: str = "doc_count", top_n: int = 12) -> go.Figure:
    """Topic distribution bar chart (dark theme). topic_df can have human-readable labels."""
    if topic_df.empty or label_col not in topic_df.columns or count_col not in topic_df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No topic data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="#8b949e"))
        return _apply_dark(fig)
    df = topic_df.head(top_n).copy()
    df = df.sort_values(count_col, ascending=True)
    fig = go.Figure(
        go.Bar(
            x=df[count_col],
            y=df[label_col],
            orientation="h",
            marker=dict(color="#58a6ff", line=dict(color="#388bfd", width=0.5)),
            text=df[count_col],
            textposition="outside",
            textfont=dict(color="#e6edf3"),
        )
    )
    fig.update_layout(
        title=dict(text="Topic distribution", font=dict(size=14, color="#8b949e")),
        xaxis_title="Documents",
        yaxis_title="",
        yaxis=dict(autorange="reversed"),
        showlegend=False,
    )
    return _apply_dark(fig)


def market_line(df: pd.DataFrame, price_col: str = "close") -> go.Figure:
    """Market price over time (dark theme)."""
    if df.empty or "date" not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No market data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=14, color="#8b949e"))
        return _apply_dark(fig)
    df = df.sort_values("date")
    col = price_col if price_col in df.columns else df.columns[-1]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df[col],
            mode="lines",
            name="Price",
            line=dict(color="#d29922", width=2),
        )
    )
    fig.update_layout(
        title=dict(text="SPY (close)", font=dict(size=14, color="#8b949e")),
        xaxis_title="Date",
        yaxis_title="Price",
    )
    return _apply_dark(fig)


def dual_axis_overlay(
    df: pd.DataFrame,
    date_col: str,
    left_col: str,
    right_col: str,
    left_name: str = "Regime prob",
    right_name: str = "SPY close",
) -> go.Figure:
    """Dual-axis: regime probability + market (dark theme)."""
    if df.empty or date_col not in df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(color="#8b949e"))
        return _apply_dark(fig)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=df[date_col], y=df[left_col], name=left_name, line=dict(color="#58a6ff", width=2))
    )
    fig.add_trace(
        go.Scatter(x=df[date_col], y=df[right_col], name=right_name, yaxis="y2", line=dict(color="#d29922", width=2))
    )
    fig.update_layout(
        yaxis=dict(title=left_name, side="left", tickformat=".0%"),
        yaxis2=dict(title=right_name, overlaying="y", side="right"),
        xaxis_title="Date",
    )
    return _apply_dark(fig)


def stress_gauge(score: float, level_name: str, color: str) -> go.Figure:
    """Gauge 0–100 for market stress (dark theme)."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number=dict(suffix="/100", font=dict(size=24, color="#e6edf3")),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor="#8b949e"),
            bar=dict(color=color, thickness=0.75),
            bgcolor="rgba(22,27,34,0.95)",
            borderwidth=1,
            bordercolor="#30363d",
            steps=[dict(range=[0, 100], color="rgba(48,54,61,0.4)")],
            threshold=dict(line=dict(color=color, width=4), thickness=0.8, value=score),
        ),
        title=dict(text=f"Stress: {level_name}", font=dict(size=14, color="#8b949e")),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(10,14,20,0.9)",
        font=dict(color="#e6edf3"),
        margin=dict(t=50, b=30, l=30, r=30),
        height=220,
    )
    return fig


# Alias for legacy import
regime_area_chart = regime_timeseries
