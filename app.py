from flask import Flask, render_template, jsonify, request, redirect
from datetime import datetime, timezone
import os
import random
import sqlite3
import time
import traceback
import requests

from backend.config import read_json, write_json, DB_PATH, LOG_FILE
from backend.query_generator import extract_table
from backend.simulator import (
    start_simulator_thread,
    start_index_manager_thread,
    start_focus_rotation_thread,
)

app = Flask(__name__)


@app.route('/')
def index():
    return redirect('/dashboard')


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@app.route('/queries')
def queries_page():
    return render_template('queries.html')


@app.route('/settings')
def settings_page():
    settings = read_json(
        'settings.json',
        {
            "db": {"host": "localhost", "port": 5432, "user": "admin", "database": "app"},
            "refreshIntervalMs": 5000,
            "dataSource": "json",
        },
    )
    return render_template('settings.html', settings=settings)


@app.route('/statistics')
def statistics_page():
    return render_template('statistics.html')


# ------------------------ API ENDPOINTS ------------------------


@app.route('/api/metrics')
def api_metrics():
    settings = read_json(
        'settings.json',
        {"dataSource": "json", "backendBaseUrl": ""},
    )
    if settings.get('dataSource') == 'rest' and settings.get('backendBaseUrl'):
        try:
            res = requests.get(
                settings['backendBaseUrl'].rstrip('/') + '/metrics',
                timeout=3,
            )
            return jsonify(res.json())
        except Exception:
            pass

    data = read_json(
        'metrics.json',
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "series": {
                "labels": [],
                "qps": [],
                "latencyMs": [],
                "cpu": [],
                "memory": [],
                "storageGb": [],
            },
        },
    )
    return jsonify(data)


@app.route('/api/queries')
def api_queries():
    """Read queries from query_log.txt (last 20) or REST backend"""
    settings = read_json(
        'settings.json',
        {"dataSource": "json", "backendBaseUrl": ""},
    )
    if settings.get('dataSource') == 'rest' and settings.get('backendBaseUrl'):
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('pageSize', 20))
            search = request.args.get('search', '').strip()
            url = (
                f"{settings['backendBaseUrl'].rstrip('/')}"
                f"/queries?page={page}&pageSize={page_size}&search={search}"
            )
            res = requests.get(url, timeout=3)
            return jsonify(res.json())
        except Exception:
            pass

    try:
        items = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    parts = line.strip().split("|")
                    if len(parts) >= 2:
                        timestamp = parts[0].strip()
                        sql = parts[1].strip()
                        params = parts[2].strip() if len(parts) > 2 else ""

                        sql_upper = sql.upper()
                        if sql_upper.startswith("SELECT"):
                            qtype = "SELECT"
                        elif sql_upper.startswith("INSERT"):
                            qtype = "INSERT"
                        elif sql_upper.startswith("UPDATE"):
                            qtype = "UPDATE"
                        elif sql_upper.startswith("DELETE"):
                            qtype = "DELETE"
                        else:
                            qtype = "UNKNOWN"

                        table = extract_table(sql)

                        items.append(
                            {
                                "timestamp": timestamp,
                                "latencyMs": round(max(5, random.gauss(20, 6)), 2),
                                "database": "app",
                                "sql": sql,
                                "type": qtype,
                                "table": table,
                            }
                        )

        # newest first
        items.reverse()

        # search
        search = request.args.get('search', '').lower().strip()
        if search:
            items = [q for q in items if search in q.get('sql', '').lower()]

        # pagination
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 20))
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size

        return jsonify(
            {"items": items[start:end], "total": total, "page": page, "pageSize": page_size}
        )
    except Exception:
        return jsonify({"items": [], "total": 0, "page": 1, "pageSize": 20})


