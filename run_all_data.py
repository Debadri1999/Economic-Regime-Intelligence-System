"""
Run all data pipelines to fill the ERIS dashboard.
Execute from project root:  python run_all_data.py

Order: schema -> collectors (news, fed, market, [kaggle]) -> preprocess -> Phase 2+3 (sentiment + regime).
Optional: run topic engine afterward for Topics page labels.
"""

import os
import sys
import subprocess

# Run from project root (directory containing this script)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def run(cmd: list) -> bool:
    print("  Running:", " ".join(cmd))
    r = subprocess.run([sys.executable, "-m", cmd[0]] + cmd[1:], cwd=PROJECT_ROOT)
    ok = r.returncode == 0
    if not ok:
        print("  -> Non-zero exit:", r.returncode)
    return ok

def main():
    print("ERIS — Populating all data for the dashboard\n")
    from data.storage.db_manager import ensure_schema
    ensure_schema()
    print("  Schema ensured.\n")

    print("Phase 1: Collectors")
    run(["data.collectors.news_collector"])
    run(["data.collectors.fed_scraper"])
    run(["data.collectors.market_collector"])
    if run(["data.collectors.kaggle_collector"]) is False:
        print("  (Kaggle optional; ensure KAGGLE_USERNAME/KAGGLE_KEY in .env if needed)\n")

    print("Phase 1: Preprocessing")
    run(["data.preprocessing.preprocess"])

    print("Phase 2 + 3: Sentiment (FinBERT) and Regime (HMM)")
    r = subprocess.run([sys.executable, "run_phase2_and_3.py"], cwd=PROJECT_ROOT)
    if r.returncode != 0:
        print("  Phase 2/3 had errors; check output above.\n")

    print("\nDone. Optional: run topic labels for the Topics page:")
    print("  python -m models.topic_engine")
    print("\nStart dashboard:  python -m streamlit run app.py")

if __name__ == "__main__":
    main()
