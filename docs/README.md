# ERIS Dashboard

## Viewing the dashboard

**The dashboard must be served over HTTP.** Opening `index.html` directly (double‑click or `file://`) will not load the JSON data because browsers block local file requests.

### Option 1: Use the server script

```bash
# Windows
serve.bat

# Or from dashboard folder:
python -m http.server 8080
```

Then open **http://localhost:8080** in your browser.

### Option 2: VS Code Live Server

Right‑click `index.html` → "Open with Live Server".

---

## Before viewing

1. Run the pipeline: `python scripts/run_offline_pipeline.py`
2. Export data: `python scripts/export_dashboard_data.py`

Data files are written to `dashboard/data/*.json`.