@app.route('/api/statistics')
def api_statistics():
    """Generate query statistics including column frequency"""

    settings = read_json(
        'settings.json',
        {"dataSource": "json", "backendBaseUrl": ""},
    )
    if settings.get('dataSource') == 'rest' and settings.get('backendBaseUrl'):
        try:
            res = requests.get(
                settings['backendBaseUrl'].rstrip('/') + '/statistics',
                timeout=3,
            )
            return jsonify(res.json())
        except Exception:
            pass

    try:
        column_frequency = []
        total_freq = 0

        if os.path.exists(DB_PATH):
            max_retries = 3
            retry_delay = 0.1
            for attempt in range(max_retries):
                try:
                    conn = sqlite3.connect(
                        DB_PATH,
                        check_same_thread=False,
                        timeout=5.0,
                    )
                    cur = conn.cursor()
                    cur.execute(
                        """
                        SELECT table_name, column_name, frequency
                        FROM attribute_frequency
                        ORDER BY frequency DESC
                        """
                    )
                    rows = cur.fetchall()
                    for table_name, column_name, frequency in rows:
                        column_frequency.append(
                            {
                                "table": table_name,
                                "column": column_name,
                                "frequency": frequency,
                            }
                        )
                        total_freq += frequency
                    conn.close()
                    break
                except sqlite3.OperationalError as e:
                    if "locked" in str(e).lower() and attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        break
                except Exception:
                    break

        for item in column_frequency:
            item["percent"] = (
                round((item["frequency"] / total_freq * 100), 2)
                if total_freq > 0
                else 0
            )

        current_indexes = []
        if os.path.exists(DB_PATH):
            max_retries = 3
            retry_delay = 0.1
            for attempt in range(max_retries):
                try:
                    conn = sqlite3.connect(
                        DB_PATH,
                        check_same_thread=False,
                        timeout=5.0,
                    )
                    cur = conn.cursor()
                    cur.execute(
                        """
                        SELECT name, tbl_name, sql
                        FROM sqlite_master
                        WHERE type='index' AND name NOT LIKE 'sqlite_%'
                        """
                    )
                    for name, tbl_name, sql in cur.fetchall():
                        current_indexes.append(
                            {"name": name, "table": tbl_name, "sql": sql}
                        )
                    conn.close()
                    break
                except sqlite3.OperationalError as e:
                    if "locked" in str(e).lower() and attempt < max_retries - 1:
                        time.sleep(retry_delay * (attempt + 1))
                        continue
                    else:
                        break
                except Exception:
                    break

        query_types = {}
        table_usage = {}
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in lines:
                    parts = line.strip().split("|")
                    if len(parts) >= 2:
                        sql = parts[1].strip()
                        sql_upper = sql.upper()

                        if sql_upper.startswith("SELECT"):
                            qtype = "SELECT"
                        elif sql_upper.startswith("INSERT"):
                            qtype = "INSERT"
                        elif sql_upper.startswith("UPDATE"):
                            qtype = "UPDATE"
                        elif sql_upper.startswith("DELETE"):
                            qtype = "DELETE"
                        else:
                            qtype = "UNKNOWN"
                        query_types[qtype] = query_types.get(qtype, 0) + 1

                        table = extract_table(sql)
                        table_usage[table] = table_usage.get(table, 0) + 1

        return jsonify(
            {
                "query_types": query_types,
                "table_usage": table_usage,
                "column_frequency": column_frequency,
                "current_indexes": current_indexes,
                "total_queries": sum(query_types.values()),
            }
        )
    except Exception as e:
        error_msg = str(e)
        print(f"Error in api_statistics: {error_msg}")
        print(traceback.format_exc())
        return jsonify(
            {
                "query_types": {},
                "table_usage": {},
                "column_frequency": [],
                "current_indexes": [],
                "total_queries": 0,
                "error": error_msg,
            }
        )


@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if request.method == 'GET':
        settings = read_json(
            'settings.json',
            {
                "db": {
                    "host": "localhost",
                    "port": 5432,
                    "user": "admin",
                    "database": "app",
                },
                "refreshIntervalMs": 5000,
                "dataSource": "json",
            },
        )
        return jsonify(settings)
    else:
        payload = request.get_json(silent=True) or {}
        write_json('settings.json', payload)
        return jsonify({"ok": True})


if __name__ == '__main__':
    # Start background threads
    start_simulator_thread()          # ~1000 ticks/sec target
    start_index_manager_thread()
    start_focus_rotation_thread()

    port = int(os.environ.get('PORT', 5000))
    use_waitress = os.environ.get('USE_WAITRESS', '0') == '1'
    if use_waitress:
        from waitress import serve
        serve(app, host='0.0.0.0', port=port)
    else:
        app.run(host='0.0.0.0', port=port, debug=True)
