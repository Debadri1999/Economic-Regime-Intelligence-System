"""
Reusable Plotly chart functions for ERIS dashboard.
"""

from typing import List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def regime_area_chart(df: pd.DataFrame, prob_col: str = "regime_probability") -> go.Figure:
    """Full-width area chart of regime probability over time."""
    if df.empty or "date" not in df.columns:
        return go.Figure().add_annotation(text="No data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    df = df.sort_values("date")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df[prob_col] if prob_col in df.columns else df.get("regime_prob_risk_off", df.iloc[:, 1]),
            fill="tozeroy",
            mode="lines",
            name="Regime probability",
            line=dict(color="#2E75B6"),
        )
    )
    fig.update_layout(
        template="plotly_white",
        margin=dict(t=40, b=40, l=60, r=40),
        xaxis_title="Date",
        yaxis_title="Probability",
        yaxis=dict(range=[0, 1]),
        height=350,
    )
    return fig


def metric_sparkline(series: pd.Series, title: str = "") -> go.Figure:
    """Tiny trend chart for metric cards."""
    fig = go.Figure(go.Scatter(x=range(len(series)), y=series.values, mode="lines", line=dict(width=2)))
    fig.update_layout(template="plotly_white", margin=dict(t=24, b=0, l=0, r=0), height=40, showlegend=False)
    if title:
        fig.update_layout(title=dict(text=title, font=dict(size=10)))
    return fig


def dual_axis_overlay(
    df: pd.DataFrame,
    date_col: str,
    left_col: str,
    right_col: str,
    left_name: str = "Signal",
    right_name: str = "Market",
) -> go.Figure:
    """Dual-axis line chart for signal vs market variable."""
    if df.empty or date_col not in df.columns:
        return go.Figure().add_annotation(text="No data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=df[date_col], y=df[left_col], name=left_name, line=dict(color="#2E75B6"))
    )
    fig.add_trace(
        go.Scatter(x=df[date_col], y=df[right_col], name=right_name, yaxis="y2", line=dict(color="#888"))
    )
    fig.update_layout(
        template="plotly_white",
        yaxis=dict(title=left_name),
        yaxis2=dict(title=right_name, overlaying="y", side="right"),
        height=350,
    )
    return fig
