import os
import json
from datetime import datetime, timezone

try:
    import psutil  # optional, for realistic cpu/memory
except Exception:
    psutil = None


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
QUERY_LOG_DIR = BASE_DIR

DB_PATH = os.path.join(QUERY_LOG_DIR, "auto_index.db")
LOG_FILE = os.path.join(QUERY_LOG_DIR, "query_log.txt")
STATUS_FILE = os.path.join(QUERY_LOG_DIR, "generator_status.txt")


def read_json(filename, default):
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def write_json(filename, payload):
    path = os.path.join(DATA_DIR, filename)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
