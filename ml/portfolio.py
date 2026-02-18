"""
Portfolio construction: rank by predicted ret_excess, long top decile / short bottom decile.
Value-weighted by mktcap_lag. Cumulative returns, Sharpe, max drawdown, annualized alpha.
"""

from typing import Optional, Tuple

import numpy as np
import pandas as pd


def decile_long_short_returns(
    predictions_df: pd.DataFrame,
    pred_col: str = "pred_XGBoost",
    ret_col: str = "ret_excess",
    weight_col: str = "mktcap_lag",
) -> pd.DataFrame:
    """
    Each month: rank stocks by pred_col, long top decile, short bottom decile.
    Value-weight by weight_col (mktcap_lag). Return DataFrame with month_dt, strategy_return, long_return, short_return.
    """
    out = []
    for month, grp in predictions_df.groupby("month_dt"):
        if grp[pred_col].isna().all():
            continue
        grp = grp.copy()
        grp["decile"] = pd.qcut(grp[pred_col].rank(method="first"), 10, labels=False)
        top = grp[grp["decile"] == 9]
        bot = grp[grp["decile"] == 0]
        if weight_col in grp.columns and top[weight_col].sum() > 0 and bot[weight_col].sum() > 0:
            w_top = top[weight_col].values / top[weight_col].sum()
            w_bot = bot[weight_col].values / bot[weight_col].sum()
            long_ret = np.average(top[ret_col].values, weights=w_top)
            short_ret = np.average(bot[ret_col].values, weights=w_bot)
        else:
            long_ret = top[ret_col].mean()
            short_ret = bot[ret_col].mean()
        strategy_ret = long_ret - short_ret
        out.append({"month_dt": month, "strategy_return": strategy_ret, "long_return": long_ret, "short_return": short_ret})
    return pd.DataFrame(out)


def market_return_per_month(panel: pd.DataFrame, ret_col: str = "ret_excess", weight_col: str = "mktcap_lag") -> pd.Series:
    """Value-weighted market return per month (for benchmark)."""
    if weight_col not in panel.columns:
        return panel.groupby("month_dt")[ret_col].mean()
    def vw_ret(grp):
        w = grp[weight_col].values
        if w.sum() == 0:
            return grp[ret_col].mean()
        return np.average(grp[ret_col].values, weights=w)
    return panel.groupby("month_dt").apply(vw_ret)


def cumulative_returns(monthly_returns: pd.Series) -> pd.Series:
    """Cumulative gross return (1 + r1)(1 + r2)... - 1."""
    return (1 + monthly_returns).cumprod() - 1


def sharpe_ratio(monthly_returns: pd.Series, annualize: bool = True) -> float:
    """Sharpe; annualize with sqrt(12) for monthly."""
    r = monthly_returns.dropna()
    if len(r) < 2:
        return 0.0
    sr = r.mean() / (r.std() + 1e-12)
    if annualize:
        sr *= np.sqrt(12)
    return float(sr)


def max_drawdown(cumulative: pd.Series) -> float:
    """Max drawdown from cumulative return series."""
    cum = (1 + cumulative).cumprod()
    run_max = cum.cummax()
    dd = (cum - run_max) / run_max
    return float(dd.min())


def annualized_alpha(
    strategy_returns: pd.Series,
    market_returns: pd.Series,
) -> float:
    """Annualized alpha: (mean(strategy) - mean(market)) * 12."""
    common = strategy_returns.index.intersection(market_returns.index)
    if len(common) == 0:
        return 0.0
    s = strategy_returns.reindex(common).fillna(0)
    m = market_returns.reindex(common).fillna(0)
    return float((s.mean() - m.mean()) * 12)


def portfolio_metrics(
    predictions_df: pd.DataFrame,
    panel: pd.DataFrame,
    pred_col: str = "pred_XGBoost",
) -> Tuple[pd.DataFrame, dict]:
    """
    Build decile long-short, merge with market return, compute cumulative plot data and metrics.
    Returns (portfolio_df with month_dt, strategy_return, market_return, cum_strategy, cum_market), metrics_dict.
    """
    port = decile_long_short_returns(predictions_df, pred_col=pred_col)
    market = market_return_per_month(panel)
    port = port.set_index("month_dt")
    port["market_return"] = market.reindex(port.index).fillna(0)
    port["cum_strategy"] = cumulative_returns(port["strategy_return"])
    port["cum_market"] = cumulative_returns(port["market_return"])
    port = port.reset_index()

    metrics = {
        "sharpe_ratio": sharpe_ratio(port["strategy_return"]),
        "max_drawdown": max_drawdown(port["strategy_return"]),
        "annualized_alpha": annualized_alpha(port["strategy_return"], port["market_return"]),
        "long_short_spread_mean": port["strategy_return"].mean(),
    }
    return port, metrics
