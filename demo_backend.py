"""
Demo Backend Server for DBMS Project
This is a standalone Flask server that mimics the API endpoints
for testing the REST data source functionality.
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime, timezone
import random
import sqlite3

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DB_PATH = os.path.join(BASE_DIR, "auto_index.db")
LOG_FILE = os.path.join(BASE_DIR, "query_log.txt")

def read_json(filename, default):
    """Read JSON file from data directory"""
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

@app.route('/', methods=['GET'])
def root():
    """Root endpoint - API information"""
    return jsonify({
        "message": "Demo Backend API Server",
        "status": "running",
        "endpoints": {
            "/health": "Health check",
            "/metrics": "Real-time metrics",
            "/queries": "Query logs (supports ?page=1&pageSize=20&search=)",
            "/statistics": "Query statistics",
            "/benchmarks": "Performance benchmarks"
        },
        "usage": "Configure your main app to use this backend by setting Data Source to 'REST' and Backend URL to 'http://localhost:5001'"
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Demo backend is running"})

@app.route('/metrics', methods=['GET'])
def get_metrics():
    """Get real-time metrics"""
    data = read_json('metrics.json', {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "series": {
            "labels": [],
            "qps": [],
            "latencyMs": [],
            "cpu": [],
            "memory": [],
            "storageGb": []
        }
    })
    return jsonify(data)

@app.route('/queries', methods=['GET'])
def get_queries():
    """Get paginated queries from log file"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 20))
        search = request.args.get('search', '').lower().strip()
        
        items = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # Get last 20 lines
                for line in lines[-20:]:
                    parts = line.strip().split("|")
                    if len(parts) >= 2:
                        timestamp = parts[0].strip()
                        sql = parts[1].strip()
                        
                        # Apply search filter
                        if search and search not in sql.lower():
                            continue
                        
                        # Extract query type
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
                        
                        items.append({
                            "timestamp": timestamp,
                            "latencyMs": round(max(5, random.gauss(20, 6)), 2),
                            "database": "app",
                            "sql": sql,
                            "type": qtype,
                            "table": "customers" if "customers" in sql.lower() else "orders"
                        })
        
        # Reverse to show newest first
        items.reverse()
        
        # Pagination
        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        
        return jsonify({
            "items": items[start:end],
            "total": total,
            "page": page,
            "pageSize": page_size
        })
    except Exception as e:
        return jsonify({"items": [], "total": 0, "page": 1, "pageSize": 20})

@app.route('/statistics', methods=['GET'])
def get_statistics():
    """Get query statistics"""
    try:
        # Get column frequency from database
        column_frequency = []
        total_freq = 0
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5.0)
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT table_name, column_name, frequency
                    FROM attribute_frequency
                    ORDER BY frequency DESC
                """)
                rows = cur.fetchall()
                for table_name, column_name, frequency in rows:
                    column_frequency.append({
                        "table": table_name,
                        "column": column_name,
                        "frequency": frequency
                    })
                    total_freq += frequency
            except:
                pass
            finally:
                conn.close()
        
        # Calculate percentages
        for item in column_frequency:
            item["percent"] = round((item["frequency"] / total_freq * 100), 2) if total_freq > 0 else 0
        
        # Get current indexes
        current_indexes = []
        if os.path.exists(DB_PATH):
            conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5.0)
            cur = conn.cursor()
            try:
                cur.execute("""
                    SELECT name, tbl_name, sql
                    FROM sqlite_master
                    WHERE type='index' AND name NOT LIKE 'sqlite_%'
                """)
                for name, tbl_name, sql in cur.fetchall():
                    current_indexes.append({
                        "name": name,
                        "table": tbl_name,
                        "sql": sql
                    })
            except:
                pass
            finally:
                conn.close()
        
        # Read queries from log file for query type and table usage
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
                        
                        # Query type
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
                        
                        # Table usage
                        if "customers" in sql.lower():
                            table_usage["customers"] = table_usage.get("customers", 0) + 1
                        elif "orders" in sql.lower():
                            table_usage["orders"] = table_usage.get("orders", 0) + 1
        
        return jsonify({
            "query_types": query_types,
            "table_usage": table_usage,
            "column_frequency": column_frequency,
            "current_indexes": current_indexes,
            "total_queries": sum(query_types.values())
        })
    except Exception as e:
        return jsonify({
            "query_types": {},
            "table_usage": {},
            "column_frequency": [],
            "current_indexes": [],
            "total_queries": 0
        })

@app.route('/benchmarks', methods=['GET'])
def get_benchmarks():
    """Get performance benchmarks (for compatibility)"""
    data = read_json('benchmarks.json', {
        "baseline": {"latencyMs": []},
        "optimized": {"latencyMs": []}
    })
    return jsonify(data)

if __name__ == '__main__':
    print("=" * 60)
    print("Demo Backend Server Starting...")
    print("=" * 60)
    print(f"Server will run on: http://localhost:5001")
    print(f"API Endpoints available:")
    print(f"  - GET /health - Health check")
    print(f"  - GET /metrics - Real-time metrics")
    print(f"  - GET /queries - Query logs")
    print(f"  - GET /statistics - Query statistics")
    print(f"  - GET /benchmarks - Performance benchmarks")
    print("=" * 60)
    print("\nTo use this backend:")
    print("1. Go to Settings page in the main app")
    print("2. Change Data Source to 'REST'")
    print("3. Set Backend Base URL to: http://localhost:5001")
    print("4. Save settings")
    print("=" * 60)
    
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=True)

