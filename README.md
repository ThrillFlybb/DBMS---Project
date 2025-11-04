# Automated Index Optimization – Frontend (Flask + Chart.js)

This is the Python/Flask dashboard for the Automated Index Optimization System. It provides a query log viewer, statistics, a performance comparison module, and a settings page.

## Prerequisites
- Python 3.9+

## Setup (Windows PowerShell)
```bash
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Or use the script (recommended):
```powershell
scripts\start.ps1
```

Then open `http://localhost:5000`.

## Structure
- `app.py`: Flask app and API endpoints
- `templates/`: HTML templates (queries, statistics, performance, settings)
- `static/js/app.js`: Frontend logic, Chart.js rendering, UI handlers
- `static/css/styles.css`: Minimal styles
- `data/`: Sample JSON data used by the app

## Notes
- By default the app reads JSON from `data/`. The C++ engine should overwrite these files or serve equivalent REST endpoints in future versions.
- Auto-refresh interval is controlled via the Settings page.
- To run with a production-style server locally, use the script above (Waitress).


