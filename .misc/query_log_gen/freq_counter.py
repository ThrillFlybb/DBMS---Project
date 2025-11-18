import re
import time
import os
import sqlite3
from collections import Counter

LOG_FILE = "query_log.txt"
STATUS_FILE = "generator_status.txt"
DB_PATH = "auto_index.db"
REFRESH_INTERVAL = 2
GENERATOR_TIMEOUT = 10
CHECK_INTERVAL = 1.0

# Regex patterns for columns and table extraction
COLUMN_PATTERNS = [
    r"SELECT\s+(.*?)\s+FROM",
    r"WHERE\s+(.*?)\s*(?:GROUP|ORDER|LIMIT|;|$)",
    r"ORDER\s+BY\s+(.*?)\s*(?:LIMIT|;|$)",
    r"GROUP\s+BY\s+(.*?)\s*(?:ORDER|;|$)",
    r"SET\s+(.*?)\s*(?:WHERE|;|$)",
    r"INSERT\s+INTO\s+\w+\s*\((.*?)\)"
]

TABLE_PATTERN = r"(?:FROM|INTO|UPDATE|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)"

# --- Extract column names ---
def extract_columns(sql):
    cols = []
    sql_upper = sql.upper()
    for pattern in COLUMN_PATTERNS:
        matches = re.findall(pattern, sql_upper, re.IGNORECASE)
        for match in matches:
            for col in re.split(r"[,\s=]+", match):
                col = col.strip().replace("(", "").replace(")", "")
                if col and re.match(r"^[A-Z_][A-Z0-9_]*$", col) and col.upper() not in {
                    "SELECT", "FROM", "WHERE", "AND", "OR", "AS", "ON", "IN",
                    "VALUES", "SET", "BY", "GROUP", "ORDER"
                }:
                    cols.append(col.lower())
    return cols

# --- Extract table name ---
def extract_table(sql):
    match = re.search(TABLE_PATTERN, sql, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return "unknown"

# --- Check if generator is still alive ---
def is_generator_alive():
    if not os.path.exists(STATUS_FILE):
        return False
    try:
        content = open(STATUS_FILE).read().strip()
        if content == "STOP":
            return False
        last_heartbeat = float(content)
        return (time.time() - last_heartbeat) <= GENERATOR_TIMEOUT
    except Exception:
        return True

# --- Follow log file ---
def follow_log(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        f.seek(0, 0)
        while True:
            if not is_generator_alive():
                time.sleep(CHECK_INTERVAL)
                if not is_generator_alive():
                    break

            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue
            yield line

# --- Initialize or reset the frequency table ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attribute_frequency (
            table_name TEXT,
            column_name TEXT,
            frequency INTEGER
        )
    """)
    conn.commit()
    conn.close()

# --- Save frequency data into SQLite ---
def save_frequencies_to_db(counter):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # clear old entries before inserting new ones
    cur.execute("DELETE FROM attribute_frequency")

    # Insert updated frequencies
    for key, freq in counter.items():
        table_name, column_name = key.split(".")
        cur.execute("""
            INSERT INTO attribute_frequency (table_name, column_name, frequency)
            VALUES (?, ?, ?)
        """, (table_name, column_name, freq))

    conn.commit()
    conn.close()

# --- Live Analyzer ---
def live_analyzer():
    counter = Counter()
    last_refresh = 0

    print("Frequency counter started. Data will be stored in 'attribute_frequency' table.\n")
    init_db()

    for line in follow_log(LOG_FILE):
        parts = line.split("|")
        if len(parts) < 3:
            continue

        sql_part = parts[1].strip()
        table_name = extract_table(sql_part)
        cols = extract_columns(sql_part)

        for col in cols:
            counter[f"{table_name}.{col}"] += 1

        # Refresh display and update DB
        if time.time() - last_refresh >= REFRESH_INTERVAL:
            os.system("cls" if os.name == "nt" else "clear")
            print("Attribute Usage Frequency (auto-updating in database)\n")

            # Print to terminal
            for key, count in sorted(counter.items(), key=lambda x: x[1], reverse=True):
                t, c = key.split(".")
                print(f"{t:<12} | {c:<15} -> {count} times")

            # Save to database
            save_frequencies_to_db(counter)
            last_refresh = time.time()

    print("\nGenerator stopped. Saving final data to database...\n")
    save_frequencies_to_db(counter)
    print("Counter terminated.\n")

# --- Entry Point ---
if __name__ == "__main__":
    if not os.path.exists(LOG_FILE):
        print("Log file not found. Run the query generator first.")
    else:
        live_analyzer()
