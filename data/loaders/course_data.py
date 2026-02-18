"""
Course dataset loader: Gu, Kelly & Xiu monthly panel.
Loads parquet files from Data1, stacks into one panel, handles NaN and imputation.
Features at month-start predict ret_excess at month-end (already aligned in each row).
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
import numpy as np
import yaml

logger = logging.getLogger(__name__)

# Project root (parent of data/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _get_config() -> dict:
    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _parquet_dir() -> Path:
    cfg = _get_config()
    raw = cfg.get("course", {}).get("parquet_dir", "Data1")
    p = Path(raw)
    if not p.is_absolute():
        p = PROJECT_ROOT / p
    return p


def _sample_range() -> Tuple[int, int]:
    """Return (start_year, end_year) for data loading."""
    cfg = _get_config()
    sample = cfg.get("course", {}).get("sample", "recent")
    if sample == "full":
        return 1957, 2021
    return 2001, 2021


def _list_parquet_files(parquet_dir: Path, start_year: int, end_year: int) -> List[Path]:
    """List YYYYMM.parquet or YYYYMM_0.parquet files in range."""
    files = []
    for p in parquet_dir.glob("*.parquet"):
        try:
            # accept 200101.parquet or 200101_0.parquet
            stem = p.stem.split("_")[0]
            if len(stem) >= 6 and stem.isdigit():
                y = int(stem[:4])
                if start_year <= y <= end_year:
                    files.append(p)
        except (ValueError, IndexError):
            continue
    return sorted(files)


def load_course_panel(
    parquet_dir: Optional[Path] = None,
    sample: Optional[str] = None,
    drop_ret_null: bool = True,
    impute_missing: bool = True,
) -> pd.DataFrame:
    """
    Load and stack course parquet files into one panel DataFrame.

    - Filters to sample date range (full 1957-2021 or recent 2001-2021).
    - Drops rows where ret_excess is null if drop_ret_null.
    - Cross-sectional median imputation per month for missing characteristics if impute_missing.

    Returns:
        DataFrame with columns: permno, month, ret_excess, mktcap_lag, macro_*, characteristic_*, sic2_*
    """
    cfg = _get_config()
    course_cfg = cfg.get("course", {})
    dir_path = Path(parquet_dir) if parquet_dir else _parquet_dir()
    if not dir_path.exists():
        raise FileNotFoundError(
            f"Course parquet directory not found: {dir_path}. "
            "Place YYYYMM.parquet files in Data1 (or set course.parquet_dir in config)."
        )
    start_year, end_year = _sample_range()
    if sample == "full":
        start_year, end_year = 1957, 2021
    elif sample == "recent":
        start_year, end_year = 2001, 2021

    files = _list_parquet_files(dir_path, start_year, end_year)
    if not files:
        raise FileNotFoundError(
            f"No parquet files found in {dir_path} for {start_year}-{end_year}. "
            "Expected files like 200101.parquet, 200102.parquet, ..."
        )

    dfs = []
    for f in files:
        try:
            df = pd.read_parquet(f)
            dfs.append(df)
        except Exception as e:
            logger.warning("Skip %s: %s", f.name, e)
    if not dfs:
        raise ValueError("No parquet file could be read.")

    panel = pd.concat(dfs, ignore_index=True)
    if "month" not in panel.columns:
        raise ValueError("Panel must have 'month' column (e.g. period like YYYYMM or datetime).")

    # Normalize month to first-of-month date for consistency
    if pd.api.types.is_numeric_dtype(panel["month"]):
        # YYYYMM integer
        panel["month_dt"] = pd.to_datetime(panel["month"].astype(str), format="%Y%m").dt.to_period("M")
    else:
        panel["month_dt"] = pd.to_datetime(panel["month"]).dt.to_period("M")
    panel = panel.sort_values(["month_dt", "permno"]).reset_index(drop=True)

    if drop_ret_null and "ret_excess" in panel.columns:
        before = len(panel)
        panel = panel.dropna(subset=["ret_excess"])
        logger.info("Dropped %d rows with null ret_excess.", before - len(panel))

    if impute_missing:
        char_cols = [c for c in panel.columns if c.startswith("characteristic_")]
        if char_cols:
            # Cross-sectional median per month
            for col in char_cols:
                if panel[col].isna().any():
                    med = panel.groupby("month_dt")[col].transform("median")
                    panel[col] = panel[col].fillna(med)
            # Any remaining NaN fill with 0 (e.g. if whole month missing)
            panel[char_cols] = panel[char_cols].fillna(0)

    return panel


def get_feature_columns(panel: pd.DataFrame) -> dict:
    """
    Detect macro, characteristic, and industry columns from panel.
    Returns dict: macro, characteristic, industry, all_features.
    """
    macro = [c for c in panel.columns if c.startswith("macro_")]
    characteristic = [c for c in panel.columns if c.startswith("characteristic_")]
    industry = [c for c in panel.columns if c.startswith("sic2_")]
    id_cols = ["permno", "month", "month_dt"]
    target = ["ret_excess"] if "ret_excess" in panel.columns else []
    mktcap = ["mktcap_lag"] if "mktcap_lag" in panel.columns else []

    all_features = macro + characteristic + industry
    return {
        "macro": macro,
        "characteristic": characteristic,
        "industry": industry,
        "all_features": all_features,
        "id_cols": id_cols,
        "target": target,
        "mktcap": mktcap,
    }
