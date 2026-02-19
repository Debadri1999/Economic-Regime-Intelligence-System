#!/usr/bin/env bash
# Run course ML pipeline then export dashboard data. From project root.
set -e
echo "Running course pipeline..."
python scripts/run_offline_pipeline.py
echo "Exporting dashboard data..."
python scripts/export_dashboard_data.py
echo "Done. Open dashboard/index.html or run: streamlit run app.py → Course ML"
