"""
Create a small synthetic parquet in Data1 for testing the offline pipeline.
Run from project root: python scripts/create_synthetic_parquet.py
Generates Data1/200101.parquet and Data1/200102.parquet with dummy columns.
"""

from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA1 = PROJECT_ROOT / "Data1"


def main():
    DATA1.mkdir(parents=True, exist_ok=True)
    np.random.seed(42)
    n_stocks = 300
    macro_cols = ["macro_dp", "macro_tbl", "macro_tms", "macro_dfy", "macro_svar", "macro_ep", "macro_de", "macro_bm"]
    n_char = 10  # subset for demo
    char_cols = [f"characteristic_{i}" for i in range(n_char)]
    sic_cols = [f"sic2_{i}" for i in range(5)]

    # Generate 2001-01 through 2010-12 so expanding window (first_pred=2010) has OOS months
    months_list = []
    for y in range(2001, 2011):
        for m in range(1, 13):
            months_list.append(y * 100 + m)

    for yyyymm in months_list:
        macro_vals = np.random.randn(len(macro_cols)) * 0.1
        rows = []
        for i in range(n_stocks):
            row = {
                "permno": 10000 + i,
                "month": yyyymm,
                "ret_excess": np.random.randn() * 0.05,
                "mktcap_lag": np.exp(np.random.randn() * 2),
            }
            for j, c in enumerate(macro_cols):
                row[c] = macro_vals[j]
            for c in char_cols:
                row[c] = np.clip(np.random.randn(), -1, 1)
            for c in sic_cols:
                row[c] = 1 if np.random.rand() < 0.2 else 0
            rows.append(row)
        df = pd.DataFrame(rows)
        out = DATA1 / f"{yyyymm}.parquet"
        df.to_parquet(out, index=False)
        if yyyymm % 12 == 1:
            print(f"Wrote {out} shape {df.shape}")

    print("Done. Run: python scripts/run_offline_pipeline.py")


if __name__ == "__main__":
    main()
